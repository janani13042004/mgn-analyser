import time
import subprocess
import shlex
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton, QFileDialog, QGridLayout, QWidget,
    QMessageBox, QTextEdit, QLineEdit, QComboBox, QDesktopWidget
)

class Kraken2_GUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.forward_files = []
        self.reverse_files = []
        self.db_path = ""
        self.output_folder = ""

        layout = QGridLayout()

        # DB selection
        layout.addWidget(QLabel("Select Kraken2 DB Folder:"), 0, 0)
        self.db_label = QLabel("")
        layout.addWidget(self.db_label, 0, 1)
        db_btn = QPushButton("Browse")
        db_btn.clicked.connect(self.select_db_folder)
        layout.addWidget(db_btn, 0, 2)

        # Forward reads
        layout.addWidget(QLabel("Forward Reads (R1):"), 1, 0)
        self.fwd_text = QTextEdit()
        self.fwd_text.setReadOnly(True)
        layout.addWidget(self.fwd_text, 1, 1, 1, 2)
        fwd_btn = QPushButton("Browse R1")
        fwd_btn.clicked.connect(self.select_forward_files)
        layout.addWidget(fwd_btn, 2, 1)
        fwd_clear = QPushButton("Clear")
        fwd_clear.clicked.connect(self.clear_forward_files)
        layout.addWidget(fwd_clear, 2, 2)

        # Reverse reads
        layout.addWidget(QLabel("Reverse Reads (R2):"), 3, 0)
        self.rev_text = QTextEdit()
        self.rev_text.setReadOnly(True)
        layout.addWidget(self.rev_text, 3, 1, 1, 2)
        rev_btn = QPushButton("Browse R2")
        rev_btn.clicked.connect(self.select_reverse_files)
        layout.addWidget(rev_btn, 4, 1)
        rev_clear = QPushButton("Clear")
        rev_clear.clicked.connect(self.clear_reverse_files)
        layout.addWidget(rev_clear, 4, 2)

        # Output folder
        layout.addWidget(QLabel("Select Output Folder:"), 5, 0)
        self.out_label = QLabel("")
        layout.addWidget(self.out_label, 5, 1)
        out_btn = QPushButton("Browse")
        out_btn.clicked.connect(self.select_output_folder)
        layout.addWidget(out_btn, 5, 2)

        # Sample name
        layout.addWidget(QLabel("Sample Name:"), 6, 0)
        self.sample_edit = QLineEdit()
        layout.addWidget(self.sample_edit, 6, 1, 1, 2)

        # Threads
        layout.addWidget(QLabel("Threads (default 1):"), 7, 0)
        self.thread_edit = QLineEdit()
        self.thread_edit.setPlaceholderText("1")
        layout.addWidget(self.thread_edit, 7, 1, 1, 2)

        # Read type
        layout.addWidget(QLabel("Read Type:"), 8, 0)
        self.read_type_combo = QComboBox()
        self.read_type_combo.addItems(["Single-end", "Paired-end"])
        layout.addWidget(self.read_type_combo, 8, 1, 1, 2)

        # Run button
        run_btn = QPushButton("Run Kraken2")
        run_btn.clicked.connect(self.run_kraken2)
        layout.addWidget(run_btn, 9, 0, 1, 3)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        self.setWindowTitle("Kraken2")
        self.resize(700, 500)
        self.center_window()

    def center_window(self):
        frame = self.frameGeometry()
        center = QDesktopWidget().availableGeometry().center()
        frame.moveCenter(center)
        self.move(frame.topLeft())

    def select_db_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Kraken2 DB Folder")
        if path:
            self.db_path = path
            self.db_label.setText(path)

    def select_forward_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Forward Reads (R1)", "", "FASTQ files (*.fastq *.fq *.gz)")
        if files:
            self.forward_files = files
            self.fwd_text.setPlainText("\n".join(files))

    def clear_forward_files(self):
        self.forward_files = []
        self.fwd_text.clear()

    def select_reverse_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Reverse Reads (R2)", "", "FASTQ files (*.fastq *.fq *.gz)")
        if files:
            self.reverse_files = files
            self.rev_text.setPlainText("\n".join(files))

    def clear_reverse_files(self):
        self.reverse_files = []
        self.rev_text.clear()

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_folder = folder
            self.out_label.setText(folder)

    def run_kraken2(self):
        # Validate inputs
        if not self.db_path or not self.forward_files or not self.output_folder:
            QMessageBox.warning(self, "Missing Input", "Please fill all required fields.")
            return

        sample_name = self.sample_edit.text().strip()
        if not sample_name:
            QMessageBox.warning(self, "Missing Sample", "Enter a sample name.")
            return

        try:
            threads = int(self.thread_edit.text().strip()) if self.thread_edit.text().strip() else 1
        except ValueError:
            threads = 1

        read_type = self.read_type_combo.currentText()

        if read_type == "Single-end":
            files_str = " ".join(shlex.quote(f) for f in self.forward_files)
            output_txt = f"{self.output_folder}/{sample_name}_output.txt"
            report_txt = f"{self.output_folder}/{sample_name}_report.txt"
            classified_out = f"{self.output_folder}/{sample_name}_classified.fq"
            unclassified_out = f"{self.output_folder}/{sample_name}_unclassified.fq"

            cmd = (
                f"kraken2 --db {shlex.quote(self.db_path)} "
                f"--threads {threads} "
                f"--report {shlex.quote(report_txt)} "
                f"--output {shlex.quote(output_txt)} "
                f"--classified-out {shlex.quote(classified_out)} "
                f"--unclassified-out {shlex.quote(unclassified_out)} "
                f"--use-names {files_str}"
            )
            self.run_command(cmd)

        elif read_type == "Paired-end":
            if not self.reverse_files or len(self.forward_files) != len(self.reverse_files):
                QMessageBox.warning(self, "Pairing Error", "Paired-end requires equal number of R1 and R2 files.")
                return

            for r1, r2 in zip(self.forward_files, self.reverse_files):
                sample_tag = sample_name
                output_txt = f"{self.output_folder}/{sample_tag}_output.txt"
                report_txt = f"{self.output_folder}/{sample_tag}_report.txt"
                classified_out = f"{self.output_folder}/{sample_tag}_classified#.fq"
                unclassified_out = f"{self.output_folder}/{sample_tag}_unclassified#.fq"

                cmd = (
                    f"kraken2 --db {shlex.quote(self.db_path)} "
                    f"--threads {threads} "
                    f"--report {shlex.quote(report_txt)} "
                    f"--output {shlex.quote(output_txt)} "
                    f"--classified-out {shlex.quote(classified_out)} "
                    f"--unclassified-out {shlex.quote(unclassified_out)} "
                    f"--use-names --paired {shlex.quote(r1)} {shlex.quote(r2)}"
                )
                self.run_command(cmd)

    def run_command(self, cmd):
        msg = QMessageBox(self)
        msg.setWindowTitle("Running Kraken2")
        msg.setText("Kraken2 is running. Please wait...")
        msg.setStandardButtons(QMessageBox.NoButton)
        msg.show()

        try:
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            while process.poll() is None:
                QApplication.processEvents()
                time.sleep(0.1)

            out, err = process.communicate()
            if process.returncode != 0:
                QMessageBox.critical(self, "Error", f"Kraken2 failed:\n{err.decode()}")
            else:
                QMessageBox.information(self, "Success", "Kraken2 run completed successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Execution Error", str(e))
        finally:
            msg.close()

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    gui = Kraken2_GUI()
    gui.show()
    sys.exit(app.exec_())

