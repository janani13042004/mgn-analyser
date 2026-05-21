import sys
from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QLabel, QPushButton, QFileDialog, 
    QMessageBox, QTextEdit, QHBoxLayout
)
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
import subprocess
import threading
import time
import os

class Signal(QObject):
    started = pyqtSignal()
    completed = pyqtSignal(float)
    error = pyqtSignal(str)

class PopupWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.read_files = []
        self.output_folder = ""
        self.process = None
        self.signal = Signal()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('HiFiAsm GUI')
        self.setFixedSize(600, 400)
        layout = QVBoxLayout()

        # Read file selection
        read_layout = QVBoxLayout()
        read_layout.addWidget(QLabel('Select HiFi Read Files:'))

        self.read_paths = QTextEdit()
        self.read_paths.setReadOnly(True)
        read_layout.addWidget(self.read_paths)

        read_button_layout = QHBoxLayout()
        read_select_button = QPushButton('Select', self)
        read_select_button.clicked.connect(self.select_read_files)
        read_button_layout.addWidget(read_select_button)

        read_add_button = QPushButton('Add', self)
        read_add_button.clicked.connect(self.add_read_files)
        read_button_layout.addWidget(read_add_button)

        read_delete_button = QPushButton('Delete', self)
        read_delete_button.clicked.connect(self.delete_read_file)
        read_button_layout.addWidget(read_delete_button)

        read_clear_button = QPushButton('Clear', self)
        read_clear_button.clicked.connect(self.clear_read_files)
        read_button_layout.addWidget(read_clear_button)

        read_layout.addLayout(read_button_layout)
        layout.addLayout(read_layout)

        # Output folder selection
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel('Select Output Folder:'), 0)
        self.output_path_label = QLabel()
        output_layout.addWidget(self.output_path_label)
        output_select_button = QPushButton('Select', self)
        output_select_button.clicked.connect(self.select_output_folder)
        output_layout.addWidget(output_select_button)
        layout.addLayout(output_layout)

        # Run and Cancel buttons
        buttons_layout = QHBoxLayout()
        run_button = QPushButton('Run', self)
        run_button.clicked.connect(self.run_analysis)
        buttons_layout.addWidget(run_button)
        cancel_button = QPushButton('Cancel', self)
        cancel_button.clicked.connect(self.cancel_analysis)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)

        # Connect signals
        self.signal.started.connect(self.show_running_msg)
        self.signal.completed.connect(self.show_complete_msg)
        self.signal.error.connect(self.show_error_msg)

    def select_read_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, 'Select HiFi Read Files', '', 'FASTQ Files (*.fastq *.fq *.fastq.gz *.fq.gz *.fa.gz)'
        )
        self.read_files.extend(file_paths)
        self.update_read_paths()

    def add_read_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, 'Add HiFi Read Files', '', 'FASTQ Files (*.fastq *.fq *.fastq.gz *.fq.gz *.fa.gz)'
        )
        self.read_files.extend(file_paths)
        self.update_read_paths()

    def delete_read_file(self):
        selected_index = self.read_paths.textCursor().blockNumber()
        if selected_index >= 0 and selected_index < len(self.read_files):
            del self.read_files[selected_index]
            self.update_read_paths()

    def clear_read_files(self):
        self.read_files.clear()
        self.update_read_paths()

    def select_output_folder(self):
        output_folder = QFileDialog.getExistingDirectory(self, 'Select Output Folder')
        if output_folder:
            self.output_folder = output_folder
            self.update_output_path()

    def update_read_paths(self):
        paths = '\n'.join(self.read_files)
        self.read_paths.setPlainText(paths)

    def update_output_path(self):
        self.output_path_label.setText(self.output_folder)

    def run_analysis(self):
        if not self.read_files or not self.output_folder:
            QMessageBox.critical(self, 'Error', 'Please select HiFi read files and an output folder.')
            return

        # Clone and build HiFiAsm if not already done
        if not os.path.exists('hifiasm'):
            clone_cmd = ['git', 'clone', 'https://github.com/chhylp123/hifiasm']
            build_cmd = ['make', '-C', 'hifiasm']
            subprocess.run(clone_cmd)
            subprocess.run(build_cmd)

        cmd = ['conda', 'run', '-n', 'hifiasm_env', './hifiasm/hifiasm']
        cmd.extend([
            '-o', f'{self.output_folder}/result.asm',
            '-t', '4',  # Using 4 threads
            '-f0'
        ])
        cmd.extend(self.read_files)

        # Start the timer
        start_time = time.time()

        def run_hifiasm():
            self.signal.started.emit()
            try:
                print("Running command:", " ".join(cmd))  # Debugging output
                self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = self.process.communicate()
                returncode = self.process.returncode

                print("HiFiAsm stdout:", stdout.decode())  # Debugging output
                print("HiFiAsm stderr:", stderr.decode())  # Debugging output

                if returncode == 0:
                    # Run awk command to convert GFA to FASTA
                    gfa_file = f"{self.output_folder}/result.asm.bp.p_ctg.gfa"
                    fasta_file = f"{self.output_folder}/result.p_ctg.fa"
                    awk_cmd = f"awk '/^S/{{print \">\"$2;print $3}}' {gfa_file} > {fasta_file}"
                    
                    print("Running awk command:", awk_cmd)  # Debugging output
                    awk_process = subprocess.Popen(awk_cmd, shell=True)
                    awk_stdout, awk_stderr = awk_process.communicate()
                    awk_returncode = awk_process.returncode

                    print("Awk stdout:", awk_stdout)  # Debugging output
                    print("Awk stderr:", awk_stderr)  # Debugging output

                    if awk_returncode == 0:
                        self.signal.completed.emit(time.time() - start_time)
                    else:
                        self.signal.error.emit("Awk command failed. Could not convert GFA to FASTA.")
                else:
                    self.signal.error.emit("HiFiAsm command failed. Please check your inputs and try again.")
            except Exception as e:
                self.signal.error.emit(f"An error occurred while running HiFiAsm: {str(e)}")

        # Start the thread
        threading.Thread(target=run_hifiasm, daemon=True).start()

    @pyqtSlot()
    def show_running_msg(self):
        self.running_msg = QMessageBox(self)
        self.running_msg.setIcon(QMessageBox.Information)
        self.running_msg.setText("The process is running. Please wait until the process finishes.")
        self.running_msg.setWindowTitle("Running")
        self.running_msg.setStandardButtons(QMessageBox.Cancel)
        self.running_msg.buttonClicked.connect(self.cancel_analysis)
        self.running_msg.show()

    @pyqtSlot(float)
    def show_complete_msg(self, duration):
        if self.running_msg:
            self.running_msg.close()

        hours = int(duration / 3600)
        minutes = int((duration % 3600) / 60)
        seconds = int(duration % 60)
        duration_str = f"{hours}h {minutes}m {seconds}s"

        complete_msg = QMessageBox(self)
        complete_msg.setIcon(QMessageBox.Information)
        complete_msg.setText(f"Assembly is completed.\nDuration: {duration_str}")
        complete_msg.setWindowTitle("Complete")
        complete_msg.setStandardButtons(QMessageBox.Ok)
        complete_msg.buttonClicked.connect(self.close_windows)
        complete_msg.show()

    @pyqtSlot(str)
    def show_error_msg(self, error_message):
        if self.running_msg:
            self.running_msg.close()

        QMessageBox.critical(self, "HiFiAsm Error", error_message)

    def cancel_analysis(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait()

        if self.running_msg:
            self.running_msg.close()

    def close_windows(self):
        if self.running_msg:
            self.running_msg.close()
        self.close()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PopupWindow()
    window.show()
    sys.exit(app.exec_())

