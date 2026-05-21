import csv
import datetime
from collections import Counter
import matplotlib.pyplot as plt
import os
import shutil
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QDesktopWidget

blast_csv = ''
blast_split_csv = 'blast_split.csv'
other_csv_file = 'swiss_go_pathway.csv'
protein_id_column = 'protein id'
output_directory = ''

# Function to handle the "GO map" button click event
def go_map():
    # Step 1: Modify blast.csv and save it as blast_split.csv
    blast_data = []
    with open(blast_csv, 'r') as input_file:
        reader = csv.reader(input_file, delimiter='\t')
        blast_data = list(reader)

    header_row = ['qseqid', 'sp', 'protein id', 'species name', 'pident', 'length', 'mismatch', 'gapopen', 'qstart', 'qend', 'sstart', 'send', 'evalue', 'bitscore', 'sseq']
    blast_data[0] = header_row

    # Split the "sp" column into three columns
    for i in range(1, len(blast_data)):
        sp_value = blast_data[i][1]
        sp_values = sp_value.split('|')
        blast_data[i][1] = sp_values[0]  # sp
        blast_data[i].insert(2, sp_values[1])  # A2YW91
        blast_data[i].insert(3, sp_values[2])  # PLP2_ORYSI

    with open(blast_split_csv, 'w', newline='') as output_file:
        writer = csv.writer(output_file, delimiter='\t')
        writer.writerows(blast_data)

    fasta_output_path = f"{output_directory}/protein.fasta"
    with open(blast_split_csv, 'r') as input_file, open(fasta_output_path, 'w') as fasta_output:
        reader = csv.DictReader(input_file, delimiter='\t')
        for row in reader:
            protein_id = row['protein id']
            sequence = row['sseq']
            fasta_output.write(f">{protein_id}\n{sequence}\n")

    # Step 2: Compare and merge blast_split.csv with other_csv_file based on "protein id"
    blast_data_dict = {}
    other_data_dict = {}

    with open(blast_split_csv, 'r') as blast_file:
        reader = csv.DictReader(blast_file, delimiter='\t')
        for row in reader:
            protein_id = row[protein_id_column]
            blast_data_dict[protein_id] = row

    with open(other_csv_file, 'r') as other_file:
        reader = csv.DictReader(other_file)
        for row in reader:
            protein_id = row[protein_id_column]
            other_data_dict[protein_id] = row

    matched_protein_ids = set(blast_data_dict.keys()) & set(other_data_dict.keys())

    if matched_protein_ids:
        header = list(blast_data_dict[matched_protein_ids.pop()].keys()) + list(other_data_dict[matched_protein_ids.pop()].keys())

        # Add timestamp to the output file name
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        output_file_name = f"annotation_{timestamp}.csv"
        output_file_path = f"{output_directory}/{output_file_name}"

        with open(output_file_path, 'w', newline='') as output_file:
            writer = csv.DictWriter(output_file, fieldnames=header)
            writer.writeheader()
            for protein_id in matched_protein_ids:
                merged_data = {**blast_data_dict[protein_id], **other_data_dict[protein_id]}
                writer.writerow(merged_data)
        QMessageBox.information(window, 'Success', f'GO map generated successfully. Output file: {output_file_path}')

        # Generate separate CSV files for each column
        biological_process_file = f"{output_directory}/biological_process.csv"
        cellular_component_file = f"{output_directory}/cellular_component.csv"
        molecular_function_file = f"{output_directory}/molecular_function.csv"

        with open(output_file_path, 'r') as input_file, \
             open(biological_process_file, 'w', newline='') as bp_file, \
             open(cellular_component_file, 'w', newline='') as cc_file, \
             open(molecular_function_file, 'w', newline='') as mf_file:
            reader = csv.DictReader(input_file)
            bp_writer = csv.DictWriter(bp_file, fieldnames=['Gene Ontology (biological process)'])
            cc_writer = csv.DictWriter(cc_file, fieldnames=['Gene Ontology (cellular component)'])
            mf_writer = csv.DictWriter(mf_file, fieldnames=['Gene Ontology (molecular function)'])
            bp_writer.writeheader()
            cc_writer.writeheader()
            mf_writer.writeheader()
            for row in reader:
                bp_data = {'Gene Ontology (biological process)': row['Gene Ontology (biological process)']}
                cc_data = {'Gene Ontology (cellular component)': row['Gene Ontology (cellular component)']}
                mf_data = {'Gene Ontology (molecular function)': row['Gene Ontology (molecular function)']}
                bp_writer.writerow(bp_data)
                cc_writer.writerow(cc_data)
                mf_writer.writerow(mf_data)

        # Additional code provided
        def process_data(input_file, output_file):
            data = []

            # Read the input CSV file
            with open(input_file, 'r') as file:
                reader = csv.reader(file)
                header = next(reader)  # Get the header row
                for row in reader:
                    data.append(row)

            # Process the data
            processed_data = []
            for row in data:
                if len(row) > 0:
                    process_row = []
                    for item in row:
                        if '[' in item and ']' in item:
                            item = item[:item.index('[')].strip()  # Remove information within brackets
                        if item:
                            process_row.extend(item.split(';'))  # Split items by ';'
                    processed_data.append(process_row)

            # Count the occurrences of each sequence
            sequence_counts = Counter()
            for row in processed_data:
                sequence_counts.update(row)

            # Generate the output data with sequence counts
            output_data = []
            for sequence, count in sequence_counts.items():
                output_data.append([sequence, count])

            # Sort the output data by count in descending order
            sorted_output_data = sorted(output_data, key=lambda x: x[1], reverse=True)

            # Write the output data to a CSV file
            with open(output_file, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['Gene Ontology', 'Sequences'])
                writer.writerows(sorted_output_data)

            print(f"Processed data saved to {output_file}")

        # Call the process_data function for each output file
        process_data(biological_process_file, biological_process_file)
        process_data(cellular_component_file, cellular_component_file)
        process_data(molecular_function_file, molecular_function_file)

        # Create the "charts" folder if it doesn't exist
        charts_folder = f"{output_directory}/charts"
        os.makedirs(charts_folder, exist_ok=True)

        # Function to generate bar graph and pie chart
        def generate_charts(csv_file, chart_title):
            data = []
            with open(csv_file, 'r') as file:
                reader = csv.reader(file)
                header = next(reader)  # Get the header row
                for row in reader:
                    data.append(row)

            # Sort the data by count in descending order
            sorted_data = sorted(data, key=lambda x: int(x[1]), reverse=True)

            # Get the top 10 data entries
            top_10_data = sorted_data[:10]

            sequences = [item[0] for item in top_10_data]
            counts = [int(item[1]) for item in top_10_data]

            # Generate bar graph
            plt.figure(figsize=(10, 6))
            plt.bar(sequences, counts)
            plt.title(f"Top 10 {chart_title}")
            plt.xlabel("Gene Ontology")
            plt.ylabel("Count")
            plt.xticks(rotation=90)
            plt.tight_layout()
            plt.savefig(f"{charts_folder}/{chart_title.lower().replace(' ', '_')}_bar.png")
            plt.close()

            # Generate pie chart
            plt.figure(figsize=(10, 6))
            plt.pie(counts, labels=sequences, autopct='%1.1f%%')
            plt.title(f"Top 10 {chart_title}")
            plt.axis('equal')
            plt.tight_layout()
            plt.savefig(f"{charts_folder}/{chart_title.lower().replace(' ', '_')}_pie.png")
            plt.close()

        # Generate charts for each output file
        generate_charts(biological_process_file, "Biological Process")
        generate_charts(cellular_component_file, "Cellular Component")
        generate_charts(molecular_function_file, "Molecular Function")

        # Move the blast_split.csv file to the output directory
        output_blast_split_csv = os.path.join(output_directory, 'blast_split.csv')
        shutil.move(blast_split_csv, output_blast_split_csv)

        print(f"blast_split.csv moved to {output_blast_split_csv}")

        # Show completion message and close the window
        QMessageBox.information(window, 'Complete', 'GO mapping completed.')
        window.close()

    else:
        QMessageBox.warning(window, 'Error', 'No matching protein IDs found in the input files.')

