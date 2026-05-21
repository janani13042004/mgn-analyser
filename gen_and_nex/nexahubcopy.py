import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QAction, QMenu, QLabel, QVBoxLayout, QWidget, QStackedWidget
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("Main Window")
        self.showMaximized()  # Set the window to full screen

        # Create menu bar
        menu_bar = self.menuBar()
        self.setMenuBar(menu_bar)  # Set the menu bar

        # Tools menu
        tools_menu = menu_bar.addMenu("Tools")
        self.setFontSize(tools_menu, 20)

        # SAM/BAM Conversion submenu
        self.addSubMenuAction(tools_menu, "SAM/BAM Conversion", "samtools.py")

        # GFF/GTF Conversion submenu
        self.addSubMenuAction(tools_menu, "GFF/GTF Conversion", "gffread.py")

        # Pre-Processing menu
        pre_processing_menu = menu_bar.addMenu("Pre-Processing")
        self.setFontSize(pre_processing_menu, 20)

        # FastQC submenu
        self.addSubMenuAction(pre_processing_menu, "FastQC", "fastqc.py")

        # FastP submenu
        self.addSubMenuAction(pre_processing_menu, "FastP", "fastp.py")

        # Trimming submenu
        self.addSubMenuAction(pre_processing_menu, "Trimmomatic", "trimmomatic.py")

        # Genomics Assembly menu
        genomics_assembly_menu = menu_bar.addMenu("Genomics Assembly")
        self.setFontSize(genomics_assembly_menu, 20)

        # Denovo Assembly submenu
        denovo_genomics = QMenu("Denovo Assembly", self)

        # Spades submenu
        self.addSubMenuAction(denovo_genomics, "Spades", "spades.py")

        # Velvet submenu
        self.addSubMenuAction(denovo_genomics, "Velvet", "velvet.py")

        # Hifiasm submenu
        self.addSubMenuAction(denovo_genomics, "Hifiasm", "hifiasm.py")
        
        # Abyss submenu
        self.addSubMenuAction(denovo_genomics, "Abyss", "abyss.py")

        genomics_assembly_menu.addMenu(denovo_genomics)

        # Genome Mapping menu
        gmapping_menu = genomics_assembly_menu.addMenu("Mapping")
        self.setFontSize(gmapping_menu, 20)

        # Bowtie2 submenu
        self.addSubMenuAction(gmapping_menu, "Bowtie2", "bowtie.py")

        # BWA submenu
        self.addSubMenuAction(gmapping_menu, "BWA", "bwa.py")

        # Analysis menu
        analysis_menu = menu_bar.addMenu("Analysis")
        self.setFontSize(analysis_menu, 20)

        # Blast submenu
        self.addSubMenuAction(analysis_menu, "Blast", "blast.py")

        # GO_mapping submenu
        self.addSubMenuAction(analysis_menu, "GO Mapping", "annotation_go.py")

        # interproscan submenu
        self.addSubMenuAction(analysis_menu, "Interproscan", "interproscan.py")

        # Genomics Pipeline menu
        genomics_pipeline_menu = menu_bar.addMenu("Genomics Pipeline")
        self.setFontSize(genomics_pipeline_menu, 20)

        # Denovo submenu
        self.addSubMenuAction(genomics_pipeline_menu, "Denovo Pipeline", "denovopipeline.py")

        # Reference submenu
        self.addSubMenuAction(genomics_pipeline_menu, "Reference Pipeline", "referencepipeline.py")

        # Create a QLabel for the message
        message_label = QLabel(self)
        message_label.setText("Developed by Anitha Ravichandran\nCorresponding author N Saranya\nCPMB & B, TNAU.")
        message_label.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        message_label.setFont(QFont("Arial", 16, QFont.Bold))  # Increase the font size and make it bold
        self.statusBar().addPermanentWidget(message_label, 1)

        # Create a central widget with QVBoxLayout
        central_widget = QWidget(self)
        layout = QVBoxLayout()
        layout.setContentsMargins(50, 50, 50, 50)  # Add margins to leave empty space
        central_widget.setLayout(layout)

        # Create a QLabel for the image
        image_label = QLabel(self)
        pixmap = QPixmap("flow.png")  # Replace with the actual image path
        image_label.setPixmap(pixmap.scaled(1000, 1000, Qt.AspectRatioMode.KeepAspectRatio, Qt.SmoothTransformation))
        image_label.setAlignment(Qt.AlignCenter)

        # Add the image label to the layout
        layout.addWidget(image_label)

        # Set the central widget
        self.setCentralWidget(central_widget)

        # Create a QStackedWidget for dynamic content
        self.stacked_widget = QStackedWidget(self)
        layout.addWidget(self.stacked_widget)

        # Apply custom stylesheet
        style = """
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
                font-size: 30px;  /* Increase the font size */
                font-family: GlasgowSerial;
                font-weight: bold;  /* Set the font weight to bold */
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
                font-size: 20px;  /* Increase the font size */
                font-weight: bold;  /* Set the font weight to bold */
            }
            
            QMenu::item:selected {
                background-color: #bbb;
                padding: 10px 20px;
                font-size: 10px;
                font-family: Arial;
            }
            
            QToolBar {
                background-color: #f3f3f3;
                border: none;
            }
        """
        self.setStyleSheet(style)

    def setFontSize(self, menu, font_size):
        font = QFont("Arial", font_size)
        menu.setFont(font)

    def addSubMenuAction(self, menu, action_text, script_name):
        action = QAction(action_text, self)
        action.triggered.connect(lambda: self.loadScript(script_name))
        menu.addAction(action)

    def loadScript(self, filename):
        import subprocess
        subprocess.Popen(['python3', filename])

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

