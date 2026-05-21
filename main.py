import os
import sys
import subprocess

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel,
    QVBoxLayout, QHBoxLayout, QWidget, QStackedWidget,
    QPushButton, QFrame, QMenu, QAction, QScrollArea,
    QSizePolicy
)
from PyQt5.QtGui import (
    QPixmap, QFont, QIcon, QPainter, QColor, QPen, QBrush, QPolygon
)
from PyQt5.QtCore import Qt, QPoint


# ══════════════════════════════════════════════════════════════════
#  Vertical arrow
# ══════════════════════════════════════════════════════════════════
class Arrow(QWidget):
    def __init__(self, color="#4a8ab0", w=16, h=36, parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self.setFixedSize(w, h)
        self.setStyleSheet("background: transparent;")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(self._color, 2))
        p.setBrush(QBrush(self._color))
        cx, h = self.width() // 2, self.height()
        p.drawLine(cx, 0, cx, h - 9)
        p.drawPolygon(QPolygon([
            QPoint(cx - 6, h - 9),
            QPoint(cx + 6, h - 9),
            QPoint(cx, h),
        ]))


# ══════════════════════════════════════════════════════════════════
#  Branching connector widget — draws L-shaped lines from a single
#  source point down to N evenly-spaced destination columns.
# ══════════════════════════════════════════════════════════════════
class BranchConnector(QWidget):
    """
    Paints a horizontal bus + vertical drop lines for split arrows.
    colors: list of QColor (one per branch), must match dest_xs count.
    dest_xs: x-centres of each destination column (in parent coords,
             but this widget is laid out so its own x=0 aligns with
             the leftmost column centre).
    """
    def __init__(self, src_x, dest_xs, colors, height=48, parent=None):
        super().__init__(parent)
        self._src_x  = src_x
        self._dest_xs = dest_xs
        self._colors  = [QColor(c) for c in colors]
        self.setFixedHeight(height)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet("background: transparent;")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()

        # Map dest_xs (absolute) into widget-local coords by offsetting
        # by the widget's left edge within the scroll content.
        # Since we use addLayout(stretch) on both sides the widget fills
        # the full scroll width, so widget coords == content coords.
        src_x = self._src_x
        bus_y = self.height() // 3      # horizontal bus sits at 1/3 height
        drop_y = self.height() - 9      # arrow tip Y

        # Draw horizontal bus from leftmost to rightmost dest
        xs = self._dest_xs
        pen = QPen(QColor("#4a8ab0"), 2)
        p.setPen(pen)
        p.drawLine(xs[0], bus_y, xs[-1], bus_y)

        # Vertical stem from source to bus
        p.drawLine(src_x, 0, src_x, bus_y)

        # Drop lines + arrowheads for each branch
        for i, (dx, col) in enumerate(zip(xs, self._colors)):
            p.setPen(QPen(col, 2))
            p.setBrush(QBrush(col))
            p.drawLine(dx, bus_y, dx, drop_y)
            # arrowhead triangle
            p.drawPolygon(QPolygon([
                QPoint(dx - 6, drop_y),
                QPoint(dx + 6, drop_y),
                QPoint(dx, self.height()),
            ]))


# ══════════════════════════════════════════════════════════════════
#  Merge connector widget — draws vertical rise lines from N columns
#  merging onto a horizontal bus then a single stem to the dest.
# ══════════════════════════════════════════════════════════════════
class MergeConnector(QWidget):
    def __init__(self, src_xs, dst_x, colors, height=48, parent=None):
        super().__init__(parent)
        self._src_xs = src_xs
        self._dst_x  = dst_x
        self._colors  = [QColor(c) for c in colors]
        self.setFixedHeight(height)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet("background: transparent;")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        bus_y  = self.height() * 2 // 3   # bus sits at 2/3 height
        drop_y = self.height() - 9

        # Rise lines from each column up to bus
        for sx, col in zip(self._src_xs, self._colors):
            p.setPen(QPen(col, 2))
            p.drawLine(sx, 0, sx, bus_y)

        # Horizontal bus (neutral colour)
        p.setPen(QPen(QColor("#4a8ab0"), 2))
        p.drawLine(self._src_xs[0], bus_y, self._src_xs[-1], bus_y)

        # Vertical stem from bus to arrow tip
        p.drawLine(self._dst_x, bus_y, self._dst_x, drop_y)
        p.setBrush(QBrush(QColor("#4a8ab0")))
        p.drawPolygon(QPolygon([
            QPoint(self._dst_x - 6, drop_y),
            QPoint(self._dst_x + 6, drop_y),
            QPoint(self._dst_x, self.height()),
        ]))


