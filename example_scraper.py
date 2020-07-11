from tools import Source, Format

import os.path

# Each target is scraped using a specialised Scraper object
SOURCE = Source.fpbase

if SOURCE == Source.bd:
    from tools.scraper.bd import Scraper
    SAVE_FILE = "Data_BD"
elif SOURCE == Source.biolegend:
    from tools.scraper.biolegend import Scraper
    SAVE_FILE = "Data_BioLegend"
elif SOURCE == Source.biotium:
    from tools.scraper.biotium import Scraper
    SAVE_FILE = "Data_Biotium"
elif SOURCE == Source.chroma:
    from tools.scraper.chroma import Scraper
    SAVE_FILE = "Data_Chroma"
elif SOURCE == Source.fluorofinder:
    from tools.scraper.fluorofinder import Scraper
    SAVE_FILE = "Data_FluoroFinder"
elif SOURCE == Source.fpbase:
    from tools.scraper.fpbase import Scraper
    SAVE_FILE = "Data_FPbase"
elif SOURCE == Source.thermofisher:
    from tools.scraper.thermofisher import Scraper
    SAVE_FILE = "Data_ThermoFisher"

SAVE_DIR = os.path.dirname(os.path.realpath(__file__))

# Initialize the Scraper object
scraper = Scraper()

# In most cases the scraping target uses special identifiers to request fluorophores information
# In those cases, the identifiers (ids) need to be scraped first
try:
    scraper.scrape_ids()
except NotImplementedError:
    pass

# Scrape the main fluorophore information
scraper.scrape_fluorophores()

# Export the scraped data in the specified format to the specified location.
scraper.export(SAVE_DIR, SAVE_FILE, Format.json)
