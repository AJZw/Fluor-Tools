from tools import Source, Format
from tools.reader import Reader
from tools.comparer import Comparer
import os.path

# Each target is scraped using a specialised Scraper object
SOURCE = Source.thermofisher

if SOURCE == Source.bd:
    from tools.scraper.bd import Scraper
    DATA_FILE = "Data_BD.json"
elif SOURCE == Source.biolegend:
    from tools.scraper.biolegend import Scraper
    DATA_FILE = "Data_BioLegend.json"
elif SOURCE == Source.biotium:
    from tools.scraper.biotium import Scraper
    DATA_FILE = "Data_Biotium.json"
elif SOURCE == Source.chroma:
    from tools.scraper.chroma import Scraper
    DATA_FILE = "Data_Chroma.json"
elif SOURCE == Source.fluorofinder:
    from tools.scraper.fluorofinder import Scraper
    DATA_FILE = "Data_FluoroFinder.json"
elif SOURCE == Source.fpbase:
    from tools.scraper.fpbase import Scraper
    DATA_FILE = "Data_FPbase.json"
elif SOURCE == Source.thermofisher:
    from tools.scraper.thermofisher import Scraper
    DATA_FILE = "Data_ThermoFisher.json"

DATA_DIR = os.path.dirname(os.path.realpath(__file__))
READER_OLD = Reader(os.path.join(DATA_DIR, DATA_FILE))

# Initialize the Scraper object
SCRAPER_NEW = Scraper()

# In most cases the scraping target uses special identifiers to request fluorophores information
# In those cases the identifiers (ids) need to be scraped first
try:
    SCRAPER_NEW.scrape_ids()
except NotImplementedError:
    pass

# Scrape the main fluorophore information
SCRAPER_NEW.scrape_fluorophores()

COMPARISON = Comparer(READER_OLD, SCRAPER_NEW)

# To show the comparison results use
repr(COMPARISON)

# SCRAPER_NEW.export(DATA_DIR, DATA_FILE, Format.json)