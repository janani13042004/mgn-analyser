import sys
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
        self.input_files = []
        self.genome_db = ""
        self.output_folder = ""
        self.process = None  # Store the subprocess instance
        self.signal = Signal()  # Signal object for communicating between threads
        self.initUI()

    def initUI(self):
        self.setWindowTitle('SnpEff')
        self.setFixedSize(600, 400)  # Set the window size
        layout = QVBoxLayout()

        # Input file selection
        input_layout = QVBoxLayout()
        input_layout.addWidget(QLabel('Select Input VCF Files:'))

        self.input_paths = QTextEdit()
        self.input_paths.setReadOnly(True)
        input_layout.addWidget(self.input_paths)

        input_button_layout = QHBoxLayout()
        input_select_button = QPushButton('Select', self)
        input_select_button.clicked.connect(self.select_input_files)
        input_button_layout.addWidget(input_select_button)

        input_add_button = QPushButton('Add', self)
        input_add_button.clicked.connect(self.add_input_files)
        input_button_layout.addWidget(input_add_button)

        input_delete_button = QPushButton('Delete', self)
        input_delete_button.clicked.connect(self.delete_input_file)
        input_button_layout.addWidget(input_delete_button)

        input_clear_button = QPushButton('Clear', self)
        input_clear_button.clicked.connect(self.clear_input_files)
        input_button_layout.addWidget(input_clear_button)

        input_layout.addLayout(input_button_layout)
        layout.addLayout(input_layout)

        # Genome database selection
        genome_layout = QVBoxLayout()
        genome_layout.addWidget(QLabel('Select Genome Database:'))

        self.genome_path_label = QLabel()
        genome_layout.addWidget(self.genome_path_label)

        genome_button_layout = QHBoxLayout()
        genome_select_button = QPushButton('Select', self)
        genome_select_button.clicked.connect(self.select_genome_db)
        genome_button_layout.addWidget(genome_select_button)

        genome_layout.addLayout(genome_button_layout)
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

    def select_input_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, 'Select Input VCF Files', '', 'VCF Files (*.vcf *.vcf.gz)'
        )
        self.input_files.extend(file_paths)
        self.update_input_paths()

    def add_input_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, 'Add Input VCF Files', '', 'VCF Files (*.vcf *.vcf.gz)'
        )
        self.input_files.extend(file_paths)
        self.update_input_paths()

    def delete_input_file(self):
        selected_index = self.input_paths.textCursor().blockNumber()
        if selected_index >= 0 and selected_index < len(self.input_files):
            del self.input_files[selected_index]
            self.update_input_paths()

    def clear_input_files(self):
        self.input_files.clear()
        self.update_input_paths()

    def select_genome_db(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, 'Select Genome Database', '', 'Genome Database Files (*.txt *.fasta *.fa)'
        )
        if file_path:
            self.genome_db = file_path
            self.update_genome_path()

    def select_output_folder(self):
        output_folder = QFileDialog.getExistingDirectory(self, 'Select Output Folder')
        if output_folder:
            self.output_folder = output_folder
            self.update_output_path()

    def update_input_paths(self):
        paths = '\n'.join(self.input_files)
        self.input_paths.setPlainText(paths)

    def update_genome_path(self):
        self.genome_path_label.setText(self.genome_db)

    def update_output_path(self):
        self.output_path_label.setText(self.output_folder)

    def run_analysis(self):
        if not self.input_files or not self.genome_db or not self.output_folder:
            QMessageBox.critical(
                self, 'Error', 'Please select input VCF files, a genome database, and an output folder.'
            )
            return

        cmd = ['java', '-jar', 'snpEff.jar', 'eff', self.genome_db]
        cmd.extend(self.input_files)
        cmd.extend(['-csvStats', f'{self.output_folder}/snpEff_summary.csv'])
        
        # Start the timer
        start_time = time.time()

        def run_snpeff():
            self.signal.started.emit()

            try:
                self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.process.communicate()
                returncode = self.process.returncode

                if returncode == 0:
                    self.signal.completed.emit(time.time() - start_time)
                else:
                    self.signal.error.emit("SnpEff command failed. Please check your inputs and try again.")
            except Exception as e:
                self.signal.error.emit(f"An error occurred while running SnpEff: {str(e)}")

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

        # Show "Analysis complete" message box with timestamp
        complete_msg = QMessageBox(self)
        complete_msg.setIcon(QMessageBox.Information)
        complete_msg.setText(f"Analysis is completed.\nDuration: {duration_str}")
        complete_msg.setWindowTitle("Complete")
        complete_msg.setStandardButtons(QMessageBox.Ok)
        complete_msg.buttonClicked.connect(self.close_windows)
        complete_msg.show()

    @pyqtSlot(str)
    def show_error_msg(self, error_message):
        if self.running_msg:
            self.running_msg.close()  # Close the "Running" message box

        QMessageBox.critical(self, "SnpEff Error", error_message)

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

