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

class ABySS_GUI(QMainWindow):
    def __init__(self):
        super().__init__()

        self.forward_files = []
        self.reverse_files = []
        self.output_folder = ""
        self.kmer_length = 21  # Default k-mer length

        self.setWindowTitle("ABySS")
        self.setGeometry(200, 200, 800, 600)  # Set the window geometry

        layout = QVBoxLayout()

        # Forward file selection
        forward_layout = QGridLayout()
        forward_layout.addWidget(QLabel('Select Forward Files:'), 0, 0)
        self.forward_paths = QTextEdit()
        self.forward_paths.setReadOnly(True)
        forward_layout.addWidget(self.forward_paths, 1, 0, 1, 2)
        forward_select_button = QPushButton('Select Forward Reads', self)
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
        reverse_select_button = QPushButton('Select Reverse Reads', self)
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

        # K-mer length input
        kmer_layout = QGridLayout()
        kmer_layout.addWidget(QLabel('K-mer Length:'), 0, 0)
        self.kmer_input = QTextEdit(str(self.kmer_length))
        kmer_layout.addWidget(self.kmer_input, 0, 1)
        layout.addLayout(kmer_layout)

        # Run button
        run_button = QPushButton('Run', self)
        run_button.clicked.connect(self.run_assembly)
        layout.addWidget(run_button)

        # Time label
        self.time_label = QLabel()
        layout.addWidget(self.time_label)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        self.center_window()

    def center_window(self):
        frame_geometry = self.frameGeometry()
        center_point = QDesktopWidget().availableGeometry().center()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())

    def select_forward_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, 'Select Forward Files', '', 'FASTQ Files (*.fastq *.fq *fastq.gz *.fq.gz)'
        )
        self.forward_files.extend(file_paths)
        self.update_forward_paths()

    def select_reverse_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, 'Select Reverse Files', '', 'FASTQ Files (*.fastq *.fq *fastq.gz *.fq.gz)'
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

    def run_assembly(self):
        if not self.forward_files or not self.reverse_files or not self.output_folder:
            QMessageBox.critical(
                self, 'Error', 'Please select forward and reverse files, and an output folder.'
            )
            return

        self.running_msg = QMessageBox(self)
        self.running_msg.setIcon(QMessageBox.Information)
        self.running_msg.setText("The ABySS assembly is running. Please wait until the process finishes.")
        self.running_msg.setWindowTitle("Running")
        self.running_msg.setStandardButtons(QMessageBox.Cancel)
        self.running_msg.buttonClicked.connect(self.cancel_assembly)
        self.running_msg.show()

        self.timer = QElapsedTimer()
        self.timer.start()

        threading.Thread(target=self.run_abyss, daemon=True).start()

    def run_abyss(self):
        try:
            kmer_length = self.kmer_input.toPlainText()
            output_folder = os.path.join(self.output_folder, "abyss_assembly")  # Create output folder within chosen output directory
            os.makedirs(output_folder, exist_ok=True)
            # Run ABySS assembly
            cmd_assembly = f'abyss-pe k={kmer_length} name=assembly B=1G in=\'{",".join(self.forward_files)} {",".join(self.reverse_files)}\' -o {self.output_folder}/Abyss_assembly'
            subprocess.run(cmd_assembly, shell=True, check=True)

            elapsed_time = self.timer.elapsed()
            self.running_msg.close()  # Close the "Running" message box

            QMessageBox.information(None, "Success", f"ABySS assembly completed successfully! Time taken: {str(datetime.timedelta(milliseconds=elapsed_time))}")
        except subprocess.CalledProcessError as e:
            self.running_msg.close()  # Close the "Running" message box
            QMessageBox.critical(None, "Error", f"An error occurred while running ABySS: {e.stderr.decode()}")

    def cancel_assembly(self):
        # Terminate the ABySS process
        subprocess.Popen("pkill abyss", shell=True)

        self.running_msg.close()  # Close the "Running" message box

    def closeEvent(self, event):
        event.accept()  # Accept the close event without asking for confirmation

    def delete_forward_files(self):
        del self.forward_files[:]
        self.update_forward_paths()

    def delete_reverse_files(self):
        del self.reverse_files[:]
        self.update_reverse_paths()

    def clear_forward_files(self):
        self.forward_paths.clear()
        del self.forward_files[:]

    def clear_reverse_files(self):
        self.reverse_paths.clear()
        del self.reverse_files[:]


if __name__ == '__main__':
    app = QApplication(sys.argv)
    abyss_tool = ABySS_GUI()
    abyss_tool.show()
    sys.exit(app.exec_())

