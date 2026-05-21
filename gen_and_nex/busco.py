import os
import shutil
import subprocess
import time
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QWidget, QComboBox, QLabel, QPushButton,
    QFileDialog, QHBoxLayout, QVBoxLayout, QMessageBox,
    QTextEdit, QDesktopWidget, QProgressBar
)
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QThread


# ── Worker thread — keeps UI responsive ──────────────────────────────
class BuscoWorker(QThread):
    log_signal       = pyqtSignal(str)
    completed_signal = pyqtSignal(float)
    error_signal     = pyqtSignal(str)

    def __init__(self, fasta_file, busco_database, output_dir):
        super().__init__()
        self.fasta_file      = fasta_file
        self.busco_database  = busco_database
        self.output_dir      = output_dir

    def run(self):
        start_time = time.time()

        # FIX 3: Write output directly into the selected folder using a
        # timestamped name — avoids the "already exists" clash and the
        # fragile shutil.move step entirely.
        timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_name   = f"busco_{timestamp}"           # e.g. busco_20250520_143022
        out_path   = os.path.join(self.output_dir, out_name)

        cmd = [
            "conda", "run", "-n", "busco_env",
            "busco",
            "-i", self.fasta_file,
            "-o", out_path,           # full absolute path → no move needed
            "-l", self.busco_database,
            "-m", "transcriptome",
            "--cpu", "16",
            # FIX 4: removed -f (force) because we always use a fresh timestamped dir
        ]

        self.log_signal.emit("Running command:\n" + " ".join(cmd) + "\n")

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,   # merge so all output is visible live
                text=True
            )
            for line in process.stdout:
                self.log_signal.emit(line.rstrip())
            process.wait()
        except Exception as e:
            self.error_signal.emit(f"Failed to launch BUSCO:\n{e}")
            return

        if process.returncode != 0:
            self.error_signal.emit(
                "BUSCO analysis failed.\nCheck the log window for details."
            )
            return

        # Generate summary plot
        plot_cmd = [
            "conda", "run", "-n", "busco_env",
            "generate_plot.py", "-wd", out_path
        ]
        self.log_signal.emit("\nGenerating plot...\n" + " ".join(plot_cmd))
        subprocess.run(plot_cmd)   # non-fatal if it fails

        elapsed = time.time() - start_time
        self.completed_signal.emit(elapsed)


