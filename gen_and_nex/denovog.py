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

    def __init__(self, forward_files, reverse_files, output_folder, adapter_file, customized_params, blast_db, go_annotation_tool):
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
        self.blast_db = blast_db
        self.go_annotation_tool = go_annotation_tool
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
        self.blast_output_dir = f"{self.output_folder}/blast_output"
        self.go_output_dir = f"{self.output_folder}/go_output"

        # Create directories if they don't exist
        for dir in [self.fastqc_dir, self.trimmed_dir, self.assembly_dir, self.blast_output_dir, self.go_output_dir]:
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

        spades_cmd = [
            "conda", "run", "-n", "spades_env", "spades.py",
            "--pe1-1", *self.trimmed_forward_files,
            "--pe1-2", *self.trimmed_reverse_files,
            "--phred-offset", "33",
            "-o", self.assembly_dir
        ]

        process = subprocess.Popen(spades_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            self.error_msg = f"SPAdes assembly failed. Error: {stderr.decode()}"
            self.finished.emit(False)
        else:
            self.update_progress.emit("SPAdes assembly completed.")

        # Making BLAST database
        blast_cmd1 = f"conda run -n blast_env makeblastdb -in {self.blast_db_path} -dbtype prot -out {self.output_folder}\n"
        subprocess.run(blast_cmd1, shell=True, check=True)

        # Running BLASTx using SPAdes contigs
        blast_cmd2 = f"conda run -n blast_env blastx -query {self.output_folder}/contigs.fasta -db {self.blast_db_path} -out {self.output_folder}/blast.csv -outfmt \"6 qseqid sseqid pident length mismatch gapopen qstart qend sstart send evalue bitscore sseq\" -evalue 1e-5 -max_target_seqs 5 -num_threads 16"
        subprocess.run(blast_cmd2, shell=True, check=True)

        # Emit progress update
        self.update_progress.emit("BLAST process is completed")


        # Running GO Annotation
        self.update_progress.emit("Running GO Annotation.")
        go_cmd = [
            "conda", "run", "-n", self.go_annotation_tool, "blast2go", "-in", blast_output_file, "-out", os.path.join(self.go_output_dir, "go_annotation.txt")
        ]
        process = subprocess.Popen(go_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            self.error_msg = f"GO Annotation failed. Error: {stderr.decode()}"
            self.finished.emit(False)
            return
        self.update_progress.emit("GO Annotation completed.")

        elapsed_time = time.time() - start_time
        elapsed_time_str = time.strftime("%Hh %Mm %Ss", time.gmtime(elapsed_time))

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
        self.blast_db = ""
        self.go_annotation_tool = ""
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
        forward_btn = QPushButton('Add Forward Files')
        forward_btn.clicked.connect(self.add_forward_files)
        forward_layout.addWidget(forward_btn)

        scroll_layout.addLayout(forward_layout)

        # Reverse files selection
        reverse_layout = QVBoxLayout()
        reverse_layout.addWidget(QLabel('Select Reverse Files:'))
        self.reverse_paths = QTextEdit()
        self.reverse_paths.setReadOnly(True)
        reverse_layout.addWidget(self.reverse_paths)
        reverse_btn = QPushButton('Add Reverse Files')
        reverse_btn.clicked.connect(self.add_reverse_files)
        reverse_layout.addWidget(reverse_btn)

        scroll_layout.addLayout(reverse_layout)

        # Output folder selection
        output_layout = QVBoxLayout()
        output_layout.addWidget(QLabel('Select Output Folder:'))
        self.output_path = QLineEdit()
        self.output_path.setReadOnly(True)
        output_layout.addWidget(self.output_path)
        output_btn = QPushButton('Select Folder')
        output_btn.clicked.connect(self.select_output_folder)
        output_layout.addWidget(output_btn)

        scroll_layout.addLayout(output_layout)

        # Adapter file selection
        adapter_layout = QVBoxLayout()
        adapter_layout.addWidget(QLabel('Select Adapter File (FASTA):'))
        self.adapter_path = QLineEdit()
        self.adapter_path.setReadOnly(True)
        adapter_layout.addWidget(self.adapter_path)
        adapter_btn = QPushButton('Select File')
        adapter_btn.clicked.connect(self.select_adapter_file)
        adapter_layout.addWidget(adapter_btn)

        scroll_layout.addLayout(adapter_layout)

        # BLAST DB selection
        blast_db_layout = QVBoxLayout()
        blast_db_layout.addWidget(QLabel('Select BLAST Database:'))
        self.blast_db_path = QLineEdit()
        self.blast_db_path.setReadOnly(True)
        blast_db_layout.addWidget(self.blast_db_path)
        blast_db_btn = QPushButton('Select BLAST DB')
        blast_db_btn.clicked.connect(self.select_blast_db)
        blast_db_layout.addWidget(blast_db_btn)

        scroll_layout.addLayout(blast_db_layout)

        # GO Annotation Tool Selection
        go_layout = QVBoxLayout()
        go_layout.addWidget(QLabel('Select GO Annotation Tool:'))
        self.go_tool_path = QLineEdit()
        self.go_tool_path.setReadOnly(True)
        go_layout.addWidget(self.go_tool_path)
        go_tool_btn = QPushButton('Select GO Annotation Tool')
        go_tool_btn.clicked.connect(self.select_go_tool)
        go_layout.addWidget(go_tool_btn)

        scroll_layout.addLayout(go_layout)

        # Customized parameters checkbox
        self.customized_params_checkbox = QCheckBox('Use Customized Parameters for Trimmomatic')
        scroll_layout.addWidget(self.customized_params_checkbox)
        self.customized_params_checkbox.stateChanged.connect(self.toggle_customized_params)

        # Customized parameters layout
        self.customized_params_layout = QVBoxLayout()
        self.leading_edit = QLineEdit()
        self.trailing_edit = QLineEdit()
        self.minlen_edit = QLineEdit()
        self.headcrop_edit = QLineEdit()
        scroll_layout.addLayout(self.customized_params_layout)

        scroll_layout.addWidget(QLabel('Trimmomatic Customized Parameters:'))
        self.customized_params_layout.addWidget(QLabel('LEADING'))
        self.customized_params_layout.addWidget(self.leading_edit)
        self.customized_params_layout.addWidget(QLabel('TRAILING'))
        self.customized_params_layout.addWidget(self.trailing_edit)
        self.customized_params_layout.addWidget(QLabel('MINLEN'))
        self.customized_params_layout.addWidget(self.minlen_edit)
        self.customized_params_layout.addWidget(QLabel('HEADCROP'))
        self.customized_params_layout.addWidget(self.headcrop_edit)

        # Hide customized parameters initially
        self.customized_params_layout.setEnabled(False)

        # Start and Cancel buttons
        buttons_layout = QHBoxLayout()
        start_btn = QPushButton('Start Pipeline')
        start_btn.clicked.connect(self.start_pipeline)
        cancel_btn = QPushButton('Cancel Pipeline')
        cancel_btn.clicked.connect(self.cancel_pipeline)
        buttons_layout.addWidget(start_btn)
        buttons_layout.addWidget(cancel_btn)
        scroll_layout.addLayout(buttons_layout)

        self.show()

    def add_forward_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, 'Select Forward FASTQ Files', '', 'FASTQ Files (*.fastq *.fq *.fastq.gz *.fq.gz)')
        if files:
            self.forward_files += files
            self.forward_paths.setPlainText('\n'.join(self.forward_files))

    def add_reverse_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, 'Select Reverse FASTQ Files', '', 'FASTQ Files (*.fastq *.fq *.fastq.gz *.fq.gz)')
        if files:
            self.reverse_files += files
            self.reverse_paths.setPlainText('\n'.join(self.reverse_files))

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Select Output Folder')
        if folder:
            self.output_folder = folder
            self.output_path.setText(folder)

    def select_adapter_file(self):
        file, _ = QFileDialog.getOpenFileName(self, 'Select Adapter File', '', 'FASTA Files (*.fasta *.fa *.fna)')
        if file:
            self.adapter_file = file
            self.adapter_path.setText(file)

    def select_blast_db(self):
        file, _ = QFileDialog.getOpenFileName(self, 'Select BLAST Database File', '', 'FASTA Files (*.fasta *.fa *.fna)')
        if file:
            self.blast_db = file
            self.blast_db_path.setText(file)

    def select_go_tool(self):
        tool, ok = QInputDialog.getText(self, 'Select GO Annotation Tool', 'Enter GO Annotation Tool (e.g., Blast2GO):')
        if ok:
            self.go_annotation_tool = tool
            self.go_tool_path.setText(tool)

    def toggle_customized_params(self, state):
        self.customized_params_layout.setEnabled(state == Qt.Checked)

    def start_pipeline(self):
        if not self.forward_files or not self.reverse_files:
            QMessageBox.critical(self, 'Error', 'Please select both forward and reverse files.')
            return
        if not self.output_folder:
            QMessageBox.critical(self, 'Error', 'Please select an output folder.')
            return
        if not self.adapter_file:
            QMessageBox.critical(self, 'Error', 'Please select an adapter file.')
            return
        if not self.blast_db:
            QMessageBox.critical(self, 'Error', 'Please select a BLAST database.')
            return
        if not self.go_annotation_tool:
            QMessageBox.critical(self, 'Error', 'Please select a GO annotation tool.')
            return

        customized_params = {
            "LEADING": self.leading_edit.text(),
            "TRAILING": self.trailing_edit.text(),
            "MINLEN": self.minlen_edit.text(),
            "HEADCROP": self.headcrop_edit.text()
        } if self.customized_params_checkbox.isChecked() else None

        self.worker = GenomicsPipelineWorker(self.forward_files, self.reverse_files, self.output_folder,
                                             self.adapter_file, customized_params, self.blast_db, self.go_annotation_tool)
        self.worker.update_progress.connect(self.update_progress)
        self.worker.finished.connect(self.pipeline_finished)
        self.worker.error.connect(self.show_error)
        self.worker.start()

    def cancel_pipeline(self):
        if self.worker:
            self.worker.cancel()

    def update_progress(self, message):
        QMessageBox.information(self, 'Progress', message)

    def pipeline_finished(self, success):
        if success:
            QMessageBox.information(self, 'Success', 'Pipeline completed successfully.')
        else:
            QMessageBox.critical(self, 'Error', 'Pipeline failed.')

    def show_error(self, message):
        QMessageBox.critical(self, 'Error', message)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = GenomicsPipelineGUI()
    sys.exit(app.exec_())
