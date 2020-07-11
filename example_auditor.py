from tools.reader import Reader
from tools.auditor import Auditor

import os.path

# Get the files directory
FILE_DIR = os.path.dirname(os.path.realpath(__file__))
FILE_NAME = "Data_FPbase.json"
PATH = os.path.join(FILE_DIR, FILE_NAME)

# Read the file using the Reader class
reader = Reader(PATH)

# Audit the fluorophore data
audit = Auditor(reader[0])
print(audit)

# A new fluorophore can be audited using
# audit.audit(reader[1])
