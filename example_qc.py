from tools.qc import QC
import os

FILE_DIR = os.path.dirname(os.path.realpath(__file__))

# Load the data into the quality control class for qc checking
qc = QC(os.path.join(FILE_DIR, "Source_data.json"))

# Print the qc results
print(qc)
