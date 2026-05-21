import sys
from PyQt5.QtWidgets import (
    QApplication, QDialog, QGridLayout, QLabel, QPushButton,
    QFileDialog, QMessageBox, QVBoxLayout, QTextEdit, QHBoxLayout
)
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
import subprocess
import threading
import time

class Signal(QObject):
    started = pyqtSignal()
    completed = pyqtSignal(float)
    error = pyqtSignal(str)

class PopupWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.vcf_files = []
        self.genome_file = ""
        self.output_folder = ""
        self.process = None
        self.signal = Signal()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('SNPeff')
        self.setFixedSize(600, 400)
        layout = QVBoxLayout()

        # VCF file selection
        vcf_layout = QVBoxLayout()
        vcf_layout.addWidget(QLabel('Select VCF Files:'))

        self.vcf_paths = QTextEdit()
        self.vcf_paths.setReadOnly(True)
        vcf_layout.addWidget(self.vcf_paths)

        vcf_button_layout = QHBoxLayout()
        vcf_select_button = QPushButton('Select', self)
        vcf_select_button.clicked.connect(self.select_vcf_files)
        vcf_button_layout.addWidget(vcf_select_button)

        vcf_add_button = QPushButton('Add', self)
        vcf_add_button.clicked.connect(self.add_vcf_files)
        vcf_button_layout.addWidget(vcf_add_button)

        vcf_delete_button = QPushButton('Delete', self)
        vcf_delete_button.clicked.connect(self.delete_vcf_file)
        vcf_button_layout.addWidget(vcf_delete_button)

        vcf_clear_button = QPushButton('Clear', self)
        vcf_clear_button.clicked.connect(self.clear_vcf_files)
        vcf_button_layout.addWidget(vcf_clear_button)

        vcf_layout.addLayout(vcf_button_layout)
        layout.addLayout(vcf_layout)

        # Genome file selection
        genome_layout = QHBoxLayout()
        genome_layout.addWidget(QLabel('Select Genome File:'))
        self.genome_path_label = QLabel()
        genome_layout.addWidget(self.genome_path_label)
        genome_select_button = QPushButton('Select', self)
        genome_select_button.clicked.connect(self.select_genome_file)
        genome_layout.addWidget(genome_select_button)
        layout.addLayout(genome_layout)

        # Output folder selection
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel('Select Output Folder:'))
        self.output_path_label = QLabel()
        output_layout.addWidget(self.output_path_label)
        output_select_button = QPushButton('Select', self)
        output_select_button.clicked.connect(self.select_output_folder)
        output_layout.addWidget(output_select_button)
        layout.addLayout(output_layout)

        # Run and Cancel buttons
        buttons_layout = QHBoxLayout()
        run_button = QPushButton('Run', self)
        run_button.clicked.connect(self.run_analysis)
        buttons_layout.addWidget(run_button)
        cancel_button = QPushButton('Cancel', self)
        cancel_button.clicked.connect(self.cancel_analysis)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)

        # Connect signals
        self.signal.started.connect(self.show_running_msg)
        self.signal.completed.connect(self.show_complete_msg)
        self.signal.error.connect(self.show_error_msg)

    def select_vcf_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, 'Select VCF Files', '', 'VCF Files (*.vcf *.vcf.gz)'
        )
        self.vcf_files.extend(file_paths)
        self.update_vcf_paths()

    def add_vcf_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, 'Add VCF Files', '', 'VCF Files (*.vcf *.vcf.gz)'
        )
        self.vcf_files.extend(file_paths)
        self.update_vcf_paths()

    def delete_vcf_file(self):
        selected_index = self.vcf_paths.textCursor().blockNumber()
        if selected_index >= 0 and selected_index < len(self.vcf_files):
            del self.vcf_files[selected_index]
            self.update_vcf_paths()

    def clear_vcf_files(self):
        self.vcf_files.clear()
        self.update_vcf_paths()

    def select_genome_file(self):
        genome_file, _ = QFileDialog.getOpenFileName(
            self, 'Select Genome File', '', 'FASTA Files (*.fa *.fasta *.fna)'
        )
        if genome_file:
            self.genome_file = genome_file
            self.update_genome_path()

    def select_output_folder(self):
        output_folder = QFileDialog.getExistingDirectory(self, 'Select Output Folder')
        if output_folder:
            self.output_folder = output_folder
            self.update_output_path()

    def update_vcf_paths(self):
        paths = '\n'.join(self.vcf_files)
        self.vcf_paths.setPlainText(paths)

    def update_genome_path(self):
        self.genome_path_label.setText(self.genome_file)

    def update_output_path(self):
        self.output_path_label.setText(self.output_folder)

    def run_analysis(self):
        if not self.vcf_files or not self.genome_file or not self.output_folder:
            QMessageBox.critical(
                self, 'Error', 'Please select VCF files, a genome file, and an output folder.'
            )
            return

        cmd = [
            'java', '-jar', '/home/altschul/anaconda3/envs/snpeff_env/share/snpeff-5.2-1/snpEff.jar',
            'annotate', self.genome_file, '-v', ','.join(self.vcf_files), '-o', self.output_folder
        ]

        start_time = time.time()

        def run_snpeff():
            self.signal.started.emit()
            try:
                self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = self.process.communicate()
                returncode = self.process.returncode

                if returncode == 0:
                    self.signal.completed.emit(time.time() - start_time)
                else:
                    self.signal.error.emit(f"SNPeff command failed. Please check your inputs and try again.\n\n{stderr.decode()}")
            except Exception as e:
                self.signal.error.emit(f"An error occurred while running SNPeff: {str(e)}")

        threading.Thread(target=run_snpeff, daemon=True).start()

    @pyqtSlot()
    def show_running_msg(self):
        self.running_msg = QMessageBox(self)
        self.running_msg.setIcon(QMessageBox.Information)
        self.running_msg.setText("The process is running. Please wait until the process finishes.")
        self.running_msg.setWindowTitle("Running")
        self.running_msg.setStandardButtons(QMessageBox.Cancel)
        self.running_msg.buttonClicked.connect(self.cancel_analysis)
        self.running_msg.show()

    @pyqtSlot(float)
    def show_complete_msg(self, duration):
        if self.running_msg:
            self.running_msg.close()

        hours = int(duration / 3600)
        minutes = int((duration % 3600) / 60)
        seconds = int(duration % 60)
        duration_str = f"{hours}h {minutes}m {seconds}s"

        complete_msg = QMessageBox(self)
        complete_msg.setIcon(QMessageBox.Information)
        complete_msg.setText(f"Annotation is completed.\nDuration: {duration_str}")
        complete_msg.setWindowTitle("Complete")
        complete_msg.setStandardButtons(QMessageBox.Ok)
        complete_msg.buttonClicked.connect(self.close_windows)
        complete_msg.show()

    @pyqtSlot(str)
    def show_error_msg(self, error_message):
        if self.running_msg:
            self.running_msg.close()
        QMessageBox.critical(self, "SNPeff Error", error_message)

    def cancel_analysis(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait()

        if self.running_msg:
            self.running_msg.close()

    def close_windows(self):
        if self.running_msg:
            self.running_msg.close()
        self.close()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PopupWindow()
    window.show()
    sys.exit(app.exec_())