# ── Main GUI ──────────────────────────────────────────────────────────
class BUSCO_GUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BUSCO")
        self.fasta_file     = ""
        self.output_dir     = ""
        self.busco_database = ""
        self.worker         = None

        self._build_ui()
        self.center()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)

        # ── FASTA file row ────────────────────────────────────────
        fasta_row = QHBoxLayout()
        fasta_row.addWidget(QLabel("Select a FASTA file:"))
        self.fasta_path_label = QLabel("No file selected")
        self.fasta_path_label.setStyleSheet("color: grey;")
        fasta_btn = QPushButton("Select File")
        fasta_btn.clicked.connect(self.select_fasta_file)
        fasta_row.addWidget(fasta_btn)
        fasta_row.addWidget(self.fasta_path_label, 1)
        main_layout.addLayout(fasta_row)

        # ── Database combo row ────────────────────────────────────
        busco_row = QHBoxLayout()
        busco_row.addWidget(QLabel("BUSCO database\n(e.g. viridiplantae for plants):"))
        self.busco_combo = QComboBox()

        # FIX 1: load database.txt relative to THIS script's folder,
        # not the current working directory
        db_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.txt")
        if os.path.exists(db_file):
            with open(db_file) as f:
                databases = [line.strip() for line in f if line.strip()]
            self.busco_combo.addItems(databases)
        else:
            # Fallback hardcoded list so the GUI still opens
            fallback = [
                "viridiplantae_odb10", "embryophyta_odb10", "eudicots_odb10",
                "liliopsida_odb10", "bacteria_odb10", "fungi_odb10",
                "metazoa_odb10", "insecta_odb10", "vertebrata_odb10",
            ]
            self.busco_combo.addItems(fallback)
            self._warn(
                "database.txt not found",
                f"Could not find:\n{db_file}\n\nUsing a built-in fallback list."
            )

        self.busco_database = self.busco_combo.currentText()
        self.busco_combo.currentIndexChanged.connect(self.update_busco_database)
        busco_row.addWidget(self.busco_combo, 1)
        main_layout.addLayout(busco_row)

        # ── Output directory row ──────────────────────────────────
        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Select Output directory:"))
        self.out_path_label = QLabel("No directory selected")
        self.out_path_label.setStyleSheet("color: grey;")
        out_btn = QPushButton("Select Directory")
        out_btn.clicked.connect(self.select_output_dir)
        out_row.addWidget(out_btn)
        out_row.addWidget(self.out_path_label, 1)
        main_layout.addLayout(out_row)

        # ── Run button ────────────────────────────────────────────
        self.run_button = QPushButton("Run BUSCO")
        self.run_button.setFixedHeight(36)
        self.run_button.clicked.connect(self.run_busco)
        main_layout.addWidget(self.run_button)

        # ── Progress bar (indeterminate while running) ─────────────
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)   # indeterminate
        self.progress.setVisible(False)
        main_layout.addWidget(self.progress)

        # ── Log window ────────────────────────────────────────────
        main_layout.addWidget(QLabel("Log Output:"))
        self.log_window = QTextEdit()
        self.log_window.setReadOnly(True)
        self.log_window.setMinimumHeight(200)
        main_layout.addWidget(self.log_window)

        self.resize(750, 500)

    def center(self):
        screen_rect = QDesktopWidget().availableGeometry()
        center_pos  = screen_rect.center()
        self.move(center_pos.x() - self.width() // 2,
                  center_pos.y() - self.height() // 2)

    # ── Slots ─────────────────────────────────────────────────────
    def select_fasta_file(self):
        # FIX 5: accept .fasta, .fa and .fna
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Select FASTA File", "",
            "FASTA Files (*.fasta *.fa *.fna)"
        )
        if file_name:
            self.fasta_file = file_name
            self.fasta_path_label.setText(file_name)
            self.fasta_path_label.setStyleSheet("color: black;")

    def update_busco_database(self):
        self.busco_database = self.busco_combo.currentText()

    def select_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if dir_path:
            self.output_dir = dir_path
            self.out_path_label.setText(dir_path)
            self.out_path_label.setStyleSheet("color: black;")

    def run_busco(self):
        # Validation
        if not self.fasta_file:
            self._warn("Missing Input", "Please select a FASTA file.")
            return
        if not self.busco_database:
            self._warn("Missing Input", "Please select a BUSCO database.")
            return
        if not self.output_dir:
            self._warn("Missing Output Directory", "Please select an output directory.")
            return

        # Disable button, show progress bar
        self.run_button.setEnabled(False)
        self.run_button.setText("Running...")
        self.progress.setVisible(True)
        self.log_window.clear()

        # FIX 2: use QThread instead of threading.Thread,
        # and do NOT show a blocking modal "Running" dialog
        self.worker = BuscoWorker(self.fasta_file, self.busco_database, self.output_dir)
        self.worker.log_signal.connect(self.append_log)
        self.worker.completed_signal.connect(self.on_success)
        self.worker.error_signal.connect(self.on_error)
        self.worker.start()

    @pyqtSlot(str)
    def append_log(self, text):
        self.log_window.append(text)
        self.log_window.verticalScrollBar().setValue(
            self.log_window.verticalScrollBar().maximum()
        )

    @pyqtSlot(float)
    def on_success(self, elapsed):
        self._reset_button()
        elapsed_str = time.strftime("%Hh %Mm %Ss", time.gmtime(elapsed))
        self.log_window.append(f"\n✅ BUSCO finished successfully.  Elapsed: {elapsed_str}")
        QMessageBox.information(self, "Success",
                                f"BUSCO finished successfully.\nElapsed Time: {elapsed_str}")

    @pyqtSlot(str)
    def on_error(self, msg):
        self._reset_button()
        self.log_window.append(f"\n❌ ERROR: {msg}")
        QMessageBox.critical(self, "BUSCO Failed", msg)

    def _reset_button(self):
        self.run_button.setEnabled(True)
        self.run_button.setText("Run BUSCO")
        self.progress.setVisible(False)

    def _warn(self, title, msg):
        QMessageBox.warning(self, title, msg)


if __name__ == "__main__":
    app = QApplication([])
    app.setStyle("Fusion")
    gui = BUSCO_GUI()
    gui.show()
    app.exec_()
