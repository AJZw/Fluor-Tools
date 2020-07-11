# -*- coding: utf-8 -*-

## Fluor Tools Scraper #######################################################
# Author:     AJ Zwijnenburg
# Version:    v2.0
# Date:       2020-02-15
# Copyright:  Copyright (C) 2020 - AJ Zwijnenburg
# License:    MIT
##############################################################################

## Copyright notice ##########################################################
# Copyright 2020 AJ Zwijnenburg
#
# Permission is hereby granted, free of charge, to any person obtaining a copy 
# of this software and associated documentation files (the "Software"), to deal 
# in the Software without restriction, including without limitation the rights 
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell 
# copies of the Software, and to permit persons to whom the Software is 
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in  
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE # WARRANTIES OF MERCHANTABILITY, 
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE 
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, 
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN 
# THE SOFTWARE.
##############################################################################

"""
The Fluor scraper of FluoroFinder Spectra Viewer

FluoroFinder retreives a html file which contains a <option> list of fluorophore
names and their respective id's. This list is used to request the spectra 
information from the server. The FluoroFinder spectra information only contains
the excitation and emission intensities as the wavelenghts are standardized to
a range from 300-1000 (stepsize 1). When comparing the brightness_bin data it
can be quite different from other sources. So I dont think that information is
very trustworthy.

:class ID:
FluoroFinder identifier class

:class IDCollection:
FluoroFinder identifier collection class, parses the identifier response

:class: Data:
FluoroFinder data container, parses the spectrum responses

:class: Scraper:
FluoroFinder general scraper class, contains all relevant/scraped information
"""

from __future__ import annotations
from typing import Union, List, Tuple, Dict, Any

import requests
from lxml import etree
from io import StringIO

from .. import Format, Source
from . import abstract, ParseError, ScrapeError

import os.path
import time
import datetime

class ID(abstract.AbstractID):
    def __init__(self, source: Source, identifier: str, name: str):
        super().__init__(source, identifier)
        self.name: str = name

    def _export_ini(self) -> str:
        output = super()._export_ini()
        output += "name=" + self.name + "\n"

        return output

    def _export_json(self) -> dict():
        output = super()._export_json()
        #output["name"] = self.name

        return output

class IDCollection(abstract.AbstractCollection):
    """
    Collection of bd ids
    """
    def __init__(self) -> None:
        super().__init__()

    def parse(self, response: requests.Response) -> None:
        """
        Parse the response and extract the different fluorophore ids
            :param response: the get response
            :raises HTTPError: any error from requests
            :raises ValueError: if response contains invalid json
            :raises ParseError: if json contains invalid/missing data
        """
        try:
            response.raise_for_status()
        except:
            print("parsing error")
            raise

        page = etree.parse(StringIO(response.content.decode("utf-8")), parser=etree.HTMLParser())

        data_options = page.xpath('//select[@id="spectra_color_id"]/option')
        
        for data_option in data_options[1:]:
            fluorophore_id = data_option.get("value")
            fluorophore_name = data_option.text
            self.collection[fluorophore_id] = ID(Source.fluorofinder, fluorophore_id, fluorophore_name)

class Data(abstract.AbstractData):
    def __init__(self, identifier: abstract.AbstractID) -> None:
        """
        Initiates the Data object based on the identifier. Also loads the category data
        """
        super().__init__(identifier)
        self.source = "FluoroFinder"

        self.excitation_wavelength = [float(x) for x in list(range(300, 1000, 1))]
        self.emission_wavelength = [float(x) for x in list(range(300, 1000, 1))]

    def parse(self, response: requests.Response) -> None:
        """
        Parse the fluorophore data
            :param response: the response containing the data
            :raises HTTPError: upon any html error during response request
            :raises ValueError: if response contains invalid json
            :raises ParseError: if json contains invalid/missing data
        """
        try:
            response.raise_for_status()
        except:
            print(f"parsing error: {self.data_id}")
            raise
        
        try:
            data = response.json()
        except:
            print(f"parsing error: {self.data_id}")
            raise

        if not all(item in data.keys() for item in ["name", "intensity", "excitation_array", "emission_array"]):
            raise ParseError("data dictionary is missing required keys")

        self.names.append(data["name"])
        self.brightness_bin = data["intensity"]
        self.excitation_intensity = [float(x) for x in data["excitation_array"]]
        self.emission_intensity = [float(x) for x in data["emission_array"]]

class Scraper(abstract.AbstractScraper):
    def __init__(self) -> None:
        """
        Instantiates the FluoroFinder scraper
        """
        super().__init__()
        self.date = datetime.date(2020, 2, 15)

        self.url_ids = "https://app.fluorofinder.com/ff/spectra_viewers/"
        self.url_spectra = "https://app.fluorofinder.com/colors/"
        
        self.ids = IDCollection()
        self.fluorophores = abstract.AbstractCollection()

    def scrape_ids(self) -> None:
        """
        Performs the scraping of the ids
            :raises ScrapeError: upon failure
        """
        try:
            self.ids.parse(requests.get(self.url_ids))
        except Exception as error:
            raise ScrapeError("error scraping fluorophore ids") from error

    def scrape_fluorophores(self, begin: Union[None, int]=None, end: Union[None, int]=None) -> None:
        """
        Performs the scraping of the fluorophores
            :param begin: the ids index to start with (index is unstable, so can change upon modification of the ids dictionary)
            :param end: the ids index to end before (index is unstable, so can change upon modification of the ids dictionary)
            :raises ScrapeError: when scraping failes (example: ids are missing) / html errors
        """
        if not self.ids:
            raise ScrapeError()

        if not begin:
            begin = 0
        if not end:
            end = len(self.ids)

        for i, fluorophore_id in enumerate(self.ids):
            # Skip entrees if:
            if i < begin or i >= end:
                continue

            # Retreive all spectral data and metadata
            fluorophore = Data(fluorophore_id)
            try:
                fluorophore.parse(requests.get(f"{self.url_spectra}{fluorophore_id.identifier}"))
            except Exception as error: 
                raise ScrapeError(f"error scraping spectra data {i}:{fluorophore_id.identifier}") from error

            self.fluorophores[fluorophore_id.identifier] = fluorophore

            print(f"{i}:{fluorophore_id.identifier}:{fluorophore_id.name}")
            time.sleep(self.timeout)

if __name__ == "__main__":
    save_dir = os.path.dirname(os.path.realpath(__file__))
    save_file = "FluoroFinder"

    scraper = Scraper()
    scraper.scrape_ids()
    scraper.scrape_fluorophores()

    scraper.export(save_dir, save_file, Format.json)
