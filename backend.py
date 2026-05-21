import os
import sys
import subprocess

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QAction, QMenu, QLabel,
    QVBoxLayout, QHBoxLayout, QWidget, QStackedWidget
)
from PyQt5.QtGui import QPixmap, QFont, QIcon
from PyQt5.QtCore import Qt


class MGNAnalyser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("MGN Analyser")
        self.setWindowIcon(QIcon(self.absPath("logo_b.png")))
        self.showMaximized()

        menu_bar = self.menuBar()
        menu_bar.setFont(QFont("Arial Black", 13))

        # ======================================================
        #                  GENARC PIPELINE MENU
        # ======================================================
        genarc_menu = menu_bar.addMenu("GenArc Pipeline")

        home_genarc = QAction("GenArc Home", self)
        home_genarc.triggered.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        genarc_menu.addAction(home_genarc)
        genarc_menu.addSeparator()

        # Tools
        tools_menu = genarc_menu.addMenu("Tools")
        self.addAction_(tools_menu, "SAM/BAM Conversion", "gen_and_nex/samtools.py")
        self.addAction_(tools_menu, "GFF/GTF Conversion",  "gen_and_nex/gffread.py")

        # Pre-Processing
        genarc_pre = genarc_menu.addMenu("Pre-Processing")
        self.addAction_(genarc_pre, "FastQC",      "gen_and_nex/fastqc.py")
        self.addAction_(genarc_pre, "FastP",       "gen_and_nex/fastp.py")
        self.addAction_(genarc_pre, "Trimmomatic", "gen_and_nex/trimmomatic.py")

        # Transcriptomics Assembly
        trans_menu = genarc_menu.addMenu("Transcriptomics Assembly")
        denovo_trans = trans_menu.addMenu("Denovo")
        self.addAction_(denovo_trans, "Trinity",                    "gen_and_nex/trinity.py")
        self.addAction_(denovo_trans, "RNA SPAdes",                 "gen_and_nex/rnaspades.py")
        self.addAction_(denovo_trans, "Assembly Quality Assessment", "gen_and_nex/busco.py")
        self.addAction_(denovo_trans, "ORF Prediction",             "gen_and_nex/transdecoder.py")
        self.addAction_(denovo_trans, "Count Table",                "gen_and_nex/rsem.py")
        mapping_trans = trans_menu.addMenu("Mapping")
        self.addAction_(mapping_trans, "Bowtie2",     "gen_and_nex/bowtie.py")
        self.addAction_(mapping_trans, "STAR",        "gen_and_nex/star.py")
        self.addAction_(mapping_trans, "HiSat2",      "gen_and_nex/hisat.py")
        self.addAction_(mapping_trans, "Count Table", "gen_and_nex/counts.py")

        # Genomics Assembly
        genomics_menu = genarc_menu.addMenu("Genomics Assembly")
        denovo_genomics = genomics_menu.addMenu("Denovo Assembly")
        self.addAction_(denovo_genomics, "Spades",  "gen_and_nex/spades.py")
        self.addAction_(denovo_genomics, "Velvet",  "gen_and_nex/velvet.py")
        self.addAction_(denovo_genomics, "Hifiasm", "gen_and_nex/hifiasm.py")
        self.addAction_(denovo_genomics, "Abyss",   "gen_and_nex/abyss.py")
        mapping_genomics = genomics_menu.addMenu("Mapping")
        self.addAction_(mapping_genomics, "Bowtie2", "gen_and_nex/bowtie.py")
        self.addAction_(mapping_genomics, "BWA",     "gen_and_nex/bwa.py")

        # Analysis
        genarc_analysis = genarc_menu.addMenu("Analysis")
        self.addAction_(genarc_analysis, "Blast",        "gen_and_nex/blast.py")
        self.addAction_(genarc_analysis, "GO Mapping",   "gen_and_nex/annotation_go.py")
        self.addAction_(genarc_analysis, "Interproscan", "gen_and_nex/interproscan.py")

        # Transcriptomics Pipeline
        trans_pipe = genarc_menu.addMenu("Transcriptomics Pipeline")
        self.addAction_(trans_pipe, "Denovo Pipeline",    "gen_and_nex/denovo.py")
        self.addAction_(trans_pipe, "Reference Pipeline", "gen_and_nex/reference.py")

        # Genomics Pipeline
        genomics_pipe = genarc_menu.addMenu("Genomics Pipeline")
        self.addAction_(genomics_pipe, "Denovo Pipeline",    "gen_and_nex/denovopipeline.py")
        self.addAction_(genomics_pipe, "Reference Pipeline", "gen_and_nex/genomics.py")

        # ======================================================
        #                  METYLIX PIPELINE MENU
        # ======================================================
        metylix_menu = menu_bar.addMenu("Metylix Pipeline")

        home_metylix = QAction("Metylix Home", self)
        home_metylix.triggered.connect(lambda: self.stacked_widget.setCurrentIndex(2))
        metylix_menu.addAction(home_metylix)
        metylix_menu.addSeparator()

        # Pre-Processing
        metylix_pre = metylix_menu.addMenu("Pre-Processing")
        self.addAction_(metylix_pre, "FastQC",      "metylix/fastqc.py")
        self.addAction_(metylix_pre, "FastP",       "metylix/fastp.py")
        self.addAction_(metylix_pre, "Trimmomatic", "metylix/trimmomatic.py")
        self.addAction_(metylix_pre, "Trimgalore",  "metylix/trimgalore.py")

        # Metagenomics Assembly
        assembly_menu = metylix_menu.addMenu("Metagenomics Assembly")
        self.addAction_(assembly_menu, "MEGAHIT",                    "metylix/megahit.py")
        self.addAction_(assembly_menu, "MetaSPAdes",                 "metylix/metaspades.py")
        self.addAction_(assembly_menu, "Assembly Summary Statistics", "metylix/assembly_stat.py")
        self.addAction_(assembly_menu, "QUAST",                      "metylix/quast.py")

        # Analysis
        metylix_analysis = metylix_menu.addMenu("Analysis")
        self.addAction_(metylix_analysis, "Gene Prediction",          "metylix/geneprediction.py")
        self.addAction_(metylix_analysis, "Taxonomic Classification",  "metylix/kraken2.py")
        self.addAction_(metylix_analysis, "Annotation",               "metylix/annotation.py")
        self.addAction_(metylix_analysis, "Visualization",            "metylix/krona_n.py")

        # Pipeline
        metylix_pipe = metylix_menu.addMenu("Pipeline")
        self.addAction_(metylix_pipe, "16S rRNA",             "metylix/16s_rRNA.py")
        self.addAction_(metylix_pipe, "Shotgun Metagenomics", "metylix/wms.py")

        # ======================================================
        #              CENTRAL WIDGET + STACKED WIDGET
        # ======================================================
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(40, 20, 40, 10)
        central_widget.setLayout(main_layout)

        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)

        # Page 0: MGN Home
        self.stacked_widget.addWidget(self.buildHomePage(
            title="Welcome to MGN Analyser",
            subtitle="Select a pipeline from the menu above",
            image_file="flowchart.png",
            title_color="#003152"
        ))

        # Page 1: GenArc Home
        self.stacked_widget.addWidget(self.buildHomePage(
            title="GenArc Pipeline",
            subtitle="Genomics and Transcriptomics Analysis",
            image_file="gen_and_nex/flow.png",
            title_color="#1a5276"
        ))

        # Page 2: Metylix Home
        self.stacked_widget.addWidget(self.buildHomePage(
            title="Metylix Pipeline",
            subtitle="Metagenomics Analysis",
            image_file="metylix/flowchart.png",
            title_color="#4a235a"
        ))

        self.stacked_widget.setCurrentIndex(0)

        # ======================================================
        #                       FOOTER
        # ======================================================
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(10, 5, 10, 5)

        icon_label = QLabel()
        icon_pixmap = QPixmap(self.absPath("bgd.png"))
        if not icon_pixmap.isNull():
            icon_label.setPixmap(
                icon_pixmap.scaled(70, 70, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        footer_layout.addWidget(icon_label, alignment=Qt.AlignLeft | Qt.AlignBottom)

        footer_layout.addStretch()

        message_label = QLabel(
            "Developed by Anitha Ravichandran, Akhansha and Nivetha V  |  "
            "Corresponding author: N Saranya  |  CPMB & B, TNAU."
        )
        message_label.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        message_label.setFont(QFont("Times New Roman", 12, QFont.Bold))
        message_label.setStyleSheet("color: #003152;")
        footer_layout.addWidget(message_label)

        main_layout.addLayout(footer_layout)

        # ======================================================
        #                    STYLESHEET
        # ======================================================
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f4f8;
            }
            QWidget {
                background-color: #f0f4f8;
            }
            QMenuBar {
                background-color: #003152;
                color: white;
                spacing: 4px;
            }
            QMenuBar::item {
                background-color: #003152;
                padding: 10px 18px;
                font-size: 26px;
                font-family: Arial Black;
                font-weight: bold;
                border-radius: 4px;
            }
            QMenuBar::item:selected {
                background-color: #005580;
            }
            QMenuBar::item:pressed {
                background-color: #004466;
            }
            QMenu {
                background-color: #ffffff;
                color: #222;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            QMenu::item {
                padding: 10px 28px;
                font-size: 17px;
                font-weight: bold;
                font-family: Arial;
            }
            QMenu::item:selected {
                background-color: #d6eaf8;
                color: #003152;
            }
            QMenu::separator {
                height: 1px;
                background: #ccc;
                margin: 4px 10px;
            }
            QLabel {
                background-color: transparent;
            }
        """)

    # ======================================================
    #              BUILD REUSABLE HOME PAGE
    # ======================================================
    def buildHomePage(self, title, subtitle, image_file, title_color="#003152"):
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        page.setLayout(layout)

        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial Black", 22, QFont.Bold))
        title_label.setStyleSheet(f"color: {title_color}; padding: 6px;")

        sub_label = QLabel(subtitle)
        sub_label.setAlignment(Qt.AlignCenter)
        sub_label.setFont(QFont("Arial", 13))
        sub_label.setStyleSheet("color: #555; padding-bottom: 8px;")

        image_label = QLabel()
        pixmap = QPixmap(self.absPath(image_file))
        if pixmap.isNull():
            image_label.setText(f"Image not found: {image_file}")
            image_label.setAlignment(Qt.AlignCenter)
            image_label.setStyleSheet("color: red; font-size: 14px;")
            print(f"[DEBUG] Image not found: {self.absPath(image_file)}")
        else:
            image_label.setPixmap(
                pixmap.scaled(1050, 680, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        image_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(title_label)
        layout.addWidget(sub_label)
        layout.addStretch()
        layout.addWidget(image_label)
        layout.addStretch()

        return page

    # ======================================================
    #                      HELPERS
    # ======================================================
    def absPath(self, filename):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, filename)

    def addAction_(self, menu, name, script):
        action = QAction(name, self)
        action.triggered.connect(lambda: self.runScript(script))
        menu.addAction(action)
        return action

    def runScript(self, script):
        script_path = self.absPath(script)
        try:
            subprocess.Popen(["python3", script_path])
        except Exception as e:
            print(f"[ERROR] Could not run {script_path}: {e}")


# ======================================================
#                        MAIN
# ======================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MGNAnalyser()
    window.show()
    sys.exit(app.exec_())
