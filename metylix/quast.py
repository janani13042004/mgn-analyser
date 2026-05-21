import sys
from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QLabel, QPushButton,
    QTextEdit, QFileDialog, QMessageBox, QHBoxLayout
)
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
import subprocess
import threading
import time


class Signal(QObject):
    started = pyqtSignal()
    completed = pyqtSignal(float)
    error = pyqtSignal(str)


class QuastGUI(QDialog):
    def __init__(self):
        super().__init__()
        self.input_files = []
        self.output_folder = ""
        self.process = None
        self.signal = Signal()
        self.running_msg = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle('QUAST')
        self.setFixedSize(600, 300)
        layout = QVBoxLayout()

        layout.addWidget(QLabel('Select Assembly Files (.fa or .fasta):'))
        self.file_display = QTextEdit()
        self.file_display.setReadOnly(True)
        layout.addWidget(self.file_display)

        file_buttons = QHBoxLayout()
        select_button = QPushButton('Select Files')
        select_button.clicked.connect(self.select_files)
        clear_button = QPushButton('Clear')
        clear_button.clicked.connect(self.clear_files)
        file_buttons.addWidget(select_button)
        file_buttons.addWidget(clear_button)
        layout.addLayout(file_buttons)

        layout.addWidget(QLabel('Select Output Folder:'))
        self.output_display = QLabel()
        layout.addWidget(self.output_display)
        output_button = QPushButton('Select Output Folder')
        output_button.clicked.connect(self.select_output_folder)
        layout.addWidget(output_button)

        button_layout = QHBoxLayout()
        run_button = QPushButton('Run')
        run_button.clicked.connect(self.run_quast)
        cancel_button = QPushButton('Cancel')
        cancel_button.clicked.connect(self.cancel_analysis)
        button_layout.addWidget(run_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        self.signal.started.connect(self.show_running_msg)
        self.signal.completed.connect(self.show_complete_msg)
        self.signal.error.connect(self.show_error_msg)

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, 'Select Assembly Files', '', 'FASTA Files (*.fa *.fasta)')
        self.input_files = files
        self.file_display.setPlainText('\n'.join(self.input_files))

    def clear_files(self):
        self.input_files = []
        self.file_display.clear()

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Select Output Folder')
        if folder:
            self.output_folder = folder
            self.output_display.setText(folder)

    def run_quast(self):
        if not self.input_files or not self.output_folder:
            QMessageBox.critical(self, 'Error', 'Please select input file(s) and output folder.')
            return

        cmd = ['conda', 'run', '-n', 'quast', 'quast']

        if len(self.input_files) == 1:
            cmd.extend([self.input_files[0], '-o', f'{self.output_folder}/metaquast_output'])
        else:
            cmd.extend(self.input_files + ['-o', f'{self.output_folder}/quast_comparison_output'])

        start_time = time.time()

        def run():
            self.signal.started.emit()
            try:
                self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                _, stderr = self.process.communicate()
                if self.process.returncode == 0:
                    self.signal.completed.emit(time.time() - start_time)
                else:
                    self.signal.error.emit(stderr.decode())
            except Exception as e:
                self.signal.error.emit(str(e))

        threading.Thread(target=run, daemon=True).start()

    @pyqtSlot()
    def show_running_msg(self):
        self.running_msg = QMessageBox(self)
        self.running_msg.setIcon(QMessageBox.Information)
        self.running_msg.setText("Running QUAST/metaQUAST. Please wait...")
        self.running_msg.setWindowTitle("Running")
        self.running_msg.setStandardButtons(QMessageBox.Cancel)
        self.running_msg.buttonClicked.connect(self.cancel_analysis)
        self.running_msg.show()

    @pyqtSlot(float)
    def show_complete_msg(self, duration):
        if self.running_msg:
            self.running_msg.close()
        h = int(duration // 3600)
        m = int((duration % 3600) // 60)
        s = int(duration % 60)
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setText(f"QUAST completed in {h}h {m}m {s}s.")
        msg.setWindowTitle("Complete")
        msg.exec_()

    @pyqtSlot(str)
    def show_error_msg(self, error):
        if self.running_msg:
            self.running_msg.close()
        QMessageBox.critical(self, "Error", error)

    def cancel_analysis(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait()
        if self.running_msg:
            self.running_msg.close()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = QuastGUI()
    gui.show()
    sys.exit(app.exec_())
