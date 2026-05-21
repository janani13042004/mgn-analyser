import sys
from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QLabel, QPushButton, QTextEdit, QHBoxLayout,
    QFileDialog, QMessageBox, QRadioButton, QSpinBox, QGroupBox, QWidget
)
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, Qt
import subprocess
import threading
import time


class Signal(QObject):
    started = pyqtSignal()
    completed = pyqtSignal(float)
    error = pyqtSignal(str)


class TrimGaloreGUI(QDialog):
    def __init__(self):
        super().__init__()
        self.forward_files = []
        self.reverse_files = []
        self.output_folder = ""
        self.signal = Signal()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Trim Galore")
        self.setMinimumSize(650, 600)
        layout = QVBoxLayout()
        layout.setSpacing(15)

        # Mode selection
        mode_group = QGroupBox("Select Mode")
        mode_layout = QHBoxLayout()
        self.single_btn = QRadioButton("Single-end")
        self.paired_btn = QRadioButton("Paired-end")
        self.single_btn.setChecked(True)
        mode_layout.addWidget(self.single_btn)
        mode_layout.addWidget(self.paired_btn)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # Forward files
        layout.addWidget(QLabel("Forward Files:"))
        self.forward_display = QTextEdit()
        self.forward_display.setReadOnly(True)
        layout.addWidget(self.forward_display)

        f_btns = QHBoxLayout()
        add_f = QPushButton("Add")
        add_f.clicked.connect(self.add_forward)
        clr_f = QPushButton("Clear")
        clr_f.clicked.connect(self.clear_forward)
        f_btns.addWidget(add_f)
        f_btns.addWidget(clr_f)
        layout.addLayout(f_btns)

        # Reverse files
        layout.addWidget(QLabel("Reverse Files (Paired-end only):"))
        self.reverse_display = QTextEdit()
        self.reverse_display.setReadOnly(True)
        layout.addWidget(self.reverse_display)

        r_btns = QHBoxLayout()
        add_r = QPushButton("Add")
        add_r.clicked.connect(self.add_reverse)
        clr_r = QPushButton("Clear")
        clr_r.clicked.connect(self.clear_reverse)
        r_btns.addWidget(add_r)
        r_btns.addWidget(clr_r)
        layout.addLayout(r_btns)

        # Output folder
        out_btn = QPushButton("Select Output Folder")
        out_btn.clicked.connect(self.select_output)
        self.out_label = QLabel("No folder selected")
        layout.addWidget(out_btn)
        layout.addWidget(self.out_label)

        # Parameters section
        param_group = QGroupBox("Trimming Parameters")
        param_layout = QVBoxLayout()

        # Quality Cutoff
        quality_layout = QHBoxLayout()
        quality_label = QLabel("Quality Cutoff:")
        self.quality_spin = QSpinBox()
        self.quality_spin.setMinimum(0)
        self.quality_spin.setMaximum(40)
        self.quality_spin.setValue(25)
        self.quality_spin.setFixedWidth(80)
        quality_layout.addWidget(quality_label)
        quality_layout.addWidget(self.quality_spin)
        quality_layout.addStretch()

        # Minimum Length
        length_layout = QHBoxLayout()
        length_label = QLabel("Minimum Length:")
        self.length_spin = QSpinBox()
        self.length_spin.setMinimum(10)
        self.length_spin.setMaximum(1000)
        self.length_spin.setValue(36)
        self.length_spin.setFixedWidth(80)
        length_layout.addWidget(length_label)
        length_layout.addWidget(self.length_spin)
        length_layout.addStretch()

        param_layout.addLayout(quality_layout)
        param_layout.addLayout(length_layout)
        param_group.setLayout(param_layout)
        layout.addWidget(param_group)

        # Run button
        run_btn = QPushButton("Run Trim Galore")
        run_btn.clicked.connect(self.run_trimgalore)
        layout.addWidget(run_btn, alignment=Qt.AlignCenter)

        self.setLayout(layout)

        # Connect signals
        self.signal.started.connect(self.show_running)
        self.signal.completed.connect(self.show_complete)
        self.signal.error.connect(self.show_error)

    def add_forward(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Forward Files")
        self.forward_files.extend(files)
        self.forward_display.setText('\n'.join(self.forward_files))

    def clear_forward(self):
        self.forward_files.clear()
        self.forward_display.clear()

    def add_reverse(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Reverse Files")
        self.reverse_files.extend(files)
        self.reverse_display.setText('\n'.join(self.reverse_files))

    def clear_reverse(self):
        self.reverse_files.clear()
        self.reverse_display.clear()

    def select_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_folder = folder
            self.out_label.setText(folder)

    def run_trimgalore(self):
        if not self.forward_files:
            QMessageBox.critical(self, "Error", "Please select at least one forward file.")
            return
        if self.paired_btn.isChecked() and len(self.forward_files) != len(self.reverse_files):
            QMessageBox.critical(self, "Error", "Number of forward and reverse files must match.")
            return
        if not self.output_folder:
            QMessageBox.critical(self, "Error", "Please select an output folder.")
            return

        base_cmd = ['conda', 'run', '-n', 'base', 'trim_galore']
        base_cmd += ['-q', str(self.quality_spin.value()), '--length', str(self.length_spin.value()), '--fastqc', '--output_dir', self.output_folder]

        if self.paired_btn.isChecked():
            for fwd, rev in zip(self.forward_files, self.reverse_files):
                cmd = base_cmd + ['--paired', fwd, rev]
                self.execute_command(cmd)
        else:
            for fwd in self.forward_files:
                cmd = base_cmd + [fwd]
                self.execute_command(cmd)

    def execute_command(self, cmd):
        def worker():
            self.signal.started.emit()
            start = time.time()
            try:
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = process.communicate()
                if process.returncode == 0:
                    self.signal.completed.emit(time.time() - start)
                else:
                    self.signal.error.emit(stderr.decode())
            except Exception as e:
                self.signal.error.emit(str(e))

        threading.Thread(target=worker, daemon=True).start()

    @pyqtSlot()
    def show_running(self):
        QMessageBox.information(self, "Running", "Trim Galore is running...")

    @pyqtSlot(float)
    def show_complete(self, seconds):
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        QMessageBox.information(self, "Completed", f"Trim Galore completed in {mins}m {secs}s.")

    @pyqtSlot(str)
    def show_error(self, msg):
        QMessageBox.critical(self, "Error", msg)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = TrimGaloreGUI()
    win.show()
    sys.exit(app.exec_())

