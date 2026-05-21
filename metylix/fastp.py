import sys
import subprocess
import os
import time
import shlex
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton, QFileDialog, QGridLayout,
    QWidget, QMessageBox, QCheckBox, QLineEdit
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices


class FastP_GUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("fastp")

        self.mode_checkbox = QCheckBox("Single-End Mode")
        self.input_label1 = QLabel("Input File 1:")
        self.input_path_label1 = QLabel()
        self.input_button1 = QPushButton("Select File")

        self.input_label2 = QLabel("Input File 2:")
        self.input_path_label2 = QLabel()
        self.input_button2 = QPushButton("Select File")

        self.output_label = QLabel("Output Directory:")
        self.output_path_label = QLabel()
        self.output_button = QPushButton("Select Directory")

        self.checkbox = QCheckBox("Customize Parameters")
        self.adapter_label1 = QLabel("Adapter Sequence (Read1):")
        self.adapter_input1 = QLineEdit()
        self.adapter_label2 = QLabel("Adapter Sequence (Read2):")
        self.adapter_input2 = QLineEdit()
        self.leading_label = QLabel("Leading:")
        self.leading_input = QLineEdit()
        self.trailing_label = QLabel("Trailing:")
        self.trailing_input = QLineEdit()
        self.length_label = QLabel("Length:")
        self.length_input = QLineEdit()

        self.run_button = QPushButton("Run fastp")

        layout = QGridLayout()
        layout.addWidget(self.mode_checkbox, 0, 0, 1, 3)

        layout.addWidget(self.input_label1, 1, 0)
        layout.addWidget(self.input_path_label1, 1, 1)
        layout.addWidget(self.input_button1, 1, 2)

        layout.addWidget(self.input_label2, 2, 0)
        layout.addWidget(self.input_path_label2, 2, 1)
        layout.addWidget(self.input_button2, 2, 2)

        layout.addWidget(self.output_label, 3, 0)
        layout.addWidget(self.output_path_label, 3, 1)
        layout.addWidget(self.output_button, 3, 2)

        layout.addWidget(self.checkbox, 4, 0, 1, 3)

        layout.addWidget(self.adapter_label1, 5, 0)
        layout.addWidget(self.adapter_input1, 5, 1)

        layout.addWidget(self.adapter_label2, 6, 0)
        layout.addWidget(self.adapter_input2, 6, 1)

        layout.addWidget(self.leading_label, 7, 0)
        layout.addWidget(self.leading_input, 7, 1)

        layout.addWidget(self.trailing_label, 8, 0)
        layout.addWidget(self.trailing_input, 8, 1)

        layout.addWidget(self.length_label, 9, 0)
        layout.addWidget(self.length_input, 9, 1)

        layout.addWidget(self.run_button, 10, 1)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Connections
        self.input_button1.clicked.connect(self.select_input_file1)
        self.input_button2.clicked.connect(self.select_input_file2)
        self.output_button.clicked.connect(self.select_output_dir)
        self.run_button.clicked.connect(self.run_fastp)
        self.mode_checkbox.stateChanged.connect(self.toggle_paired_mode)

        self.toggle_paired_mode()  # Initial UI setup

    def toggle_paired_mode(self):
        is_single = self.mode_checkbox.isChecked()
        self.input_label2.setVisible(not is_single)
        self.input_path_label2.setVisible(not is_single)
        self.input_button2.setVisible(not is_single)
        self.adapter_label2.setVisible(not is_single)
        self.adapter_input2.setVisible(not is_single)

    def select_input_file1(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select Input File 1", "", "FASTQ Files (*.fastq *.fq.gz *.fastq.gz)")
        self.input_path_label1.setText(file_name)

    def select_input_file2(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select Input File 2", "", "FASTQ Files (*.fastq *.fq.gz *.fastq.gz)")
        self.input_path_label2.setText(file_name)

    def select_output_dir(self):
        dir_name = QFileDialog.getExistingDirectory(self, "Select Directory")
        self.output_path_label.setText(dir_name)

    def run_fastp(self):
        start_time = time.time()

        input_file1 = self.input_path_label1.text()
        input_file2 = self.input_path_label2.text()
        output_dir = self.output_path_label.text()
        is_single = self.mode_checkbox.isChecked()

        if not input_file1 or not output_dir or (not is_single and not input_file2):
            QMessageBox.warning(self, "Error", "Please select all required inputs.")
            return

        output_file1 = os.path.join(output_dir, 'output_R1.fastq.gz')
        output_file2 = os.path.join(output_dir, 'output_R2.fastq.gz')
        html_result = os.path.join(output_dir, 'fastp.html')
        json_result = os.path.join(output_dir, 'fastp.json')

        adapter_seq1 = self.adapter_input1.text()
        adapter_seq2 = self.adapter_input2.text()
        leading = self.leading_input.text()
        trailing = self.trailing_input.text()
        length = self.length_input.text()

        conda_env_command = 'conda run -n fastp_env'

        # Base command
        if is_single:
            fastp_cmd = f'fastp -i {input_file1} -o {output_file1} -j {json_result} -h {html_result}'
        else:
            fastp_cmd = f'fastp -i {input_file1} -I {input_file2} -o {output_file1} -O {output_file2} -j {json_result} -h {html_result}'

        if self.checkbox.isChecked():
            if adapter_seq1:
                fastp_cmd += f' --adapter_sequence {adapter_seq1}'
            if adapter_seq2 and not is_single:
                fastp_cmd += f' --adapter_sequence_r2 {adapter_seq2}'
            if leading:
                fastp_cmd += f' --cut_by_quality5 --qualified_quality_phred {leading}'
            if trailing:
                fastp_cmd += f' --cut_by_quality3 --qualified_quality_phred {trailing}'
            if length:
                fastp_cmd += f' -l {length}'

        try:
            full_cmd = f'{conda_env_command} {fastp_cmd}'
            process = subprocess.Popen(full_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()

            elapsed_time = time.time() - start_time
            elapsed_time_str = time.strftime("%Hh %Mm %Ss", time.gmtime(elapsed_time))

            QMessageBox.information(self, "Success", f"fastp execution completed successfully.\nElapsed Time: {elapsed_time_str}")
            QDesktopServices.openUrl(QUrl.fromLocalFile(html_result))

        except Exception as e:
            QMessageBox.critical(self, "Error", f"fastp execution failed:\n{str(e)}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = FastP_GUI()
    gui.show()
    sys.exit(app.exec_())

