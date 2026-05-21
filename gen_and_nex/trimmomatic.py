from PyQt5.QtWidgets import (QApplication, QWidget, QComboBox, QLabel, QPushButton,
                             QFileDialog, QHBoxLayout, QVBoxLayout, QLineEdit, QMessageBox,
                             QDialog, QTextEdit, QGridLayout, QCheckBox, QGroupBox, QRadioButton,
                             QButtonGroup, QStackedWidget)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import subprocess
import os
import sys
import time
import tempfile


# ── Built-in adapter sequences ────────────────────────────────────────────────
BUILTIN_ADAPTERS = {
    "TruSeq2-PE (Illumina GAII paired-end)": """>PrefixPE/1
AATGATACGGCGACCACCGAGATCTACACTCTTTCCCTACACGACGCTCTTCCGATCT
>PrefixPE/2
CAAGCAGAAGACGGCATACGAGATCGGTCTCGGCATTCCTGCTGAACCGCTCTTCCGATCT
>PE1
AATGATACGGCGACCACCGAGATCTACACTCTTTCCCTACACGACGCTCTTCCGATCT
>PE1_rc
AGATCGGAAGAGCGTCGTGTAGGGAAAGAGTGTAGATCTCGGTGGTCGCCGTATCATT
>PE2
CAAGCAGAAGACGGCATACGAGATCGGTCTCGGCATTCCTGCTGAACCGCTCTTCCGATCT
>PE2_rc
AGATCGGAAGAGCGGTTCAGCAGGAATGCCGAGACCGATCTCGTATGCCGTCTTCTGCTTG""",

    "TruSeq3-PE (Illumina HiSeq/MiSeq paired-end)": """>PrefixPE/1
TACACTCTTTCCCTACACGACGCTCTTCCGATCT
>PrefixPE/2
GTGACTGGAGTTCAGACGTGTGCTCTTCCGATCT""",

    "TruSeq3-PE-2 (Illumina HiSeq/MiSeq PE, extended)": """>PrefixPE/1
TACACTCTTTCCCTACACGACGCTCTTCCGATCT
>PrefixPE/2
GTGACTGGAGTTCAGACGTGTGCTCTTCCGATCT
>PE1
TACACTCTTTCCCTACACGACGCTCTTCCGATCT
>PE1_rc
AGATCGGAAGAGCGTCGTGTAGGGAAAGAGTGTA
>PE2
GTGACTGGAGTTCAGACGTGTGCTCTTCCGATCT
>PE2_rc
AGATCGGAAGAGCACACGTCTGAACTCCAGTCAC""",

    "TruSeq2-SE (Illumina GAII single-end)": """>TruSeq2_SE
AGATCGGAAGAGCTCGTATGCCGTCTTCTGCTTG
>TruSeq2_SE_rc
CAAGCAGAAGACGGCATACGAGCTCTTCCGATCT""",

    "TruSeq3-SE (Illumina HiSeq/MiSeq single-end)": """>TruSeq3_SE
AGATCGGAAGAGCACACGTCTGAACTCCAGTCAC""",

    "NexteraPE-PE (Nextera paired-end)": """>PrefixNX/1
AGATGTGTATAAGAGACAG
>PrefixNX/2
AGATGTGTATAAGAGACAG
>Trans1
TCGTCGGCAGCGTCAGATGTGTATAAGAGACAG
>Trans1_rc
CTGTCTCTTATACACATCTGACGCTGCCGACGA
>Trans2
GTCTCGTGGGCTCGGAGATGTGTATAAGAGACAG
>Trans2_rc
CTGTCTCTTATACACATCTCCGAGCCCACGAGACT""",
}


