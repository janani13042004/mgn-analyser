import os
import subprocess
import threading
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QFileDialog, 
                             QHBoxLayout, QVBoxLayout, QMessageBox, QCheckBox, QGridLayout)

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

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

        # Additional GUI elements for selecting output directory
        self.output_label = QLabel("Select an Output Directory:")
        self.output_button = QPushButton("Select Directory")
        self.output_dir = ""  # Will store the selected output directory
        self.output_path_label = QLabel()

        self.databases = ["SMART", "Pfam", "CDD", "Gene3D", "HAMAP", "PANTHER", "PRINTS", "SFLD", "SUPERFAMILY", "TIGRFAM"]
        self.database_checkboxes = []

        # Create checkboxes for databases
        self.db_grid = QGridLayout()
        for i, db in enumerate(self.databases):
            checkbox = QCheckBox(db)
            self.database_checkboxes.append(checkbox)
            self.db_grid.addWidget(checkbox, i // 2, i % 2)

        self.run_button = QPushButton("Run InterProScan")

        # Layouts
        fasta_layout = QHBoxLayout()
        fasta_layout.addWidget(self.fasta_label)
        fasta_layout.addWidget(self.fasta_button)
        fasta_layout.addWidget(self.fasta_path_label)

        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_label)
        output_layout.addWidget(self.output_button)
        output_layout.addWidget(self.output_path_label)

        layout = QVBoxLayout()
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
        
        def run_process():
            # Create directories inside the user-selected output directory
            split_files_dir = os.path.join(self.output_dir, "split_files")
            results_dir = os.path.join(self.output_dir, "interproscan_result")

            os.makedirs(split_files_dir, exist_ok=True)
            os.makedirs(results_dir, exist_ok=True)

            # Splitting using the splitter_env
            split_cmd = f"conda run -n splitter_env fasta-splitter --n-parts 1000 --output-dir {split_files_dir} {self.fasta_file}"
            subprocess.run(split_cmd, shell=True)

            # Change to split_files directory for running interproscan
            os.chdir(split_files_dir)

            for db in selected_databases:
                # Running interproscan in interproscan_env for each partition for the given database
                cmd = f'for file in *.part-*.fasta; do conda run -n interproscan_env interproscan.sh -i "$file" -t n -f tsv -appl {db} --goterms -o "${{file%.fasta}}_{db}.tsv" -dp -cpu 16; done'
                subprocess.run(cmd, shell=True)
                # Collate results for the given database into a single file in the interproscan_result directory
                cmd2 = f"cat *_{db}.tsv > {results_dir}/{db}_combined.tsv"
                subprocess.run(cmd2, shell=True)

            # Change back to the original directory (in case of further operations)
            os.chdir(self.output_dir)
            
            self.signal.completed.emit()

        thread = threading.Thread(target=run_process)
        thread.start()


    @pyqtSlot()
    def show_success_msg(self):
        self.show_message_box("Success", "InterProScan finished successfully.")

    @pyqtSlot(str)
    def show_error_msg(self, error_message):
        self.show_message_box("Error", error_message)

    def show_message_box(self, title, message):
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setText(message)
        msg_box.setWindowTitle(title)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.show()

if __name__ == "__main__":
    app = QApplication([])
    gui = InterProScan_GUI()
    gui.show()
    app.exec_()
