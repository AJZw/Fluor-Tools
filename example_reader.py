from tools.reader import Reader
import os.path

# Get the files directory
FILE_DIR = os.path.dirname(os.path.realpath(__file__))
PATH = os.path.join(FILE_DIR, "Data_FPbase.json")

# Read the file using the Reader class
reader = Reader(PATH)
