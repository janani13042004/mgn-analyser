from PyQt5.QtWidgets import (QApplication, QWidget, QComboBox, QLabel, QPushButton,
                             QFileDialog, QHBoxLayout, QVBoxLayout, QLineEdit, QMessageBox,
                             QDialog, QTextEdit, QGridLayout, QCheckBox, QScrollArea, QFrame)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import subprocess
import os
import sys
import time
import shutil


class TrimmomaticWorker(QThread):
    finished = pyqtSignal(bool)
    error = pyqtSignal(str)
    update_progress = pyqtSignal(str)

    def __init__(self, forward_files, reverse_files, output_folder, adapter_file, customized_params, selected_database):
        super().__init__()
        self.forward_files = forward_files
        self.reverse_files = reverse_files
        self.output_folder = output_folder
        self.adapter_file = adapter_file
        self.customized_params = customized_params
        self.busco_database = ""  # Initializing the BUSCO database attribute
        self.selected_database = selected_database  
        self.cancelled = False
        self.error_msg = ""
        self.signal = self


    def cancel(self):
        self.cancelled = True

    def run(self):
        start_time = time.time()  # Start time

        # Check if customized parameters are enabled
        if self.customized_params:
            leading_value = self.customized_params.get("LEADING", "30")
            trailing_value = self.customized_params.get("TRAILING", "30")
            minlen_value = self.customized_params.get("MINLEN", "36")
            headcrop_value = self.customized_params.get("HEADCROP", "15")
        else:
            leading_value = "30"
            trailing_value = "30"
            minlen_value = "36"
            headcrop_value = "15"

        # make directories
        fastqc_dir = f"{self.output_folder}/fastqc_output"
        trimmed_dir = f"{self.output_folder}/Trimmed_output"
        trimmed_fastqc_dir = f"{self.output_folder}/Trimmed_fastqc_output"
        assembly_dir = f"{self.output_folder}/trinity_assembly"
        busco_dir = f"{self.output_folder}/busco_output"
        rsem_dir = f"{self.output_folder}/rsem_output"

        # create directories if they don't exist
        for dir in [fastqc_dir, trimmed_dir, trimmed_fastqc_dir, assembly_dir, busco_dir, rsem_dir]:
            if not os.path.exists(dir):
                os.mkdir(dir)

        try:
            # FastQC for all raw reads
            fastqc_cmd = f"conda run -n fastqc_env fastqc -o {fastqc_dir} {' '.join(self.forward_files)} {' '.join(self.reverse_files)}"
            process = subprocess.Popen(fastqc_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                self.error_msg = "FastQC command failed. Please check your inputs and try again."
                self.finished.emit(False)
                return
            self.update_progress.emit("Quality Check is completed")

            trimmed_paired_forward_files = []
            trimmed_paired_reverse_files = []

            for i in range(len(self.forward_files)):
                forward_file = self.forward_files[i]
                reverse_file = self.reverse_files[i]
                
                # Extracting the base name without the '.fastq.gz' extension.
                forward_base = "_".join(os.path.basename(forward_file).split(".")[:-2])
                reverse_base = "_".join(os.path.basename(reverse_file).split(".")[:-2])

                paired_output_file = os.path.join(trimmed_dir, f"{forward_base}_paired.fastq.gz")
                unpaired_output_file = os.path.join(trimmed_dir, f"{forward_base}_unpaired.fastq.gz")
                paired_output2_file = os.path.join(trimmed_dir, f"{reverse_base}_paired.fastq.gz")
                unpaired_output2_file = os.path.join(trimmed_dir, f"{reverse_base}_unpaired.fastq.gz")

                trimmomatic_cmd = [
                    'conda', 'run', '-n', 'trimmomatic_env', 'trimmomatic', 'PE', '-threads', '16',
                    forward_file, reverse_file,
                    paired_output_file, unpaired_output_file, paired_output2_file, unpaired_output2_file,
                    "ILLUMINACLIP:" + self.adapter_file + ":2:30:10", "LEADING:" + leading_value,
                    "TRAILING:" + trailing_value, "SLIDINGWINDOW:4:15", "MINLEN:" + minlen_value, "HEADCROP:" + headcrop_value, "-summary", os.path.join(trimmed_dir, f"{forward_base}_{reverse_base}_report.txt")
                ]


                process = subprocess.Popen(trimmomatic_cmd, stdout=subprocess.PIPE)
                output, error = process.communicate()

                if process.returncode != 0:
                    self.error_msg = "Trimmomatic command failed. Please check your inputs and try again."
                    self.finished.emit(False)
                    return
                self.update_progress.emit("Trimming reads are completed")

                trimmed_paired_forward_files.append(paired_output_file)
                trimmed_paired_reverse_files.append(paired_output2_file)

            # FastQC for only the trimmed paired reads
            fastqc_cmd = f"conda run -n fastqc_env fastqc -o {trimmed_fastqc_dir} {' '.join(trimmed_paired_forward_files)} {' '.join(trimmed_paired_reverse_files)}"
            process = subprocess.Popen(fastqc_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                self.error_msg = "FastQC command failed for trimmed reads. Please check your inputs and try again."
                self.finished.emit(False)
                return
            self.update_progress.emit("Quality Check for the trimmed reads is completed")

            # Trinity assembly for the trimmed paired reads
            command = [
                'conda', 'run', '-n', 'trinity_env', 'Trinity',
                '--seqType', 'fq',
                '--left', ','.join(trimmed_paired_forward_files),
                '--right', ','.join(trimmed_paired_reverse_files),
                '--max_memory', '50G',
                '--output', assembly_dir,
                '--CPU', '16'
            ]

            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                self.error_msg = "Trinity command failed. Please check your inputs and try again."
                self.finished.emit(False)
                return
            self.update_progress.emit("Assembly is completed")

            # BUSCO Analysis

            if not os.path.exists(f"{self.output_folder}/trinity_assembly.Trinity.fasta"):
                self.error_msg = "Trinity assembly output not found!"
                self.finished.emit(False)
                return
            busco_file = f"{self.selected_database}"  # BUSCO database
            activate_command = f"conda run -n busco_env busco -i {self.output_folder}/trinity_assembly.Trinity.fasta -o busco_result -l {self.selected_database} -m transcriptome --cpu 16 -f"
            process = subprocess.Popen(activate_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()

            target_dir1 = os.path.join(self.output_folder, "busco_output")
            target_dir2 = os.path.join(self.output_folder, "busco_output", "busco_downloads")
            if os.path.exists(target_dir1):
                shutil.rmtree(target_dir1)
            if os.path.exists(target_dir2):
                shutil.rmtree(target_dir2)
            shutil.move("busco_result", target_dir1)
            shutil.move("busco_downloads", target_dir2)

            if process.returncode != 0:
                self.error_msg = "BUSCO analysis failed."
                self.finished.emit(False)
                return
            self.update_progress.emit("Completeness is completed")

            # Generate the plot within the BUSCO environment
            generate_plot_command = f"conda run -n busco_env generate_plot.py -wd {busco_dir}"
            subprocess.run(generate_plot_command, shell=True)

            #rsem analysis

            rsem_output_files = []
            activate_command1 = f"conda run -n rsem_env rsem-prepare-reference --bowtie2 {self.output_folder}/trinity_assembly.Trinity.fasta {rsem_dir}/reference_index"
            subprocess.run(activate_command1, shell=True, check=True)

            for i in range(len(trimmed_paired_forward_files)):
                paired_output_file = trimmed_paired_forward_files[i]
                paired_output2_file = trimmed_paired_reverse_files[i]

                activate_command2 = f"conda run -n rsem_env rsem-calculate-expression --bowtie2 --paired-end -p 16 --append-names --no-bam-output {paired_output_file} {paired_output2_file} {rsem_dir}/reference_index {rsem_dir}/Rsem_output_sample{i}"
                subprocess.run(activate_command2, shell=True, check=True)

                rsem_output_files.append(f"{rsem_dir}/Rsem_output_sample{i}.genes.results")

            # Once all paired-end reads are processed, combine the resulting files
            activate_command3 = f"conda run -n rsem_env rsem-generate-data-matrix {' '.join(rsem_output_files)} > {rsem_dir}/gene_expression.txt"
            subprocess.run(activate_command3, shell=True, check=True)

            elapsed_time = time.time() - start_time  # Elapsed time
            elapsed_time_str = time.strftime("%Hh %Mm %Ss", time.gmtime(elapsed_time))  # Format elapsed time

            if self.cancelled:
                self.finished.emit(False)
            else:
                self.finished.emit(True)

            QMessageBox.information(None, "Success", f"Process finished successfully.\nElapsed Time: {elapsed_time_str}")

        except Exception as e:
            self.error_msg = str(e)
            self.finished.emit(False)
        self.update_progress.emit("Count table has been generated")


class Trimmomatic_GUI(QDialog):
    def __init__(self):
        super().__init__()

        self.forward_files = []
        self.reverse_files = []
        self.output_folder = ""
        self.adapter_file = ""
        self.customized_params = False

        self.initUI()

    def initUI(self):
        self.setWindowTitle('Denovo Pipeline')
        self.setFixedSize(700, 600)  # Set the window size

        #Main Layout
        main_layout = QVBoxLayout(self)

        # Scroll Area Setup

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)  # This layout will hold the content inside the scroll area
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)


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
        scroll_layout.addLayout(forward_layout)

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
        scroll_layout.addLayout(reverse_layout)

        # Adapter file selection
        adapter_layout = QHBoxLayout()
        adapter_layout.addWidget(QLabel('Select Adapter File:'))

        self.adapter_label = QLabel()
        adapter_layout.addWidget(self.adapter_label)

        adapter_select_button = QPushButton('Select', self)
        adapter_select_button.clicked.connect(self.select_adapter_file)
        adapter_layout.addWidget(adapter_select_button)

        scroll_layout.addLayout(adapter_layout)

        # Output folder selection
        output_layout = QGridLayout()
        output_layout.addWidget(QLabel('Select Output Folder:'), 0, 0)
        self.output_path_label = QLabel()
        output_layout.addWidget(self.output_path_label, 1, 0, 1, 2)
        output_select_button = QPushButton('Select', self)
        output_select_button.clicked.connect(self.select_output_folder)
        output_layout.addWidget(output_select_button, 0, 1)
        scroll_layout.addLayout(output_layout)

        # Customized parameters
        customized_layout = QHBoxLayout()
        self.customized_checkbox = QCheckBox('Customized Parameters', self)
        self.customized_checkbox.setChecked(False)
        self.customized_checkbox.stateChanged.connect(self.update_customized_params)
        customized_layout.addWidget(self.customized_checkbox)

        self.leading_label = QLabel("LEADING:")
        self.leading_lineedit = QLineEdit("30")
        self.leading_lineedit.setEnabled(False)

        self.trailing_label = QLabel("TRAILING:")
        self.trailing_lineedit = QLineEdit("30")
        self.trailing_lineedit.setEnabled(False)

        self.minlen_label = QLabel("MINLEN:")
        self.minlen_lineedit = QLineEdit("36")
        self.minlen_lineedit.setEnabled(False)

        self.headcrop_label = QLabel("HEADCROP:")
        self.headcrop_lineedit = QLineEdit("15")
        self.headcrop_lineedit.setEnabled(False)

        customized_layout.addWidget(self.leading_label)
        customized_layout.addWidget(self.leading_lineedit)
        customized_layout.addWidget(self.trailing_label)
        customized_layout.addWidget(self.trailing_lineedit)
        customized_layout.addWidget(self.minlen_label)
        customized_layout.addWidget(self.minlen_lineedit)
        customized_layout.addWidget(self.headcrop_label)
        customized_layout.addWidget(self.headcrop_lineedit)

        scroll_layout.addLayout(customized_layout)

        layout = QVBoxLayout()

        self.busco_label = QLabel("Select a BUSCO database for your closest species (Ex: for plants(viridiplantae))")
        layout.addWidget(self.busco_label)

        self.busco_combo = QComboBox()
        with open("database.txt") as f:  # Read the database names from the file
            databases = f.read().splitlines()
        self.busco_combo.addItems(databases)  # Add the database names to the QComboBox
        layout.addWidget(self.busco_combo)


        # BUSCO database selection
        scroll_layout.addWidget(self.busco_label)
        scroll_layout.addWidget(self.busco_combo)

        # Button Layout at the bottom (Outside the scroll area)
        btn_layout = QVBoxLayout()
        buttons_layout = QHBoxLayout()
        run_button = QPushButton('Run', self)
        run_button.clicked.connect(self.run_trimmomatic)
        buttons_layout.addWidget(run_button)
        cancel_button = QPushButton('Cancel', self)
        cancel_button.clicked.connect(self.close)
        buttons_layout.addWidget(cancel_button)
        btn_layout.addStretch()
        btn_layout.addLayout(buttons_layout)
        main_layout.addLayout(btn_layout)  # Added to main_layout, so it stays outside the scrollbar

        # Center the window on the screen
        self.center()

    def center(self):
        # Center the window on the screen
        frame_geometry = self.frameGeometry()
        center_point = QApplication.desktop().availableGeometry().center()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())

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

    def select_reverse_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, 'Select Reverse Files', '', 'FASTQ Files (*.fastq *.fq *fastq.gz *.fq.gz)'
        )
        self.reverse_files.extend(file_paths)
        self.update_reverse_files()

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

    def update_forward_files(self):
        self.forward_paths.setPlainText('\n'.join(self.forward_files))

    def update_reverse_files(self):
        self.reverse_paths.setPlainText('\n'.join(self.reverse_files))

    def select_adapter_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, 'Select Adapter File', '', 'All Files (*)')
        if file_path:
            self.adapter_file = file_path
            self.adapter_label.setText(file_path)

    def select_output_folder(self):
        output_folder = QFileDialog.getExistingDirectory(self, 'Select Output Folder')
        if output_folder:
            self.output_folder = output_folder
            self.output_path_label.setText(output_folder)

    def update_customized_params(self, state):
        self.customized_params = state == Qt.Checked
        self.leading_lineedit.setEnabled(self.customized_params)
        self.trailing_lineedit.setEnabled(self.customized_params)
        self.minlen_lineedit.setEnabled(self.customized_params)
        self.headcrop_lineedit.setEnabled(self.customized_params)

    def run_trimmomatic(self):
        if not self.forward_files or not self.reverse_files:
            QMessageBox.warning(self, "Error", "Please select forward and reverse files.")
            return

        if not self.output_folder:
            QMessageBox.warning(self, "Error", "Please select an output folder.")
            return

        if not self.adapter_file:
            QMessageBox.warning(self, "Error", "Please select an adapter file.")
            return

        self.busco_database = self.busco_combo.currentText()
        if not self.busco_database:  
            self.show_message_box("Missing Input", "Please select a BUSCO database.")
            return



        customized_params = {
            "LEADING": self.leading_lineedit.text(),
            "TRAILING": self.trailing_lineedit.text(),
            "MINLEN": self.minlen_lineedit.text(),
            "HEADCROP": self.headcrop_lineedit.text()
        } if self.customized_params else None

        self.worker = TrimmomaticWorker(
            self.forward_files, self.reverse_files, self.output_folder, self.adapter_file, customized_params, self.busco_database
        )
        self.worker.finished.connect(self.handle_trimmomatic_finished)
        self.worker.start()

        # Show progress message box
        self.progress_msg = QMessageBox(QMessageBox.Information, "Processing", "please wait until the process finishes, It will take some time to complete...", QMessageBox.Cancel, self)
        self.progress_msg.setWindowModality(Qt.WindowModal)
        self.progress_msg.button(QMessageBox.Cancel).clicked.connect(self.worker.cancel)
        self.progress_msg.show()
        self.worker.update_progress.connect(self.update_progress_msg)

        self.start_time = time.time()  # Start time


    def handle_trimmomatic_finished(self, success):
        if success:
            elapsed_time = time.time() - self.start_time  # Elapsed time
            elapsed_time_str = time.strftime("%Hh %Mm %Ss", time.gmtime(elapsed_time))  # Format elapsed time

            # Close the progress message box
            self.progress_msg.close()

            # Show time stamp message box
            timestamp_msg = QMessageBox(QMessageBox.Information, "Process Complete", f"Trimmomatic finished successfully.\nElapsed Time: {elapsed_time_str}", QMessageBox.Ok, self)
            timestamp_msg.setWindowModality(Qt.WindowModal)
            timestamp_msg.accepted.connect(self.close)
            timestamp_msg.exec_()
        else:
            # Close the progress message box
            self.progress_msg.close()

            # Show error message with error details
            error_msg = QMessageBox(QMessageBox.Critical, "Error", "An error occurred during Trimmomatic processing.", QMessageBox.Ok, self)
            error_msg.setWindowModality(Qt.WindowModal)

            # Get the error message from the worker
            error_details = self.worker.error_msg
            error_msg.setDetailedText(error_details)

            error_msg.accepted.connect(self.close)
            error_msg.exec_()

    def closeEvent(self, event):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.cancel()
            self.worker.finished.disconnect()
            self.worker.terminate()

        super().closeEvent(event)

    def update_progress_msg(self, message):
        current_text = self.progress_msg.text()
        if current_text.count("\n") > 10:  # Clear the box if there are more than 10 lines
            current_text = "\n".join(current_text.split("\n")[-5:])  # Keep the last 5 messages
        updated_text = current_text + "\n " + message
        self.progress_msg.setText(updated_text)




if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Trimmomatic_GUI()
    window.show()
    sys.exit(app.exec_())
