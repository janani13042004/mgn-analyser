import datetime
import random
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QVBoxLayout, QWidget, QLabel,
    QPushButton, QTextEdit, QMessageBox, QGridLayout, QHBoxLayout, QDesktopWidget
)

class RSEMTool(QMainWindow):
    def __init__(self):
        super().__init__()

        self.forward_files = []
        self.reverse_files = []
        self.output_folder = ""
        self.reference_file = ""

        self.setWindowTitle("RSEM Tool")
        self.setFixedSize(700, 500)

        self.center()
        self.init_ui()

    def center(self):
        """Center the window on the screen."""
        screen_rect = QDesktopWidget().availableGeometry()
        center_pos = screen_rect.center()
        self.move(center_pos.x() - self.width() // 2, center_pos.y() - self.height() // 2)

    def init_ui(self):
        layout = QVBoxLayout()

        # Reference file selection
        reference_layout = QHBoxLayout()
        reference_layout.addWidget(QLabel('Select Reference File (.fasta):'))
        self.reference_path_label = QLabel("Path not selected.")
        reference_layout.addWidget(self.reference_path_label)
        reference_select_button = QPushButton('Select', self)
        reference_select_button.clicked.connect(self.select_reference_file)
        reference_layout.addWidget(reference_select_button)
        layout.addLayout(reference_layout)

        # Forward file selection
        self.add_file_selector(layout, 'Select Forward Files:', self.select_forward_files, 
                               self.add_forward_files, self.delete_forward_file, self.clear_forward_files)

        # Reverse file selection
        self.add_file_selector(layout, 'Select Reverse Files:', self.select_reverse_files, 
                               self.add_reverse_files, self.delete_reverse_file, self.clear_reverse_files)

        # Output folder selection
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel('Select Output Folder:'))
        self.output_path_label = QLabel("Path not selected.")
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
        cancel_button.clicked.connect(self.close)  # Assuming you want to close the app on cancel
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    def add_file_selector(self, main_layout, label_text, select_func, add_func, delete_func, clear_func):
        layout = QVBoxLayout()
        layout.addWidget(QLabel(label_text))

        paths = QTextEdit()
        paths.setReadOnly(True)
        layout.addWidget(paths)

        if "Forward" in label_text:
            self.forward_paths = paths
        elif "Reverse" in label_text:
            self.reverse_paths = paths

        button_layout = QHBoxLayout()
        select_button = QPushButton('Select', self)
        select_button.clicked.connect(select_func)
        button_layout.addWidget(select_button)

        add_button = QPushButton('Add', self)
        add_button.clicked.connect(add_func)
        button_layout.addWidget(add_button)

        delete_button = QPushButton('Delete', self)
        delete_button.clicked.connect(delete_func)
        button_layout.addWidget(delete_button)

        clear_button = QPushButton('Clear', self)
        clear_button.clicked.connect(clear_func)
        button_layout.addWidget(clear_button)

        layout.addLayout(button_layout)
        main_layout.addLayout(layout)

    def select_reference_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, 'Select Reference File (.fasta)', '', 'FASTA Files (*.fasta *.fa *.fna)'
        )
        if file_path:
            self.reference_file = file_path
            self.reference_path_label.setText(file_path)

    def select_forward_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, 'Select Forward Files', '', 'FASTQ Files (*.fastq *.fq *fastq.gz *fq.gz)'
        )
        self.forward_files.extend(file_paths)
        self.update_forward_paths()

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
            self, 'Select Reverse Files', '', 'FASTQ Files (*.fastq *.fq *fastq.gz *fq.gz)'
        )
        self.reverse_files.extend(file_paths)
        self.update_reverse_paths()

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
            self.update_output_path()

    def update_forward_paths(self):
        paths = '\n'.join(self.forward_files)
        self.forward_paths.setPlainText(paths)

    def update_reverse_paths(self):
        paths = '\n'.join(self.reverse_files)
        self.reverse_paths.setPlainText(paths)

    def update_output_path(self):
        self.output_path_label.setText(self.output_folder)

    def run_analysis(self):
        if not self.reference_file or not self.forward_files or not self.reverse_files or not self.output_folder:
            QMessageBox.critical(
                self, 'Error', 'Please select the reference file, forward and reverse files, and an output folder.'
            )
            return

        start_time = datetime.datetime.now()  # Start time stamp

        random_string = str(random.getrandbits(32))

        activate_command1 = f"conda run -n rsem_env rsem-prepare-reference --bowtie2 {self.reference_file} {self.output_folder}/{random_string}"
        subprocess.run(activate_command1, shell=True, check=True)

        if len(self.forward_files) == 1 and len(self.reverse_files) == 1:
            forward_file = self.forward_files[0]
            reverse_file = self.reverse_files[0]
            activate_command2 = f"conda run -n rsem_env rsem-calculate-expression --bowtie2 --paired-end -p 16 {forward_file} {reverse_file} {self.output_folder}/{random_string} {self.output_folder}/Rsem_output_sample1"
            subprocess.run(activate_command2, shell=True, check=True)
        else:
            for i, (forward_file, reverse_file) in enumerate(zip(self.forward_files, self.reverse_files), start=1):
                activate_command2 = f"conda run -n rsem_env rsem-calculate-expression --bowtie2 --paired-end -p 16 {forward_file} {reverse_file} {self.output_folder}/{random_string} {self.output_folder}/{random_string}_{i}"
                subprocess.run(activate_command2, shell=True, check=True)

        rsem_output_files = [f"{self.output_folder}/{random_string}_{i}.genes.results" for i in range(1, len(self.forward_files) + 1)]
        activate_command3 = f"conda run -n rsem_env rsem-generate-data-matrix {' '.join(rsem_output_files)} > {self.output_folder}/gene_expression.txt"
        subprocess.run(activate_command3, shell=True, check=True)

        end_time = datetime.datetime.now()  # End time stamp
        elapsed_time = end_time - start_time  # Calculate elapsed time

        # Convert elapsed time to hours, minutes, and seconds
        seconds = int(elapsed_time.total_seconds())
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        # Format the elapsed time as 'hours:minutes:seconds'
        elapsed_time_formatted = f'{hours}h.{minutes}m.{seconds}s'

        QMessageBox.information(self, 'Success', f'Analysis completed successfully.\nElapsed Time: {elapsed_time_formatted}')


if __name__ == '__main__':
    app = QApplication([])
    rsem_tool = RSEMTool()
    rsem_tool.show()
    app.exec_()



