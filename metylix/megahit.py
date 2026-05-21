import sys
import os
import time
import subprocess
import shutil
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton, QFileDialog, QGridLayout, QWidget,
    QMessageBox, QTextEdit, QLineEdit, QDesktopWidget
)
from PyQt5.QtCore import QThread, pyqtSignal


class MegahitWorker(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool)

    def __init__(self, cmd):
        super().__init__()
        self.cmd = cmd

    def run(self):
        try:
            process = subprocess.Popen(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # merge stderr into stdout for live logging
                text=True
            )
            for line in process.stdout:
                self.log_signal.emit(line.rstrip())
            process.wait()
            self.finished_signal.emit(process.returncode == 0)
        except Exception as e:
            self.log_signal.emit(f"Exception: {str(e)}")
            self.finished_signal.emit(False)


class MegahitGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.forward_files = []
        self.reverse_files = []
        self.single_files = []
        self.output_folder = ""
        self.worker = None

        layout = QGridLayout()

        # Forward reads
        layout.addWidget(QLabel("Forward Reads (R1, paired-end):"), 0, 0)
        self.fwd_text = QTextEdit()
        self.fwd_text.setReadOnly(True)
        self.fwd_text.setMaximumHeight(60)
        layout.addWidget(self.fwd_text, 0, 1, 1, 2)
        fwd_btn = QPushButton("Browse R1")
        fwd_btn.clicked.connect(self.select_forward_files)
        layout.addWidget(fwd_btn, 1, 1)
        fwd_clear = QPushButton("Clear R1")
        fwd_clear.clicked.connect(self.clear_forward_files)
        layout.addWidget(fwd_clear, 1, 2)

        # Reverse reads
        layout.addWidget(QLabel("Reverse Reads (R2, paired-end):"), 2, 0)
        self.rev_text = QTextEdit()
        self.rev_text.setReadOnly(True)
        self.rev_text.setMaximumHeight(60)
        layout.addWidget(self.rev_text, 2, 1, 1, 2)
        rev_btn = QPushButton("Browse R2")
        rev_btn.clicked.connect(self.select_reverse_files)
        layout.addWidget(rev_btn, 3, 1)
        rev_clear = QPushButton("Clear R2")
        rev_clear.clicked.connect(self.clear_reverse_files)
        layout.addWidget(rev_clear, 3, 2)

        # Single-end reads
        layout.addWidget(QLabel("Single-End Reads (-r):"), 4, 0)
        self.single_text = QTextEdit()
        self.single_text.setReadOnly(True)
        self.single_text.setMaximumHeight(60)
        layout.addWidget(self.single_text, 4, 1, 1, 2)
        single_btn = QPushButton("Browse Single-end")
        single_btn.clicked.connect(self.select_single_files)
        layout.addWidget(single_btn, 5, 1)
        single_clear = QPushButton("Clear Single-end")
        single_clear.clicked.connect(self.clear_single_files)
        layout.addWidget(single_clear, 5, 2)

        # Output folder
        layout.addWidget(QLabel("Select Output Folder:"), 6, 0)
        self.out_label = QLabel("No folder selected")
        layout.addWidget(self.out_label, 6, 1)
        out_btn = QPushButton("Browse")
        out_btn.clicked.connect(self.select_output_folder)
        layout.addWidget(out_btn, 6, 2)

        # Min contig length
        layout.addWidget(QLabel("Min Contig Length (default 500):"), 7, 0)
        self.min_contig_edit = QLineEdit()
        self.min_contig_edit.setPlaceholderText("500")
        layout.addWidget(self.min_contig_edit, 7, 1, 1, 2)

        # Threads
        layout.addWidget(QLabel("Threads (default 1):"), 8, 0)
        self.thread_edit = QLineEdit()
        self.thread_edit.setPlaceholderText("1")
        layout.addWidget(self.thread_edit, 8, 1, 1, 2)

        # Run button
        self.run_btn = QPushButton("Run MEGAHIT")
        self.run_btn.clicked.connect(self.run_megahit)
        layout.addWidget(self.run_btn, 9, 0, 1, 3)

        # Log output
        layout.addWidget(QLabel("Log Output:"), 10, 0)
        self.log_window = QTextEdit()
        self.log_window.setReadOnly(True)
        layout.addWidget(self.log_window, 11, 0, 1, 3)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        self.setWindowTitle("MEGAHIT GUI")
        self.resize(750, 700)
        self.center_window()

    def center_window(self):
        frame = self.frameGeometry()
        center = QDesktopWidget().availableGeometry().center()
        frame.moveCenter(center)
        self.move(frame.topLeft())

    def select_forward_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Forward Reads (R1)", "", "FASTQ files (*.fastq *.fq *.gz)"
        )
        if files:
            self.forward_files = files
            self.fwd_text.setPlainText("\n".join(files))

    def clear_forward_files(self):
        self.forward_files = []
        self.fwd_text.clear()

    def select_reverse_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Reverse Reads (R2)", "", "FASTQ files (*.fastq *.fq *.gz)"
        )
        if files:
            self.reverse_files = files
            self.rev_text.setPlainText("\n".join(files))

    def clear_reverse_files(self):
        self.reverse_files = []
        self.rev_text.clear()

    def select_single_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Single-End Reads", "", "FASTQ files (*.fastq *.fq *.gz)"
        )
        if files:
            self.single_files = files
            self.single_text.setPlainText("\n".join(files))

    def clear_single_files(self):
        self.single_files = []
        self.single_text.clear()

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_folder = folder
            self.out_label.setText(folder)

    def run_megahit(self):
        # --- Validation ---
        if not self.output_folder:
            QMessageBox.warning(self, "Missing Output Folder", "Please select an output folder.")
            return

        has_paired = (
            bool(self.forward_files)
            and bool(self.reverse_files)
            and len(self.forward_files) == len(self.reverse_files)
        )
        has_single = bool(self.single_files)

        if not has_paired and not has_single:
            QMessageBox.warning(
                self, "Missing Input",
                "Please provide paired-end reads (both R1 and R2 with equal file counts) or single-end reads."
            )
            return

        if bool(self.forward_files) != bool(self.reverse_files):
            QMessageBox.warning(
                self, "Mismatched Reads",
                f"R1 has {len(self.forward_files)} file(s) but R2 has {len(self.reverse_files)} file(s). Counts must match."
            )
            return

        if not shutil.which("conda"):
            QMessageBox.critical(self, "Error", "Conda is not available. Make sure conda is installed and on PATH.")
            return

        try:
            threads = int(self.thread_edit.text().strip()) if self.thread_edit.text().strip() else 1
        except ValueError:
            threads = 1

        try:
            min_contig_len = int(self.min_contig_edit.text().strip()) if self.min_contig_edit.text().strip() else 500
        except ValueError:
            min_contig_len = 500

        # --- FIX: Always create a fresh timestamped subdirectory so MEGAHIT never sees an existing output dir ---
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(self.output_folder, f"megahit_{timestamp}")
        # output_dir does not exist yet — MEGAHIT will create it

        # --- Build command as a proper list (no shell=True, no shlex.quote needed) ---
        cmd = ["conda", "run", "-n", "megahit_env", "megahit"]

        if has_paired:
            cmd += ["-1", ",".join(self.forward_files)]
            cmd += ["-2", ",".join(self.reverse_files)]

        if has_single:
            cmd += ["-r", ",".join(self.single_files)]

        cmd += [
            "-o", output_dir,
            "--min-contig-len", str(min_contig_len),
            "-t", str(threads),
        ]

        # Log the command
        display_cmd = " ".join(cmd)
        self.log_window.append(f"Output directory: {output_dir}\n")
        self.log_window.append(f"Running command:\n{display_cmd}\n")
        self.log_window.append("Executing...\n")

        # Save the script for reference
        try:
            script_path = os.path.join(self.output_folder, "run_megahit.sh")
            with open(script_path, "w") as f:
                f.write("#!/bin/bash\n" + display_cmd + "\n")
            self.log_window.append(f"Script saved to: {script_path}\n")
        except Exception as e:
            self.log_window.append(f"(Could not save script: {e})\n")

        # Disable run button while running
        self.run_btn.setEnabled(False)
        self.run_btn.setText("Running...")

        # Run in background thread so UI stays responsive
        self.worker = MegahitWorker(cmd)
        self.worker.log_signal.connect(self.append_log)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def append_log(self, text):
        self.log_window.append(text)
        # Auto-scroll to bottom
        self.log_window.verticalScrollBar().setValue(
            self.log_window.verticalScrollBar().maximum()
        )

    def on_finished(self, success):
        self.run_btn.setEnabled(True)
        self.run_btn.setText("Run MEGAHIT")
        if success:
            self.log_window.append("\n✅ Assembly completed successfully.")
            QMessageBox.information(self, "MEGAHIT", "Assembly completed successfully!")
        else:
            self.log_window.append("\n❌ MEGAHIT encountered an error. Check the log above.")
            QMessageBox.critical(self, "MEGAHIT Error", "An error occurred. Check the log window for details.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = MegahitGUI()
    gui.show()
    sys.exit(app.exec_())
