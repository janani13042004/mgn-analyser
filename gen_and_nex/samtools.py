import os
import sys
import subprocess
import time 
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QFileDialog, QMessageBox, QProgressDialog
from PyQt5.QtGui import QFont


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("SAM/BAM Converter")
        self.setGeometry(100, 100, 400, 200)

        self.file_path = ""
        self.output_folder_path = ""

        self.initUI()

    def initUI(self):
        # Label for SAM/BAM file selection
        label = QLabel("Select SAM/BAM file:", self)
        label.setGeometry(20, 20, 120, 20)

        # Button for selecting SAM/BAM file
        btn = QPushButton("Select File", self)
        btn.setGeometry(150, 20, 100, 20)
        btn.clicked.connect(self.select_file)

        # Label for displaying selected SAM file path
        self.path_label = QLabel("", self)
        self.path_label.setGeometry(20, 50, 360, 20)

        # Label for output folder selection
        output_label = QLabel("Select output folder:", self)
        output_label.setGeometry(20, 80, 120, 20)

        # Button for selecting output folder
        output_btn = QPushButton("Select Folder", self)
        output_btn.setGeometry(150, 80, 100, 20)
        output_btn.clicked.connect(self.select_output_folder)

        # Label for displaying selected output folder path
        self.output_path_label = QLabel("", self)
        self.output_path_label.setGeometry(20, 110, 360, 20)

        # Button for running conversion to BAM
        run_btn = QPushButton("Convert to BAM", self)
        run_btn.setGeometry(20, 150, 160, 30)
        run_btn.clicked.connect(self.convert_to_bam)

        # Button for running conversion to SAM
        sam_run_btn = QPushButton("Convert to SAM", self)
        sam_run_btn.setGeometry(220, 150, 160, 30)
        sam_run_btn.clicked.connect(self.convert_to_sam)

    def select_file(self):
        file_dialog = QFileDialog()
        self.file_path, _ = file_dialog.getOpenFileName(self, "Select SAM/BAM file")
        self.path_label.setText(self.file_path)

    def select_output_folder(self):
        file_dialog = QFileDialog()
        self.output_folder_path = file_dialog.getExistingDirectory(self, "Select output folder")
        self.output_path_label.setText(self.output_folder_path)

    def convert_to_bam(self):
        if self.file_path and self.output_folder_path:
            command = f'conda run -n samtools_env samtools view -bS {self.file_path} > {self.output_folder_path}/output.bam'
            print("Running command:", command)
            QTimer.singleShot(0, lambda: self.run_command(command, "Conversion to BAM"))
        else:
            print("Please select SAM/BAM file and output folder.")

    def convert_to_sam(self):
        if self.file_path and self.output_folder_path:
            command = f'conda run -n samtools_env samtools view -h -o {self.output_folder_path}/output.sam {self.file_path}'
            print("Running command:", command)
            QTimer.singleShot(0, lambda: self.run_command(command, "Conversion to SAM"))
        else:
            print("Please select SAM/BAM file and output folder.")

    def run_command(self, command, task_name):
        progress_dialog = QProgressDialog(self)
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setWindowFlag(Qt.FramelessWindowHint)
        progress_dialog.setFixedSize(400, 150)
        progress_dialog.setWindowTitle("Conversion Progress")
        progress_dialog.setLabelText(f"Running {task_name}...")
        progress_dialog.setCancelButton(None)
        progress_dialog.setRange(0, 0)
        progress_dialog.setFont(QFont("Arial", 12))

        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )

        while process.poll() is None:
            QApplication.processEvents()

        stdout, stderr = process.communicate()

        if process.returncode == 0:
            elapsed_time = self.format_duration(time.process_time())
            finish_msg_box = QMessageBox(self)
            finish_msg_box.setIcon(QMessageBox.Information)
            finish_msg_box.setWindowTitle("Conversion Complete")
            finish_msg_box.setText(f"{task_name} is completed.\nElapsed time: {elapsed_time}")
            finish_msg_box.setFont(QFont("Arial", 12))
            finish_msg_box.setStandardButtons(QMessageBox.Ok)
            finish_msg_box.buttonClicked.connect(self.close_windows)
            finish_msg_box.exec_()
        else:
            error_msg_box = QMessageBox(self)
            error_msg_box.setIcon(QMessageBox.Critical)
            error_msg_box.setWindowTitle("Conversion Failed")
            error_msg_box.setText(f"An error occurred during {task_name}:\n\n{stderr}")
            error_msg_box.setFont(QFont("Arial", 12))
            error_msg_box.setStandardButtons(QMessageBox.Ok)
            error_msg_box.buttonClicked.connect(self.close_windows)
            error_msg_box.exec_()

        progress_dialog.close()

    def format_duration(self, duration):
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = int(duration % 60)
        return f"{hours}h.{minutes}m.{seconds}s"

    def close_windows(self):
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
