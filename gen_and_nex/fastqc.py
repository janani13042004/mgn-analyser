import time
import subprocess
import os
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QFileDialog, QGridLayout, QWidget, QMessageBox, QTextEdit, QProgressDialog, QDesktopWidget
import shlex

class FastQC_GUI(QMainWindow):
    def __init__(self):
        super().__init__()

        self.forward_files = []
        self.output_folder = ""
        self.running_msg = None  # Reference to the running QMessageBox

        layout = QGridLayout()

        # File selection
        forward_layout = QGridLayout()
        forward_layout.addWidget(QLabel('Select Files:'), 0, 0)
        self.forward_paths = QTextEdit()
        self.forward_paths.setReadOnly(True)
        forward_layout.addWidget(self.forward_paths, 1, 0, 1, 2)
        forward_select_button = QPushButton('Select', self)
        forward_select_button.clicked.connect(self.select_files)
        forward_layout.addWidget(forward_select_button, 0, 1)

        forward_delete_button = QPushButton('Delete', self)
        forward_delete_button.clicked.connect(self.delete_files)
        forward_layout.addWidget(forward_delete_button, 0, 2)

        forward_clear_button = QPushButton('Clear', self)
        forward_clear_button.clicked.connect(self.clear_files)
        forward_layout.addWidget(forward_clear_button, 0, 3)

        layout.addLayout(forward_layout, 0, 0)

        # Output folder selection
        output_layout = QGridLayout()
        output_layout.addWidget(QLabel('Select Output Folder:'), 0, 0)
        self.output_path_label = QLabel()
        output_layout.addWidget(self.output_path_label, 1, 0, 1, 2)
        output_select_button = QPushButton('Select', self)
        output_select_button.clicked.connect(self.select_output_folder)
        output_layout.addWidget(output_select_button, 0, 1)

        layout.addLayout(output_layout, 1, 0)

        # Run button
        run_button = QPushButton('Run', self)
        run_button.clicked.connect(self.run_analysis)
        layout.addWidget(run_button)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)
        self.setWindowTitle('fastQC')

        # Center the window on the screen
        self.center_window()

    def center_window(self):
        frame_geometry = self.frameGeometry()
        center_point = QDesktopWidget().availableGeometry().center()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())


    def select_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, 'Select Forward Files', '', 'FASTQ Files (*.fastq *.fq *fastq.gz *fq.gz)'
        )
        self.forward_files.extend(file_paths)
        self.update_select_paths()

    def select_output_folder(self):
        output_folder = QFileDialog.getExistingDirectory(self, 'Select Output Folder')
        if output_folder:
            self.output_folder = output_folder
            self.update_output_path()

    def delete_files(self):
        self.forward_files = []
        self.update_select_paths()

    def clear_files(self):
        self.forward_files = []
        self.output_folder = ""
        self.update_select_paths()
        self.update_output_path()

    def update_select_paths(self):
        paths = '\n'.join(self.forward_files)
        self.forward_paths.setPlainText(paths)

    def update_output_path(self):
        self.output_path_label.setText(self.output_folder)

    def run_analysis(self):
        if not self.forward_files:
            QMessageBox.warning(self, "Missing Input", "Please select forward files.")
            return
        if not self.output_folder:
            QMessageBox.warning(self, "Missing Input", "Please select output folder.")
            return

        # Build the FastQC command
        fastqc_cmd = f"conda run -n fastqc_env fastqc -o {self.output_folder} {' '.join(self.forward_files)}"

        # Start time
        start_time = time.time()

        # Show "Running" message box within the window
        self.running_msg = QMessageBox(self)
        self.running_msg.setIcon(QMessageBox.Information)
        self.running_msg.setText("The process is running. Please wait until the process finishes.")
        self.running_msg.setWindowTitle("Running")
        self.running_msg.setStandardButtons(QMessageBox.NoButton)
        self.running_msg.show()

        # Run the FastQC command using subprocess
        try:
            process = subprocess.Popen(fastqc_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            while process.poll() is None:
                time.sleep(0.1)  # Sleep for a short interval
                QApplication.processEvents()  # Process pending events

            stdout, stderr = process.communicate()
            if process.returncode != 0:
                QMessageBox.critical(self, "FastQC Error", "FastQC command failed. Please check your inputs and try again.")
                return
            else:
                # End time
                end_time = time.time()
                duration = end_time - start_time

                # Convert duration to hours, minutes, and seconds
                hours = int(duration / 3600)
                minutes = int((duration % 3600) / 60)
                seconds = int(duration % 60)

                # Format the duration as "hours minutes seconds"
                duration_str = f"{hours}h {minutes}m {seconds}s"

                # Show "FastQC is complete" message box with timestamp
                complete_msg = QMessageBox(self)
                complete_msg.setIcon(QMessageBox.Information)
                complete_msg.setText(f"FastQC is complete.\nDuration: {duration_str}")
                complete_msg.setWindowTitle("Complete")
                complete_msg.setStandardButtons(QMessageBox.Ok)
                complete_msg.buttonClicked.connect(self.close_windows)
                complete_msg.show()
        except Exception as e:
            QMessageBox.critical(self, "FastQC Error", f"An error occurred while running FastQC: {str(e)}")
            return
        finally:
            if self.running_msg:
                self.running_msg.close()  # Close the "Running" message box

            # Deactivate the Conda environment
            deactivate_env_command = 'conda deactivate'
            subprocess.run(shlex.split(deactivate_env_command), shell=True)

    def close_windows(self):
        if self.running_msg:
            self.running_msg.close()  # Close the "Running" message box
        self.close()


if __name__ == "__main__":
    app = QApplication([])
    app.setStyle('Fusion')
    gui = FastQC_GUI()
    gui.show()
    gui.resize(600, 300)  # Set the window size
    app.exec_()
