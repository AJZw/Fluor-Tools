# -*- coding: utf-8 -*-

## Fluor Tools Scraper #######################################################
# Author:     AJ Zwijnenburg
# Version:    v1.0
# Date:       2020-02-19
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
The Fluor scraper of Biotium Fluorescence Spectra Viewer

The Biotium spectra viewer receives a data table (csv format) directly from
the server. This file is parsed.

:class: Data:
Biotium data container

:class: DataCollection
Biotium container of fluorophore data. Parses the data response

:class: Scraper:
Biotium general scraper class, contains all relevant/scraped information

"""

from __future__ import annotations
from typing import Union

import requests

from .. import Format, Source
from . import abstract, ParseError, ScrapeError

import datetime
import os.path
import time

class Data(abstract.AbstractData):
    def __init__(self, identifier: ID) -> None:
        """
        Initiates the Data object based on the identifier. Also loads the category data
        """
        super().__init__(identifier)
        self.source = "Biotium"

class DataCollection(abstract.AbstractCollection):
    """
    Data container for BioLegend data files
    """
    def __init__(self) -> None:
        super().__init__()

    def parse(self, response: requests.response) -> None:
        """
        Parse the response and extract the different fluorophore data
            :param response: the get response
            :raises HTTPError: any error from requests
            :raises ParseError: if json contains invalid/missing data
        """
        try:
            response.raise_for_status()
        except Exception:
            print("exception upon getting fluorophore data response")
            raise

        table = response.text.split("\r\n")
        table_header = table[0]
        table = [row.split(",") for row in table[1:-1]]

        # Some name entrees have ',' in their names, so split while taking that into account
        table_names = []
        name = ""
        is_text = False
        for letter in table_header:
            if letter == '"':
                is_text = not is_text
            elif letter == ",":
                if is_text:
                    name += letter
                else:
                    table_names.append(name)
                    name = ""
            else:
                name += letter
        table_names.append(name)
        
        if table_names[0] != "Wavelength(nm)":
            raise ParseError("unknown csv data format")

        # transpose data to have a list for each column
        spectra = dict()
        for i, column in enumerate(table_names):
            spectrum = [row[i] for row in table[1:-1]]
            spectra[column] = spectrum
        
        # tranpose wavelength
        wavelength = [float(x) for x in spectra["Wavelength(nm)"]]
        spectra.pop("Wavelength(nm)")

        for i, key in enumerate(spectra.keys()):
            spectrum_type = ""
            if key[-3:] == "Abs":
                fluorophore_id = key[:-4]
                spectrum_type = "AB"
            elif key[-2:] == "Em":
                fluorophore_id = key[:-3]
                spectrum_type = "EM"
            else:
                ParseError(f"unknown spectrum type: {key}")

            # Get limits of spectrum
            begin = 0
            end = len(spectra[key])
            if spectra[key][0] == "":
                flag_start = True
            else:
                flag_start = False

            for j, value in enumerate(spectra[key]):
                if not value or value == "":
                    if flag_start:
                        begin = j + 1
                    elif not flag_start:
                        end = j
                        break
                else:
                    flag_start = False
      
            if fluorophore_id not in self.collection:
                self.collection[fluorophore_id] = Data(abstract.AbstractID(Source.biotium, fluorophore_id))
                self.collection[fluorophore_id].names.append(fluorophore_id)

            spectrum_wavelength = [float(x) for x in wavelength[begin:end]]
            spectrum_intensity = [float(x) for x in spectra[key][begin:end]]

            if spectrum_type == "AB":
                self.collection[fluorophore_id].absorption_wavelength = spectrum_wavelength
                self.collection[fluorophore_id].absorption_intensity = spectrum_intensity
            elif spectrum_type == "EM":
                self.collection[fluorophore_id].emission_wavelength = spectrum_wavelength
                self.collection[fluorophore_id].emission_intensity = spectrum_intensity
            else:
                raise ParseError(f"unknown spectrum type: {key}")

            print(f"{i}:{fluorophore_id}")

class Scraper(abstract.AbstractScraper):
    def __init__(self) -> None:
        """
        Instantiates the Biotium scraper
        """
        super().__init__()
        self.date = datetime.date(2020, 5, 20)

        self.url_spectra = "https://biotium.com/wp-content/uploads/2018/02/082218-data.csv"
        
        self.ids = abstract.AbstractCollection()
        self.fluorophores = DataCollection()

    def scrape_ids(self) -> None:
        """
        placeholder - Biotium spectra can be directly scraped, no need to build a list of ids first
            raises NotImplementedError: -
        """
        NotImplementedError("biotium.Scraper doesnt need ids")

    def scrape_fluorophores(self, begin: Union[None, int]=None, end: Union[None, int]=None) -> None:
        """
        Performs the scraping of the fluorophores
            :param begin: not used, as each run requires only 1 request
            :param end: not used, as each run requires only 1 request
            :raises ScrapeError: when scraping failes (example: ids are missing) / html errors
        """
        try:
            self.fluorophores.parse(requests.get(self.url_spectra))
        except Exception as error:
            raise ScrapeError("failure scraping fluorophores") from error

        # Fill ids, although in principle unnecessary, keeps the scraper interface consistent
        for key in self.fluorophores.keys():
            self.ids[key] = abstract.AbstractID(Source.biotium, key)

if __name__ == "__main__":
    save_dir = os.path.dirname(os.path.realpath(__file__))
    save_file = "Biotium"

    scraper = Scraper()
    scraper.scrape_fluorophores()

    scraper.export(save_dir, save_file, Format.json)
