# Variant Calling with Freebayes
freebayes_output = f"{self.output_folder}/freebayes_output.vcf"
self.update_progress.emit("Freebayes variant calling is running.")

# Ensure all paths are properly quoted in case they contain spaces
bam_files_quoted = [f'"{bam}"' for bam in bam_files]
reference_genome_quoted = f'"{self.reference_genome}"'
freebayes_output_quoted = f'"{freebayes_output}"'

# Construct the Freebayes command
freebayes_cmd = f"freebayes -f {reference_genome_quoted} {' '.join(bam_files_quoted)} > {freebayes_output_quoted}"

# Log the command being run for debugging purposes
print(f"Running command: {freebayes_cmd}")

process = subprocess.Popen(freebayes_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
stdout, stderr = process.communicate()

# Log the stdout and stderr for debugging purposes
print(f"Freebayes stdout: {stdout.decode()}")
print(f"Freebayes stderr: {stderr.decode()}")

if process.returncode != 0:
    self.error_msg = f"Freebayes command failed. Error: {stderr.decode()}"
    self.finished.emit(False)
    return

self.update_progress.emit("Freebayes variant calling completed.")

