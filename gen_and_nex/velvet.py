import tkinter as tk
from tkinter import filedialog
import subprocess

def run_velvet():
    k_value = k_entry.get()
    input_folder = input_folder_entry.get()
    output_folder = output_folder_entry.get()

    command = f'velveth {output_folder} {k_value} -fastq {input_folder}'
    subprocess.run(command, shell=True)

    result_label.config(text="Velvet assembly complete.")

def browse_input_folder():
    input_folder = filedialog.askdirectory()
    input_folder_entry.delete(0, tk.END)
    input_folder_entry.insert(0, input_folder)

def browse_output_folder():
    output_folder = filedialog.askdirectory()
    output_folder_entry.delete(0, tk.END)
    output_folder_entry.insert(0, output_folder)

# Create the main window
root = tk.Tk()
root.title("Velvet Assembler")

# Create input frame
input_frame = tk.Frame(root)
input_frame.pack(pady=10)

k_label = tk.Label(input_frame, text="K Value:")
k_label.grid(row=0, column=0)

k_entry = tk.Entry(input_frame)
k_entry.grid(row=0, column=1)

input_folder_label = tk.Label(input_frame, text="Input Folder:")
input_folder_label.grid(row=1, column=0)

input_folder_entry = tk.Entry(input_frame, width=40)
input_folder_entry.grid(row=1, column=1)

browse_input_button = tk.Button(input_frame, text="Browse", command=browse_input_folder)
browse_input_button.grid(row=1, column=2)

# Create output frame
output_frame = tk.Frame(root)
output_frame.pack(pady=10)

output_folder_label = tk.Label(output_frame, text="Output Folder:")
output_folder_label.grid(row=0, column=0)

output_folder_entry = tk.Entry(output_frame, width=40)
output_folder_entry.grid(row=0, column=1)

browse_output_button = tk.Button(output_frame, text="Browse", command=browse_output_folder)
browse_output_button.grid(row=0, column=2)

# Run button
run_button = tk.Button(root, text="Run Velvet", command=run_velvet)
run_button.pack(pady=10)

# Result label
result_label = tk.Label(root, text="")
result_label.pack()

# Run the main loop
root.mainloop()