class TrimmomaticWorker(QThread):
    finished = pyqtSignal(bool)

    def __init__(self, forward_files, reverse_files, output_folder,
                 adapter_file, customized_params, phred, output_ext=".fastq.gz"):
        super().__init__()
        self.forward_files = forward_files
        self.reverse_files = reverse_files
        self.output_folder = output_folder
        self.adapter_file = adapter_file
        self.customized_params = customized_params
        self.phred = phred
        self.output_ext = output_ext          # ".fastq.gz", ".fq.gz", ".fastq", or ".fq"
        self.cancelled = False
        self.error_msg = ""
        self._temp_adapter = None

    def set_temp_adapter(self, tmp):
        """Hold a reference so the temp file isn't deleted while the thread runs."""
        self._temp_adapter = tmp

    def cancel(self):
        self.cancelled = True

    def run(self):
        start_time = time.time()

        if self.customized_params:
            leading_value  = self.customized_params.get("LEADING",  "30")
            trailing_value = self.customized_params.get("TRAILING", "30")
            minlen_value   = self.customized_params.get("MINLEN",   "36")
            headcrop_value = self.customized_params.get("HEADCROP", "15")
        else:
            leading_value  = "30"
            trailing_value = "30"
            minlen_value   = "36"
            headcrop_value = "15"

        def stem(path):
            """Strip compression/format suffix to get bare sample name.
            e.g. SRR396637_1.fq.gz  -> SRR396637_1
                 SRR396637_1.fastq  -> SRR396637_1
            """
            base = os.path.basename(path)
            for suffix in (".fastq.gz", ".fq.gz", ".fastq", ".fq"):
                if base.endswith(suffix):
                    return base[: -len(suffix)]
            return os.path.splitext(base)[0]

        try:
            for i in range(len(self.forward_files)):
                if self.cancelled:
                    self.finished.emit(False)
                    return

                forward_file = self.forward_files[i]
                reverse_file = self.reverse_files[i]

                fwd_stem = stem(forward_file)   # e.g. "SRR396637_1"
                rev_stem = stem(reverse_file)   # e.g. "SRR396637_2"

                # Output filenames:  SRR396637_1_paired.fq.gz  etc.
                paired_output_file    = os.path.join(self.output_folder, f"{fwd_stem}_paired{self.output_ext}")
                unpaired_output_file  = os.path.join(self.output_folder, f"{fwd_stem}_unpaired{self.output_ext}")
                paired_output2_file   = os.path.join(self.output_folder, f"{rev_stem}_paired{self.output_ext}")
                unpaired_output2_file = os.path.join(self.output_folder, f"{rev_stem}_unpaired{self.output_ext}")
                report_file           = os.path.join(self.output_folder, f"{fwd_stem}_{rev_stem}_report.txt")

                trimmomatic_cmd = [
                    'conda', 'run', '-n', 'trimmomatic_env',
                    'trimmomatic', 'PE',
                    self.phred,
                    '-threads', '16',
                    forward_file, reverse_file,
                    paired_output_file, unpaired_output_file,
                    paired_output2_file, unpaired_output2_file,
                    f"ILLUMINACLIP:{self.adapter_file}:2:30:10",
                    f"LEADING:{leading_value}",
                    f"TRAILING:{trailing_value}",
                    "SLIDINGWINDOW:4:15",
                    f"MINLEN:{minlen_value}",
                    f"HEADCROP:{headcrop_value}",
                    "-summary", report_file,
                ]

                try:
                    process = subprocess.Popen(trimmomatic_cmd, stdout=subprocess.PIPE,
                                               stderr=subprocess.PIPE)
                    output, error = process.communicate()
                    if process.returncode != 0:
                        self.error_msg = error.decode(errors="replace")
                        self.finished.emit(False)
                        return
                except Exception as e:
                    self.error_msg = str(e)
                    self.finished.emit(False)
                    return

            self.finished.emit(True)

        except Exception as e:
            self.error_msg = str(e)
            self.finished.emit(False)


