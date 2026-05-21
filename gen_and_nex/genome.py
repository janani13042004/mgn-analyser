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
        self.trimmed_forward_files = []
        self.trimmed_reverse_files = []
        self.sam_files = []
        self.bam_files = []
        self.fastqc_dir = ""
        self.trimmed_dir = ""
        self.trimmed_fastqc_dir = ""
        self.assembly_dir = ""
        self.sam_dir = ""
        self.freebayes_dir = ""
        self.freebayes_output = ""
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

        # Check if customized parameters are enabled
        if self.customized_params:
            leading_value = self.customized_params.get("LEADING", "30")
            trailing_value = self.customized_params.get("TRAILING", "30")
            minlen_value = self.customized_params.get("MINLEN", "36")
            headcrop_value = self.customized_params.get("HEADCROP", "15")
        else:
            leading_value = "30"
            trailing_value = "30"
            minlen_value = "36"
            headcrop_value = "15"

        # Make directories
        fastqc_dir = f"{self.output_folder}/fastqc_output"
        trimmed_dir = f"{self.output_folder}/Trimmed_output"
        trimmed_fastqc_dir = f"{self.output_folder}/Trimmed_fastqc_output"
        assembly_dir = f"{self.output_folder}/bwa_assembly"
        sam_dir = f"{self.output_folder}/sam_output"
        freebayes_dir = f"{self.output_folder}/freebayes_output"

        # Create directories if they don't exist
        for dir in [fastqc_dir, trimmed_dir, trimmed_fastqc_dir, assembly_dir, sam_dir, freebayes_dir]:
            if not os.path.exists(dir):
                os.mkdir(dir)

        # Running FastQC
        self.update_progress.emit("FastQC is running.")
        fastqc_cmd = f"conda run -n fastqc_env fastqc -o {fastqc_dir} {' '.join(self.forward_files)} {' '.join(self.reverse_files)}"
        process = subprocess.Popen(fastqc_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            self.error_msg = "FastQC command failed. Please check your inputs and try again."
            self.finished.emit(False)
            return
        self.update_progress.emit("Quality Check is completed.")  # Updated message

        # Running Trimmomatic
        self.update_progress.emit("Trimmomatic is running.")
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

            self.trimmed_forward_files.append(paired_output_file)
            self.trimmed_reverse_files.append(paired_output2_file)

        self.update_progress.emit("Trimming is completed.")  # Updated message

        # Running FastQC for only the trimmed paired reads
        self.update_progress.emit("Running FastQC on trimmed reads.")
        fastqc_cmd = f"conda run -n fastqc_env fastqc -o {trimmed_fastqc_dir} {' '.join(self.trimmed_forward_files)} {' '.join(self.trimmed_reverse_files)}"
        process = subprocess.Popen(fastqc_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            self.error_msg = "FastQC command failed for trimmed reads. Please check your inputs and try again."
            self.finished.emit(False)
            return
        self.update_progress.emit("Quality Check for the trimmed reads is completed.")

        # Indexing the reference genome with BWA
        self.update_progress.emit("Indexing the reference genome with BWA.")
        index_cmd = f"bwa index -a is {self.reference_genome}"
        try:
            process = subprocess.Popen(index_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                raise Exception(stderr.decode())
            self.update_progress.emit("Reference genome indexing is completed.")
        except Exception as e:
            self.error_msg = f"Indexing reference genome failed: {str(e)}"
            self.finished.emit(False)
            return

        # Running BWA mapping
        self.update_progress.emit("BWA is running.")
        for forward_file, reverse_file in zip(self.trimmed_forward_files, self.trimmed_reverse_files):
            output_sam_path = os.path.join(assembly_dir, f"{os.path.basename(forward_file).split('_')[0]}.sam")
            cmd_alignment = f'bwa mem -t 24 {self.reference_genome} {forward_file} {reverse_file} > {output_sam_path}'
            subprocess.run(cmd_alignment, shell=True)

            report_file_path = os.path.join(sam_dir, f"{os.path.basename(forward_file)}_alignment_report.txt")
            cmd_alignment_report = f'bwa mem -t 24 {self.reference_genome} {forward_file} {reverse_file} 2> {report_file_path}'
            subprocess.run(cmd_alignment_report, shell=True)

            self.sam_files.append(output_sam_path)

        self.update_progress.emit("BWA Assembly is completed.")  # Updated message

         # Running SAMtools view
        self.update_progress.emit("Converting SAM to BAM.")
        for sam_file in self.sam_files:
            output_bam_file = os.path.join(self.sam_dir, os.path.basename(sam_file).replace('.sam', '.bam'))

            # Check if the input SAM file exists
            if not os.path.exists(sam_file):
                self.error_msg = f"File {sam_file} does not exist."
                print(self.error_msg)
                self.finished(False)
                return

            # SAMtools view command to convert SAM to BAM
            samtools_view_cmd = f"conda run -n samtools_env samtools view -Sb {sam_file} > {output_bam_file}"

            process = subprocess.Popen(samtools_view_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()

            # Print standard output and error for debugging
            print(f"SAMtools view stdout: {stdout.decode()}")
            print(f"SAMtools view stderr: {stderr.decode()}")

            if process.returncode != 0:
                self.error_msg = f"SAMtools view command failed for {sam_file}. Error: {stderr.decode()}"
                print(self.error_msg)
                self.finished(False)
                return

            self.bam_files.append(output_bam_file)

        self.update_progress.emit("SAM to BAM conversion completed.")

        # Running SAMtools rmdup
        self.update_progress.emit("Running SAMtools rmdup.")
        for bam_file in self.bam_files:
            dedup_bam_file = bam_file.replace('.bam', '_dedup.bam')

            # SAMtools rmdup command
            samtools_rmdup_cmd = f"conda run -n samtools_env samtools rmdup {bam_file} {dedup_bam_file}"

            process = subprocess.Popen(samtools_rmdup_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()

            # Print standard output and error for debugging
            print(f"SAMtools rmdup stdout: {stdout.decode()}")
            print(f"SAMtools rmdup stderr: {stderr.decode()}")

            if process.returncode != 0:
                self.error_msg = f"SAMtools rmdup command failed for {bam_file}. Error: {stderr.decode()}"
                print(self.error_msg)
                self.finished(False)
                return

            # Update the bam_files list with deduped files
            self.bam_files.append(dedup_bam_file)

        self.update_progress.emit("SAMtools rmdup is completed.")

        # Indexing the reference FASTA
        self.update_progress.emit("Indexing the reference FASTA file.")
        samtools_faidx_cmd = f"conda run -n samtools_env samtools faidx {self.reference_genome}"
        print(f"Running SAMtools faidx command: {samtools_faidx_cmd}")
        try:
            process = subprocess.Popen(samtools_faidx_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            print(f"SAMtools faidx stdout: {stdout.decode()}")
            print(f"SAMtools faidx stderr: {stderr.decode()}")
            if process.returncode != 0:
                raise Exception(stderr.decode())
            self.update_progress.emit("Reference FASTA indexing is completed.")
        except Exception as e:
            self.error_msg = f"Indexing reference FASTA failed: {str(e)}"
            self.finished.emit(False)
            return

        # Running Freebayes variant calling
        self.update_progress.emit("Freebayes variant calling is running.")
        self.freebayes_output = os.path.join(freebayes_dir, "variants.vcf")
        freebayes_cmd = f"conda run -n freebayes_env freebayes -f {self.reference_genome} {' '.join(self.bam_files)} -v {self.freebayes_output}"
        process = subprocess.Popen(freebayes_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            self.error_msg = f"Freebayes command failed. Error: {stderr.decode()}"
            self.finished.emit(False)
            return

        self.update_progress.emit("Freebayes variant calling is completed.")  # Updated message

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

        forward_add_button = QPushButton('Add', self)
        forward_add_button.clicked.connect(self.add_forward_files)
        forward_button_layout.addWidget(forward_add_button)

        forward_delete_button = QPushButton('Delete', self)
        forward_delete_button.clicked.connect(self.delete_forward_file)
        forward_button_layout.addWidget(forward_delete_button)

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

        reverse_add_button = QPushButton('Add', self)
        reverse_add_button.clicked.connect(self.add_reverse_files)
        reverse_button_layout.addWidget(reverse_add_button)

        reverse_delete_button = QPushButton('Delete', self)
        reverse_delete_button.clicked.connect(self.delete_reverse_file)
        reverse_button_layout.addWidget(reverse_delete_button)

        reverse_clear_button = QPushButton('Clear', self)
        reverse_clear_button.clicked.connect(self.clear_reverse_files)
        reverse_button_layout.addWidget(reverse_clear_button)

        reverse_layout.addLayout(reverse_button_layout)
        scroll_layout.addLayout(reverse_layout)

        # Adapter file selection
        adapter_layout = QHBoxLayout()
        adapter_layout.addWidget(QLabel('Select Adapter File:'))
        self.adapter_path = QLineEdit()
        adapter_layout.addWidget(self.adapter_path)
        adapter_button = QPushButton('Browse', self)
        adapter_button.clicked.connect(self.select_adapter_file)
        adapter_layout.addWidget(adapter_button)
        scroll_layout.addLayout(adapter_layout)

        # Output folder selection
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel('Select Output Folder:'))
        self.output_path = QLineEdit()
        output_layout.addWidget(self.output_path)
        output_button = QPushButton('Browse', self)
        output_button.clicked.connect(self.select_output_folder)
        output_layout.addWidget(output_button)
        scroll_layout.addLayout(output_layout)

        # Customized parameters
        self.customized_checkbox = QCheckBox("Enable Customized Parameters")
        scroll_layout.addWidget(self.customized_checkbox)

        # Reference genome selection
        reference_layout = QHBoxLayout()
        reference_layout.addWidget(QLabel('Select Reference Genome:'))
        self.reference_genome_path = QLineEdit()
        reference_layout.addWidget(self.reference_genome_path)
        reference_button = QPushButton('Browse', self)
        reference_button.clicked.connect(self.select_reference_genome)
        reference_layout.addWidget(reference_button)
        scroll_layout.addLayout(reference_layout)

        # Start pipeline button
        self.start_button = QPushButton('Start Pipeline', self)
        self.start_button.clicked.connect(self.start_pipeline)
        scroll_layout.addWidget(self.start_button)

        # Progress and status
        self.progress_label = QLabel("")
        scroll_layout.addWidget(self.progress_label)

        self.setLayout(main_layout)

    def select_forward_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Forward Files", "", "FASTQ Files (*.fastq *.fq *.fastq.gz *.fq.gz)")
        if files:
            self.forward_files = files
            self.forward_paths.setPlainText("\n".join(self.forward_files))

    def add_forward_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Forward Files", "", "FASTQ Files (*.fastq *.fq *.fastq.gz *.fq.gz)")
        if files:
            self.forward_files.extend(files)
            self.forward_paths.setPlainText("\n".join(self.forward_files))

    def delete_forward_file(self):
        file, ok = QInputDialog.getItem(self, "Delete Forward File", "Select file to delete:", self.forward_files, 0, False)
        if ok and file:
            self.forward_files.remove(file)
            self.forward_paths.setPlainText("\n".join(self.forward_files))

    def clear_forward_files(self):
        self.forward_files.clear()
        self.forward_paths.clear()

    def select_reverse_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Reverse Files", "", "FASTQ Files (*.fastq *.fq *.fastq.gz *.fq.gz)")
        if files:
            self.reverse_files = files
            self.reverse_paths.setPlainText("\n".join(self.reverse_files))

    def add_reverse_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Reverse Files", "", "FASTQ Files (*.fastq *.fq *.fastq.gz *.fq.gz)")
        if files:
            self.reverse_files.extend(files)
            self.reverse_paths.setPlainText("\n".join(self.reverse_files))

    def delete_reverse_file(self):
        file, ok = QInputDialog.getItem(self, "Delete Reverse File", "Select file to delete:", self.reverse_files, 0, False)
        if ok and file:
            self.reverse_files.remove(file)
            self.reverse_paths.setPlainText("\n".join(self.reverse_files))

    def clear_reverse_files(self):
        self.reverse_files.clear()
        self.reverse_paths.clear()

    def select_adapter_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select Adapter File", "", "FASTA Files (*.fa *.fasta)")
        if file:
            self.adapter_file = file
            self.adapter_path.setText(self.adapter_file)

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_folder = folder
            self.output_path.setText(self.output_folder)

    def select_reference_genome(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select Reference Genome", "", "FASTA Files (*.fa *.fasta)")
        if file:
            self.reference_genome = file
            self.reference_genome_path.setText(self.reference_genome)

    def start_pipeline(self):
        if not self.forward_files or not self.reverse_files or not self.output_folder or not self.adapter_file or not self.reference_genome:
            QMessageBox.warning(self, "Missing Information", "Please ensure all fields are filled out before starting the pipeline.")
            return

        self.customized_params = self.customized_checkbox.isChecked()
        self.worker = GenomicsPipelineWorker(self.forward_files, self.reverse_files, self.output_folder, self.adapter_file, self.customized_params, self.reference_genome)
        self.worker.finished.connect(self.pipeline_finished)
        self.worker.error.connect(self.show_error)
        self.worker.update_progress.connect(self.update_progress)
        self.worker.start()

    # Show progress message box
        self.progress_msg = QMessageBox(QMessageBox.Information, "Processing", "please wait until the process finishes, It will take some time to complete...", QMessageBox.Cancel, self)
        self.progress_msg.setWindowModality(Qt.WindowModal)
        self.progress_msg.button(QMessageBox.Cancel).clicked.connect(self.worker.cancel)
        self.progress_msg.show()
        self.worker.update_progress.connect(self.update_progress_msg)

        self.start_time = time.time()  # Start time


    def update_progress(self, message):
        self.progress_label.setText(message)

    def pipeline_finished(self, success):
        if success:
            QMessageBox.information(self, "Success", "Genomics pipeline finished successfully.")
        else:
            QMessageBox.critical(self, "Error", f"An error occurred during the genomics pipeline.\n{self.worker.error_msg}")

    def show_error(self, error_message):
        QMessageBox.critical(self, "Error", error_message)

    def update_progress_msg(self, message):
        current_text = self.progress_msg.text()
        if current_text.count("\n") > 10:  # Clear the box if there are more than 10 lines
            current_text = "\n".join(current_text.split("\n")[-5:])  # Keep the last 5 messages
        updated_text = current_text + "\n " + message
        self.progress_msg.setText(updated_text)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = GenomicsPipelineGUI()
    window.show()
    sys.exit(app.exec_())
