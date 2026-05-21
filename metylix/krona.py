import sys
import subprocess
import threading
import time
from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QLabel, QPushButton, QTextEdit,
    QHBoxLayout, QFileDialog, QMessageBox
)
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

class Signal(QObject):
    started = pyqtSignal()
    completed = pyqtSignal(str, float)  # filename, duration
    error = pyqtSignal(str)

class KronaGUI(QDialog):
    def __init__(self):
        super().__init__()
        self.input_files = []
        self.output_folder = ""
        self.env_name = "krona_env"  # You can change or make it user-configurable
        self.signal = Signal()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Krona Chart Generator")
        self.setFixedSize(700, 500)
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Input .txt Files (from Kraken):"))
        self.input_display = QTextEdit()
        self.input_display.setReadOnly(True)
        layout.addWidget(self.input_display)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add Files")
        add_btn.clicked.connect(self.add_files)
        clr_btn = QPushButton("Clear")
        clr_btn.clicked.connect(self.clear_files)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(clr_btn)
        layout.addLayout(btn_layout)

        out_btn = QPushButton("Select Output Folder")
        out_btn.clicked.connect(self.select_output)
        self.out_label = QLabel("No output folder selected")
        layout.addWidget(out_btn)
        layout.addWidget(self.out_label)

        run_btn = QPushButton("Generate Krona Charts")
        run_btn.clicked.connect(self.run_krona)
        layout.addWidget(run_btn)

        layout.addWidget(QLabel("Logs:"))
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box)

        self.setLayout(layout)

        # Connect signals
        self.signal.started.connect(self.show_running)
        self.signal.completed.connect(self.log_success)
        self.signal.error.connect(self.log_error)

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select .txt Files", "", "Text Files (*.txt)")
        self.input_files.extend(files)
        self.input_display.setText('\n'.join(self.input_files))

    def clear_files(self):
        self.input_files.clear()
        self.input_display.clear()

    def select_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_folder = folder
            self.out_label.setText(folder)

    def run_krona(self):
        if not self.input_files:
            QMessageBox.critical(self, "Error", "Please select at least one .txt file.")
            return
        if not self.output_folder:
            QMessageBox.critical(self, "Error", "Please select an output folder.")
            return

        for file in self.input_files:
            base_name = file.split("/")[-1].split(".")[0]
            out_file = f"{self.output_folder}/{base_name}_krona.html"
            cmd = ['conda', 'run', '-n', self.env_name, 'ktImportText', file, '-o', out_file]
            self.execute_command(cmd, base_name)

    def execute_command(self, cmd, label):
        def worker():
            self.signal.started.emit()
            start = time.time()
            try:
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = process.communicate()
                duration = time.time() - start
                if process.returncode == 0:
                    self.signal.completed.emit(label, duration)
                else:
                    error_msg = stderr.decode() or stdout.decode()
                    self.signal.error.emit(f"[{label}] Error: {error_msg}")
            except Exception as e:
                self.signal.error.emit(f"[{label}] Exception: {str(e)}")

        threading.Thread(target=worker, daemon=True).start()

    @pyqtSlot()
    def show_running(self):
        self.log_box.append("⏳ Running Krona chart generation...")

    @pyqtSlot(str, float)
    def log_success(self, name, seconds):
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        self.log_box.append(f"✅ {name}: Completed in {mins}m {secs}s.\n")

    @pyqtSlot(str)
    def log_error(self, msg):
        self.log_box.append(f"❌ {msg}\n")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = KronaGUI()
    win.show()
    sys.exit(app.exec_())

