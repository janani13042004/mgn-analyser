import sys
import os
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QFileDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QMessageBox
)
from PyQt5.QtCore import QThread, pyqtSignal


class WorkerThread(QThread):
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, cmd):
        super().__init__()
        self.cmd = cmd

    def run(self):
        self.output_signal.emit(f"$ {' '.join(self.cmd)}\n")
        try:
            result = subprocess.run(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            self.output_signal.emit(result.stdout)
        except Exception as e:
            self.output_signal.emit(f"Error: {str(e)}\n")
        self.finished_signal.emit()


class AnnotationGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Functional Annotation (eggNOG + PfamScan)")
        self.resize(700, 500)
        self.init_ui()
        self.thread = None  # placeholder for current thread

    def init_ui(self):
        layout = QVBoxLayout()

        # Input .faa file
        self.faa_input = QLineEdit()
        browse_faa = QPushButton("Browse")
        browse_faa.clicked.connect(self.browse_faa)
        layout.addLayout(self.hbox_with_label("Input .faa file:", self.faa_input, browse_faa))

        # Output directory
        self.output_dir = QLineEdit()
        browse_output = QPushButton("Browse")
        browse_output.clicked.connect(self.browse_output_dir)
        layout.addLayout(self.hbox_with_label("Output Directory:", self.output_dir, browse_output))

        # eggNOG DB path
        self.eggnog_db_input = QLineEdit()
        browse_eggnog = QPushButton("Browse")
        browse_eggnog.clicked.connect(lambda: self.browse_dir(self.eggnog_db_input))
        layout.addLayout(self.hbox_with_label("eggNOG DB Directory:", self.eggnog_db_input, browse_eggnog))

        # Pfam DB path
        self.pfam_db_input = QLineEdit()
        browse_pfam = QPushButton("Browse")
        browse_pfam.clicked.connect(lambda: self.browse_dir(self.pfam_db_input))
        layout.addLayout(self.hbox_with_label("Pfam DB Directory:", self.pfam_db_input, browse_pfam))

        # Threads
        self.threads_input = QLineEdit()
        self.threads_input.setPlaceholderText("e.g., 8")
        layout.addLayout(self.hbox_with_label("Threads:", self.threads_input))

        # Run button
        run_button = QPushButton("Run Annotation")
        run_button.clicked.connect(self.run_annotation)
        layout.addWidget(run_button)

        # Output log
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

    def browse_faa(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select predicted.faa")
        if file_path:
            self.faa_input.setText(file_path)

    def browse_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if dir_path:
            self.output_dir.setText(dir_path)

    def browse_dir(self, target_input):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if dir_path:
            target_input.setText(dir_path)

    def run_annotation(self):
        faa = self.faa_input.text().strip()
        output_dir = self.output_dir.text().strip()
        eggnog_db = self.eggnog_db_input.text().strip()
        pfam_db = self.pfam_db_input.text().strip()
        threads = self.threads_input.text().strip()

        eggnog_env = "eggnog_env"
        pfamscan_env = "pfamscan_env"

        if not all([faa, output_dir, eggnog_db, pfam_db, threads]):
            QMessageBox.warning(self, "Missing Fields", "Please fill all required fields.")
            return

        eggnog_cmd = [
            'conda', 'run', '-n', eggnog_env, 'emapper.py',
            '-i', faa,
            '-o', 'eggnog',
            '--itype', 'proteins',
            '--output_dir', output_dir,
            '--data_dir', eggnog_db,
            '--cpu', threads
        ]

        pfam_cmd = [
            'conda', 'run', '-n', pfamscan_env, 'pfam_scan.pl',
            '-fasta', faa,
            '-dir', pfam_db,
            '-outfile', os.path.join(output_dir, 'pfamscan_results.txt')
        ]

        self.console.append("Running eggNOG-mapper...\n")
        self.run_command_threaded(eggnog_cmd, lambda: self.run_command_threaded(pfam_cmd))

    def run_command_threaded(self, cmd, on_finished=None):
        self.thread = WorkerThread(cmd)
        self.thread.output_signal.connect(self.console.append)
        if on_finished:
            self.thread.finished_signal.connect(on_finished)
        self.thread.start()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AnnotationGUI()
    window.show()
    sys.exit(app.exec_())

