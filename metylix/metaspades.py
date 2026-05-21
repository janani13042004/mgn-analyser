import sys
import os
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QFileDialog, QLineEdit, QMessageBox, QComboBox
)

class MetaSPAdesGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MetaSPAdes GUI")
        self.setGeometry(100, 100, 600, 300)
        layout = QVBoxLayout()

        # Input type selection
        self.read_type_label = QLabel("Select Read Type:")
        self.read_type_combo = QComboBox()
        self.read_type_combo.addItems(["Paired-end", "Single-end"])
        self.read_type_combo.currentIndexChanged.connect(self.toggle_inputs)
        layout.addWidget(self.read_type_label)
        layout.addWidget(self.read_type_combo)

        # Paired-end inputs
        self.fwd_label = QLabel("Forward Reads (-1):")
        self.fwd_input = QLineEdit()
        self.fwd_browse = QPushButton("Browse")
        self.fwd_browse.clicked.connect(lambda: self.browse_file(self.fwd_input))
        fwd_layout = QHBoxLayout()
        fwd_layout.addWidget(self.fwd_input)
        fwd_layout.addWidget(self.fwd_browse)

        self.rev_label = QLabel("Reverse Reads (-2):")
        self.rev_input = QLineEdit()
        self.rev_browse = QPushButton("Browse")
        self.rev_browse.clicked.connect(lambda: self.browse_file(self.rev_input))
        rev_layout = QHBoxLayout()
        rev_layout.addWidget(self.rev_input)
        rev_layout.addWidget(self.rev_browse)

        layout.addWidget(self.fwd_label)
        layout.addLayout(fwd_layout)
        layout.addWidget(self.rev_label)
        layout.addLayout(rev_layout)

        # Single-end input
        self.single_label = QLabel("Single Reads (-s):")
        self.single_input = QLineEdit()
        self.single_browse = QPushButton("Browse")
        self.single_browse.clicked.connect(lambda: self.browse_file(self.single_input))
        single_layout = QHBoxLayout()
        single_layout.addWidget(self.single_input)
        single_layout.addWidget(self.single_browse)
        layout.addWidget(self.single_label)
        layout.addLayout(single_layout)

        # Output directory
        self.output_label = QLabel("Output Directory (-o):")
        self.output_input = QLineEdit()
        self.output_browse = QPushButton("Browse")
        self.output_browse.clicked.connect(lambda: self.browse_folder(self.output_input))
        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_input)
        output_layout.addWidget(self.output_browse)
        layout.addWidget(self.output_label)
        layout.addLayout(output_layout)

        # Threads
        self.thread_label = QLabel("Threads (-t):")
        self.thread_input = QLineEdit("4")
        layout.addWidget(self.thread_label)
        layout.addWidget(self.thread_input)

        # Run button
        self.run_button = QPushButton("Run MetaSPAdes")
        self.run_button.clicked.connect(self.run_metaspades)
        layout.addWidget(self.run_button)

        self.setLayout(layout)
        self.toggle_inputs()

    def toggle_inputs(self):
        if self.read_type_combo.currentText() == "Paired-end":
            self.fwd_input.setEnabled(True)
            self.fwd_browse.setEnabled(True)
            self.rev_input.setEnabled(True)
            self.rev_browse.setEnabled(True)
            self.single_input.setEnabled(False)
            self.single_browse.setEnabled(False)
        else:
            self.fwd_input.setEnabled(False)
            self.fwd_browse.setEnabled(False)
            self.rev_input.setEnabled(False)
            self.rev_browse.setEnabled(False)
            self.single_input.setEnabled(True)
            self.single_browse.setEnabled(True)

    def browse_file(self, line_edit):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File")
        if file_path:
            line_edit.setText(file_path)

    def browse_folder(self, line_edit):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if folder_path:
            line_edit.setText(folder_path)

    def run_metaspades(self):
        read_type = self.read_type_combo.currentText()
        output_dir = self.output_input.text()
        threads = self.thread_input.text()

        if not output_dir:
            QMessageBox.warning(self, "Error", "Please select an output directory.")
            return

        if read_type == "Paired-end":
            fwd = self.fwd_input.text()
            rev = self.rev_input.text()
            if not fwd or not rev:
                QMessageBox.warning(self, "Error", "Please select both paired-end files.")
                return
            cmd = f"conda run -n metaspades_env metaspades.py -1 {fwd} -2 {rev} -o {output_dir} -t {threads}"
        else:
            single = self.single_input.text()
            if not single:
                QMessageBox.warning(self, "Error", "Please select a single-end file.")
                return
            cmd = f"conda run -n metaspades_env metaspades.py -s {single} -o {output_dir} -t {threads}"

        try:
            subprocess.run(cmd, shell=True, check=True)
            QMessageBox.information(self, "Success", "MetaSPAdes finished successfully!")
        except subprocess.CalledProcessError:
            QMessageBox.critical(self, "Error", "An error occurred while running MetaSPAdes.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = MetaSPAdesGUI()
    gui.show()
    sys.exit(app.exec_())

