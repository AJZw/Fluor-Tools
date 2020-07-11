from tools.reader import Reader
from tools.comparer import Comparer

import os.path

FILE_DIR = os.path.dirname(os.path.realpath(__file__))

# Use the Reader class to retreive the fluorophore data files from the hdd 
reader_a = Reader(os.path.join(FILE_DIR, "Data_FPbase.json"))
reader_b = Reader(os.path.join(FILE_DIR, "Data_FPbase.json"))

# Compare the two reader classes
comparison = Comparer(reader_a, reader_b)

# To show the comparison results use
print(comparison)

# For a quick comparison overview use
repr(comparison)

# For a full overview you can uses
print(comparison.serialize(ignore_identical=False))
