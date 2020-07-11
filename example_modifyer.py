from tools.reader import Reader
from tools import modifyer
import os.path

# Get the files directory
FILE_DIR = os.path.dirname(os.path.realpath(__file__))
PATH = os.path.join(FILE_DIR, "Data_FPbase.json")

# Read the file using the Reader class
reader = Reader(PATH)

# Construct Modifyer
modify = modifyer.FPbase()

# Apply the modifications
data = modify.apply(reader[0])
