from tools.postprocessor import PostProcessor
from tools import Format
import os

FILE_DIR = os.path.dirname(os.path.realpath(__file__))
PATH_SOURCE = os.path.join(FILE_DIR, "Source_data.json")

# Load the data into the quality control class for qc checking
post_processor = PostProcessor(PATH_SOURCE)

# Run the post processor
post_processor.process()

# (Optional) remove all disabled fluorophore entrees
post_processor.remove_disabled()

# Export the data
post_processor.export(FILE_DIR, "fluorophores", Format.json)
