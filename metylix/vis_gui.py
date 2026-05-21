import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton,
    QFileDialog, QLabel, QLineEdit, QRadioButton, QHBoxLayout, QMessageBox, QButtonGroup
)
from PyQt5.QtGui import QFont
import matplotlib.pyplot as plt
from collections import Counter

class VisualizationApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Functional Annotation Visualizer")
        self.setGeometry(300, 200, 600, 300)

        self.initUI()

    def initUI(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # File input
        file_layout = QHBoxLayout()
        self.file_input = QLineEdit()
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browseFile)
        file_layout.addWidget(QLabel("Annotation File:"))
        file_layout.addWidget(self.file_input)
        file_layout.addWidget(browse_btn)
        layout.addLayout(file_layout)

        # Radio buttons
        self.radio_group = QButtonGroup(self)
        self.cog_radio = QRadioButton("COG Distribution")
        self.kegg_radio = QRadioButton("KEGG Orthologs")
        self.pfam_radio = QRadioButton("Pfam Domains")
        self.radio_group.addButton(self.cog_radio)
        self.radio_group.addButton(self.kegg_radio)
        self.radio_group.addButton(self.pfam_radio)
        layout.addWidget(self.cog_radio)
        layout.addWidget(self.kegg_radio)
        layout.addWidget(self.pfam_radio)

        # Visualize button
        self.plot_btn = QPushButton("Visualize")
        self.plot_btn.clicked.connect(self.generatePlot)
        layout.addWidget(self.plot_btn)

        widget.setLayout(layout)
        self.setCentralWidget(widget)

    def browseFile(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Select annotation file", "", "Text files (*.txt *.tsv *.annotations)")
        if fname:
            self.file_input.setText(fname)

    def generatePlot(self):
        filepath = self.file_input.text().strip()
        if not os.path.isfile(filepath):
            QMessageBox.warning(self, "File Error", "File not found. Please select a valid file.")
            return

        if self.cog_radio.isChecked():
            self.plotCOG(filepath)
        elif self.kegg_radio.isChecked():
            self.plotKEGG(filepath)
        elif self.pfam_radio.isChecked():
            self.plotPfam(filepath)
        else:
            QMessageBox.warning(self, "Selection Error", "Please select a visualization type.")

    def plotCOG(self, filepath):
        cog_counts = Counter()
        with open(filepath) as f:
            for line in f:
                if line.startswith("#"):
                    continue
                cols = line.strip().split("\t")
                if len(cols) > 20:
                    cogs = cols[20]
                    for c in cogs:
                        if c.isalpha():
                            cog_counts[c] += 1

        if not cog_counts:
            QMessageBox.information(self, "No Data", "No valid COG entries found.")
            return

        plt.figure(figsize=(10, 5))
        plt.bar(cog_counts.keys(), cog_counts.values(), color='skyblue')
        plt.xlabel('COG Category')
        plt.ylabel('Number of Genes')
        plt.title('COG Functional Distribution')
        plt.tight_layout()
        plt.show()

    def plotKEGG(self, filepath):
        kegg_counts = Counter()
        with open(filepath) as f:
            for line in f:
                if line.startswith("#"):
                    continue
                cols = line.strip().split("\t")
                if len(cols) > 11:
                    pathways = cols[11].split(",")
                    for p in pathways:
                        if p.startswith("ko"):
                            kegg_counts[p] += 1

        if not kegg_counts:
            QMessageBox.information(self, "No Data", "No valid KEGG orthologs found.")
            return

        top_kegg = kegg_counts.most_common(10)
        labels, values = zip(*top_kegg)

        plt.figure(figsize=(10, 6))
        plt.bar(labels, values, color='teal')
        plt.xlabel("KEGG Ortholog (KO)")
        plt.ylabel("Count")
        plt.title("Top 10 KEGG Orthologs")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()

    def plotPfam(self, filepath):
        pfam_counts = Counter()
        with open(filepath) as f:
            for line in f:
                if line.startswith("#"):
                    continue
                cols = line.strip().split()
                if len(cols) > 5:
                    pfam_id = cols[5]
                    pfam_counts[pfam_id] += 1

        if not pfam_counts:
            QMessageBox.information(self, "No Data", "No valid Pfam entries found.")
            return

        top_pfam = pfam_counts.most_common(10)
        labels, values = zip(*top_pfam)

        plt.figure(figsize=(10, 6))
        plt.bar(labels, values, color='darkorange')
        plt.xlabel("Pfam ID")
        plt.ylabel("Count")
        plt.title("Top 10 Pfam Domains")
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = VisualizationApp()
    win.show()
    sys.exit(app.exec_())

