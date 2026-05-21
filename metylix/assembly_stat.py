#!/usr/bin/env python3

import sys
import subprocess
import os
from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QLabel, QPushButton,
    QFileDialog, QTextEdit, QMessageBox
)

class AssemblyStatsGUI(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AssemblyStats")
        self.setMinimumWidth(600)

        layout = QVBoxLayout()

        self.label = QLabel("No FASTA file selected.")
        self.select_button = QPushButton("Select Assembled FASTA File")
        self.run_button = QPushButton("Run assemblystats.pl")
        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)

        layout.addWidget(self.select_button)
        layout.addWidget(self.label)
        layout.addWidget(self.run_button)
        layout.addWidget(QLabel("Output Preview:"))
        layout.addWidget(self.output_display)

        self.setLayout(layout)

        self.select_button.clicked.connect(self.select_file)
        self.run_button.clicked.connect(self.run_assembly_stats)

        self.fasta_file = ""

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Assembled FASTA File", "", "FASTA Files (*.fa *.fasta)"
        )
        if file_path:
            self.fasta_file = file_path
            self.label.setText(f"Selected: {file_path}")

    def run_assembly_stats(self):
        if not self.fasta_file:
            QMessageBox.warning(self, "No File", "Please select a FASTA file first.")
            return

        # Locate the Perl script in the same folder as this Python script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        perl_script = os.path.join(script_dir, "assemblystats.pl")

        if not os.path.isfile(perl_script):
            QMessageBox.critical(self, "Script Not Found", "assemblystats.pl not found in the script directory.")
            return

        # Output .txt file in the same folder as input FASTA
        output_file = os.path.splitext(self.fasta_file)[0] + "_assembly_stats.txt"

        try:
            command = [
                "perl", perl_script, self.fasta_file
            ]
            result = subprocess.run(command, capture_output=True, text=True)

            if result.returncode == 0:
                with open(output_file, "w") as f:
                    f.write(result.stdout)
                self.output_display.setText(result.stdout)
                QMessageBox.information(
                    self, "Assembly Stats Completed",
                    f"Statistics saved to:\n{output_file}\n\nPreview:\n{result.stdout[:500]}..."
                )
            else:
                self.output_display.setText(result.stderr)
                QMessageBox.critical(self, "Error", result.stderr)

        except Exception as e:
            QMessageBox.critical(self, "Execution Failed", str(e))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = AssemblyStatsGUI()
    gui.show()
    sys.exit(app.exec_())

