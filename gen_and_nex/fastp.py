from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QFileDialog, QVBoxLayout, QTextEdit, QGridLayout, QCheckBox, QMessageBox, QDialog, QLabel, QLineEdit, QHBoxLayout
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QDesktopWidget
from PyQt5.QtCore import QUrl
import subprocess
import shlex
import os
import sys
import time

class FastpWorker(QThread):
    finished = pyqtSignal(bool)

    def __init__(self, forward_files, reverse_files, output_folder, customized_params):
        super().__init__()
        self.forward_files = forward_files
        self.reverse_files = reverse_files
        self.output_folder = output_folder
        self.customized_params = customized_params
        self.cancelled = False
        self.error_msg = ""

    def cancel(self):
        self.cancelled = True

    def run(self):
        try:
            for i in range(len(self.forward_files)):
                if self.cancelled:
                    self.finished.emit(False)
                    return

                forward_file = self.forward_files[i]
                reverse_file = self.reverse_files[i]

                # Extract the file name without extension
                forward_name = os.path.splitext(os.path.basename(forward_file))[0]
                reverse_name = os.path.splitext(os.path.basename(reverse_file))[0]

                # Construct the output file paths
                output_file1 = os.path.join(self.output_folder, f"processed_{forward_name}.fastq.gz")
                output_file2 = os.path.join(self.output_folder, f"processed_{reverse_name}.fastq.gz")

                fastp_cmd = [
                    'conda', 'run', '-n', 'fastp_env', 'fastp', '-i', forward_file, '-I', reverse_file,
                    '-o', output_file1, '-O', output_file2
                ]

                if self.customized_params:
                    if "adapter_sequence" in self.customized_params:
                        fastp_cmd.extend(['--adapter_sequence', self.customized_params["adapter_sequence"]])
                    if "adapter_sequence_r2" in self.customized_params:
                        fastp_cmd.extend(['--adapter_sequence_r2', self.customized_params["adapter_sequence_r2"]])
                    if "leading" in self.customized_params:
                        fastp_cmd.extend(['-l', self.customized_params["leading"]])
                    if "trailing" in self.customized_params:
                        fastp_cmd.extend(['-t', self.customized_params["trailing"]])
                    if "length" in self.customized_params:
                        fastp_cmd.extend(['-L', self.customized_params["length"]])

                try:
                    process = subprocess.Popen(fastp_cmd, stdout=subprocess.PIPE)
                    output, error = process.communicate()
                except Exception as e:
                    self.error_msg = str(e)
                    self.finished.emit(False)
                    return

            self.finished.emit(True)

        except Exception as e:
            self.error_msg = str(e)
            self.finished.emit(False)


