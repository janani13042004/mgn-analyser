import os
import sys
import subprocess
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QDesktopWidget
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QFileDialog, QMessageBox

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("GFF3/GTF Converter")
        self.setGeometry(100, 100, 400, 200)

        # Call the center method after setting the geometry
        self.center()

        self.gff3_file_path = ""
        self.output_folder_path = ""

        self.initUI()

    def center(self):
        """Center the window on the screen."""
        screen_rect = QDesktopWidget().availableGeometry()
        center_pos = screen_rect.center()

        self.move(center_pos.x() - self.width() // 2, center_pos.y() - self.height() // 2)

    def initUI(self):
        # Label for GFF3/GTF file selection
        gff3_label = QLabel("Select gff3/gtf file:", self)
        gff3_label.setGeometry(20, 20, 120, 20)

        # Button for selecting GFF3/GTF file
        gff3_btn = QPushButton("Select File", self)
        gff3_btn.setGeometry(150, 20, 100, 20)
        gff3_btn.clicked.connect(self.select_gff3_file)

        # Label for displaying selected GFF3/GTF file path
        self.gff3_path_label = QLabel("", self)
        self.gff3_path_label.setGeometry(20, 50, 360, 20)

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

        # Button for running conversion to GFF3
        gff3_run_btn = QPushButton("Convert to GFF3", self)
        gff3_run_btn.setGeometry(20, 150, 160, 30)
        gff3_run_btn.clicked.connect(self.convert_to_gff3)

        # Button for running conversion to GTF
        gtf_run_btn = QPushButton("Convert to GTF", self)
        gtf_run_btn.setGeometry(220, 150, 160, 30)
        gtf_run_btn.clicked.connect(self.convert_to_gtf)

    def select_gff3_file(self):
        file_dialog = QFileDialog()
        self.gff3_file_path, _ = file_dialog.getOpenFileName(self, "Select gff3/gtf file")
        self.gff3_path_label.setText(self.gff3_file_path)

    def select_output_folder(self):
        file_dialog = QFileDialog()
        self.output_folder_path = file_dialog.getExistingDirectory(self, "Select output folder")
        self.output_path_label.setText(self.output_folder_path)

    def convert_to_gff3(self):
        if self.gff3_file_path and self.output_folder_path:
            command = f'.conda run -n gffread_env gffread "{self.gff3_file_path}" -T -o "{self.output_folder_path}/annotation.gff3"'
            print("Running command:", command)

            # Use QTimer to schedule command execution in the main thread
            QTimer.singleShot(0, lambda: self.run_command(command))
        else:
            print("Please select gff3/gtf file and output folder.")

    def convert_to_gtf(self):
        if self.gff3_file_path and self.output_folder_path:
            command = f'conda run -n gffread_env gffread "{self.gff3_file_path}" -T -o "{self.output_folder_path}/annotation.gtf"'
            print("Running command:", command)

            # Use QTimer to schedule command execution in the main thread
            QTimer.singleShot(0, lambda: self.run_command(command))
        else:
            print("Please select gff3/gtf file and output folder.")

    def run_command(self, command):
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        if process.returncode == 0:
            QMessageBox.information(self, "Conversion Completed", "Conversion is completed.")
        else:
            QMessageBox.critical(self, "Conversion Failed", f"An error occurred during conversion:\n\n{stderr.decode()}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
