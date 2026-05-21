import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QFileDialog, 
                             QComboBox, QLabel, QWidget, QMessageBox)
import rpy2.robjects as robjects
import subprocess
import shutil

class App(QMainWindow):

    def __init__(self):
        super().__init__()

        # Set window properties
        self.setWindowTitle("DEG Analysis")
        self.setGeometry(100, 100, 800, 600)

        
        # Ensure R libraries are installed
        self.check_and_install_r_libraries()

        # Create main layout
        layout = QVBoxLayout()

        # Add widgets to layout
        self.input_btn = QPushButton("Select Input File (.txt)")
        self.input_btn.clicked.connect(self.load_input_file)

        self.design_btn = QPushButton("Upload Experimental Design File (.txt)")
        self.design_btn.clicked.connect(self.load_exp_design)

        self.input_file_label = QLabel("No file selected")
        self.design_file_label = QLabel("No design file selected")

        self.log2FC_dropdown = QComboBox()
        self.log2FC_dropdown.addItems(["0.5", "1", "2"])

        self.padj_dropdown = QComboBox()
        self.padj_dropdown.addItems(["0.05", "0.01", "0.001"])

        self.output_btn = QPushButton("Save Output")
        self.output_btn.clicked.connect(self.save_output)

        self.start_btn = QPushButton("Start Analysis")
        self.start_btn.clicked.connect(self.execute_r_script)

        layout.addWidget(QLabel("Upload and Analysis"))
        layout.addWidget(self.input_btn)
        layout.addWidget(self.input_file_label)
        layout.addWidget(self.design_btn)
        layout.addWidget(self.design_file_label)
        layout.addWidget(QLabel("Select log2FC_threshold:"))
        layout.addWidget(self.log2FC_dropdown)
        layout.addWidget(QLabel("Select padj_threshold:"))
        layout.addWidget(self.padj_dropdown)
        layout.addWidget(self.start_btn)
        layout.addWidget(self.output_btn)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        self.inputFileName = ""
        self.expDesignFileName = ""

    def load_input_file(self):
        self.inputFileName, _ = QFileDialog.getOpenFileName(self, "Select Input File", "", "Text Files (*.txt)")
        if self.inputFileName:
            self.input_file_label.setText(self.inputFileName)

    def load_exp_design(self):
        self.expDesignFileName, _ = QFileDialog.getOpenFileName(self, "Select Experimental Design File", "", "Text Files (*.txt)")
        if self.expDesignFileName:
            self.design_file_label.setText(self.expDesignFileName)

    # Define the function to check and install R libraries
    @staticmethod
    def check_and_install_r_libraries():
        libraries = ["DESeq2", "ggplot2", "pheatmap"]
        
        # Install BiocManager first
        subprocess.run(['conda', 'run', '-n', 'r_env', 'Rscript', '-e', 'if (!requireNamespace("BiocManager", quietly = TRUE)) install.packages("BiocManager")'])
        for lib in libraries:
            cmd = f'if (!require("{lib}", character.only = TRUE)) {{ BiocManager::install("{lib}") }}'
            subprocess.run(['conda', 'run', '-n', 'r_env', 'Rscript', '-e', cmd])


    def execute_r_script(self):
        if not self.inputFileName or not self.expDesignFileName:
            QMessageBox.warning(self, "Warning", "Please select both input and experimental design files.")
            return

        try:
            # Call the R script function
            self.run_r_analysis()
            QMessageBox.information(self, "Success", "Analysis complete!")
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def run_r_analysis(self):
        robjects.r('''
        library(DESeq2)
        library(ggplot2)
        library(pheatmap)
        ''')

        robjects.r.assign("input_file", self.inputFileName)
        robjects.r.assign("log2FC_threshold", float(self.log2FC_dropdown.currentText()))
        robjects.r.assign("padj_threshold", float(self.padj_dropdown.currentText()))

        # Run your R code using rpy2
        robjects.r('''
        
        # Read the count table into R (replace "proso.txt" with your actual input file name)
        countTable <- read.table(input_file, header = TRUE, row.names = 1)

        # Extract sample names from column names of count table
        sampleNames <- colnames(countTable)

        # Extract condition and replicate information from sample names
        conditions <- gsub("_.*", "", sampleNames)
        replicates <- gsub(".*_", "", sampleNames)

        # Create a metadata table with sample information
        sampleInfo <- data.frame(
          condition = conditions,
          replicate = replicates
        )

        # Convert the count table and sample metadata to DESeqDataSet object
        dds <- DESeqDataSetFromMatrix(countData = countTable, colData = sampleInfo, design = ~ condition)

        # Normalize the count data
        dds <- DESeq(dds)

        # Perform differential expression analysis
        res <- results(dds)

        # Filter differentially expressed genes based on thresholds
        downregulated_genes <- subset(res, log2FoldChange < -log2FC_threshold & padj < padj_threshold)
        upregulated_genes <- subset(res, log2FoldChange > log2FC_threshold & padj < padj_threshold)

        # Create a data frame to store the differentially expressed genes
        diff_expr_genes <- data.frame(
          GeneID = row.names(res),
          log2FoldChange = res$log2FoldChange,
          padj = res$padj,
          Regulation = ifelse(res$log2FoldChange < -log2FC_threshold, "Downregulated",
                              ifelse(res$log2FoldChange > log2FC_threshold, "Upregulated", "Not significant"))
        )

        # Exclude rows with "NA" and "Not significant" in the "Regulation" column
        diff_expr_genes <- diff_expr_genes[!is.na(diff_expr_genes$Regulation) & diff_expr_genes$Regulation != "Not significant", ]

        # Save differentially expressed genes as a CSV file
        write.csv(diff_expr_genes, file = "differentially_expressed_genes.csv", row.names = FALSE)

        # Subset the count table to include only the differentially expressed genes
        diff_expr_counts <- countTable[row.names(diff_expr_genes), ]

        # Generate a heatmap of the differentially expressed genes with black and red color scheme
        heatmapData <- diff_expr_counts
        pheatmap(heatmapData, cluster_rows = FALSE, cluster_cols = TRUE,
                 scale = "row", show_rownames = FALSE, show_colnames = FALSE,
                 color = colorRampPalette(c("black", "red"))(50),
                 main = "Heatmap of Differentially Expressed Genes")

        # Generate a heatmap of differentially expressed genes
        heatmapData <- assay(dds)[row.names(DEgenes), ]
        pheatmap(heatmapData, cluster_rows = FALSE, cluster_cols = FALSE, scale = "row",
                 color = colorRampPalette(c("black", "red"))(50),
                 show_rownames = FALSE, show_colnames = TRUE, fontsize = 8, main = "Differentially Expressed Genes Heatmap")

        # Generate a volcano plot of differentially expressed genes
        ggplot(res_df, aes(x = log2FoldChange, y = -log10(padj))) +
          geom_point(size = 1, color = ifelse(res_df$padj < alpha, "red", "black")) +
          geom_hline(yintercept = -log10(alpha), linetype = "dashed", color = "blue") +
          labs(x = "log2 Fold Change", y = "-log10(adjusted p-value)", title = "Volcano Plot")


        ''')

        # For plots, you might want to save them to files and then display them in the GUI:
        png("heatmap.png")
        # Generate the heatmap...
        dev.off()

        png("volcano.png")
        # Generate the volcano plot...
        dev.off()
       

    def save_output(self):
        output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if output_dir:
            heatmap_path = "heatmap.png"
            volcano_path = "volcano.png"
            diff_expr_genes_path = "differentially_expressed_genes.csv"
        
            shutil.copy(heatmap_path, output_dir)
            shutil.copy(volcano_path, output_dir)
            shutil.copy(diff_expr_genes_path, output_dir)
        
            QMessageBox.information(self, "Success", "Output files saved!")

    def display_plot(self, filepath):
        pass

app = QApplication(sys.argv)
window = App()
window.show()
sys.exit(app.exec_())