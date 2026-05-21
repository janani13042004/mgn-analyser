from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QPushButton, QFileDialog, QComboBox, QMessageBox, QLineEdit, QDesktopWidget
from PyQt5.QtCore import QTime, Qt
import os
import subprocess

class BlastGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.dbtype = "nucl"  # Default dbtype is "nucl"
        self.initUI()

    def initUI(self):
        self.setWindowTitle("BLAST")
        self.setGeometry(400, 200, 600, 400)  # Set window position and size
        self.centerWindow()  # Center the window on the screen

        layout = QVBoxLayout()

        # Database File Selection
        self.db_label = QLabel("Database File:")
        self.db_button = QPushButton("Select Database")
        self.db_button.clicked.connect(self.selectDatabaseFile)
        layout.addWidget(self.db_label)
        layout.addWidget(self.db_button)

        # Input File Selection
        self.input_label = QLabel("Input File:")
        self.input_button = QPushButton("Select Input")
        self.input_button.clicked.connect(self.selectInputFile)
        layout.addWidget(self.input_label)
        layout.addWidget(self.input_button)

        # Output Directory Selection
        self.output_label = QLabel("Output Directory:")
        self.output_button = QPushButton("Select Output")
        self.output_button.clicked.connect(self.selectOutputDirectory)
        layout.addWidget(self.output_label)
        layout.addWidget(self.output_button)

        # Blast Type Selection
        self.blast_label = QLabel("Blast Type:")
        self.blast_combo = QComboBox()
        self.blast_combo.addItem("blastp")
        self.blast_combo.addItem("blastn")
        self.blast_combo.addItem("blastx")
        self.blast_combo.addItem("tblastn")
        self.blast_combo.addItem("tblastx")
        self.blast_combo.currentIndexChanged.connect(self.updateDBType)
        layout.addWidget(self.blast_label)
        layout.addWidget(self.blast_combo)

        # Num of Hits
        self.hits_label = QLabel("Num of hits:")
        self.hits_lineedit = QLineEdit("10")
        layout.addWidget(self.hits_label)
        layout.addWidget(self.hits_lineedit)

        # E-value Selection
        self.evalue_label = QLabel("E-value:")
        self.evalue_combo = QComboBox()
        self.evalue_combo.addItem("0.001")
        self.evalue_combo.addItem("1e-5")
        self.evalue_combo.addItem("1e-10")
        self.evalue_combo.addItem("1e-20")
        layout.addWidget(self.evalue_label)
        layout.addWidget(self.evalue_combo)

        # Run Button
        self.run_button = QPushButton("RUN")
        self.run_button.clicked.connect(self.runBlast)
        layout.addWidget(self.run_button)

        self.setLayout(layout)
        self.show()

    def selectDatabaseFile(self):
        database_file, _ = QFileDialog.getOpenFileName(self, "Select Database", "", "FASTA Files (*.fasta *.fna *.fa *.faa)")
        self.db_label.setText("Database File: " + database_file)

    def selectInputFile(self):
        input_file, _ = QFileDialog.getOpenFileName(self, "Select Input", "", "FASTA Files (*.fasta *.pep)")
        self.input_label.setText("Input File: " + input_file)

    def selectOutputDirectory(self):
        output_directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        self.output_label.setText("Output Directory: " + output_directory)

    def updateDBType(self):
        blast_type = self.blast_combo.currentText()
        if blast_type in ["blastp", "blastx"]:
            self.dbtype = "prot"
        else:
            self.dbtype = "nucl"

    def runBlast(self):
        database_file = self.db_label.text().split(": ")[-1]
        input_file = self.input_label.text().split(": ")[-1]
        output_directory = self.output_label.text().split(": ")[-1]
        blast_type = self.blast_combo.currentText()
        num_hits = self.hits_lineedit.text()
        evalue = self.evalue_combo.currentText()

        if not database_file or not input_file or not output_directory:
            QMessageBox.warning(self, "File Selection", "Please select all the files and output directory.")
            return

        self.show_running_msg()  # Show running progress message box

        # Replace the placeholders in the commands with the selected values
        command = f"conda run -n blast_env makeblastdb -in {database_file} -dbtype {self.dbtype} -out {output_directory}\n"
        if blast_type == "blastp":
            command += f"conda run -n blast_env blastp -query {input_file} -db {output_directory} -out {output_directory}/blast.csv -outfmt \"6 qseqid sseqid pident length mismatch gapopen qstart qend sstart send evalue bitscore sseq\" -evalue {evalue} -max_target_seqs {num_hits} -num_threads 16"
        elif blast_type == "blastn":
            command += f"conda run -n blast_env blastn -query {input_file} -db {output_directory} -out {output_directory}/blast.csv -outfmt \"6 qseqid sseqid pident length mismatch gapopen qstart qend sstart send evalue bitscore sseq\" -evalue {evalue} -max_target_seqs {num_hits} -num_threads 16"
        elif blast_type == "blastx":
            command += f"conda run -n blast_env blastx -query {input_file} -db {output_directory} -out {output_directory}/blast.csv -outfmt \"6 qseqid sseqid pident length mismatch gapopen qstart qend sstart send evalue bitscore sseq\" -evalue {evalue} -max_target_seqs {num_hits} -num_threads 16"
        elif blast_type == "tblastn":
            command += f"conda run -n blast_env tblastn -query {input_file} -db {output_directory} -out {output_directory}/blast.csv -outfmt \"6 qseqid sseqid pident length mismatch gapopen qstart qend sstart send evalue bitscore sseq\" -evalue {evalue} -max_target_seqs {num_hits} -num_threads 16"
        elif blast_type == "tblastx":
            command += f"conda run -n blast_env tblastx -query {input_file} -db {output_directory} -out {output_directory}/blast.csv -outfmt \"6 qseqid sseqid pident length mismatch gapopen qstart qend sstart send evalue bitscore sseq\" -evalue {evalue} -max_target_seqs {num_hits} -num_threads 16"

        print("Executing the following command:")
        print(command)


        # Start the timer
        start_time = QTime.currentTime()

        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        # Calculate the elapsed time
        end_time = QTime.currentTime()
        elapsed_time = start_time.msecsTo(end_time)

        # Format the elapsed time as hh:mm:ss
        elapsed_time_str = QTime(0, 0).addMSecs(elapsed_time).toString("hh:mm:ss")

        # Close the running progress message box
        self.running_msg.close()

        # Show completion message box with elapsed time
        completion_msg = QMessageBox(self)
        completion_msg.setIcon(QMessageBox.Information)
        completion_msg.setText(f"Blast is completed. Elapsed time: {elapsed_time_str}")
        completion_msg.setWindowTitle("Blast Completed")
        completion_msg.setStandardButtons(QMessageBox.Ok)
        completion_msg.exec_()

        # Close the main window
        self.close()

    def show_running_msg(self):
        self.running_msg = QMessageBox(self)
        self.running_msg.setIcon(QMessageBox.Information)
        self.running_msg.setText("The process is running. Please wait until the process finishes.")
        self.running_msg.setWindowTitle("Running")
        self.running_msg.setStandardButtons(QMessageBox.Cancel)
        self.running_msg.show()

    def centerWindow(self):
        # Get the screen geometry
        screen = QDesktopWidget().screenGeometry()

        # Calculate the center point of the screen
        center_x = screen.width() // 2
        center_y = screen.height() // 2

        # Calculate the top-left point of the window
        window_x = center_x - (self.width() // 2)
        window_y = center_y - (self.height() // 2)

        # Move the window to the center of the screen
        self.move(window_x, window_y)


if __name__ == '__main__':
    app = QApplication([])
    blast_gui = BlastGUI()
    app.exec_()
