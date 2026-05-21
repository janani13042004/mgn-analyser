import os
import subprocess

class GenomicsPipeline:
    def __init__(self, sam_files, reference_genome, sam_dir, freebayes_dir):
        self.sam_files = sam_files
        self.reference_genome = reference_genome
        self.sam_dir = sam_dir
        self.freebayes_dir = freebayes_dir
        self.bam_files = []
        self.error_msg = None

    def update_progress(self, message):
        print(message)

    def finished(self, success):
        print(f"Pipeline finished with status: {'Success' if success else 'Failure'}")

    def run_pipeline(self):
        # Create output directory if it doesn't exist
        if not os.path.exists(self.sam_dir):
            os.makedirs(self.sam_dir)

        # Step 1: Convert SAM to BAM
        self.update_progress("Converting SAM to BAM.")
        for sam_file in self.sam_files:
            output_bam_file = os.path.join(self.sam_dir, os.path.basename(sam_file).replace('.sam', '.bam'))

            # Check if the input SAM file exists
            if not os.path.exists(sam_file):
                self.error_msg = f"File {sam_file} does not exist."
                print(self.error_msg)
                self.finished(False)
                return

            # SAMtools view command to convert SAM to BAM
            samtools_view_cmd = f"conda run -n samtools_env samtools view -Sb {sam_file} > {output_bam_file}"

            process = subprocess.Popen(samtools_view_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()

            # Print standard output and error for debugging
            print(f"SAMtools view stdout: {stdout.decode()}")
            print(f"SAMtools view stderr: {stderr.decode()}")

            if process.returncode != 0:
                self.error_msg = f"SAMtools view command failed for {sam_file}. Error: {stderr.decode()}"
                print(self.error_msg)
                self.finished(False)
                return

            self.bam_files.append(output_bam_file)

        self.update_progress("SAM to BAM conversion completed.")

        # Step 2: Running SAMtools rmdup on the BAM file
        self.update_progress("SAMtools rmdup is running.")
        for bam_file in self.bam_files:
            dedup_bam_file = bam_file.replace('.bam', '_dedup.bam')

            # SAMtools rmdup command
            samtools_rmdup_cmd = f"conda run -n samtools_env samtools rmdup {bam_file} {dedup_bam_file}"

            process = subprocess.Popen(samtools_rmdup_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()

            # Print standard output and error for debugging
            print(f"SAMtools rmdup stdout: {stdout.decode()}")
            print(f"SAMtools rmdup stderr: {stderr.decode()}")

            if process.returncode != 0:
                self.error_msg = f"SAMtools rmdup command failed for {bam_file}. Error: {stderr.decode()}"
                print(self.error_msg)
                self.finished(False)
                return

        self.update_progress("SAMtools rmdup is completed.")
        self.finished(True)


# Example usage with your actual values
sam_files = ["/home/altschul/Akhansha/Pictures/check/gendata/Output/bwa_assembly/SRR1575510.sam"]
reference_genome = "/home/altschul/Akhansha/Pictures/check/gendata/reference.fasta"
sam_dir = "/home/altschul/Akhansha/Pictures/check/gendata/new/sam_dir"
freebayes_dir = "/home/altschul/Akhansha/Pictures/check/gendata/new/freebayes_dir"

pipeline = GenomicsPipeline(sam_files, reference_genome, sam_dir, freebayes_dir)
pipeline.run_pipeline()
