from tools.viewer.viewer import MainWindow, Application
from tools.viewer.reader import MappedReader
from tools import modifyer

import sys
import os

if __name__ == "__main__":
    FILE_DIR = os.path.dirname(os.path.realpath(__file__))

    # Prepare the header data
    reader = MappedReader(os.path.join(FILE_DIR, "Source_map.json"))

    # Load single (or multiple) sources
    reader.load_source_data(os.path.join(FILE_DIR, "Source_data.json"))

    # Purge unused header information
    reader.purge()
    
    # Start event manager
    app = Application([])

    # Instantiate the main window, and show it on screen
    main = MainWindow()
    main.show()

    # Load the header and spectra data into the viewer
    main.loadData(reader)

    # Decouple the application thread, and close the main thread
    sys.exit(app.exec_())
