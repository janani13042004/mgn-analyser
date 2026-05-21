#!/usr/bin/env python3

# Enhanced Metagenome Pipeline GUI (All Steps Mandatory) with Min Contig Length Input

import sys
import subprocess
import threading
import os
from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QLabel, QPushButton,
    QFileDialog, QMessageBox, QTextEdit, QLineEdit, QHBoxLayout, QProgressBar
)
from PyQt5.QtCore import pyqtSignal, QObject, Qt


class Signal(QObject):
    started = pyqtSignal()
    completed = pyqtSignal(float)
    error = pyqtSignal(str)
    log = pyqtSignal(str)


class MetagenomePipelineGUI(QDialog):
    def __init__(self):
        super().__init__()
        self.trim_galore_env = 'trimgalore_env'
        self.megahit_env = 'megahit_env'
        self.fraggenescan_env = 'fraggenescan_env'
        self.eggnog_env = 'eggnog_env'
        self.pfamscan_env = 'pfamscan_env'
        self.kraken2_env = 'kraken2_env'

        self.kraken2_db_path = ''
        self.pfam_db_path = ''
        self.eggnog_db_path = ''
        self.default_threads = 8
        self.process = None
        self.signal = Signal()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('METYLIX')
        self.resize(700, 750)
        layout = QVBoxLayout()

        self.forward_label = QLabel('Forward Reads:')
        self.forward_text = QTextEdit()
        self.forward_text.setReadOnly(True)
        self.forward_btn = QPushButton('Select Forward Reads')
        self.forward_btn.clicked.connect(self.select_forward_reads)

        self.reverse_label = QLabel('Reverse Reads:')
        self.reverse_text = QTextEdit()
        self.reverse_text.setReadOnly(True)
        self.reverse_btn = QPushButton('Select Reverse Reads')
        self.reverse_btn.clicked.connect(self.select_reverse_reads)

        self.kraken_db_label = QLabel('Kraken2 DB Path:')
        self.kraken_db_path_text = QTextEdit()
        self.kraken_db_path_text.setFixedHeight(30)
        self.kraken_db_btn = QPushButton('Select Kraken2 DB Folder')
        self.kraken_db_btn.clicked.connect(self.select_kraken_db_path)

        self.pfam_db_label = QLabel('PfamScan DB Path:')
        self.pfam_db_path_text = QTextEdit()
        self.pfam_db_path_text.setFixedHeight(30)
        self.pfam_db_btn = QPushButton('Select PfamScan DB Folder')
        self.pfam_db_btn.clicked.connect(self.select_pfam_db_path)

        self.eggnog_db_label = QLabel('eggNOG DB Path:')
        self.eggnog_db_path_text = QTextEdit()
        self.eggnog_db_path_text.setFixedHeight(30)
        self.eggnog_db_btn = QPushButton('Select eggNOG DB Folder')
        self.eggnog_db_btn.clicked.connect(self.select_eggnog_db_path)

        self.output_label = QLabel('Output Folder:')
        self.output_path_text = QTextEdit()
        self.output_path_text.setFixedHeight(30)
        self.output_btn = QPushButton('Select Output Folder')
        self.output_btn.clicked.connect(self.select_output_folder)

        threads_layout = QHBoxLayout()
        self.threads_label = QLabel('Number of Threads:')
        self.threads_input = QLineEdit(str(self.default_threads))
        self.threads_input.setFixedWidth(50)
        threads_layout.addWidget(self.threads_label)
        threads_layout.addWidget(self.threads_input)

        contig_len_layout = QHBoxLayout()
        self.contig_len_label = QLabel('Min Contig Length:')
        self.contig_len_input = QLineEdit('1000')
        self.contig_len_input.setFixedWidth(80)
        contig_len_layout.addWidget(self.contig_len_label)
        contig_len_layout.addWidget(self.contig_len_input)

        self.run_full_pipeline_btn = QPushButton('Run Full Pipeline')
        self.run_full_pipeline_btn.clicked.connect(self.run_full_pipeline)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()

        layout.addWidget(self.forward_label)
        layout.addWidget(self.forward_text)
        layout.addWidget(self.forward_btn)
        layout.addWidget(self.reverse_label)
        layout.addWidget(self.reverse_text)
        layout.addWidget(self.reverse_btn)

        layout.addWidget(self.kraken_db_label)
        layout.addWidget(self.kraken_db_path_text)
        layout.addWidget(self.kraken_db_btn)

        layout.addWidget(self.pfam_db_label)
        layout.addWidget(self.pfam_db_path_text)
        layout.addWidget(self.pfam_db_btn)

        layout.addWidget(self.eggnog_db_label)
        layout.addWidget(self.eggnog_db_path_text)
        layout.addWidget(self.eggnog_db_btn)

        layout.addWidget(self.output_label)
        layout.addWidget(self.output_path_text)
        layout.addWidget(self.output_btn)

        layout.addLayout(threads_layout)
        layout.addLayout(contig_len_layout)
        layout.addWidget(self.run_full_pipeline_btn)
        layout.addWidget(QLabel("Log Output:"))
        layout.addWidget(self.log_output)
        layout.addWidget(self.progress)

        self.setLayout(layout)

        self.signal.started.connect(self.show_running_msg)
        self.signal.completed.connect(self.show_complete_msg)
        self.signal.error.connect(self.show_error_msg)
        self.signal.log.connect(self.append_log)

    def append_log(self, message):
        self.log_output.append(message)

    def show_running_msg(self):
        self.progress.show()
        self.append_log("Pipeline started...")

    def show_complete_msg(self, duration):
        self.progress.hide()
        self.append_log("Pipeline completed successfully.")
        QMessageBox.information(self, 'Completed', 'Pipeline finished successfully!')

    def show_error_msg(self, message):
        self.progress.hide()
        self.append_log("Error: " + message)
        QMessageBox.critical(self, 'Error', message)

    def run_command_sync(self, cmd, description):
        self.signal.log.emit(f"Running: {' '.join(cmd)}")
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        if proc.returncode != 0:
            raise Exception(f"{description} failed:\n{stderr.decode()}")

    def get_threads(self):
        try:
            t = int(self.threads_input.text())
            if t < 1:
                raise ValueError()
            return t
        except:
            QMessageBox.warning(self, 'Warning', 'Invalid thread number! Using default 8 threads.')
            self.threads_input.setText(str(self.default_threads))
            return self.default_threads

    def get_min_contig_length(self):
        try:
            value = int(self.contig_len_input.text())
            if value < 100:
                raise ValueError()
            return value
        except:
            QMessageBox.warning(self, 'Warning', 'Invalid contig length! Using default 1000 bp.')
            self.contig_len_input.setText('1000')
            return 1000

    def run_full_pipeline(self):
        def pipeline():
            self.signal.started.emit()
            try:
                output_dir = self.output_path_text.toPlainText().strip()
                forward_reads = self.forward_text.toPlainText().strip().split('\n')
                reverse_reads = self.reverse_text.toPlainText().strip().split('\n')
                kraken_db = self.kraken2_db_path
                pfam_db = self.pfam_db_path
                eggnog_db = self.eggnog_db_path
                threads = self.get_threads()
                min_contig = self.get_min_contig_length()

                if not all([forward_reads, reverse_reads, output_dir]):
                    raise Exception("Please select all required inputs.")

                for i, (fwd, rev) in enumerate(zip(forward_reads, reverse_reads)):
                    sample_name = os.path.basename(fwd).split('.')[0]
                    sample_out = os.path.join(output_dir, sample_name)
                    os.makedirs(sample_out, exist_ok=True)

                    trim_out = os.path.join(sample_out, 'trimmed')
                    os.makedirs(trim_out, exist_ok=True)
                    cmd_trim = ['conda', 'run', '-n', self.trim_galore_env, 'trim_galore', '--paired',
                                '-q', '25', '--fastqc', '--cores', str(threads), '-o', trim_out, fwd, rev]
                    self.run_command_sync(cmd_trim, f'Trim Galore for {sample_name}')

                    base_fwd = os.path.basename(fwd).split('.')[0]
                    base_rev = os.path.basename(rev).split('.')[0]
                    trimmed_fwd = os.path.join(trim_out, f'{base_fwd}_val_1.fq')
                    trimmed_rev = os.path.join(trim_out, f'{base_rev}_val_2.fq')

                    assembly_dir = os.path.join(sample_out, 'assembly')
                    cmd_megahit = ['conda', 'run', '-n', self.megahit_env, 'megahit', '-1', trimmed_fwd,
                                   '-2', trimmed_rev, '-o', assembly_dir, '--min-contig-len', str(min_contig),
                                   '-t', str(threads)]
                    self.run_command_sync(cmd_megahit, f'MEGAHIT for {sample_name}')

                    gene_dir = os.path.join(sample_out, 'gene_prediction')
                    os.makedirs(gene_dir, exist_ok=True)
                    contigs_path = os.path.join(assembly_dir, 'final.contigs.fa')
                    cmd_fgs = ['conda', 'run', '-n', self.fraggenescan_env, 'run_FragGeneScan.pl',
                               f"-genome={contigs_path}",
                               f"-out={os.path.join(gene_dir, 'predicted')}",
                               "-complete=1", "-train=complete", f"-thread={str(threads)}"]
                    self.run_command_sync(cmd_fgs, f'FragGeneScan for {sample_name}')

                    annot_dir = os.path.join(sample_out, 'annotation')
                    os.makedirs(annot_dir, exist_ok=True)
                    faa = os.path.join(gene_dir, 'predicted.faa')
                    cmd_eggnog = ['conda', 'run', '-n', self.eggnog_env, 'emapper.py', '-i', faa,
                                  '-o', 'eggnog', '--itype', 'proteins', '--output_dir', annot_dir,
                                  '--data_dir', eggnog_db, '--cpu', str(threads)]
                    self.run_command_sync(cmd_eggnog, f'eggNOG for {sample_name}')

                    cmd_pfam = ['conda', 'run', '-n', self.pfamscan_env, 'pfam_scan.pl', '-fasta', faa,
                                '-dir', pfam_db, '-outfile', os.path.join(annot_dir, 'pfamscan_results.txt')]
                    self.run_command_sync(cmd_pfam, f'PfamScan for {sample_name}')

                    cmd_kraken = ['conda', 'run', '-n', self.kraken2_env, 'kraken2', '--db', kraken_db,
                                  '--paired', trimmed_fwd, trimmed_rev,
                                  '--output', os.path.join(sample_out, 'kraken_output.txt'),
                                  '--report', os.path.join(sample_out, 'kraken_report.txt'), '--use-names']
                    self.run_command_sync(cmd_kraken, f'Kraken2 for {sample_name}')

                self.signal.completed.emit(0)
            except Exception as e:
                self.signal.error.emit(str(e))

        threading.Thread(target=pipeline, daemon=True).start()

    def select_forward_reads(self):
        files, _ = QFileDialog.getOpenFileNames(self, 'Select Forward Reads', '', 'FASTQ Files (*.fastq *.fq *.fastq.gz *.fq.gz)')
        if files:
            self.forward_text.setText('\n'.join(files))

    def select_reverse_reads(self):
        files, _ = QFileDialog.getOpenFileNames(self, 'Select Reverse Reads', '', 'FASTQ Files (*.fastq *.fq *.fastq.gz *.fq.gz)')
        if files:
            self.reverse_text.setText('\n'.join(files))

    def select_kraken_db_path(self):
        folder = QFileDialog.getExistingDirectory(self, 'Select Kraken2 DB Folder')
        if folder:
            self.kraken2_db_path = folder
            self.kraken_db_path_text.setText(folder)

    def select_pfam_db_path(self):
        folder = QFileDialog.getExistingDirectory(self, 'Select PfamScan DB Folder')
        if folder:
            self.pfam_db_path = folder
            self.pfam_db_path_text.setText(folder)

    def select_eggnog_db_path(self):
        folder = QFileDialog.getExistingDirectory(self, 'Select eggNOG DB Folder')
        if folder:
            self.eggnog_db_path = folder
            self.eggnog_db_path_text.setText(folder)

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Select Output Folder')
        if folder:
            self.output_path_text.setText(folder)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MetagenomePipelineGUI()
    window.show()
    sys.exit(app.exec_())

