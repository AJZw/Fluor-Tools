from tools.viewer.viewer import MainWindow, Application
from tools.viewer.reader import MappedReader
from tools import modifyer

import sys
import os

if __name__ == "__main__":
    FILE_DIR = os.path.dirname(os.path.realpath(__file__))

    # Prepare the header data
    reader = MappedReader(os.path.join(FILE_DIR, "Source_map.json"))

    # Add the spectra data
    reader.load_data(os.path.join(FILE_DIR, "Data_BD.json"))
    reader.load_data(os.path.join(FILE_DIR, "Data_BioLegend.json"))
    reader.load_data(os.path.join(FILE_DIR, "Data_Biotium.json"))
    reader.load_data(os.path.join(FILE_DIR, "Data_Chroma.json"))
    reader.load_data(os.path.join(FILE_DIR, "Data_FluoroFinder.json"))
    reader.load_data(os.path.join(FILE_DIR, "Data_FPbase.json"))
    reader.load_data(os.path.join(FILE_DIR, "Data_ThermoFisher.json"))

    # Apply default modification to the spectra data
    reader.load_modifyer(modifyer.BD())
    reader.load_modifyer(modifyer.BioLegend())
    reader.load_modifyer(modifyer.Biotium())
    reader.load_modifyer(modifyer.Chroma())
    reader.load_modifyer(modifyer.FluoroFinder())
    reader.load_modifyer(modifyer.FPbase())
    reader.load_modifyer(modifyer.ThermoFisher())

    # (Optional) Load previous annotated source data
    reader.load_source_data(os.path.join(FILE_DIR, "Data_Source.json"))
    
    # Start event manager
    app = Application([])

    # Instantiate the main window, set autosave, and show it on screen
    main = MainWindow()
    main.set_autosave_dir(FILE_DIR)
    main.show()

    # Load the header and spectra data into the viewer
    main.loadData(reader)

    # Decouple the application thread, and close the main thread
    sys.exit(app.exec_())
