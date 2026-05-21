from PyQt5.QtWidgets import (QApplication, QWidget, QComboBox, QLabel, QPushButton,
                             QFileDialog, QHBoxLayout, QVBoxLayout, QLineEdit, QMessageBox,
                             QDialog, QTextEdit, QGridLayout, QCheckBox, QScrollArea, QFrame, QInputDialog)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import subprocess
import os
import sys
import time
import shutil


class GenomicsPipelineWorker(QThread):
    finished = pyqtSignal(bool)
    error = pyqtSignal(str)
    update_progress = pyqtSignal(str)

    def __init__(self, forward_files, reverse_files, output_folder, adapter_file, customized_params, reference_genome):
        super().__init__()
        self.forward_files = forward_files
        self.reverse_files = reverse_files
        self.output_folder = output_folder
        self.adapter_file = adapter_file
        self.customized_params = customized_params
        self.reference_genome = reference_genome
        self.cancelled = False
        self.error_msg = ""

    def cancel(self):
        self.cancelled = True

    def run(self):
        start_time = time.time()  # Start time

        # Quality Control with FastQC
        fastqc_dir = f"{self.output_folder}/fastqc_output"
        if not os.path.exists(fastqc_dir):
            os.makedirs(fastqc_dir)

        self.update_progress.emit("FastQC is running.")
        fastqc_cmd = f"conda run -n fastqc_env fastqc -o {fastqc_dir} {' '.join(self.forward_files)} {' '.join(self.reverse_files)}"
        process = subprocess.Popen(fastqc_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            self.error_msg = "FastQC command failed. Please check your inputs and try again."
            self.finished.emit(False)
            return
        self.update_progress.emit("FastQC completed.")

        # Trimming with Trimmomatic
        trimmed_dir = f"{self.output_folder}/trimmed_output"
        if not os.path.exists(trimmed_dir):
            os.makedirs(trimmed_dir)

        self.update_progress.emit("Trimmomatic is running.")
        trimmed_forward_files = []
        trimmed_reverse_files = []

        for i, (forward_file, reverse_file) in enumerate(zip(self.forward_files, self.reverse_files)):
            forward_base = os.path.basename(forward_file).split('.')[0]
            reverse_base = os.path.basename(reverse_file).split('.')[0]
            paired_output_file = os.path.join(trimmed_dir, f"{forward_base}_paired.fastq.gz")
            unpaired_output_file = os.path.join(trimmed_dir, f"{forward_base}_unpaired.fastq.gz")
            paired_output2_file = os.path.join(trimmed_dir, f"{reverse_base}_paired.fastq.gz")
            unpaired_output2_file = os.path.join(trimmed_dir, f"{reverse_base}_unpaired.fastq.gz")

            trimmomatic_cmd = [
                'conda', 'run', '-n', 'trimmomatic_env', 'trimmomatic', 'PE', '-phred33', '-threads', '16',
                forward_file, reverse_file,
                paired_output_file, unpaired_output_file, paired_output2_file, unpaired_output2_file,
                "ILLUMINACLIP:" + self.adapter_file + ":2:30:10", "LEADING:3",
                "TRAILING:3", "SLIDINGWINDOW:4:15", "MINLEN:36", "-summary", os.path.join(trimmed_dir, f"{forward_base}_{reverse_base}_report.txt")
            ]

            process = subprocess.Popen(trimmomatic_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                self.error_msg = f"Trimmomatic command failed for {forward_file} and {reverse_file}. Error: {stderr.decode()}"
                self.finished.emit(False)
                return
            
            trimmed_forward_files.append(paired_output_file)
            trimmed_reverse_files.append(paired_output2_file)
        self.update_progress.emit("Trimmomatic completed.")

        # Mapping with BWA
        bwa_output_dir = f"{self.output_folder}/bwa_output"
        if not os.path.exists(bwa_output_dir):
            os.makedirs(bwa_output_dir)

        self.update_progress.emit("BWA is running.")
        cmd_activate = 'conda run -n bwa_env'
        subprocess.run(cmd_activate, shell=True)

        cmd_build_index = f'bwa index {self.reference_genome}'
        subprocess.run(cmd_build_index, shell=True)

        sam_files = []

        for forward_file, reverse_file in zip(trimmed_forward_files, trimmed_reverse_files):
            output_sam_path = os.path.join(bwa_output_dir, f"{os.path.basename(forward_file).split('_')[0]}.sam")
            cmd_alignment = f'bwa mem -t 16 {self.reference_genome} {forward_file} {reverse_file} > {output_sam_path}'
            subprocess.run(cmd_alignment, shell=True)

            report_file_path = os.path.join(bwa_output_dir, f"{os.path.basename(forward_file)}_alignment_report.txt")
            cmd_alignment_report = f'bwa mem -t 16 {self.reference_genome} {forward_file} {reverse_file} 2> {report_file_path}'
            subprocess.run(cmd_alignment_report, shell=True)

            sam_files.append(output_sam_path)

        self.update_progress.emit("BWA mapping completed.")

        # Remove Duplicates with SAMtools
        samtools_dir = f"{self.output_folder}/samtools_output"
        if not os.path.exists(samtools_dir):
            os.makedirs(samtools_dir)

        self.update_progress.emit("SAMtools rmdup is running.")
        bam_files = []
        for sam_file in sam_files:
            output_bam_file = os.path.join(samtools_dir, os.path.basename(sam_file).replace('.sam', '_dedup.bam'))
            samtools_cmd = f"conda run -n samtools_env samtools rmdup {sam_file} {output_bam_file}"

            process = subprocess.Popen(samtools_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                self.error_msg = f"SAMtools rmdup command failed for {sam_file}. Error: {stderr.decode()}"
                self.finished.emit(False)
                return
            
            bam_files.append(output_bam_file)

        self.update_progress.emit("SAMtools rmdup completed.")

        # Variant Calling with Freebayes
        freebayes_output = f"{self.output_folder}/freebayes_output.vcf"
        self.update_progress.emit("Freebayes variant calling is running.")
        freebayes_cmd = f"conda run -n freebayes_env freebayes -f {self.reference_genome} " \
                        f"{' '.join(bam_files)} > {freebayes_output}"

        process = subprocess.Popen(freebayes_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            self.error_msg = "Freebayes command failed. Please check your inputs and try again."
            self.finished.emit(False)
            return
        self.update_progress.emit("Freebayes variant calling completed.")

        # SNP Finding in the background (if needed, additional analysis can be done here)

        elapsed_time = time.time() - start_time  # Elapsed time
        elapsed_time_str = time.strftime("%Hh %Mm %Ss", time.gmtime(elapsed_time))  # Format elapsed time

        if self.cancelled:
            self.finished.emit(False)
        else:
            self.finished.emit(True)
            QMessageBox.information(None, "Success", f"Genomics pipeline finished successfully.\nElapsed Time: {elapsed_time_str}")

    def show_message_box(self, title, message):
        msg_box = QMessageBox()
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.exec_()



class GenomicsPipelineGUI(QDialog):
    def __init__(self):
        super().__init__()

        self.forward_files = []
        self.reverse_files = []
        self.output_folder = ""
        self.adapter_file = ""
        self.customized_params = False
        self.reference_genome = ""

        self.initUI()

    def initUI(self):
        self.setWindowTitle('Genomics Pipeline')
        self.setFixedSize(800, 600)

        main_layout = QVBoxLayout(self)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

        # Forward files selection
        forward_layout = QVBoxLayout()
        forward_layout.addWidget(QLabel('Select Forward Files:'))

        self.forward_paths = QTextEdit()
        self.forward_paths.setReadOnly(True)
        forward_layout.addWidget(self.forward_paths)

        forward_button_layout = QHBoxLayout()
        forward_select_button = QPushButton('Select', self)
        forward_select_button.clicked.connect(self.select_forward_files)
        forward_button_layout.addWidget(forward_select_button)
        forward_clear_button = QPushButton('Clear', self)
        forward_clear_button.clicked.connect(self.clear_forward_files)
        forward_button_layout.addWidget(forward_clear_button)
        forward_layout.addLayout(forward_button_layout)

        scroll_layout.addLayout(forward_layout)

        # Reverse files selection
        reverse_layout = QVBoxLayout()
        reverse_layout.addWidget(QLabel('Select Reverse Files:'))

        self.reverse_paths = QTextEdit()
        self.reverse_paths.setReadOnly(True)
        reverse_layout.addWidget(self.reverse_paths)

        reverse_button_layout = QHBoxLayout()
        reverse_select_button = QPushButton('Select', self)
        reverse_select_button.clicked.connect(self.select_reverse_files)
        reverse_button_layout.addWidget(reverse_select_button)
        reverse_clear_button = QPushButton('Clear', self)
        reverse_clear_button.clicked.connect(self.clear_reverse_files)
        reverse_button_layout.addWidget(reverse_clear_button)
        reverse_layout.addLayout(reverse_button_layout)

        scroll_layout.addLayout(reverse_layout)

        # Output folder selection
        output_layout = QVBoxLayout()
        output_layout.addWidget(QLabel('Select Output Folder:'))

        self.output_folder_edit = QLineEdit()
        output_layout.addWidget(self.output_folder_edit)

        output_button = QPushButton('Browse', self)
        output_button.clicked.connect(self.select_output_folder)
        output_layout.addWidget(output_button)

        scroll_layout.addLayout(output_layout)

        # Adapter file selection
        adapter_layout = QVBoxLayout()
        adapter_layout.addWidget(QLabel('Select Adapter File:'))

        self.adapter_file_edit = QLineEdit()
        adapter_layout.addWidget(self.adapter_file_edit)

        adapter_button = QPushButton('Browse', self)
        adapter_button.clicked.connect(self.select_adapter_file)
        adapter_layout.addWidget(adapter_button)

        scroll_layout.addLayout(adapter_layout)

        # Reference genome selection
        reference_layout = QVBoxLayout()
        reference_layout.addWidget(QLabel('Select Reference Genome:'))

        self.reference_genome_edit = QLineEdit()
        reference_layout.addWidget(self.reference_genome_edit)

        reference_button = QPushButton('Browse', self)
        reference_button.clicked.connect(self.select_reference_genome)
        reference_layout.addWidget(reference_button)

        scroll_layout.addLayout(reference_layout)

        # Custom parameters checkbox
        self.custom_params_checkbox = QCheckBox('Customize Trimmomatic Parameters')
        scroll_layout.addWidget(self.custom_params_checkbox)

        # Start button
        start_button = QPushButton('Start', self)
        start_button.clicked.connect(self.start_pipeline)
        scroll_layout.addWidget(start_button)

        # Status output
        self.status_output = QTextEdit()
        self.status_output.setReadOnly(True)
        scroll_layout.addWidget(self.status_output)

    def select_forward_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, 'Select Forward Files', '', 'FASTQ Files (*.fastq *.fq *.fastq.gz *.fq.gz)')
        if files:
            self.forward_files = files
            self.forward_paths.setPlainText('\n'.join(files))

    def clear_forward_files(self):
        self.forward_files = []
        self.forward_paths.clear()

    def select_reverse_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, 'Select Reverse Files', '', 'FASTQ Files (*.fastq *.fq *.fastq.gz *.fq.gz)')
        if files:
            self.reverse_files = files
            self.reverse_paths.setPlainText('\n'.join(files))

    def clear_reverse_files(self):
        self.reverse_files = []
        self.reverse_paths.clear()

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Select Output Folder')
        if folder:
            self.output_folder = folder
            self.output_folder_edit.setText(folder)

    def select_adapter_file(self):
        file, _ = QFileDialog.getOpenFileName(self, 'Select Adapter File', '', 'FASTA Files (*.fasta *.fa)')
        if file:
            self.adapter_file = file
            self.adapter_file_edit.setText(file)

    def select_reference_genome(self):
        file, _ = QFileDialog.getOpenFileName(self, 'Select Reference Genome', '', 'FASTA Files (*.fasta *.fa)')
        if file:
            self.reference_genome = file
            self.reference_genome_edit.setText(file)

    def start_pipeline(self):
        if not self.forward_files or not self.reverse_files:
            QMessageBox.warning(self, 'Warning', 'Please select both forward and reverse files.')
            return
        if not self.output_folder:
            QMessageBox.warning(self, 'Warning', 'Please select an output folder.')
            return
        if not self.adapter_file:
            QMessageBox.warning(self, 'Warning', 'Please select an adapter file.')
            return
        if not self.reference_genome:
            QMessageBox.warning(self, 'Warning', 'Please select a reference genome.')
            return

        customized_params = self.custom_params_checkbox.isChecked()

        self.worker = GenomicsPipelineWorker(self.forward_files, self.reverse_files, self.output_folder, self.adapter_file, customized_params, self.reference_genome)
        self.worker.update_progress.connect(self.update_status)
        self.worker.finished.connect(self.on_pipeline_finished)
        self.worker.error.connect(self.on_pipeline_error)
        self.worker.start()

    def update_status(self, message):
        self.status_output.append(message)

    def on_pipeline_finished(self, success):
        if success:
            QMessageBox.information(self, 'Success', 'Genomics pipeline finished successfully.')
        else:
            QMessageBox.warning(self, 'Failure', 'Genomics pipeline failed.')

    def on_pipeline_error(self, error):
        QMessageBox.critical(self, 'Error', f'An error occurred: {error}')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = GenomicsPipelineGUI()
    gui.show()
    sys.exit(app.exec_())
