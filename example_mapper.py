from tools.mapper import Map
from tools.reader import Reader

import os.path

FILE_DIR = os.path.dirname(os.path.realpath(__file__))
PATH_MAP = os.path.join(FILE_DIR, "Source_map.json")
PATH_READER = os.path.join(FILE_DIR, "Data_FPbase.json")

# Load header map and fluorophore data
map = Map(PATH_MAP)

reader = Reader(PATH_READER)

# Append the new data to the map. Make sure the reader object only contains data from a single Source
map.append(reader)

# Manage all non-automatically resolved identifiers
# First manage all dangling identifiers
map.manage_dangled()

# Secondly manage all unresolved identifiers
# Passing the 'reader' allows for the display of the identifiers fluorophore names
map.manage_unresolved(reader)

# Save results
map.export(PATH_MAP)