# ══════════════════════════════════════════════════════════════════
#  Simple workflow box  (no chips — just title + subtitle)
# ══════════════════════════════════════════════════════════════════
class FlowBox(QFrame):
    def __init__(self, title, subtitle="",
                 bg="#1a3a5c", border="#2a6090",
                 title_color="#ffffff", sub_color="#aabbcc",
                 width=340, height=70, parent=None):
        super().__init__(parent)
        self.setFixedSize(width, height)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: 2px solid {border};
                border-radius: 14px;
            }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 8, 16, 8)
        lay.setSpacing(3)

        t = QLabel(title)
        t.setFont(QFont("Arial", 12, QFont.Bold))
        t.setStyleSheet(f"color: {title_color}; background: transparent; border: none;")
        t.setAlignment(Qt.AlignCenter)
        lay.addWidget(t)

        if subtitle:
            s = QLabel(subtitle)
            s.setFont(QFont("Arial", 9))
            s.setStyleSheet(f"color: {sub_color}; background: transparent; border: none;")
            s.setAlignment(Qt.AlignCenter)
            lay.addWidget(s)


# ══════════════════════════════════════════════════════════════════
#  Column box  (the three pipeline columns)
# ══════════════════════════════════════════════════════════════════
class ColBox(QFrame):
    def __init__(self, title, tools_line, assem_line,
                 bg, border, title_color, badge_color,
                 width=240, height=150, parent=None):
        super().__init__(parent)
        self.setFixedSize(width, height)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: 2px solid {border};
                border-radius: 12px;
            }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)

        t = QLabel(title)
        t.setFont(QFont("Arial", 11, QFont.Bold))
        t.setStyleSheet(f"color: {title_color}; background: transparent; border: none;")
        t.setAlignment(Qt.AlignCenter)
        lay.addWidget(t)

        # tools row
        tr = QLabel(tools_line)
        tr.setFont(QFont("Arial", 8, QFont.Bold))
        tr.setStyleSheet(f"color: {badge_color}; background: transparent; border: none;")
        tr.setAlignment(Qt.AlignCenter)
        tr.setWordWrap(True)
        lay.addWidget(tr)

        # bottom label
        bl = QLabel(assem_line)
        bl.setFont(QFont("Arial", 8))
        bl.setStyleSheet("color: #888; background: transparent; border: none;")
        bl.setAlignment(Qt.AlignCenter)
        lay.addWidget(bl)


# ══════════════════════════════════════════════════════════════════
#  NavButton
# ══════════════════════════════════════════════════════════════════
class NavButton(QPushButton):
    _N = """
        QPushButton {
            background-color: transparent;
            color: #cce8f4;
            font-family: 'Arial Black';
            font-size: 14px;
            font-weight: bold;
            border: none;
            padding: 0 20px;
            min-height: 46px;
        }
        QPushButton:hover { background-color: #005580; color: #ffffff; }
    """
    _A = """
        QPushButton {
            background-color: #1a6ea8;
            color: #ffffff;
            font-family: 'Arial Black';
            font-size: 14px;
            font-weight: bold;
            border: none;
            padding: 0 20px;
            min-height: 46px;
        }
        QPushButton:hover { background-color: #005580; }
    """

    def __init__(self, label, parent=None):
        super().__init__(label, parent)
        self._menu = None
        self.setStyleSheet(self._N)
        self.setMinimumHeight(46)

    def setNavMenu(self, m):
        self._menu = m

    def setActive(self, v):
        self.setStyleSheet(self._A if v else self._N)

    def mousePressEvent(self, e):
        if self._menu and e.button() == Qt.LeftButton:
            self._menu.exec_(self.mapToGlobal(QPoint(0, self.height())))
        else:
            super().mousePressEvent(e)


