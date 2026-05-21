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
        font = QFont("Arial Black", 15)
        font.setPointSize(15)
        menu_bar.setFont(font)

        # Transcriptomics Assembly menu
        transcriptomics_assembly_menu = menu_bar.addMenu("Transcriptomics Assembly")
        transcriptomics_assembly_menu.setFont(QFont("Arial", 20))  # Set the font size using QFont
        
        # Denovo submenu
        denovo_submenu = QMenu("Denovo", self)
        
        # Trinity submenu
        trinity = QAction("Trinity", self)
        trinity.triggered.connect(lambda: self.loadScript("trinity.py"))
        denovo_submenu.addAction(trinity)
        
        # RNA SPAdes submenu
        rna_spades = QAction("RNA SPAdes", self)
        rna_spades.triggered.connect(lambda: self.loadScript("rnaspades.py"))
        denovo_submenu.addAction(rna_spades)
        
        # Assembly Quality Assessment submenu
        assembly_quality_assessment = QAction("Assembly Quality Assessment", self)
        assembly_quality_assessment.triggered.connect(lambda: self.loadScript("busco.py"))
        denovo_submenu.addAction(assembly_quality_assessment)
        
        # ORF Prediction submenu
        orf_prediction = QAction("ORF Prediction", self)
        orf_prediction.triggered.connect(lambda: self.loadScript("transdecoder.py"))
        denovo_submenu.addAction(orf_prediction)
        
        # Count Table submenu
        count_table = QAction("Count Table", self)
        count_table.triggered.connect(lambda: self.loadScript("rsem.py"))
        denovo_submenu.addAction(count_table)
        
        transcriptomics_assembly_menu.addMenu(denovo_submenu)
        
        # Mapping menu
        mapping_menu = transcriptomics_assembly_menu.addMenu("Mapping")
        
        # Bowtie2 submenu
        bowtie2 = QAction("Bowtie2", self)
        bowtie2.triggered.connect(lambda: self.loadScript("bowtie.py"))
        mapping_menu.addAction(bowtie2)
        
        # STAR submenu
        star = QAction("STAR", self)
        star.triggered.connect(lambda: self.loadScript("star.py"))
        mapping_menu.addAction(star)
        
        # HiSat2 submenu
        hisat2 = QAction("HiSat2", self)
        hisat2.triggered.connect(lambda: self.loadScript("hisat.py"))
        mapping_menu.addAction(hisat2)
        
        # Count Table submenu
        count_table_mapping = QAction("Count Table", self)
        count_table_mapping.triggered.connect(lambda: self.loadScript("counts.py"))
        mapping_menu.addAction(count_table_mapping)

        # Genomics Assembly menu
        genomics_assembly_menu = menu_bar.addMenu("Genomics Assembly")
        genomics_assembly_menu.setFont(QFont("Arial", 20))  # Set the font size using QFont
        
        # Denovo submenu
        denovo_genomics = QMenu("Denovo", self)
        
        # Example actions for Genomics Denovo submenu
        action1_genomics = QAction("Action 1", self)
        action2_genomics = QAction("Action 2", self)
        action3_genomics = QAction("Action 3", self)
        
        denovo_genomics.addAction(action1_genomics)
        denovo_genomics.addAction(action2_genomics)
        denovo_genomics.addAction(action3_genomics)
        
        genomics_assembly_menu.addMenu(denovo_genomics)

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

        # Set the central widget
        self.setCentralWidget(central_widget)

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

    def loadScript(self, filename):
        import subprocess
        subprocess.Popen(['python3', filename])
        
    def executeCommand(self, command):
        import subprocess
        subprocess.Popen(command.split())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

