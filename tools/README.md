# Fluor Scraper Tools

The Fluor Tools is a set of Python classes for the scraping, parsing, comparing, and annotating of fluorophore spectra.  
Additionally, a GUI interface is provided for detailed annotation of the data.  

The toolset is subdivided in three modules:  
● tools - all general class definitions  
● tools.scraper - definitions for the scraping of fluorophore spectra  
● tools.viewer - definitions for the annotation graphical user interface

## Authors

AJ Zwijnenburg

## Requirements

Python >= 3.8.1  

tools.scraper:  
● requests >= 2.22.0  
● lxml >= 4.5.0  
● cryptography >= 2.8  

tools.viewer:  
● PyQt5 >= 5.14.1  
● matplotlib >= 3.1.3  
● scipy >= 1.4.1  

## Installation

Copy the tools folder with all its components to your working directory.  
Make sure the dependencies can be imported.

## Usage

```python
from tools import Format
from tools.scraper.fpbase import Scraper
import os.path

FILE_DIR = os.path.dirname(os.path.realpath(__file__))

# Instantiate and run scraper
scraper = Scraper()
scraper.scrape_ids()
scraper.scrape_fluorophores()

# Export the data
scraper.export(save_dir, "FPbase", ExportFormat.json)
```

```python
from tools.mapper import Map
from tools.reader import Reader
import os.path

FILE_DIR = os.path.dirname(os.path.realpath(__file__))

# Load the Spectra data identification map
map = Map(os.path.join(FILE_DIR, "Source_map.json"))

# Append the scraped data to the map
reader = Reader(os.path.join(FILE_DIR, "Data_FPbase.json"))
map.append(reader)

# Manage dangling and unresolved identifiers
map.manage_dangled()
map.manage_unresolved(reader)

# Export the identification map
map.export(os.path.join(FILE_DIR, "Source_map.json"))
```

```python
from tools.viewer.viewer import MainWindow, Application
from tools.viewer.reader import MappedReader
from tools import modifyer
import sys, os

if __name__ == "__main__":
    FILE_DIR = os.path.dirname(os.path.realpath(__file__))

    # Prepare the header data
    reader = MappedReader(os.path.join(FILE_DIR, "Source_map.json"))

    # Add the spectra data
    reader.load_data(os.path.join(FILE_DIR, "Data_FPbase.json"))

    # (Optional) Load previous annotated source data
    reader.load_source_data(os.path.join(FILE_DIR, "Source_data.json"))

    # Start the viewer graphical user interface
    app = Application([])
    main = MainWindow()
    main.show()

    # Load the header and spectra data into the viewer
    main.loadData(reader)

    sys.exit(app.exec_())
```

```python
from tools.qc import QC
import os

FILE_DIR = os.path.dirname(os.path.realpath(__file__))

# Load the data into the quality control class for qc checking
qc = QC(os.path.join(FILE_DIR, "Source_data.json"))

# Print the qc results
print(qc)
```

```python
from tools.postprocessor import PostProcessor
from tools import Format
import os

FILE_DIR = os.path.dirname(os.path.realpath(__file__))

# Load the data into the quality control class for qc checking
post_processor = PostProcessor(os.path.join(FILE_DIR, "Source_data.json"))

# Run the post processor
post_processor.process()

# Export the data
post_processor.export(FILE_DIR, "fluorophores")
```

## Contributing

Bug reports, idea's, and push request are very welcome!

## Version List

v1.0 - Selenium library based scrapers  
v2.0 - Updated scrapers to only use the requests library

## License

tools: [MIT](https://choosealicense.com/licenses/mit/)  
tools.scraper: [MIT](https://choosealicense.com/licenses/mit/)  
tools.viewer: [GPLv3](https://choosealicense.com/licenses/gpl-3.0/)  
