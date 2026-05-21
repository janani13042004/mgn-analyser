import os
import subprocess
import threading
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QFileDialog, 
                             QHBoxLayout, QVBoxLayout, QMessageBox, QCheckBox, QGridLayout, QComboBox)
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
import datetime

class Signal(QObject):
    completed = pyqtSignal()
    error = pyqtSignal(str)

class InterProScan_GUI(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('InterProScan GUI')
        self.center()

        # GUI elements
        self.fasta_label = QLabel("Select a FASTA file:")
        self.fasta_button = QPushButton("Select File")
        self.fasta_file = ""
        self.fasta_path_label = QLabel()


        # Create a dropdown (QComboBox) for input data type
        self.input_data_type_label = QLabel("Select Input Data Type:")
        self.input_data_type_dropdown = QComboBox()
        self.input_data_type_dropdown.addItems(["Protein", "Nucleotide"])

        # Additional GUI elements for selecting output directory
        self.output_label = QLabel("Select an Output Directory:")
        self.output_button = QPushButton("Select Directory")
        self.output_dir = ""  # Will store the selected output directory
        self.output_path_label = QLabel()

        self.databases = ["SMART", "Pfam", "CDD", "Gene3D", "HAMAP", "PANTHER", "PRINTS", "SFLD", "SUPERFAMILY", "TIGRFAM", "COILS", "MobiDBLite", "PIRSF", "PROSITEPATTERNS", "PROSITEPROFILES"]
        self.database_checkboxes = []

        # Create checkboxes for databases
        self.db_grid = QGridLayout()
        for i, db in enumerate(self.databases):
            checkbox = QCheckBox(db)
            self.database_checkboxes.append(checkbox)
            self.db_grid.addWidget(checkbox, i // 2, i % 2)

        self.run_button = QPushButton("Run InterProScan")


        # Layouts
        layout = QVBoxLayout()  

        fasta_layout = QHBoxLayout()
        fasta_layout.addWidget(self.fasta_label)
        fasta_layout.addWidget(self.fasta_button)
        fasta_layout.addWidget(self.fasta_path_label)

        input_data_type_layout = QHBoxLayout()
        input_data_type_layout.addWidget(self.input_data_type_label)
        input_data_type_layout.addWidget(self.input_data_type_dropdown)
        layout.addLayout(input_data_type_layout)  

        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_label)
        output_layout.addWidget(self.output_button)
        output_layout.addWidget(self.output_path_label)

        layout.addLayout(fasta_layout)
        layout.addLayout(self.db_grid)
        layout.addLayout(output_layout)  # add the output layout after the database grid
        layout.addWidget(self.run_button)
        self.setLayout(layout)

        # Signal-slot connections
        self.fasta_button.clicked.connect(self.select_fasta_file)
        self.output_button.clicked.connect(self.select_output_directory)
        self.run_button.clicked.connect(self.run_interproscan)

        self.signal = Signal()
        self.signal.completed.connect(self.show_success_msg)
        self.signal.error.connect(self.show_error_msg)

    def center(self):
        from PyQt5.QtWidgets import QDesktopWidget
        screen_rect = QDesktopWidget().availableGeometry()
        center_pos = screen_rect.center()
        self.move(center_pos.x() - self.width() // 2, center_pos.y() - self.height() // 2)

    def select_fasta_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select File", "", "FASTA Files (*.fasta)")
        if file_name:
            self.fasta_file = file_name
            self.fasta_path_label.setText(file_name)    

    def select_output_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if dir_path:
            self.output_dir = dir_path
            self.output_path_label.setText(dir_path)

    def run_interproscan(self):
        # Check if FASTA file was selected
        if not self.fasta_file:
            self.show_message_box("Error", "Please select a FASTA file.")
            return
        
        # Check if output directory is selected
        if not self.output_dir:
            self.show_message_box("Error", "Please select an output directory.")
            return
        
        # Check if at least one database is selected
        selected_databases = [db.text() for db in self.database_checkboxes if db.isChecked()]
        if not selected_databases:
            self.show_message_box("Error", "Please select at least one database.")
            return

        # Show the user that the process has started
        self.show_running_msg()

        # Get the selected data type
        selected_data_type = self.input_data_type_dropdown.currentText()
        data_type_flag = 'p' if selected_data_type == "Protein" else 'n'
        
        def run_process():
            # 1. Set up directories
            split_files_dir = os.path.join(self.output_dir, "split_files")
            results_dir = os.path.join(self.output_dir, "interproscan_result")

            os.makedirs(split_files_dir, exist_ok=True)
            os.makedirs(results_dir, exist_ok=True)

            # 2. Split FASTA files into smaller chunks
            split_cmd = f"conda run -n splitter_env fasta-splitter --n-parts 1000 --out-dir {split_files_dir} {self.fasta_file}"
            result = subprocess.run(split_cmd, shell=True)
            if result.returncode != 0:
                self.signal.error.emit("Error during fasta-splitter execution.")
                return

            for db in selected_databases:
                cmd = (
                    f'for filepath in {split_files_dir}/*.part-*.fasta; '
                    f'do '
                    f'conda run -n interproscan_env interproscan.sh -i "$filepath" -t {data_type_flag} -f tsv -appl {db} --goterms --pathways -o "${{filepath}}_{db}.tsv" -dp -cpu 16; '
                    f'done'
                )
                result = subprocess.run(cmd, shell=True)
                if result.returncode != 0:
                    self.signal.error.emit(f"Error during InterProScan execution for database: {db}.")
                    continue

                cmd2 = f"cat {split_files_dir}/*_{db}.tsv > {results_dir}/{db}_combined.tsv"
                result = subprocess.run(cmd2, shell=True)
                if result.returncode != 0:
                    self.signal.error.emit(f"Error collating results for database: {db}.")
                    continue

            self.signal.completed.emit()

        thread = threading.Thread(target=run_process)
        thread.start()

    @pyqtSlot()
    def show_running_msg(self):
        self.running_msg = QMessageBox(self)
        self.running_msg.setIcon(QMessageBox.Information)
        self.running_msg.setText("The process is running. Please wait until the process finishes.")
        self.running_msg.setWindowTitle("Running")
        self.running_msg.setStandardButtons(QMessageBox.NoButton)  # No buttons since this is just an info box
        self.running_msg.show()

    @pyqtSlot()
    def show_success_msg(self):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.running_msg.close()  # Close the "process running" message box
        success_msg = QMessageBox(self)
        success_msg.setIcon(QMessageBox.Information)
        success_msg.setText(f"InterProScan finished successfully at {timestamp}.")
        success_msg.setWindowTitle("Success")
        success_msg.setStandardButtons(QMessageBox.Ok)
        success_msg.buttonClicked.connect(self.close_windows)
        success_msg.show()

    @pyqtSlot(str)
    def show_error_msg(self, error_message):
        if self.running_msg:
            self.running_msg.close()  # Close the "process running" message box
        error_msg = QMessageBox(self)
        error_msg.setIcon(QMessageBox.Critical)
        error_msg.setText(error_message)
        error_msg.setWindowTitle("Error")
        error_msg.setStandardButtons(QMessageBox.Ok)
        error_msg.show()

    def close_windows(self):
        if self.running_msg:
            self.running_msg.close()  # Close the "Running" message box
        self.close()

if __name__ == "__main__":
    app = QApplication([])
    gui = InterProScan_GUI()
    gui.show()
    app.exec_()
