import os
import shutil
import subprocess
import time
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QFileDialog, QHBoxLayout, QVBoxLayout, QMessageBox, QDesktopWidget
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTime

class TransdecoderThread(QThread):
    process_completed = pyqtSignal(float)


    def __init__(self, assembled_file, output_path):
        super().__init__()
        self.assembled_file = assembled_file
        self.output_path = output_path

    def run(self):
        # Build the Transdecoder commands
        assembly_file = self.assembled_file
        output_folder = self.output_path

        start_time = time.time()  # Start the timer

        # Run TransDecoder.LongOrfs
        activate_command1 = f"conda run -n transdecoder_env TransDecoder.LongOrfs -t {assembly_file} --output_dir {output_folder}/Transdecoder_output"
        process = subprocess.Popen(activate_command1, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        # Run TransDecoder.Predict
        activate_command2 = f"conda run -n transdecoder_env TransDecoder.Predict -t {assembly_file} --output_dir {output_folder}/Transdecoder_output"
        process = subprocess.Popen(activate_command2, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        destination_folder = f"{output_folder}/Transdecoder_output"

        # Define the file extensions to be transferred
        file_extensions = [".transdecoder.bed", ".transdecoder.cds", ".transdecoder.gff3", ".transdecoder.pep"]

        # Loop over the files in the current directory
        for file_name in os.listdir():
            # Check if the file has one of the specified extensions
            if any(file_name.endswith(extension) for extension in file_extensions):
                # Construct the full paths for the source and destination files
                source_path = os.path.abspath(file_name)
                destination_path = os.path.join(destination_folder, file_name)
                # Move the file to the destination folder
                shutil.move(source_path, destination_path)

        end_time = time.time()  # Stop the timer
        duration = end_time - start_time  # Calculate the duration

        self.process_completed.emit(duration)

class Transdecoder_GUI(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Transdecoder Tool")
        self.center()  # Center the window on the screen

        # Set up the GUI elements
        self.assembled_label = QLabel("Select an assembled file (.fasta format):")
        self.assembled_button = QPushButton("Select File")
        self.assembled_file = ""
        self.assembled_path_label = QLabel()

        self.output_label = QLabel("Select an output folder:")
        self.output_button = QPushButton("Select Folder")
        self.output_path = ""
        self.output_path_label = QLabel()

        self.run_button = QPushButton("Run TransDecoder")

        # Set up the layout
        assembled_layout = QHBoxLayout()
        assembled_layout.addWidget(self.assembled_label)
        assembled_layout.addWidget(self.assembled_button)
        assembled_layout.addWidget(self.assembled_path_label)

        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_label)
        output_layout.addWidget(self.output_button)
        output_layout.addWidget(self.output_path_label)

        layout = QVBoxLayout()
        layout.addLayout(assembled_layout)
        layout.addLayout(output_layout)
        layout.addWidget(self.run_button)
        self.setLayout(layout)

        # Connect the signals to the slots
        self.assembled_button.clicked.connect(self.select_assembled_file)
        self.output_button.clicked.connect(self.select_output_folder)
        self.run_button.clicked.connect(self.run_transdecoder)

        # Create the Transdecoder thread
        self.transdecoder_thread = TransdecoderThread("", "")

    def center(self):
        """Center the window on the screen."""
        screen_rect = QDesktopWidget().availableGeometry()
        center_pos = screen_rect.center()
        self.move(center_pos.x() - self.width() // 2, center_pos.y() - self.height() // 2)

    def select_assembled_file(self):
        # Open a file dialog to select the assembled file
        file_name, _ = QFileDialog.getOpenFileName(self, "Select File", "", "FASTA Files (*.fasta)")
        self.assembled_file = file_name
        self.assembled_path_label.setText(file_name) # Update the file path label

    def select_output_folder(self):
        # Open a file dialog to select the output folder
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        self.output_path = directory
        self.output_path_label.setText(directory) # Update the path label

    def run_transdecoder(self):
        # Check if all required inputs are provided
        if not self.assembled_file:
            QMessageBox.warning(self, "Missing Input", "Please select an assembly file.")
            return
        if not self.output_path:
            QMessageBox.warning(self, "Missing Input", "Please select an output folder.")
            return

        self.running_msg = QMessageBox(self)
        self.running_msg.setIcon(QMessageBox.Information)
        self.running_msg.setText("The process is running. Please wait until the process finishes.")
        self.running_msg.setWindowTitle("Running")
        self.running_msg.setStandardButtons(QMessageBox.Cancel)
        self.running_msg.show()

        # Set the assembled file and output path for the Transdecoder thread
        self.transdecoder_thread.assembled_file = self.assembled_file
        self.transdecoder_thread.output_path = self.output_path

        # Connect the signal from the Transdecoder thread to the slot
        self.transdecoder_thread.process_completed.connect(self.show_result)

        # Start the Transdecoder thread
        self.transdecoder_thread.start()
        

    def show_result(self, duration):
        # Close the running message box
        if self.running_msg is not None:
            self.running_msg.close()


        # Display a message box with the duration
        duration_str = time.strftime("%Hh %Mm %Ss", time.gmtime(duration))
        QMessageBox.information(self, "Transdecoder Completed", f"Transdecoder has finished running.\nDuration: {duration_str}")

        # Count the number of ORFs
        orf_file = os.path.join(self.output_path, "Transdecoder_output/longest_orfs.pep")
        if os.path.exists(orf_file):
            with open(orf_file, 'r') as file:
                num_orfs = sum(1 for line in file if line.startswith('>'))
            QMessageBox.information(self, "Number of ORFs", f"Number of ORFs: {num_orfs}")
        else:
            QMessageBox.warning(self, "ORF File Not Found", "longest_orfs.pep file not found.")

        # Close the window
        self.close()


if __name__ == "__main__":
    app = QApplication([])
    app.setStyle('Fusion')
    gui = Transdecoder_GUI()
    gui.show()
    app.exec_()
