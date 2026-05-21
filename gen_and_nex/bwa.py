import sys
import subprocess
import threading
import datetime
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QVBoxLayout, QWidget, QLabel, QPushButton, QTextEdit, QMessageBox,
    QGridLayout, QDesktopWidget
)
from PyQt5.QtCore import QElapsedTimer

class BWA_GUI(QMainWindow):
    def __init__(self):
        super().__init__()

        self.forward_files = []
        self.reverse_files = []
        self.output_folder = ""
        self.reference_file = ""

        self.setWindowTitle("BWA")
        self.setGeometry(200, 200, 800, 600)  # Set the window geometry

        layout = QVBoxLayout()

        # Reference file selection
        reference_layout = QGridLayout()
        reference_layout.addWidget(QLabel('Select Reference File (.fasta):'), 0, 0)
        self.reference_path_label = QLabel()
        reference_layout.addWidget(self.reference_path_label, 1, 0, 1, 2)
        reference_select_button = QPushButton('Select', self)
        reference_select_button.clicked.connect(self.select_reference_file)
        reference_layout.addWidget(reference_select_button, 0, 1)
        layout.addLayout(reference_layout)

        # Forward file selection
        forward_layout = QGridLayout()
        forward_layout.addWidget(QLabel('Select Forward Files:'), 0, 0)
        self.forward_paths = QTextEdit()
        self.forward_paths.setReadOnly(True)
        forward_layout.addWidget(self.forward_paths, 1, 0, 1, 2)
        forward_select_button = QPushButton('Select Forward Read', self)
        forward_select_button.clicked.connect(self.select_forward_files)
        forward_layout.addWidget(forward_select_button, 0, 0)
        forward_delete_button = QPushButton('Delete', self)
        forward_delete_button.clicked.connect(self.delete_forward_files)
        forward_layout.addWidget(forward_delete_button, 0, 1)
        forward_clear_button = QPushButton('Clear', self)
        forward_clear_button.clicked.connect(self.clear_forward_files)
        forward_layout.addWidget(forward_clear_button, 0, 2)
        layout.addLayout(forward_layout)


        # Reverse file selection
        reverse_layout = QGridLayout()
        reverse_layout.addWidget(QLabel('Select Reverse Files:'), 0, 0)
        self.reverse_paths = QTextEdit()
        self.reverse_paths.setReadOnly(True)
        reverse_layout.addWidget(self.reverse_paths, 1, 0, 1, 2)
        reverse_select_button = QPushButton('Select Reverse Read', self)
        reverse_select_button.clicked.connect(self.select_reverse_files)
        reverse_layout.addWidget(reverse_select_button, 0, 0)
        reverse_delete_button = QPushButton('Delete', self)
        reverse_delete_button.clicked.connect(self.delete_reverse_files)
        reverse_layout.addWidget(reverse_delete_button, 0, 1)
        reverse_clear_button = QPushButton('Clear', self)
        reverse_clear_button.clicked.connect(self.clear_reverse_files)
        reverse_layout.addWidget(reverse_clear_button, 0, 2)
        layout.addLayout(reverse_layout)

        # Output folder selection
        output_layout = QGridLayout()
        output_layout.addWidget(QLabel('Select Output Folder:'), 0, 0)
        self.output_path_label = QLabel()
        output_layout.addWidget(self.output_path_label, 1, 0, 1, 2)
        output_select_button = QPushButton('Select', self)
        output_select_button.clicked.connect(self.select_output_folder)
        output_layout.addWidget(output_select_button, 0, 1)
        layout.addLayout(output_layout)

        # Run button
        run_button = QPushButton('Run', self)
        run_button.clicked.connect(self.run_analysis)
        layout.addWidget(run_button)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        self.center_window()

    def center_window(self):
        frame_geometry = self.frameGeometry()
        center_point = QDesktopWidget().availableGeometry().center()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())

    def select_reference_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, 'Select Reference File (.fasta)', '', 'FASTA Files (*.fasta *.fa *.fna)'
        )
        if file_path:
            self.reference_file = file_path
            self.reference_path_label.setText(file_path)

    def select_forward_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, 'Select Forward Files', '', 'FASTQ Files (*.fastq *.fq *fastq.gz *fq.gz)'
        )
        self.forward_files.extend(file_paths)
        self.update_forward_paths()

    def select_reverse_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, 'Select Reverse Files', '', 'FASTQ Files (*.fastq *.fq *fastq.gz *fq.gz)'
        )
        self.reverse_files.extend(file_paths)
        self.update_reverse_paths()

    def select_output_folder(self):
        output_folder = QFileDialog.getExistingDirectory(self, 'Select Output Folder')
        if output_folder:
            self.output_folder = output_folder
            self.update_output_path()

    def update_forward_paths(self):
        paths = '\n'.join(self.forward_files)
        self.forward_paths.setPlainText(paths)

    def update_reverse_paths(self):
        paths = '\n'.join(self.reverse_files)
        self.reverse_paths.setPlainText(paths)

    def update_output_path(self):
        self.output_path_label.setText(self.output_folder)

    def run_analysis(self):
        if not self.reference_file or not self.forward_files or not self.reverse_files or not self.output_folder:
            QMessageBox.critical(
                self, 'Error', 'Please select the reference file, forward and reverse files, and an output folder.'
            )
            return

        os.makedirs(self.output_folder, exist_ok=True)

        self.running_msg = QMessageBox(self)
        self.running_msg.setIcon(QMessageBox.Information)
        self.running_msg.setText("The process is running. Please wait until the process finishes.")
        self.running_msg.setWindowTitle("Running")
        self.running_msg.setStandardButtons(QMessageBox.Cancel)
        self.running_msg.buttonClicked.connect(self.cancel_analysis)
        self.running_msg.show()

        threading.Thread(target=self.run_bwa, daemon=True).start()

    def run_bwa(self):
        try:
            start_time = datetime.datetime.now()  # Start time stamp

            # Activate the Conda environment
            cmd_activate = 'conda activate bwa_env'
            subprocess.run(cmd_activate, shell=True)

            # Build the BWA index
            cmd_build_index = f'bwa index {self.reference_file}'
            subprocess.run(cmd_build_index, shell=True)

            # Run BWA alignment for each pair of forward and reverse files
            for forward_file, reverse_file in zip(self.forward_files, self.reverse_files):
                output_sam_path = os.path.join(self.output_folder, f"{os.path.basename(forward_file).split('.')[0]}.sam")
                cmd_alignment = f'bwa mem -t 16 {self.reference_file} {forward_file} {reverse_file} > {output_sam_path}'
                subprocess.run(cmd_alignment, shell=True)

                # Optionally, you can generate an alignment report
                report_file_path = os.path.join(self.output_folder, f"{os.path.basename(forward_file)}_alignment_report.txt")
                cmd_alignment_report = f'bwa mem -t 16 {self.reference_file} {forward_file} {reverse_file} 2> {report_file_path}'
                subprocess.run(cmd_alignment_report, shell=True)

            elapsed_time = datetime.datetime.now() - start_time  # Calculate elapsed time

            # Convert elapsed time to hours, minutes, and seconds
            seconds = int(elapsed_time.total_seconds())
            hours, remainder = divmod(seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            # Format the elapsed time as 'hours.minutes.seconds'
            elapsed_time_formatted = f"{hours}h.{minutes}m.{seconds}s"

            self.running_msg.close()  # Close the "Running" message box

            QMessageBox.information(None, "Success", f"Alignment completed successfully!\nElapsed Time: {elapsed_time_formatted}")
        except Exception as e:
            self.running_msg.close()  # Close the "Running" message box
            QMessageBox.critical(None, "Error", f"An error occurred while running BWA: {str(e)}")

    def cancel_analysis(self):
        # Terminate the BWA process
        subprocess.Popen("pkill bwa", shell=True)

        self.running_msg.close()  # Close the "Running" message box

    def closeEvent(self, event):
        event.accept()  # Accept the close event without asking for confirmation

    def delete_forward_files(self):
        selected_paths = self.forward_paths.textCursor().selectedText().split("\n")
        self.forward_files = [file for file in self.forward_files if file not in selected_paths]
        self.update_forward_paths()

    def clear_forward_files(self):
        self.forward_files = []
        self.update_forward_paths()

    def delete_reverse_files(self):
        selected_paths = self.reverse_paths.textCursor().selectedText().split("\n")
        self.reverse_files = [file for file in self.reverse_files if file not in selected_paths]
        self.update_reverse_paths()

    def clear_reverse_files(self):
        self.reverse_files = []
        self.update_reverse_paths()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    bwa_tool = BWA_GUI()
    bwa_tool.show()
    sys.exit(app.exec_())