class Fastp_GUI(QDialog):
    def __init__(self):
        super().__init__()

        self.forward_files = []
        self.reverse_files = []
        self.output_folder = ""
        self.customized_params = {}

        # Call the center method after setting the geometry
        self.center()

        self.initUI()

    def center(self):
        """Center the window on the screen."""
        screen_rect = QDesktopWidget().availableGeometry()
        center_pos = screen_rect.center()

    def initUI(self):
        self.setWindowTitle('Fastp GUI')
        self.setFixedSize(700, 500)
        layout = QVBoxLayout()

        # Forward file selection
        forward_layout = QVBoxLayout()
        forward_layout.addWidget(QLabel('Select Forward Files:'))

        self.forward_paths = QTextEdit()
        self.forward_paths.setReadOnly(True)
        forward_layout.addWidget(self.forward_paths)

        forward_button_layout = QHBoxLayout()
        forward_select_button = QPushButton('Select', self)
        forward_select_button.clicked.connect(self.select_forward_files)
        forward_button_layout.addWidget(forward_select_button)

        forward_add_button = QPushButton('Add', self)
        forward_add_button.clicked.connect(self.add_forward_files)
        forward_button_layout.addWidget(forward_add_button)

        forward_delete_button = QPushButton('Delete', self)
        forward_delete_button.clicked.connect(self.delete_forward_file)
        forward_button_layout.addWidget(forward_delete_button)

        forward_clear_button = QPushButton('Clear', self)
        forward_clear_button.clicked.connect(self.clear_forward_files)
        forward_button_layout.addWidget(forward_clear_button)

        forward_layout.addLayout(forward_button_layout)
        layout.addLayout(forward_layout)

        # Reverse file selection
        reverse_layout = QVBoxLayout()
        reverse_layout.addWidget(QLabel('Select Reverse Files:'))

        self.reverse_paths = QTextEdit()
        self.reverse_paths.setReadOnly(True)
        reverse_layout.addWidget(self.reverse_paths)

        reverse_button_layout = QHBoxLayout()
        reverse_select_button = QPushButton('Select', self)
        reverse_select_button.clicked.connect(self.select_reverse_files)
        reverse_button_layout.addWidget(reverse_select_button)

        reverse_add_button = QPushButton('Add', self)
        reverse_add_button.clicked.connect(self.add_reverse_files)
        reverse_button_layout.addWidget(reverse_add_button)

        reverse_delete_button = QPushButton('Delete', self)
        reverse_delete_button.clicked.connect(self.delete_reverse_file)
        reverse_button_layout.addWidget(reverse_delete_button)

        reverse_clear_button = QPushButton('Clear', self)
        reverse_clear_button.clicked.connect(self.clear_reverse_files)
        reverse_button_layout.addWidget(reverse_clear_button)

        reverse_layout.addLayout(reverse_button_layout)
        layout.addLayout(reverse_layout)

        # Output folder selection
        output_layout = QVBoxLayout()
        output_layout.addWidget(QLabel('Select Output Folder:'))
        self.output_path_label = QLabel()
        output_layout.addWidget(self.output_path_label)
        output_select_button = QPushButton('Select', self)
        output_select_button.clicked.connect(self.select_output_folder)
        output_layout.addWidget(output_select_button)
        layout.addLayout(output_layout)

        # Customized parameters
        customized_layout = QVBoxLayout()
        self.customized_checkbox = QCheckBox('Customized Parameters', self)
        self.customized_checkbox.setChecked(False)
        self.customized_checkbox.stateChanged.connect(self.update_customized_params)
        customized_layout.addWidget(self.customized_checkbox)

        grid_layout = QGridLayout()
        self.adapter_label1 = QLabel("Adapter Sequence (Read1):")
        self.adapter_input1 = QLineEdit()
        self.adapter_input1.setEnabled(False)
        grid_layout.addWidget(self.adapter_label1, 0, 0)
        grid_layout.addWidget(self.adapter_input1, 0, 1)

        self.adapter_label2 = QLabel("Adapter Sequence (Read2):")
        self.adapter_input2 = QLineEdit()
        self.adapter_input2.setEnabled(False)
        grid_layout.addWidget(self.adapter_label2, 1, 0)
        grid_layout.addWidget(self.adapter_input2, 1, 1)

        self.leading_label = QLabel("Leading:")
        self.leading_input = QLineEdit()
        self.leading_input.setEnabled(False)
        grid_layout.addWidget(self.leading_label, 2, 0)
        grid_layout.addWidget(self.leading_input, 2, 1)

        self.trailing_label = QLabel("Tailing:")
        self.trailing_input = QLineEdit()
        self.trailing_input.setEnabled(False)
        grid_layout.addWidget(self.trailing_label, 3, 0)
        grid_layout.addWidget(self.trailing_input, 3, 1)

        self.length_label = QLabel("Length:")
        self.length_input = QLineEdit()
        self.length_input.setEnabled(False)
        grid_layout.addWidget(self.length_label, 4, 0)
        grid_layout.addWidget(self.length_input, 4, 1)

        customized_layout.addLayout(grid_layout)
        layout.addLayout(customized_layout)

        # Run and Cancel buttons
        buttons_layout = QHBoxLayout()
        run_button = QPushButton('Run', self)
        run_button.clicked.connect(self.run_fastp)
        buttons_layout.addWidget(run_button)
        cancel_button = QPushButton('Cancel', self)
        cancel_button.clicked.connect(self.close)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)
        self.center()

    def center(self):
        # Center the window on the screen
        frame_geometry = self.frameGeometry()
        center_point = QApplication.desktop().availableGeometry().center()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())

        # Connect the buttons to the slots
        self.input_button1.clicked.connect(self.select_input_file1)
        self.input_button2.clicked.connect(self.select_input_file2)
        self.output_button.clicked.connect(self.select_output_dir)
        self.run_button.clicked.connect(self.run_fastp)

    def select_forward_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, 'Select Forward Files', '', 'FASTQ Files (*.fastq *.fq *fastq.gz *.fq.gz)'
        )
        self.forward_files.extend(file_paths)
        self.update_forward_files()

    def add_forward_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, 'Add Forward Files', '', 'FASTQ Files (*.fastq *.fq *fastq.gz *.fq.gz)'
        )
        self.forward_files.extend(file_paths)
        self.update_forward_files()

    def delete_forward_file(self):
        selected_index = self.forward_paths.textCursor().blockNumber()
        if selected_index >= 0 and selected_index < len(self.forward_files):
            del self.forward_files[selected_index]
            self.update_forward_files()

    def clear_forward_files(self):
        self.forward_files.clear()
        self.update_forward_files()

    def update_forward_files(self):
        self.forward_paths.setPlainText('\n'.join(self.forward_files))

    def select_reverse_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, 'Select Reverse Files', '', 'FASTQ Files (*.fastq *.fq *fastq.gz *.fq.gz)'
        )
        self.reverse_files.extend(file_paths)
        self.update_reverse_files()
    
    def update_reverse_files(self):
        self.reverse_paths.setPlainText('\n'.join(self.reverse_files))

    def add_reverse_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, 'Add Reverse Files', '', 'FASTQ Files (*.fastq *.fq *fastq.gz *.fq.gz)'
        )
        self.reverse_files.extend(file_paths)
        self.update_reverse_files()

    def delete_reverse_file(self):
        selected_index = self.reverse_paths.textCursor().blockNumber()
        if selected_index >= 0 and selected_index < len(self.reverse_files):
            del self.reverse_files[selected_index]
            self.update_reverse_files()

    def clear_reverse_files(self):
        self.reverse_files.clear()
        self.update_reverse_files()

    def select_output_folder(self):
        output_folder = QFileDialog.getExistingDirectory(self, 'Select Output Folder')
        if output_folder:
            self.output_folder = output_folder
            self.output_path_label.setText(output_folder)

    def update_customized_params(self, state):
        # This method updates the enabled status of the parameter input boxes based on the checkbox
        is_enabled = state == Qt.Checked
        self.adapter_input1.setEnabled(is_enabled)
        self.adapter_input2.setEnabled(is_enabled)
        self.leading_input.setEnabled(is_enabled)
        self.trailing_input.setEnabled(is_enabled)
        self.length_input.setEnabled(is_enabled)

    def center(self):
        # Center the window on the screen
        frame_geometry = self.frameGeometry()
        center_point = QApplication.desktop().availableGeometry().center()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())

    def run_fastp(self):
        start_time = time.time()  # Start time

        input_files1 = self.forward_paths.toPlainText().split('\n')
        input_files2 = self.reverse_paths.toPlainText().split('\n')

        if len(input_files1) != len(input_files2):
            QMessageBox.warning(self, "Error", "Number of files in Input File 1 and Input File 2 do not match.")
            return

        output_dir = self.output_path_label.text()
        if not input_files1 or not input_files2 or not output_dir:
            QMessageBox.warning(self, "Error", "Please select input files and output directory.")
            return

        adapter_seq1 = self.adapter_input1.text()
        adapter_seq2 = self.adapter_input2.text()
        leading = self.leading_input.text()
        trailing = self.trailing_input.text()
        length = self.length_input.text()

        for input_file1, input_file2 in zip(input_files1, input_files2):
            # Create distinct output filenames based on the input filenames
            base_name1 = os.path.basename(input_file1).split('.')[0]
            base_name2 = os.path.basename(input_file2).split('.')[0]

            output_file1 = os.path.join(output_dir, f'{base_name1}_output_R1.fastq.gz')
            output_file2 = os.path.join(output_dir, f'{base_name2}_output_R2.fastq.gz')
            html_result = os.path.join(output_dir, f'{base_name1}_{base_name2}_fastp.html')

            conda_env_command = 'conda run -n fastp_env'
            fastp_cmd = f'fastp -i "{input_file1}" -I "{input_file2}" -o "{output_file1}" -O "{output_file2}" -j "{os.path.join(output_dir, f"{base_name1}_{base_name2}_fastp.json")}" -h "{html_result}"'

            if self.customized_checkbox.isChecked():
                if adapter_seq1:
                    fastp_cmd += f' --adapter_sequence {adapter_seq1}'
                if adapter_seq2:
                    fastp_cmd += f' --adapter_sequence_r2 {adapter_seq2}'
                if leading:
                    fastp_cmd += f' -l {leading}'
                if trailing:
                    fastp_cmd += f' -t {trailing}'
                if length:
                    fastp_cmd += f' -L {length}'

            try:
                cmd = f'{conda_env_command} {fastp_cmd}'
                process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = process.communicate()

                elapsed_time = time.time() - start_time  # Elapsed time
                elapsed_time_str = time.strftime("%Hh %Mm %Ss", time.gmtime(elapsed_time))  # Format elapsed time

                QMessageBox.information(self, "Success", f"fastp execution completed successfully for {base_name1} and {base_name2}.\nElapsed Time: {elapsed_time_str}")

                # Open HTML file
                QDesktopServices.openUrl(QUrl.fromLocalFile(html_result))

            except subprocess.CalledProcessError as e:
                QMessageBox.warning(self, "Error", f"fastp execution failed for {base_name1} and {base_name2}:\n{e}")

    

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Fastp_GUI()
    window.show()
    sys.exit(app.exec_())