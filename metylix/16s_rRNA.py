import sys
from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QLabel, QPushButton,
    QFileDialog, QMessageBox, QHBoxLayout, QComboBox, QLineEdit
)
from PyQt5.QtGui import QIntValidator
from PyQt5.QtCore import pyqtSignal, QObject
import subprocess
import threading
import time


class Signal(QObject):
    started = pyqtSignal()
    completed = pyqtSignal(float)
    error = pyqtSignal(str)


class QIIME2Window(QDialog):
    def __init__(self):
        super().__init__()
        self.input_folder = ""
        self.output_folder = ""
        self.metadata_file = ""
        self.signal = Signal()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('QIIME 2')
        self.setFixedSize(650, 600)
        layout = QVBoxLayout()

        # Input Folder
        input_layout = QVBoxLayout()
        input_layout.addWidget(QLabel('Select Input Folder:'))
        self.input_path_label = QLabel()
        input_layout.addWidget(self.input_path_label)
        input_buttons = QHBoxLayout()
        select_input_btn = QPushButton('Select')
        select_input_btn.clicked.connect(self.select_input_folder)
        clear_input_btn = QPushButton('Clear')
        clear_input_btn.clicked.connect(self.clear_input_folder)
        input_buttons.addWidget(select_input_btn)
        input_buttons.addWidget(clear_input_btn)
        input_layout.addLayout(input_buttons)
        layout.addLayout(input_layout)

        # Metadata File
        metadata_layout = QVBoxLayout()
        metadata_layout.addWidget(QLabel('Select Metadata File (TSV):'))
        self.metadata_path_label = QLabel()
        metadata_layout.addWidget(self.metadata_path_label)
        metadata_buttons = QHBoxLayout()
        select_meta_btn = QPushButton('Select')
        select_meta_btn.clicked.connect(self.select_metadata_file)
        clear_meta_btn = QPushButton('Clear')
        clear_meta_btn.clicked.connect(self.clear_metadata_file)
        metadata_buttons.addWidget(select_meta_btn)
        metadata_buttons.addWidget(clear_meta_btn)
        metadata_layout.addLayout(metadata_buttons)
        layout.addLayout(metadata_layout)

        # Output Folder
        output_layout = QVBoxLayout()
        output_layout.addWidget(QLabel('Select Output Folder:'))
        self.output_path_label = QLabel()
        output_layout.addWidget(self.output_path_label)
        output_buttons = QHBoxLayout()
        select_output_btn = QPushButton('Select')
        select_output_btn.clicked.connect(self.select_output_folder)
        clear_output_btn = QPushButton('Clear')
        clear_output_btn.clicked.connect(self.clear_output_folder)
        output_buttons.addWidget(select_output_btn)
        output_buttons.addWidget(clear_output_btn)
        output_layout.addLayout(output_buttons)
        layout.addLayout(output_layout)

        # Sequence Type Dropdown
        seqtype_layout = QVBoxLayout()
        seqtype_layout.addWidget(QLabel("Select Sequence Type:"))
        self.seq_type_dropdown = QComboBox()
        self.seq_type_dropdown.addItems(["EMPSingleEndSequences", "EMPPairedEndSequences"])
        seqtype_layout.addWidget(self.seq_type_dropdown)
        layout.addLayout(seqtype_layout)

        # Trimming Parameters
        trim_layout = QHBoxLayout()
        self.trim_left_input = QLineEdit()
        self.trim_left_input.setPlaceholderText("Trim Left")
        self.trim_left_input.setValidator(QIntValidator(0, 10000))

        self.trunc_len_input = QLineEdit()
        self.trunc_len_input.setPlaceholderText("Trunc Len")
        self.trunc_len_input.setValidator(QIntValidator(0, 10000))

        trim_layout.addWidget(QLabel("Trim Left:"))
        trim_layout.addWidget(self.trim_left_input)
        trim_layout.addWidget(QLabel("Trunc Len:"))
        trim_layout.addWidget(self.trunc_len_input)
        layout.addLayout(trim_layout)

        # Sampling Depth
        sampling_layout = QHBoxLayout()
        self.sampling_depth_input = QLineEdit()
        self.sampling_depth_input.setPlaceholderText("Sampling Depth")
        self.sampling_depth_input.setValidator(QIntValidator(1, 1000000))

        sampling_layout.addWidget(QLabel("Sampling Depth:"))
        sampling_layout.addWidget(self.sampling_depth_input)
        layout.addLayout(sampling_layout)

        # Run and Cancel Buttons
        buttons_layout = QHBoxLayout()
        run_btn = QPushButton('Run QIIME 2 Analysis')
        run_btn.clicked.connect(self.run_analysis)
        cancel_btn = QPushButton('Cancel')
        cancel_btn.clicked.connect(self.close)
        buttons_layout.addWidget(run_btn)
        buttons_layout.addWidget(cancel_btn)
        layout.addLayout(buttons_layout)

        # Connect signals
        self.signal.started.connect(self.show_running_msg)
        self.signal.completed.connect(self.show_complete_msg)
        self.signal.error.connect(self.show_error_msg)

        self.setLayout(layout)

    def select_input_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Select Input Folder')
        if folder:
            self.input_folder = folder
            self.input_path_label.setText(folder)

    def clear_input_folder(self):
        self.input_folder = ""
        self.input_path_label.setText("")

    def select_metadata_file(self):
        file, _ = QFileDialog.getOpenFileName(self, 'Select Metadata File', '', 'TSV Files (*.tsv)')
        if file:
            self.metadata_file = file
            self.metadata_path_label.setText(file)

    def clear_metadata_file(self):
        self.metadata_file = ""
        self.metadata_path_label.setText("")

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Select Output Folder')
        if folder:
            self.output_folder = folder
            self.output_path_label.setText(folder)

    def clear_output_folder(self):
        self.output_folder = ""
        self.output_path_label.setText("")

    def run_analysis(self):
        if not self.input_folder or not self.output_folder or not self.metadata_file:
            QMessageBox.critical(self, 'Error', 'Please select input/output folders and metadata file.')
            return

        if not self.trim_left_input.text() or not self.trunc_len_input.text() or not self.sampling_depth_input.text():
            QMessageBox.critical(self, 'Error', 'Please fill all numeric fields (Trim Left, Trunc Len, Sampling Depth).')
            return

        seq_type = self.seq_type_dropdown.currentText()
        trim_left = self.trim_left_input.text()
        trunc_len = self.trunc_len_input.text()
        sampling_depth = self.sampling_depth_input.text()

        commands = [
            ['qiime', 'tools', 'import', '--type', seq_type,
             '--input-path', self.input_folder,
             '--output-path', f'{self.output_folder}/emp-sequences.qza'],

            ['qiime', 'demux', 'emp-single',
             '--i-seqs', f'{self.output_folder}/emp-sequences.qza',
             '--m-barcodes-file', self.metadata_file,
             '--m-barcodes-column', 'barcode-sequence',
             '--o-per-sample-sequences', f'{self.output_folder}/demux.qza',
             '--o-error-correction-details', f'{self.output_folder}/demux-details.qza'],

            ['qiime', 'dada2', 'denoise-single',
             '--i-demultiplexed-seqs', f'{self.output_folder}/demux.qza',
             '--p-trim-left', trim_left,
             '--p-trunc-len', trunc_len,
             '--o-representative-sequences', f'{self.output_folder}/rep-seqs.qza',
             '--o-table', f'{self.output_folder}/table.qza',
             '--o-denoising-stats', f'{self.output_folder}/stats.qza'],

            ['qiime', 'phylogeny', 'align-to-tree-mafft-fasttree',
             '--i-sequences', f'{self.output_folder}/rep-seqs.qza',
             '--o-alignment', f'{self.output_folder}/aligned.qza',
             '--o-masked-alignment', f'{self.output_folder}/masked-aligned.qza',
             '--o-tree', f'{self.output_folder}/unrooted-tree.qza',
             '--o-rooted-tree', f'{self.output_folder}/rooted-tree.qza'],

            ['qiime', 'diversity', 'core-metrics-phylogenetic',
             '--i-phylogeny', f'{self.output_folder}/rooted-tree.qza',
             '--i-table', f'{self.output_folder}/table.qza',
             '--p-sampling-depth', sampling_depth,
             '--m-metadata-file', self.metadata_file,
             '--output-dir', f'{self.output_folder}/core-metrics-results'],
        ]

        threading.Thread(target=self.execute_commands, args=(commands,)).start()

    def execute_commands(self, commands):
        start_time = time.time()
        self.signal.started.emit()
        for command in commands:
            try:
                subprocess.run(command, check=True)
            except subprocess.CalledProcessError as e:
                self.signal.error.emit(f"Error: {' '.join(e.cmd)}\nExit code: {e.returncode}")
                return
        duration = time.time() - start_time
        self.signal.completed.emit(duration)

    def show_running_msg(self):
        QMessageBox.information(self, 'Running', 'QIIME 2 analysis has started.')

    def show_complete_msg(self, duration):
        QMessageBox.information(self, 'Completed', f'QIIME 2 completed in {duration:.2f} seconds.')

    def show_error_msg(self, error_msg):
        QMessageBox.critical(self, 'Error', error_msg)


def main():
    app = QApplication(sys.argv)
    window = QIIME2Window()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()


