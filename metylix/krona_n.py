import sys
import os
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QFileDialog,
    QVBoxLayout, QHBoxLayout, QTextEdit, QListWidget, QMessageBox
)

class KronaGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Krona Chart Generator")
        self.setGeometry(200, 200, 700, 500)

        self.input_files = []
        self.output_folder = ""

        self.label_input = QLabel("Input Kraken2 Output (.txt) Files:")
        self.list_input_files = QListWidget()
        self.btn_add_files = QPushButton("Add Files")
        self.btn_clear_files = QPushButton("Clear Files")

        self.btn_add_files.clicked.connect(self.add_files)
        self.btn_clear_files.clicked.connect(self.clear_files)

        self.btn_select_output = QPushButton("Select Output Folder")
        self.label_output = QLabel("No folder selected")
        self.btn_select_output.clicked.connect(self.select_output_folder)

        self.btn_generate = QPushButton("Generate Krona Charts")
        self.btn_generate.clicked.connect(self.generate_krona_charts)

        self.logs = QTextEdit()
        self.logs.setReadOnly(True)

        layout = QVBoxLayout()
        layout.addWidget(self.label_input)
        layout.addWidget(self.list_input_files)

        hlayout = QHBoxLayout()
        hlayout.addWidget(self.btn_add_files)
        hlayout.addWidget(self.btn_clear_files)
        layout.addLayout(hlayout)

        layout.addWidget(self.btn_select_output)
        layout.addWidget(self.label_output)
        layout.addWidget(self.btn_generate)
        layout.addWidget(QLabel("Logs:"))
        layout.addWidget(self.logs)

        self.setLayout(layout)

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Kraken2 Output Files", "", "Text Files (*.txt)")
        if files:
            self.input_files.extend(files)
            self.list_input_files.addItems(files)

    def clear_files(self):
        self.input_files = []
        self.list_input_files.clear()

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_folder = folder
            self.label_output.setText(folder)

    def generate_krona_charts(self):
        if not self.input_files:
            QMessageBox.warning(self, "Missing Input", "Please add at least one Kraken2 .txt file.")
            return

        if not self.output_folder:
            QMessageBox.warning(self, "Missing Output Folder", "Please select an output folder.")
            return

        if not self.check_krona_installed():
            QMessageBox.critical(self, "Krona Not Found", "❌ 'ktImportText' is not installed or not in PATH.")
            return

        self.logs.clear()
        self.logs.append("⏳ Starting Krona chart generation...\n")

        for file_path in self.input_files:
            base_name = os.path.basename(file_path)
            base_no_ext = os.path.splitext(base_name)[0]
            krona_input_file = os.path.join(self.output_folder, f"{base_no_ext}_krona_input.txt")
            krona_output_file = os.path.join(self.output_folder, f"{base_no_ext}_krona.html")

            self.logs.append(f"📂 Processing: {base_name}")

            try:
                # Step 1: Filter only classified reads and extract taxonomy field
                self.logs.append("🔍 Filtering classified reads and formatting input...")
                with open(file_path, 'r') as infile:
                    taxonomy_counts = {}
                    for line in infile:
                        if line.startswith("C"):  # Only classified reads
                            parts = line.strip().split('\t')
                            if len(parts) >= 6:
                                taxonomy = parts[5]
                                taxonomy_counts[taxonomy] = taxonomy_counts.get(taxonomy, 0) + 1

                with open(krona_input_file, 'w') as out:
                    for taxonomy, count in taxonomy_counts.items():
                        formatted_tax = taxonomy.replace(";", "\t")
                        out.write(f"{count}\t{formatted_tax}\n")

                self.logs.append(f"📄 Krona input saved: {krona_input_file}")

                # Step 2: Run Krona
                cmd = f"ktImportText \"{krona_input_file}\" -o \"{krona_output_file}\""
                self.logs.append(f"🔧 Running: {cmd}")
                result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                if result.returncode == 0:
                    self.logs.append(f"✅ Success: {krona_output_file}\n")
                else:
                    self.logs.append(f"❌ Error:\n{result.stderr}\n")

            except Exception as e:
                self.logs.append(f"❌ Exception while processing {base_name}: {str(e)}\n")

        self.logs.append("✅ Krona chart generation complete.")

    def check_krona_installed(self):
        try:
            subprocess.run(["ktImportText", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except FileNotFoundError:
            return False

if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = KronaGUI()
    gui.show()
    sys.exit(app.exec_())
import sys
import os
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QFileDialog,
    QVBoxLayout, QHBoxLayout, QTextEdit, QListWidget, QMessageBox
)

class KronaGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Krona Chart Generator")
        self.setGeometry(200, 200, 700, 500)

        self.input_files = []
        self.output_folder = ""

        # Input file section
        self.label_input = QLabel("Input .txt Files (from Kraken2):")
        self.list_input_files = QListWidget()
        self.btn_add_files = QPushButton("Add Files")
        self.btn_clear_files = QPushButton("Clear Files")

        self.btn_add_files.clicked.connect(self.add_files)
        self.btn_clear_files.clicked.connect(self.clear_files)

        # Output folder section
        self.btn_select_output = QPushButton("Select Output Folder")
        self.label_output = QLabel("No folder selected")
        self.btn_select_output.clicked.connect(self.select_output_folder)

        # Generate button
        self.btn_generate = QPushButton("Generate Krona Charts")
        self.btn_generate.clicked.connect(self.generate_krona_charts)

        # Logs
        self.logs = QTextEdit()
        self.logs.setReadOnly(True)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.label_input)
        layout.addWidget(self.list_input_files)

        hlayout = QHBoxLayout()
        hlayout.addWidget(self.btn_add_files)
        hlayout.addWidget(self.btn_clear_files)
        layout.addLayout(hlayout)

        layout.addWidget(self.btn_select_output)
        layout.addWidget(self.label_output)
        layout.addWidget(self.btn_generate)
        layout.addWidget(QLabel("Logs:"))
        layout.addWidget(self.logs)

        self.setLayout(layout)

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Kraken2 Output (.txt) Files", "", "Text Files (*.txt)")
        if files:
            self.input_files.extend(files)
            self.list_input_files.addItems(files)

    def clear_files(self):
        self.input_files = []
        self.list_input_files.clear()

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_folder = folder
            self.label_output.setText(folder)

    def generate_krona_charts(self):
        if not self.input_files:
            QMessageBox.warning(self, "Missing Input", "Please add at least one Kraken2 .txt file.")
            return

        if not self.output_folder:
            QMessageBox.warning(self, "Missing Output Folder", "Please select an output folder.")
            return

        # Check if ktImportText is available
        if not self.check_krona_installed():
            QMessageBox.critical(self, "Krona Not Found", "❌ 'ktImportText' is not installed or not in PATH.")
            return

        self.logs.clear()
        self.logs.append("⏳ Starting Krona chart generation...\n")

        for file_path in self.input_files:
            base_name = os.path.basename(file_path)
            base_no_ext = os.path.splitext(base_name)[0]
            output_file = os.path.join(self.output_folder, f"{base_no_ext}_krona.html")

            cmd = f"ktImportText \"{file_path}\" -o \"{output_file}\""

            self.logs.append(f"📂 Processing: {base_name}")
            self.logs.append(f"🔧 Running: {cmd}")

            try:
                result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                if result.returncode == 0:
                    self.logs.append(f"✅ Success: {output_file}\n")
                else:
                    self.logs.append(f"❌ Error for {base_name}:\n{result.stderr}\n")

            except Exception as e:
                self.logs.append(f"❌ Exception while processing {base_name}: {str(e)}\n")

        self.logs.append("✅ Krona chart generation complete.")

    def check_krona_installed(self):
        try:
            subprocess.run(["ktImportText", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return