class Trimmomatic_GUI(QDialog):
    def __init__(self):
        super().__init__()

        self.forward_files = []
        self.reverse_files = []
        self.output_folder = ""
        self.adapter_file  = ""
        self.customized_params = False
        self._temp_adapter_file = None

        self.initUI()

    # ── UI construction ────────────────────────────────────────────────────────

    def initUI(self):
        self.setWindowTitle('Trimmomatic')
        self.setMinimumWidth(720)
        layout = QVBoxLayout()
        layout.setSpacing(8)

        # ── Forward files ──────────────────────────────────────────────────────
        layout.addWidget(self._file_group(
            label="Forward Files (R1)",
            text_widget_attr="forward_paths",
            select_slot=self.select_forward_files,
            add_slot=self.add_forward_files,
            delete_slot=self.delete_forward_file,
            clear_slot=self.clear_forward_files,
        ))

        # ── Reverse files ──────────────────────────────────────────────────────
        layout.addWidget(self._file_group(
            label="Reverse Files (R2)",
            text_widget_attr="reverse_paths",
            select_slot=self.select_reverse_files,
            add_slot=self.add_reverse_files,
            delete_slot=self.delete_reverse_file,
            clear_slot=self.clear_reverse_files,
        ))

        # ── Adapter section ────────────────────────────────────────────────────
        layout.addWidget(self._adapter_group())

        # ── Output folder ──────────────────────────────────────────────────────
        out_group = QGroupBox("Output Folder")
        out_layout = QHBoxLayout()
        self.output_path_label = QLabel("(not selected)")
        self.output_path_label.setWordWrap(True)
        out_layout.addWidget(self.output_path_label, 1)
        out_btn = QPushButton("Select")
        out_btn.clicked.connect(self.select_output_folder)
        out_layout.addWidget(out_btn)
        out_group.setLayout(out_layout)
        layout.addWidget(out_group)

        # ── Output format ──────────────────────────────────────────────────────
        fmt_group = QGroupBox("Output Format")
        fmt_layout = QHBoxLayout()
        self.fmt_fqgz_rb  = QRadioButton(".fq.gz  (compressed, recommended)")
        self.fmt_fastqgz_rb = QRadioButton(".fastq.gz  (compressed)")
        self.fmt_fq_rb    = QRadioButton(".fq  (uncompressed)")
        self.fmt_fastq_rb = QRadioButton(".fastq  (uncompressed)")
        self.fmt_fqgz_rb.setChecked(True)
        fmt_bg = QButtonGroup(self)
        for rb in (self.fmt_fqgz_rb, self.fmt_fastqgz_rb, self.fmt_fq_rb, self.fmt_fastq_rb):
            fmt_bg.addButton(rb)
            fmt_layout.addWidget(rb)
        fmt_group.setLayout(fmt_layout)
        layout.addWidget(fmt_group)

        # ── Phred quality encoding ─────────────────────────────────────────────
        phred_group = QGroupBox("Quality Encoding")
        phred_layout = QHBoxLayout()
        self.phred33_rb = QRadioButton("-phred33  (Sanger / Illumina ≥1.8 — most common)")
        self.phred64_rb = QRadioButton("-phred64  (Illumina 1.3–1.7)")
        self.phred33_rb.setChecked(True)
        phred_bg = QButtonGroup(self)
        phred_bg.addButton(self.phred33_rb)
        phred_bg.addButton(self.phred64_rb)
        phred_layout.addWidget(self.phred33_rb)
        phred_layout.addWidget(self.phred64_rb)
        phred_group.setLayout(phred_layout)
        layout.addWidget(phred_group)

        # ── Customised parameters ──────────────────────────────────────────────
        layout.addWidget(self._params_group())

        # ── Run / Cancel ───────────────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        run_btn = QPushButton("▶  Run Trimmomatic")
        run_btn.setDefault(True)
        run_btn.clicked.connect(self.run_trimmomatic)
        cancel_btn = QPushButton("Close")
        cancel_btn.clicked.connect(self.close)
        btn_layout.addWidget(run_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.adjustSize()
        self._center()

    # ── Helper: forward/reverse file group ────────────────────────────────────

    def _file_group(self, label, text_widget_attr,
                    select_slot, add_slot, delete_slot, clear_slot):
        group = QGroupBox(label)
        v = QVBoxLayout()

        text = QTextEdit()
        text.setReadOnly(True)
        text.setFixedHeight(70)
        setattr(self, text_widget_attr, text)
        v.addWidget(text)

        h = QHBoxLayout()
        for name, slot in [("Select", select_slot), ("Add", add_slot),
                            ("Delete", delete_slot), ("Clear", clear_slot)]:
            b = QPushButton(name)
            b.clicked.connect(slot)
            h.addWidget(b)
        v.addLayout(h)
        group.setLayout(v)
        return group

    # ── Helper: adapter group ─────────────────────────────────────────────────

    def _adapter_group(self):
        group = QGroupBox("Adapter Sequences")
        v = QVBoxLayout()

        self.adapter_builtin_rb = QRadioButton("Use built-in adapter preset:")
        self.adapter_custom_rb  = QRadioButton("Use custom adapter file:")
        self.adapter_builtin_rb.setChecked(True)

        adapter_bg = QButtonGroup(self)
        adapter_bg.addButton(self.adapter_builtin_rb)
        adapter_bg.addButton(self.adapter_custom_rb)
        self.adapter_builtin_rb.toggled.connect(self._adapter_mode_changed)

        mode_row = QHBoxLayout()
        mode_row.addWidget(self.adapter_builtin_rb)
        mode_row.addWidget(self.adapter_custom_rb)
        mode_row.addStretch()
        v.addLayout(mode_row)

        self.adapter_stack = QStackedWidget()

        # Page 0 – preset combo
        preset_page = QWidget()
        preset_row  = QHBoxLayout(preset_page)
        preset_row.setContentsMargins(0, 0, 0, 0)
        self.adapter_combo = QComboBox()
        for name in BUILTIN_ADAPTERS:
            self.adapter_combo.addItem(name)
        preset_row.addWidget(self.adapter_combo, 1)
        preview_btn = QPushButton("Preview sequences")
        preview_btn.clicked.connect(self._preview_adapter)
        preset_row.addWidget(preview_btn)
        self.adapter_stack.addWidget(preset_page)

        # Page 1 – custom file
        custom_page = QWidget()
        custom_row  = QHBoxLayout(custom_page)
        custom_row.setContentsMargins(0, 0, 0, 0)
        self.adapter_path_label = QLabel("(no file selected)")
        self.adapter_path_label.setWordWrap(True)
        custom_row.addWidget(self.adapter_path_label, 1)
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self.select_adapter_file)
        custom_row.addWidget(browse_btn)
        self.adapter_stack.addWidget(custom_page)

        v.addWidget(self.adapter_stack)

        hint = QLabel("<i>ILLUMINACLIP parameters fixed at seedMismatches=2 "
                      "palindromeClipThreshold=30 simpleClipThreshold=10</i>")
        hint.setTextFormat(Qt.RichText)
        v.addWidget(hint)

        group.setLayout(v)
        return group

    def _adapter_mode_changed(self, builtin_checked):
        self.adapter_stack.setCurrentIndex(0 if builtin_checked else 1)

    def _preview_adapter(self):
        name = self.adapter_combo.currentText()
        seq  = BUILTIN_ADAPTERS[name]
        dlg  = QDialog(self)
        dlg.setWindowTitle(f"Adapter preview – {name}")
        v = QVBoxLayout(dlg)
        te = QTextEdit()
        te.setReadOnly(True)
        te.setPlainText(seq)
        te.setFontFamily("Courier")
        v.addWidget(te)
        ok = QPushButton("Close")
        ok.clicked.connect(dlg.accept)
        v.addWidget(ok)
        dlg.resize(600, 300)
        dlg.exec_()

    # ── Helper: customised params group ───────────────────────────────────────

    def _params_group(self):
        group = QGroupBox("Trimming Parameters")
        v = QVBoxLayout()

        self.customized_checkbox = QCheckBox("Enable customised parameters (uncheck = use defaults)")
        self.customized_checkbox.setChecked(False)
        self.customized_checkbox.stateChanged.connect(self._update_customized_params)
        v.addWidget(self.customized_checkbox)

        params_row = QHBoxLayout()
        self._param_fields = {}
        defaults = [("LEADING", "30"), ("TRAILING", "30"),
                    ("MINLEN", "36"),  ("HEADCROP", "15")]
        for name, default in defaults:
            params_row.addWidget(QLabel(f"{name}:"))
            le = QLineEdit(default)
            le.setFixedWidth(50)
            le.setEnabled(False)
            params_row.addWidget(le)
            self._param_fields[name] = le

        params_row.addStretch()
        v.addLayout(params_row)
        hint = QLabel("<i>SLIDINGWINDOW:4:15 is always applied</i>")
        hint.setTextFormat(Qt.RichText)
        v.addWidget(hint)

        group.setLayout(v)
        return group

    # ── Slots ──────────────────────────────────────────────────────────────────

    def _center(self):
        fg = self.frameGeometry()
        fg.moveCenter(QApplication.desktop().availableGeometry().center())
        self.move(fg.topLeft())

    # Forward files
    def select_forward_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, 'Select Forward Files', '',
                                                'FASTQ Files (*.fastq *.fq *.fastq.gz *.fq.gz)')
        self.forward_files = paths
        self._update_text(self.forward_paths, self.forward_files)

    def add_forward_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, 'Add Forward Files', '',
                                                'FASTQ Files (*.fastq *.fq *.fastq.gz *.fq.gz)')
        self.forward_files.extend(paths)
        self._update_text(self.forward_paths, self.forward_files)

    def delete_forward_file(self):
        idx = self.forward_paths.textCursor().blockNumber()
        if 0 <= idx < len(self.forward_files):
            del self.forward_files[idx]
            self._update_text(self.forward_paths, self.forward_files)

    def clear_forward_files(self):
        self.forward_files.clear()
        self._update_text(self.forward_paths, self.forward_files)

    # Reverse files
    def select_reverse_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, 'Select Reverse Files', '',
                                                'FASTQ Files (*.fastq *.fq *.fastq.gz *.fq.gz)')
        self.reverse_files = paths
        self._update_text(self.reverse_paths, self.reverse_files)

    def add_reverse_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, 'Add Reverse Files', '',
                                                'FASTQ Files (*.fastq *.fq *.fastq.gz *.fq.gz)')
        self.reverse_files.extend(paths)
        self._update_text(self.reverse_paths, self.reverse_files)

    def delete_reverse_file(self):
        idx = self.reverse_paths.textCursor().blockNumber()
        if 0 <= idx < len(self.reverse_files):
            del self.reverse_files[idx]
            self._update_text(self.reverse_paths, self.reverse_files)

    def clear_reverse_files(self):
        self.reverse_files.clear()
        self._update_text(self.reverse_paths, self.reverse_files)

    def _update_text(self, widget, file_list):
        widget.setPlainText('\n'.join(file_list))

    # Adapter (custom file mode)
    def select_adapter_file(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Select Adapter File', '', 'All Files (*)')
        if path:
            self.adapter_file = path
            self.adapter_path_label.setText(path)

    # Output folder
    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Select Output Folder')
        if folder:
            self.output_folder = folder
            self.output_path_label.setText(folder)

    # Customised params toggle
    def _update_customized_params(self, state):
        enabled = (state == Qt.Checked)
        self.customized_params = enabled
        for le in self._param_fields.values():
            le.setEnabled(enabled)

    # ── Run ────────────────────────────────────────────────────────────────────

    def _resolve_adapter_path(self):
        """Return a filesystem path to the adapter FASTA.

        For built-in presets, write a NamedTemporaryFile and return its path.
        For custom files, return the user-selected path.
        """
        if self.adapter_builtin_rb.isChecked():
            name = self.adapter_combo.currentText()
            seq  = BUILTIN_ADAPTERS[name]
            self._temp_adapter_file = tempfile.NamedTemporaryFile(
                mode='w', suffix='.fa', delete=False, prefix='trimmomatic_adapter_'
            )
            self._temp_adapter_file.write(seq)
            self._temp_adapter_file.flush()
            self._temp_adapter_file.close()
            return self._temp_adapter_file.name
        else:
            return self.adapter_file

    def _selected_output_ext(self):
        """Return the output file extension chosen by the user."""
        if self.fmt_fqgz_rb.isChecked():
            return ".fq.gz"
        elif self.fmt_fastqgz_rb.isChecked():
            return ".fastq.gz"
        elif self.fmt_fq_rb.isChecked():
            return ".fq"
        else:
            return ".fastq"

    def run_trimmomatic(self):
        if not self.forward_files or not self.reverse_files:
            QMessageBox.warning(self, "Missing input", "Please select forward and reverse files.")
            return
        if len(self.forward_files) != len(self.reverse_files):
            QMessageBox.warning(self, "Mismatch",
                                f"Number of forward files ({len(self.forward_files)}) "
                                f"does not match reverse files ({len(self.reverse_files)}).")
            return
        if not self.output_folder:
            QMessageBox.warning(self, "Missing output", "Please select an output folder.")
            return
        if self.adapter_custom_rb.isChecked() and not self.adapter_file:
            QMessageBox.warning(self, "Missing adapter", "Please select a custom adapter file.")
            return

        adapter_path = self._resolve_adapter_path()
        phred        = "-phred33" if self.phred33_rb.isChecked() else "-phred64"
        output_ext   = self._selected_output_ext()

        customized_params = None
        if self.customized_params:
            customized_params = {k: le.text() for k, le in self._param_fields.items()}

        self.worker = TrimmomaticWorker(
            self.forward_files, self.reverse_files,
            self.output_folder, adapter_path, customized_params, phred,
            output_ext=output_ext
        )
        if hasattr(self, '_temp_adapter_file') and self._temp_adapter_file:
            self.worker.set_temp_adapter(self._temp_adapter_file)

        self.worker.finished.connect(self.handle_trimmomatic_finished)
        self.worker.start()

        self.progress_msg = QMessageBox(
            QMessageBox.Information, "Processing",
            "Trimmomatic is running — please wait…\n\nYou may press Cancel to abort.",
            QMessageBox.Cancel, self
        )
        self.progress_msg.setWindowModality(Qt.WindowModal)
        self.progress_msg.button(QMessageBox.Cancel).clicked.connect(self.worker.cancel)
        self.progress_msg.show()
        self.start_time = time.time()

    # ── Result handler ─────────────────────────────────────────────────────────

    def handle_trimmomatic_finished(self, success):
        if hasattr(self, '_temp_adapter_file') and self._temp_adapter_file:
            try:
                os.unlink(self._temp_adapter_file.name)
            except OSError:
                pass
            self._temp_adapter_file = None

        self.progress_msg.close()

        if success:
            elapsed = time.strftime("%Hh %Mm %Ss", time.gmtime(time.time() - self.start_time))
            msg = QMessageBox(QMessageBox.Information, "Done",
                              f"Trimmomatic finished successfully.\nElapsed Time: {elapsed}",
                              QMessageBox.Ok, self)
            msg.setWindowModality(Qt.WindowModal)
            msg.accepted.connect(self.close)
            msg.exec_()
        else:
            msg = QMessageBox(QMessageBox.Critical, "Error",
                              "An error occurred during Trimmomatic processing.",
                              QMessageBox.Ok, self)
            msg.setWindowModality(Qt.WindowModal)
            msg.setDetailedText(self.worker.error_msg)
            msg.exec_()

    def closeEvent(self, event):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.cancel()
            self.worker.finished.disconnect()
            self.worker.terminate()
        if hasattr(self, '_temp_adapter_file') and self._temp_adapter_file:
            try:
                os.unlink(self._temp_adapter_file.name)
            except OSError:
                pass
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Trimmomatic_GUI()
    window.show()
    sys.exit(app.exec_())
