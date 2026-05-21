from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QVBoxLayout, QWidget, QLabel, QPushButton, QTextEdit, QMessageBox, QGridLayout, QDesktopWidget, QComboBox, QProgressBar
from PyQt5.QtCore import QTime, QElapsedTimer, Qt, QTimer
import time
import subprocess
import os
import shlex
from subprocess import Popen, PIPE, STDOUT

class FeatureCount(QMainWindow):
    def __init__(self):
        super().__init__()

        self.bam_files = []
        self.output_folder = ""
        self.gtf_file = ""

        self.setWindowTitle("Feature Counts")

        layout = QVBoxLayout()

        # gtf file selection
        gtf_layout = QGridLayout()
        gtf_layout.addWidget(QLabel('Select GTF/GFF File:'), 0, 0)
        self.gtf_path_label = QLabel()
        gtf_layout.addWidget(self.gtf_path_label, 1, 0, 1, 2)
        gtf_select_button = QPushButton('Select', self)
        gtf_select_button.clicked.connect(self.select_gtf_file)
        gtf_layout.addWidget(gtf_select_button, 0, 1)
        layout.addLayout(gtf_layout)

        # bam file selection
        bam_layout = QGridLayout()
        bam_layout.addWidget(QLabel('Select bam/sam Files:'), 0, 0)
        self.bam_paths = QTextEdit()
        self.bam_paths.setReadOnly(True)
        bam_layout.addWidget(self.bam_paths, 1, 0, 1, 2)
        bam_select_button = QPushButton('Select bam/sam files', self)
        bam_select_button.clicked.connect(self.select_bam_files)
        bam_layout.addWidget(bam_select_button, 0, 0)
        bam_delete_button = QPushButton('Delete', self)
        bam_delete_button.clicked.connect(self.delete_bam_files)
        bam_layout.addWidget(bam_delete_button, 0, 1)
        bam_clear_button = QPushButton('Clear', self)
        bam_clear_button.clicked.connect(self.clear_bam_files)
        bam_layout.addWidget(bam_clear_button, 0, 2)
        layout.addLayout(bam_layout)

        # Output folder selection
        output_layout = QGridLayout()
        output_layout.addWidget(QLabel('Select Output Folder:'), 0, 0)
        self.output_path_label = QLabel()
        output_layout.addWidget(self.output_path_label, 1, 0, 1, 2)
        output_select_button = QPushButton('Select', self)
        output_select_button.clicked.connect(self.select_output_folder)
        output_layout.addWidget(output_select_button, 0, 1)
        layout.addLayout(output_layout)

        # Add the two dropdowns
        self.select_quantification_level()
        self.select_group_by()
        dropdown_layout = QGridLayout()
        dropdown_layout.addWidget(QLabel('Quantification level:'), 0, 0)
        dropdown_layout.addWidget(self.quantification_level, 0, 1)
        dropdown_layout.addWidget(QLabel('Name/Group by:'), 1, 0)
        dropdown_layout.addWidget(self.group_by, 1, 1)
        layout.addLayout(dropdown_layout)

        # Run button
        run_button = QPushButton('Run', self)
        run_button.clicked.connect(self.run_analysis)
        layout.addWidget(run_button)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        self.start_time = None
        self.timer = QElapsedTimer()

        # Center the window on the display
        self.center_window()

        self.progress = QProgressBar(self)
        self.progress.setRange(0, 0)
        self.progress.hide()  # Hide the progress bar initially
        layout.addWidget(self.progress)

    def center_window(self):
        # Get the screen geometry
        screen_geo = QDesktopWidget().screenGeometry()

        # Get the window geometry
        window_geo = self.geometry()

        # Calculate the center point
        center_point = screen_geo.center()

        # Move the window to the center
        window_geo.moveCenter(center_point)
        self.move(window_geo.topLeft())

    def select_gtf_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, 'Select gtf/gff File', '', 'Files (*.gtf *.gff3 *.gff)'
        )
        if file_path:
            self.gtf_file = file_path
            self.gtf_path_label.setText(file_path)

    def select_bam_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, 'Select bam Files', '', 'bam/sam Files (*.bam *.sam)'
        )
        self.bam_files.extend(file_paths)
        self.update_bam_paths()

    def delete_bam_files(self):
        selected_index = self.bam_paths.textCursor().blockNumber()
        if selected_index >= 0 and selected_index < len(self.bam_files):
            del self.bam_files[selected_index]
            self.update_bam_paths()

    def clear_bam_files(self):
        self.bam_files = []
        self.update_bam_paths()

    def select_output_folder(self):
        output_folder = QFileDialog.getExistingDirectory(self, 'Select Output Folder')
        if output_folder:
            self.output_folder = output_folder
            self.update_output_path()

    def update_bam_paths(self):
        paths = '\n'.join(self.bam_files)
        self.bam_paths.setPlainText(paths)

    def update_output_path(self):
        self.output_path_label.setText(self.output_folder)

    def select_quantification_level(self):
        options = ["CDS", "cDNA_match", "exon", "gene", "lnc_RNA", "mRNA", "pseudogene", "rRNA", "region", "tRNA", "transcript"]
        self.quantification_level = QComboBox()
        self.quantification_level.addItems(options)
        self.quantification_level.setFixedWidth(150)

    def select_group_by(self):
        options = ["*pseudo", "Dbxref", "ID", "Name", "Parent", "gbkey", "gene", "model_evidence", "product", "transcript_id"]
        self.group_by = QComboBox()
        self.group_by.addItems(options)
        self.group_by.setFixedWidth(150)

    def run_analysis(self):
        if not self.gtf_file or not self.bam_files or not self.output_folder:
            QMessageBox.critical(
                self, 'Error', 'Please select the GTF file, BAM files, and an output folder.'
            )
            return

        self.start_time = QTime.currentTime()  
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)

        cmd = f'conda run -n featurecounts_env featureCounts -t {self.quantification_level.currentText()} -g {self.group_by.currentText()} -a {self.gtf_file} -o {self.output_folder}/gene_expression_count.txt {" ".join(self.bam_files)}'
        self.process = Popen(shlex.split(cmd), stdout=PIPE, stderr=STDOUT)

        self.msg = QMessageBox(QMessageBox.Information, 
            'Running', 
            'The process is running. Please wait until the process finishes.',
            QMessageBox.Cancel, 
            self)
        self.msg.buttonClicked.connect(self.check_cancel)
        self.msg.setStandardButtons(QMessageBox.Cancel)
        self.msg.show()

        # Show the progress bar here
        self.progress.show() 

        while self.process.poll() is None:
            QApplication.processEvents()

        # Hide the progress bar here
        self.progress.hide()

        self.timer.stop()
        elapsed_time = self.start_time.secsTo(QTime.currentTime())
        elapsed_time_str = self.format_elapsed_time(elapsed_time)

        if self.process.returncode == 0:
            self.msg.setIcon(QMessageBox.Information)
            self.msg.setText(f"featureCounts has finished running!")
            self.msg.setInformativeText(f"Elapsed Time: {elapsed_time_str}")
            self.msg.setStandardButtons(QMessageBox.Ok)
            self.msg.buttonClicked.connect(self.close_all)  # Connecting here to ensure it only closes for 'Ok' 
        else:
            self.msg.setIcon(QMessageBox.Critical)
            self.msg.setText(f"Command failed to run. Error message: {self.process.stderr}")
            self.msg.setStandardButtons(QMessageBox.Ok)
        # Connect the Ok button click event to close the main window
        self.msg.buttonClicked.connect(self.close_all)
        self.progress.setRange(0, 1)
        self.progress.setValue(1)


    def format_elapsed_time(self, elapsed_time):
        return QTime(0, 0, 0).addSecs(elapsed_time).toString("hh 'h' mm 'm' ss 's'")

    def update_time(self):
        elapsed_time = self.start_time.secsTo(QTime.currentTime())

    def check_cancel(self, button):
        if self.msg.standardButton(button) == QMessageBox.Cancel:
            self.process.terminate()
            self.progress.setRange(0, 1)
            self.progress.setValue(1)

    def close_all(self):
        self.msg.close()  # close the message box
        self.close()  # close the main window


if __name__ == '__main__':
    app = QApplication([])
    feature_count = FeatureCount()
    feature_count.show()
    app.exec_()
