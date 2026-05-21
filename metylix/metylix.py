import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QAction, QMenu, QLabel, QVBoxLayout, QWidget, QStackedWidget, QHBoxLayout
)
from PyQt5.QtGui import QPixmap, QFont, QIcon
from PyQt5.QtCore import Qt


class MetagenomicsGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("METYLIX")
        self.setWindowIcon(QIcon("logo_b.png"))  # Set application icon here
        self.showMaximized()

        menu_bar = self.menuBar()
        font = QFont("Arial Black", 15)
        font.setPointSize(15)
        menu_bar.setFont(font)

        # Pre-Processing menu
        preprocessing_menu = menu_bar.addMenu("Pre-Processing")
        preprocessing_menu.setFont(QFont("Arial", 20))
        preprocessing_menu.addAction(self.createAction("FastQC", "fastqc.py"))
        preprocessing_menu.addAction(self.createAction("FastP", "fastp.py"))
        preprocessing_menu.addAction(self.createAction("Trimmomatic", "trimmomatic.py"))
        preprocessing_menu.addAction(self.createAction("Trimgalore", "trimgalore.py"))

        # Metagenomics Assembly menu
        assembly_menu = menu_bar.addMenu("Metagenomics Assembly")
        assembly_menu.setFont(QFont("Arial", 20))
        assembly_menu.addAction(self.createAction("MEGAHIT", "megahit.py"))
        assembly_menu.addAction(self.createAction("MetaSPAdes", "metaspades.py"))
        assembly_menu.addAction(self.createAction("Assembly Summary Statistics", "assembly_stat.py"))
        assembly_menu.addAction(self.createAction("QUAST", "quast.py"))

        # Analysis menu
        analysis_menu = menu_bar.addMenu("Analysis")
        analysis_menu.setFont(QFont("Arial", 20))
        analysis_menu.addAction(self.createAction("Gene Prediction", "geneprediction.py"))
        analysis_menu.addAction(self.createAction("Taxonomic Classification", "kraken2.py"))
        analysis_menu.addAction(self.createAction("Annotation", "annotation.py"))
        analysis_menu.addAction(self.createAction("Visualization", "krona_n.py"))

        # Pipeline menu
        pipeline_menu = menu_bar.addMenu("Pipeline")
        pipeline_menu.setFont(QFont("Arial", 20))
        pipeline_menu.addAction(self.createAction("16S rRNA", "16s_rRNA.py"))
        pipeline_menu.addAction(self.createAction("Shotgun Metagenomics", "wms.py"))

        # Central widget
        central_widget = QWidget(self)
        layout = QVBoxLayout()
        layout.setContentsMargins(50, 50, 50, 50)
        central_widget.setLayout(layout)

        # Display flowchart image
        image_label = QLabel(self)
        pixmap = QPixmap("flowchart.png")
        if pixmap.isNull():
            image_label.setText("Image not found: flowchart.png")
        else:
            image_label.setPixmap(pixmap.scaled(1000, 1000, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(image_label)

        # Footer area
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(20, 20, 20, 20)

        # Icon above footer text
        icon_label = QLabel(self)
        icon_pixmap = QPixmap("bgd.png")
        if icon_pixmap.isNull():
            icon_label.setText("Icon not found")
        else:
            icon_label.setPixmap(icon_pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        footer_layout.addWidget(icon_label, alignment=Qt.AlignLeft | Qt.AlignBottom)

        # Footer developer credits
        message_label = QLabel(self)
        message_label.setText("Developed by Nivetha V\nCorresponding author N Saranya\nCPMB & B, TNAU.")
        message_label.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        message_label.setFont(QFont("Times New Roman", 16, QFont.Bold))
        footer_layout.addWidget(message_label)

        layout.addLayout(footer_layout)

        self.setCentralWidget(central_widget)
        self.stacked_widget = QStackedWidget(self)
        layout.addWidget(self.stacked_widget)

        # Styles
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f3f3f3;
            }
            QMenuBar {
                background-color: #003152;
                color: white;
            }
            QMenuBar::item {
                background-color: #003152;
                padding: 10px 10px;
                font-size: 30px;
                font-family: GlasgowSerial;
                font-weight: bold;
            }
            QMenuBar::item:selected {
                background-color: #555;
            }
            QMenu {
                background-color: #f3f3f3;
                color: #333;
            }
            QMenu::item {
                padding: 10px 20px;
                font-size: 20px;
                font-weight: bold;
            }
            QMenu::item:selected {
                background-color: #bbb;
                font-family: Arial;
            }
        """)

    def createAction(self, name, script):
        action = QAction(name, self)
        action.triggered.connect(lambda: self.loadScript(script))
        return action

    def loadScript(self, filename):
        import subprocess
        subprocess.Popen(['python3', filename])


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MetagenomicsGUI()
    window.show()
    sys.exit(app.exec_())