def select_blast_csv():
    global blast_csv
    blast_csv, _ = QFileDialog.getOpenFileName(window, 'Select blast.csv')
    if blast_csv:
        window.label_blast_csv.setText(blast_csv)

# Function to handle the "Select output directory" button click event
def select_output_directory():
    global output_directory
    output_directory = QFileDialog.getExistingDirectory(window, 'Select output directory')
    if output_directory:
        window.label_output_directory.setText(output_directory)

def center(window):
    '''Center the window on the screen.'''
    screen = QDesktopWidget().screenGeometry()
    window.setGeometry(
        (screen.width() - window.width()) // 2,
        (screen.height() - window.height()) // 2,
        window.width(),
        window.height()
    )

app = QtWidgets.QApplication([])
window = QtWidgets.QWidget(windowTitle='GO Mapper')
window.setGeometry(200, 200, 500, 300) # Set the window position and size
window.setWindowIcon(QtGui.QIcon('icon.png')) # Set the window icon

layout = QtWidgets.QVBoxLayout()
window.setLayout(layout)

button_select_blast_csv = QtWidgets.QPushButton('Select blast.csv')
button_select_blast_csv.clicked.connect(select_blast_csv)
layout.addWidget(button_select_blast_csv)

label_blast_csv = QtWidgets.QLabel('No file selected')
window.label_blast_csv = label_blast_csv
layout.addWidget(label_blast_csv)

button_select_output_directory = QtWidgets.QPushButton('Select output directory')
button_select_output_directory.clicked.connect(select_output_directory)
layout.addWidget(button_select_output_directory)

label_output_directory = QtWidgets.QLabel('No directory selected')
window.label_output_directory = label_output_directory
layout.addWidget(label_output_directory)

button_go_map = QtWidgets.QPushButton('GO map')
button_go_map.clicked.connect(go_map)
layout.addWidget(button_go_map)

center(window)  # Center the window before showing it
window.show()
app.exec_()
