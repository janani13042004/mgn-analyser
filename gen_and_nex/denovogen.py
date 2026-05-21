from PyQt5.QtWidgets import (QApplication, QWidget, QComboBox, QLabel, QPushButton,
                             QFileDialog, QHBoxLayout, QVBoxLayout, QLineEdit, QMessageBox,
                             QDialog, QTextEdit, QGridLayout, QCheckBox, QScrollArea, QFrame, QInputDialog)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import subprocess
import os
import sys
import time


class GenomicsPipelineWorker(QThread):
    finished = pyqtSignal(bool)
    error = pyqtSignal(str)
    update_progress = pyqtSignal(str)

    def __init__(self, forward_files, reverse_files, output_folder, adapter_file, customized_params):
        super().__init__()
        self.trimmed_forward_files = []
        self.trimmed_reverse_files = []
        self.fastqc_dir = ""
        self.trimmed_dir = ""
        self.assembly_dir = ""
        self.forward_files = forward_files
        self.reverse_files = reverse_files
        self.output_folder = output_folder
        self.adapter_file = adapter_file
        self.customized_params = customized_params
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
        self.fastqc_dir = f"{self.output_folder}/fastqc_output"
        self.trimmed_dir = f"{self.output_folder}/Trimmed_output"
        self.assembly_dir = f"{self.output_folder}/spades_output"

        # Create directories if they don't exist
        for dir in [self.fastqc_dir, self.trimmed_dir, self.assembly_dir]:
            if not os.path.exists(dir):
                os.mkdir(dir)

        # Running FastQC
        self.update_progress.emit("Running FastQC.")
        fastqc_cmd = f"conda run -n fastqc_env fastqc -o {self.fastqc_dir} {' '.join(self.forward_files)} {' '.join(self.reverse_files)}"
        process = subprocess.Popen(fastqc_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            self.error_msg = "FastQC command failed. Please check your inputs and try again."
            self.finished.emit(False)
            return
        self.update_progress.emit("FastQC completed.")

        # Running Trimmomatic
        self.update_progress.emit("Running Trimmomatic.")
        for i, (forward_file, reverse_file) in enumerate(zip(self.forward_files, self.reverse_files)):
            forward_base = os.path.basename(forward_file).split('.')[0]
            reverse_base = os.path.basename(reverse_file).split('.')[0]
            paired_output_file = os.path.join(self.trimmed_dir, f"{forward_base}_paired.fastq.gz")
            unpaired_output_file = os.path.join(self.trimmed_dir, f"{forward_base}_unpaired.fastq.gz")
            paired_output2_file = os.path.join(self.trimmed_dir, f"{reverse_base}_paired.fastq.gz")
            unpaired_output2_file = os.path.join(self.trimmed_dir, f"{reverse_base}_unpaired.fastq.gz")

            trimmomatic_cmd = [
                'conda', 'run', '-n', 'trimmomatic_env', 'trimmomatic', 'PE', '-phred33', '-threads', '16',
                forward_file, reverse_file,
                paired_output_file, unpaired_output_file, paired_output2_file, unpaired_output2_file,
                "ILLUMINACLIP:" + self.adapter_file + ":2:30:10", "LEADING:3",
                "TRAILING:3", "SLIDINGWINDOW:4:15", "MINLEN:36", "-summary", os.path.join(self.trimmed_dir, f"{forward_base}_{reverse_base}_report.txt")
            ]

            process = subprocess.Popen(trimmomatic_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                self.error_msg = f"Trimmomatic command failed for {forward_file} and {reverse_file}. Error: {stderr.decode()}"
                self.finished.emit(False)
                return

            self.trimmed_forward_files.append(paired_output_file)
            self.trimmed_reverse_files.append(paired_output2_file)

        self.update_progress.emit("Trimming completed.")

        # Running SPAdes for assembly
        self.update_progress.emit("Running SPAdes for assembly.")

        # Prepare the command as a list
        spades_cmd = [
            "conda", "run", "-n", "spades_env", "spades.py",
            "--pe1-1", *self.trimmed_forward_files,
            "--pe1-2", *self.trimmed_reverse_files,
            "--phred-offset", "33",  # Added PHRED offset
            "-o", self.assembly_dir
        ]

        # Print the command for debugging
        print("Running command:", ' '.join(spades_cmd))

        # Run the command
        process = subprocess.Popen(spades_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        # Check for errors
        if process.returncode != 0:
            print("SPAdes Error Output:", stderr.decode())  # Print the error output
            self.error_msg = f"SPAdes assembly failed. Error: {stderr.decode()}"
            self.finished.emit(False)
        else:
            self.update_progress.emit("SPAdes assembly completed.")

        elapsed_time = time.time() - start_time  # Elapsed time
        elapsed_time_str = time.strftime("%Hh %Mm %Ss", time.gmtime(elapsed_time))  # Format elapsed time

        if self.cancelled:
            self.finished.emit(False)
        else:
            self.finished.emit(True)

        QMessageBox.information(None, "Success", f"Genomics pipeline finished successfully.\nElapsed Time: {elapsed_time_str}")


class GenomicsPipelineGUI(QDialog):
    def __init__(self):
        super().__init__()

        self.forward_files = []
        self.reverse_files = []
        self.output_folder = ""
        self.adapter_file = ""
        self.customized_params = False

        self.initUI()

    def initUI(self):
        self.setWindowTitle('De Novo Genomics Pipeline')
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
        self.output_folder_line = QLineEdit()
        output_layout.addWidget(self.output_folder_line)
        output_button = QPushButton('Browse', self)
        output_button.clicked.connect(self.select_output_folder)
        output_layout.addWidget(output_button)
        scroll_layout.addLayout(output_layout)

        # Run button
        run_button = QPushButton('Run Pipeline', self)
        run_button.clicked.connect(self.run_pipeline)
        main_layout.addWidget(run_button)

        # Progress output
        self.progress_output = QTextEdit()
        self.progress_output.setReadOnly(True)
        main_layout.addWidget(self.progress_output)

    def select_forward_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, 'Select Forward FASTQ Files', '', 'FASTQ Files (*.fastq *.fq *.fastq.gz *.fq.gz)')
        self.forward_files = files
        self.forward_paths.setPlainText('\n'.join(self.forward_files))

    def add_forward_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, 'Add Forward FASTQ Files', '', 'FASTQ Files (*.fastq *.fq *.fastq.gz *.fq.gz)')
        self.forward_files.extend(files)
        self.forward_paths.setPlainText('\n'.join(self.forward_files))

    def delete_forward_file(self):
        selected = self.forward_paths.textCursor().selectedText()
        if selected:
            self.forward_files = [f for f in self.forward_files if f not in selected.splitlines()]
            self.forward_paths.setPlainText('\n'.join(self.forward_files))

    def clear_forward_files(self):
        self.forward_files.clear()
        self.forward_paths.clear()

    def select_reverse_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, 'Select Reverse FASTQ Files', '', 'FASTQ Files (*.fastq *.fq *.fastq.gz *.fq.gz)')
        self.reverse_files = files
        self.reverse_paths.setPlainText('\n'.join(self.reverse_files))

    def add_reverse_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, 'Add Reverse FASTQ Files', '', 'FASTQ Files (*.fastq *.fq *.fastq.gz *.fq.gz)')
        self.reverse_files.extend(files)
        self.reverse_paths.setPlainText('\n'.join(self.reverse_files))

    def delete_reverse_file(self):
        selected = self.reverse_paths.textCursor().selectedText()
        if selected:
            self.reverse_files = [f for f in self.reverse_files if f not in selected.splitlines()]
            self.reverse_paths.setPlainText('\n'.join(self.reverse_files))

    def clear_reverse_files(self):
        self.reverse_files.clear()
        self.reverse_paths.clear()

    def select_adapter_file(self):
        file, _ = QFileDialog.getOpenFileName(self, 'Select Adapter File', '', 'Adapter Files (*.fa *.fasta *.txt)')
        if file:
            self.adapter_path.setText(file)
            self.adapter_file = file

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Select Output Folder')
        if folder:
            self.output_folder_line.setText(folder)
            self.output_folder = folder

    def run_pipeline(self):
        if not self.forward_files or not self.reverse_files:
            QMessageBox.warning(self, "Warning", "Please select forward and reverse files.")
            return
        if not self.output_folder or not self.adapter_file:
            QMessageBox.warning(self, "Warning", "Please specify output folder and adapter file.")
            return

        self.progress_output.clear()
        self.progress_output.append("Pipeline started...")

        self.worker = GenomicsPipelineWorker(self.forward_files, self.reverse_files, self.output_folder, self.adapter_file, self.customized_params)
        self.worker.finished.connect(self.pipeline_finished)
        self.worker.error.connect(self.show_error)
        self.worker.update_progress.connect(self.update_progress)
        self.worker.start()

    def update_progress(self, message):
        self.progress_output.append(message)

    def show_error(self, error_message):
        QMessageBox.critical(self, "Error", error_message)

    def pipeline_finished(self, success):
        if success:
            self.progress_output.append("Pipeline completed successfully.")
        else:
            self.progress_output.append("Pipeline encountered an error.")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = GenomicsPipelineGUI()
    gui.show()
    sys.exit(app.exec_())