# ══════════════════════════════════════════════════════════════════
#  Main Window
# ══════════════════════════════════════════════════════════════════
class MGNAnalyser(QMainWindow):
    def __init__(self):
        super().__init__()
        self._nav = []
        self.initUI()

    def initUI(self):
        self.setWindowTitle("MGN Analyser")
        self.setWindowIcon(QIcon(self.absPath("logo_b.png")))
        self.showMaximized()
        self.menuBar().setVisible(False)

        central = QWidget(self)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── HEADER ────────────────────────────────────────────────
        header = QWidget()
        header.setFixedHeight(100)
        header.setStyleSheet("background-color: #002845;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(20, 8, 20, 8)
        hl.setSpacing(16)

        logo = QLabel()
        px = QPixmap(self.absPath("logo_b.png"))
        if not px.isNull():
            logo.setPixmap(px.scaled(76, 76, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        hl.addWidget(logo, alignment=Qt.AlignVCenter)

        tc = QVBoxLayout()
        tc.setSpacing(2)
        t1 = QLabel("MGN Analyser")
        t1.setFont(QFont("Arial Black", 26, QFont.Bold))
        t1.setStyleSheet("color: #ffffff; background: transparent;")
        tc.addWidget(t1)
        t2 = QLabel("Integrated Bioinformatics Platform  •  CPMB & B., TNAU")
        t2.setFont(QFont("Arial", 11))
        t2.setStyleSheet("color: #7ab8d9; background: transparent;")
        tc.addWidget(t2)
        hl.addLayout(tc)
        hl.addStretch()
        root.addWidget(header)

        # ── TASKBAR ───────────────────────────────────────────────
        taskbar = QWidget()
        taskbar.setFixedHeight(46)
        taskbar.setStyleSheet("background-color: #003152;")
        tb = QHBoxLayout(taskbar)
        tb.setContentsMargins(0, 0, 0, 0)
        tb.setSpacing(0)

        # Home
        b_home = NavButton("Home")
        b_home.clicked.connect(lambda: self.showPage(0))
        b_home.setActive(True)
        self._nav.append(b_home)
        tb.addWidget(b_home)

        # Tools
        m_tools = self._menu()
        self._act(m_tools, "SAM/BAM Conversion", "gen_and_nex/samtools.py")
        self._act(m_tools, "GFF/GTF Conversion",  "gen_and_nex/gffread.py")
        tb.addWidget(self._nbtn("Tools", m_tools))

        # Pre-Processing
        m_pre = self._menu()
        self._act(m_pre, "FastQC",      "gen_and_nex/fastqc.py")
        self._act(m_pre, "FastP",       "gen_and_nex/fastp.py")
        self._act(m_pre, "Trimmomatic", "gen_and_nex/trimmomatic.py")
        self._act(m_pre, "Trimgalore",  "metylix/trimgalore.py")
        tb.addWidget(self._nbtn("Pre-Processing", m_pre))

        # Assembly
        m_asm = self._menu()
        tr = m_asm.addMenu("Transcriptomics")
        dn_t = tr.addMenu("Denovo")
        self._act(dn_t, "Trinity",                    "gen_and_nex/trinity.py")
        self._act(dn_t, "RNA SPAdes",                 "gen_and_nex/rnaspades.py")
        self._act(dn_t, "Assembly Quality Assessment","gen_and_nex/busco.py")
        self._act(dn_t, "ORF Prediction",             "gen_and_nex/transdecoder.py")
        self._act(dn_t, "Count Table",                "gen_and_nex/rsem.py")
        mp_t = tr.addMenu("Mapping")
        self._act(mp_t, "Bowtie2",     "gen_and_nex/bowtie.py")
        self._act(mp_t, "STAR",        "gen_and_nex/star.py")
        self._act(mp_t, "HiSat2",      "gen_and_nex/hisat.py")
        self._act(mp_t, "Count Table", "gen_and_nex/counts.py")
        gn = m_asm.addMenu("Genomics")
        dn_g = gn.addMenu("Denovo Assembly")
        self._act(dn_g, "Spades",  "gen_and_nex/spades.py")
        self._act(dn_g, "Velvet",  "gen_and_nex/velvet.py")
        self._act(dn_g, "Hifiasm", "gen_and_nex/hifiasm.py")
        self._act(dn_g, "Abyss",   "gen_and_nex/abyss.py")
        mp_g = gn.addMenu("Mapping")
        self._act(mp_g, "Bowtie2", "gen_and_nex/bowtie.py")
        self._act(mp_g, "BWA",     "gen_and_nex/bwa.py")
        mt = m_asm.addMenu("Metagenomics")
        self._act(mt, "MEGAHIT",                    "metylix/megahit.py")
        self._act(mt, "MetaSPAdes",                 "metylix/metaspades.py")
        self._act(mt, "Assembly Summary Statistics","metylix/assembly_stat.py")
        self._act(mt, "QUAST",                      "metylix/quast.py")
        tb.addWidget(self._nbtn("Assembly", m_asm))

        # Analysis
        m_an = self._menu()
        self._act(m_an, "Blast",                 "gen_and_nex/blast.py")
        self._act(m_an, "GO Mapping",            "gen_and_nex/annotation_go.py")
        self._act(m_an, "Interproscan",          "gen_and_nex/interproscan.py")
        self._act(m_an, "Gene Prediction",       "metylix/geneprediction.py")
        self._act(m_an, "Taxonomic Classification","metylix/kraken2.py")
        self._act(m_an, "Annotation",            "metylix/annotation.py")
        self._act(m_an, "Visualization",         "metylix/krona_n.py")
        tb.addWidget(self._nbtn("Analysis", m_an))

        # Pipeline
        m_pipe = self._menu()
        gp = m_pipe.addMenu("Genomics Pipeline")
        self._act(gp, "Denovo Pipeline",    "gen_and_nex/denovopipeline.py")
        self._act(gp, "Reference Pipeline", "gen_and_nex/genomics.py")
        tp = m_pipe.addMenu("Transcriptomics Pipeline")
        self._act(tp, "Denovo Pipeline",    "gen_and_nex/denovo.py")
        self._act(tp, "Reference Pipeline", "gen_and_nex/reference.py")
        mtp = m_pipe.addMenu("Metagenomic Pipeline")
        self._act(mtp, "16S rRNA",             "metylix/16s_rRNA.py")
        self._act(mtp, "Shotgun Metagenomics", "metylix/wms.py")
        tb.addWidget(self._nbtn("Pipeline", m_pipe))

        tb.addStretch(1)
        root.addWidget(taskbar)

        # ── CONTENT ───────────────────────────────────────────────
        self.stacked = QStackedWidget()
        self.stacked.setStyleSheet("background-color: #f0f4f8;")
        self.stacked.addWidget(self._buildWorkflow())
        self.stacked.setCurrentIndex(0)
        root.addWidget(self.stacked, 1)

        # ── FOOTER ────────────────────────────────────────────────
        footer = QWidget()
        footer.setFixedHeight(46)
        footer.setStyleSheet("background-color: #f0f4f8; border-top: 1px solid #ccd6e0;")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(14, 0, 14, 0)
        icon_l = QLabel()
        ipx = QPixmap(self.absPath("bgd.png"))
        if not ipx.isNull():
            icon_l.setPixmap(ipx.scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        fl.addWidget(icon_l, alignment=Qt.AlignVCenter)
        fl.addStretch()
        f_txt = QLabel(
            "Developed by Anitha Ravichandran, Akhansha and Nivetha V  |  "
            "Corresponding author: N Saranya  |  CPMB & B, TNAU."
        )
        f_txt.setFont(QFont("Times New Roman", 11, QFont.Bold))
        f_txt.setStyleSheet("color: #003152; background: transparent;")
        f_txt.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        fl.addWidget(f_txt)
        root.addWidget(footer)

        # ── GLOBAL STYLE ──────────────────────────────────────────
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #f0f4f8; }
            QLabel { background: transparent; }
            QMenu {
                background-color: #ffffff;
                color: #1a1a2e;
                border: 1px solid #b0c8d8;
                border-radius: 6px;
                padding: 4px 0;
            }
            QMenu::item {
                padding: 9px 26px;
                font-size: 13px;
                font-family: Arial;
                font-weight: bold;
            }
            QMenu::item:selected { background-color: #d6eaf8; color: #003152; }
            QMenu::separator { height: 1px; background: #ccc; margin: 4px 10px; }
            QScrollArea { border: none; }
            QScrollBar:vertical {
                background: #dce8f0; width: 8px; border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #7aafc8; border-radius: 4px; min-height: 24px;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical { height: 0; }
        """)

    # ══════════════════════════════════════════════════════════════
    #  WORKFLOW PAGE  — corrected continuous top-to-bottom flow
    # ══════════════════════════════════════════════════════════════
    def _buildWorkflow(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("background: #f0f4f8;")

        page = QWidget()
        page.setStyleSheet("background-color: #f0f4f8;")
        scroll.setWidget(page)

        main = QVBoxLayout(page)
        main.setContentsMargins(40, 24, 40, 24)
        main.setSpacing(0)

        # Section heading
        lbl = QLabel("INTERACTIVE WORKFLOW OVERVIEW")
        lbl.setFont(QFont("Arial", 9, QFont.Bold))
        lbl.setStyleSheet("color: #5a7a8a; letter-spacing: 2px; background: transparent;")
        main.addWidget(lbl)
        main.addSpacing(14)

        # ── Column parameters ──────────────────────────────────────
        COL_W    = 250     # width of each branch column box
        COL_H    = 130     # height of each branch column box
        COL_GAP  = 30      # gap between column boxes
        BOX_W    = 340     # width of top/bottom full-width boxes

        # Three column colours
        C_TRANS = "#00a085"   # Transcriptomics – teal
        C_GENOM = "#2a7ab0"   # Genomics – blue
        C_META  = "#8e44ad"   # Metagenomics – purple

        # ── helpers ───────────────────────────────────────────────
        def centered_row(*widgets, gap=0):
            r = QHBoxLayout()
            r.addStretch()
            for i, w in enumerate(widgets):
                r.addWidget(w)
                if i < len(widgets) - 1 and gap:
                    r.addSpacing(gap)
            r.addStretch()
            return r

        def straight_arrow(color="#4a8ab0"):
            r = QHBoxLayout()
            r.addStretch()
            r.addWidget(Arrow(color))
            r.addStretch()
            return r

        # ── Compute column centre positions ────────────────────────
        # Total width of 3 columns + 2 gaps
        cols_total = 3 * COL_W + 2 * COL_GAP
        # The content area width is (page width - 2*40 margins).
        # We rely on Qt stretch to centre; we only need relative offsets.
        # Left col centre offset from group left edge:
        left_cx  = COL_W // 2                        # 125
        mid_cx   = COL_W + COL_GAP + COL_W // 2      # 405
        right_cx = 2 * (COL_W + COL_GAP) + COL_W // 2  # 685

        # Full diagram centre (mid column centre) relative to group left = mid_cx
        # Source arrow is at diagram centre → mid_cx within group.
        # We embed everything inside a fixed-width container so pixel maths work.
        total_w = cols_total   # 810

        # ── Raw Reads ──────────────────────────────────────────────
        main.addLayout(centered_row(FlowBox(
            "Raw Reads (FASTQ)",
            "Input: paired-end / single-end reads",
            bg="#1b3d5e", border="#2a6090",
            title_color="#ffffff", sub_color="#90b8d4",
            width=BOX_W, height=70
        )))

        # Straight arrow down
        main.addLayout(straight_arrow("#4a8ab0"))

        # ── Pre-Processing ─────────────────────────────────────────
        main.addLayout(centered_row(FlowBox(
            "Pre-Processing",
            "Quality Control & Trimming",
            bg="#1b3d5e", border="#2a6090",
            title_color="#ffffff", sub_color="#90b8d4",
            width=BOX_W, height=70
        )))

        # ── Branch connector (Pre-Processing → 3 columns) ──────────
        # We use a fixed container so pixel offsets are predictable.
        branch_container = QWidget()
        branch_container.setFixedWidth(total_w)
        branch_container.setFixedHeight(52)
        branch_container.setStyleSheet("background: transparent;")

        branch_conn = BranchConnector(
            src_x=mid_cx,
            dest_xs=[left_cx, mid_cx, right_cx],
            colors=[C_TRANS, C_GENOM, C_META],
            height=52,
            parent=branch_container
        )
        branch_conn.setGeometry(0, 0, total_w, 52)

        bc_row = QHBoxLayout()
        bc_row.addStretch()
        bc_row.addWidget(branch_container)
        bc_row.addStretch()
        main.addLayout(bc_row)

        # ── Three columns ──────────────────────────────────────────
        col_row = QHBoxLayout()
        col_row.setSpacing(COL_GAP)
        col_row.addStretch()

        for (title, tools, asm, bg, border, tc, bc_col) in [
            (
                "Transcriptomics",
                "Trinity · STAR · HiSat2 · Bowtie2",
                "ASSEMBLY & MAPPING",
                "#edfff8", "#00c4a7", "#006b55", C_TRANS
            ),
            (
                "Genomics",
                "SPAdes · BWA · Bowtie2 · Hifiasm",
                "ASSEMBLY & MAPPING",
                "#eef6ff", "#4a8ab0", "#1a4a7a", C_GENOM
            ),
            (
                "Metagenomics",
                "MEGAHIT · MetaSPAdes · Kraken2",
                "ASSEMBLY & CLASSIFICATION",
                "#f8f0ff", "#9b59b6", "#5a0f8a", C_META
            ),
        ]:
            col_row.addWidget(ColBox(title, tools, asm,
                                     bg, border, tc, bc_col,
                                     width=COL_W, height=COL_H))

        col_row.addStretch()
        main.addLayout(col_row)

        # ── Merge connector (3 columns → Analysis & Annotation) ────
        merge_container = QWidget()
        merge_container.setFixedWidth(total_w)
        merge_container.setFixedHeight(52)
        merge_container.setStyleSheet("background: transparent;")

        merge_conn = MergeConnector(
            src_xs=[left_cx, mid_cx, right_cx],
            dst_x=mid_cx,
            colors=[C_TRANS, C_GENOM, C_META],
            height=52,
            parent=merge_container
        )
        merge_conn.setGeometry(0, 0, total_w, 52)

        mc_row = QHBoxLayout()
        mc_row.addStretch()
        mc_row.addWidget(merge_container)
        mc_row.addStretch()
        main.addLayout(mc_row)

        # ── Analysis & Annotation ──────────────────────────────────
        main.addLayout(centered_row(FlowBox(
            "Analysis & Annotation",
            "BLAST · GO Mapping · InterProScan · Kraken2",
            bg="#1b3d5e", border="#2a6090",
            title_color="#ffffff", sub_color="#90b8d4",
            width=400, height=70
        )))

        # Straight arrow down
        main.addLayout(straight_arrow("#4a8ab0"))

        # ── Results & Visualization ────────────────────────────────
        main.addLayout(centered_row(FlowBox(
            "Results & Visualization",
            "Reports · Plots · Annotated Outputs",
            bg="#002845", border="#1a6090",
            title_color="#7ec8e3", sub_color="#4a8aaa",
            width=360, height=70
        )))

        main.addStretch()
        return scroll

    # ══════════════════════════════════════════════════════════════
    #  HELPERS
    # ══════════════════════════════════════════════════════════════
    def showPage(self, idx):
        self.stacked.setCurrentIndex(idx)
        for i, b in enumerate(self._nav):
            b.setActive(i == idx)

    def _menu(self):
        m = QMenu(self)
        m.setFont(QFont("Arial", 11))
        return m

    def _act(self, menu, name, script):
        a = QAction(name, self)
        a.triggered.connect(lambda checked, s=script: self.runScript(s))
        menu.addAction(a)

    def _nbtn(self, label, menu):
        b = NavButton(label)
        b.setNavMenu(menu)
        self._nav.append(b)
        return b

    def absPath(self, f):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), f)

    def runScript(self, script):
        try:
            subprocess.Popen(["python3", self.absPath(script)])
        except Exception as e:
            print(f"[ERROR] {script}: {e}")


# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MGNAnalyser()
    window.show()
    sys.exit(app.exec_())
