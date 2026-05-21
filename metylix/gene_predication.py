#!/usr/bin/env python3

import sys
import os
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QFileDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QMessageBox
)


class FragGeneScanGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gene Prediction using FragGeneScan")
        self.resize(700, 450)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Input contigs file
        self.contigs_input = QLineEdit()
        browse_contigs = QPushButton("Browse")
        browse_contigs.clicked.connect(self.browse_contigs)
        layout.addLayout(self.hbox_with_label("Contigs (final.contigs.fa):", self.contigs_input, browse_contigs))

        # Output directory
        self.output_dir = QLineEdit()
        browse_output = QPushButton("Browse")
        browse_output.clicked.connect(self.browse_output_dir)
        layout.addLayout(self.hbox_with_label("Output Directory:", self.output_dir, browse_output))

        # Threads
        self.threads_input = QLineEdit()
        self.threads_input.setPlaceholderText("e.g., 8")
        layout.addLayout(self.hbox_with_label("Threads:", self.threads_input))

        # Perl script path — auto-filled if found
        self.script_input = QLineEdit()
        default_script_path = os.path.abspath("./FragGeneScan-master/run_FragGeneScan.pl")
        if os.path.exists(default_script_path):
            self.script_input.setText(default_script_path)
        else:
            self.script_input.setPlaceholderText("Perl script not found in ./FragGeneScan-master/")

        browse_script = QPushButton("Browse")
        browse_script.clicked.connect(self.browse_script)
        layout.addLayout(self.hbox_with_label("FragGeneScan Perl Script:", self.script_input, browse_script))

        # Run button
        run_button = QPushButton("Run FragGeneScan")
        run_button.clicked.connect(self.run_fraggenescan)
        layout.addWidget(run_button)

        # Output console
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        layout.addWidget(self.console)

        self.setLayout(layout)

    def hbox_with_label(self, text, widget, extra_widget=None):
        hbox = QHBoxLayout()
        hbox.addWidget(QLabel(text))
        hbox.addWidget(widget)
        if extra_widget:
            hbox.addWidget(extra_widget)
        return hbox

    def browse_contigs(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select final.contigs.fa")
        if file_path:
            self.contigs_input.setText(file_path)

    def browse_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if dir_path:
            self.output_dir.setText(dir_path)

    def browse_script(self):
        script_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select run_FragGeneScan.pl",
            filter="Perl Scripts (*.pl);;All Files (*)"
        )
        if script_path:
            self.script_input.setText(script_path)

    def run_fraggenescan(self):
        contigs = self.contigs_input.text().strip()
        output_dir = self.output_dir.text().strip()
        threads = self.threads_input.text().strip()
        script_path = self.script_input.text().strip()

        if not all([contigs, output_dir, threads, script_path]):
            QMessageBox.warning(self, "Input Error", "Please fill in all fields and select the FragGeneScan script.")
            return

        output_prefix = os.path.join(output_dir, 'predicted')

        # Command to run FragGeneScan using Conda environment
        bash_cmd = (
            f"source activate fraggenescan_env && "
            f"perl {script_path} "
            f"-genome={contigs} "
            f"-out={output_prefix} "
            f"-complete=1 "
            f"-train=complete "
            f"-thread={threads}"
        )

        self.console.append(f"Running in shell:\n{bash_cmd}\n")
        try:
            result = subprocess.run(
                ['bash', '-c', bash_cmd],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            self.console.append(result.stdout)
        except Exception as e:
            self.console.append(f"Error: {str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = FragGeneScanGUI()
    gui.show()
    sys.exit(app.exec_())

