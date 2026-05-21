import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QDialog, QGridLayout, QLabel, QPushButton,
    QFileDialog, QMessageBox, QVBoxLayout, QTextEdit, QHBoxLayout
)
from PyQt5.QtCore import Qt, QObject, pyqtSignal, pyqtSlot
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
        self.process = None  # Store the subprocess instance
        self.signal = Signal()  # Signal object for communicating between threads
        self.initUI()

    def initUI(self):
        self.setWindowTitle('SNPeff')
        self.setFixedSize(600, 400)  # Set the window size
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
        genome_layout = QGridLayout()
        genome_layout.addWidget(QLabel('Select Genome File:'), 0, 0)
        self.genome_path_label = QLabel()
        genome_layout.addWidget(self.genome_path_label, 1, 0, 1, 2)
        genome_select_button = QPushButton('Select', self)
        genome_select_button.clicked.connect(self.select_genome_file)
        genome_layout.addWidget(genome_select_button, 0, 1)
        layout.addLayout(genome_layout)

        # Output folder selection
        output_layout = QGridLayout()
        output_layout.addWidget(QLabel('Select Output Folder:'), 0, 0)
        self.output_path_label = QLabel()
        output_layout.addWidget(self.output_path_label, 1, 0, 1, 2)
        output_select_button = QPushButton('Select', self)
        output_select_button.clicked.connect(self.select_output_folder)
        output_layout.addWidget(output_select_button, 0, 1)
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
        file_path, _ = QFileDialog.getOpenFileName(
            self, 'Select Genome File', '', 'Genome Files (*.fasta *.fa *.fna *.gz)'
        )
        if file_path:
            self.genome_file = file_path
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

        # Construct the command to run snpeff within the snpeff_env Conda environment
        cmd = [
            'conda', 'run', '-n', 'snpeff_env', 'snpeff', 'ann',
            self.genome_file, '-o', 'vcf', '-csvStats', os.path.join(self.output_folder, 'snpeff_stats.csv')
        ]
        cmd.extend(['-v', vcf_file for vcf_file in self.vcf_files])

        # Print the command for debugging purposes
        print("Running command:", " ".join(cmd))

        # Start the timer
        start_time = time.time()

        def run_snpeff():
            self.signal.started.emit()

            try:
                self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = self.process.communicate()
                returncode = self.process.returncode

                # Print the output and error for debugging purposes
                print("STDOUT:", stdout.decode())
                print("STDERR:", stderr.decode())

                if returncode == 0:
                    self.signal.completed.emit(time.time() - start_time)
                else:
                    self.signal.error.emit(f"SNPeff command failed. STDERR:\n{stderr.decode()}")
            except Exception as e:
                self.signal.error.emit(f"An error occurred while running SNPeff: {str(e)}")

        # Start the thread
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
            self.running_msg.close()  # Close the "Running" message box

        # Convert duration to hours, minutes, and seconds
        hours = int(duration / 3600)
        minutes = int((duration % 3600) / 60)
        seconds = int(duration % 60)

        # Format the duration as "hours minutes seconds"
        duration_str = f"{hours}h {minutes}m {seconds}s"

        # Show "Assembly is complete" message box with timestamp
        complete_msg = QMessageBox(self)
        complete_msg.setIcon(QMessageBox.Information)
        complete_msg.setText(f"SNPeff annotation is completed.\nDuration: {duration_str}")
        complete_msg.setWindowTitle("Complete")
        complete_msg.setStandardButtons(QMessageBox.Ok)
        complete_msg.buttonClicked.connect(self.close_windows)
        complete_msg.show()

    @pyqtSlot(str)
    def show_error_msg(self, error_message):
        if self.running_msg:
            self.running_msg.close()  # Close the "Running" message box

        QMessageBox.critical(self, "SNPeff Error", error_message)

    def cancel_analysis(self):
        if self.process and self.process.poll() is None:
            # Process is still running, terminate it
            self.process.terminate()
            self.process.wait()

        if self.running_msg:
            self.running_msg.close()  # Close the "Running" message box

    def close_windows(self):
        if self.running_msg:
            self.running_msg.close()  # Close the "Running" message box
        self.close()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PopupWindow()
    window.show()
    sys.exit(app.exec_())

