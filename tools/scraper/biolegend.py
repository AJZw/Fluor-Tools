# -*- coding: utf-8 -*-

## Fluor Tools Scraper #######################################################
# Author:     AJ Zwijnenburg
# Version:    v1.0
# Date:       2020-02-08
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
The Fluor scraper of BioLegend Fluorescence Spectra Analyzer

In the Biolegend Spectra Analyzer all data is stored within a source script as
a json table with some javascript text manipulations. This json table is 
extracted from the javascript script and fluorophores are extracted directly.
(Therefore no independent scraping of fluorophore ids is necessary).

:class: Data:
BioLegend data container, parses the Data responses

:class: DataContainer:
BioLegend data container for storing and parsing of multiple Data objects

:class: Scraper:
BioLegend general scraper class, contains all relevant/scraped information

"""
from __future__ import annotations
from typing import Union

import requests
import html

from .. import json, Format, Source
from . import abstract, ParseError, ScrapeError

from lxml import etree
from io import StringIO

import datetime
import os.path
import time

class Data(abstract.AbstractData):
    def __init__(self, identifier: ID) -> None:
        """
        Initiates the Data object based on the identifier. Also loads the category data
        """
        super().__init__(identifier)
        self.source = "BioLegend"

    def parse(self, data: dict) -> None:
        """
        Parse the fluorophore data
            :param response: the response containing the data
            :raises ParseError: if data contains invalid/missing data
        """
        # check for mandatory keys
        if not all(item in data.keys() for item in ["label", "data"]):
            raise ParseError("data dictionary is missing required keys")

        name = data["label"]
        spectrum_type = ""
        if name[-10:] == "Excitation":
            name = name[:-11]
            spectrum_type = "EX"
        elif name[-8:] == "Emission":
            name = name[:-9]
            spectrum_type = "EM"
        else:
            raise ParseError("unknown spectrum type")

        if not self.names:
            self.names.append(name)
        else:
            if self.names[0] != name:
                raise ParseError("name missmatch, do these spectra belong together?")

        spectrum_data = data["data"]

        wavelength = [x[0] for x in spectrum_data]
        intensity = [x[1] for x in spectrum_data]

        #if spectrum_type == "AB":
        #    self.absorption_wavelength = wavelength
        #    self.absorption_intensity = intensity
        if spectrum_type == "EX":
            self.excitation_wavelength = wavelength
            self.excitation_intensity = intensity
        elif spectrum_type == "EM":
            self.emission_wavelength = wavelength
            self.emission_intensity = intensity
        #elif spectrum_type == "A_2P":
        #    self.two_photon_wavelength = wavelength
        #    self.two_photon_intensity = intensity
        else:
            raise ParseError(f"unknown spectrum type {spectrum_type}:{self.data_id}")

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
        except:
            print("request failure")
            raise

        try:
            parse_tree = etree.parse(StringIO(response.content.decode("utf-8")), parser=etree.HTMLParser())
        except Exception as error:
            raise ParseError("error unpacking spectra response data") from error

        spectra_data = parse_tree.xpath('//script[@id="source"]')
        if len(spectra_data) != 1:
            raise ParseError("error unpacking spectra response data, cannot find fluorophore data")

        spectra_data = spectra_data[0].text
        # spectra_data is javascript, just cut-out the json table and dump the json
        spectra_data = spectra_data.split("width15);\r\n\r\n\r\n\r\n\r\ndatasets = ")
        if len(spectra_data) != 2:
            raise ParseError("error unpacking spectra response data, cannot find fluorophore data")
        spectra_data = spectra_data[1].split(";\r\n\r\n\r\nvar data = [];\r\n")
        if len(spectra_data) != 2:
            raise ParseError("error unpacking spectra response data, cannot find fluorophore data")
        spectra_data = spectra_data[0]

        # unescape special characters
        spectra_data = html.unescape(spectra_data)

        # remove javascript string manipulations
        spectra_data = spectra_data.replace('""+', '"')
        spectra_data = spectra_data.replace('+""', '"')
        spectra_data = spectra_data.replace('"+', '')
        spectra_data = spectra_data.replace('+"', '')
    
        spectra_data = spectra_data.replace('[start', '[1')
        spectra_data = spectra_data.replace('[finish', '[1')

        # parse into json table
        try:
            spectra_data = json.loads(spectra_data)
        except Exception as error:
            raise ParseError("error unpacking spectra json table") from error

        # Remove non-spectra keys from the data
        for key in list(spectra_data.keys()):
            if key in ("ex325", "ex355", "ex405", "ex488", "ex561", "ex532", "ex633", "customfilter", "customfilter1", "customfilter2", "customfilter3", "customfilter4", "customfilter5", "customfilter6", "customfilter7", "customfilter8", "customfilter9", "customfilter10", "customfilter11", "customfilter12", "customfilter13", "customfilter14", "customfilter15", "example", "exampleex", "resetzoom"):
                spectra_data.pop(key)

        for i, spectra_id in enumerate(spectra_data.keys()):
            # Extract proper id
            if spectra_id[-2:] == "ex":
                fluorophore_id = spectra_id[:-2]
            elif spectra_id[-2:] == "em":
                fluorophore_id = spectra_id[:-2]
            else:
                raise ParseError(f"unknown spectra type {i}:{fluorophore_id}")

            # Retreive all spectral data and metadata
            if fluorophore_id not in self.collection:
                self.collection[fluorophore_id] = Data(abstract.AbstractID(Source.biolegend, fluorophore_id))

            try:
                self.collection[fluorophore_id].parse(spectra_data[spectra_id])
            except Exception as error: 
                raise ParseError(f"error parsing spectra data {i}:{fluorophore_id}") from error

            print(f"{i}:{fluorophore_id}")

class Scraper(abstract.AbstractScraper):
    def __init__(self) -> None:
        """
        Instantiates the BioLegend scraper
        """
        super().__init__()
        self.date = datetime.date(2020, 2, 18)

        self.url_spectra = "https://www.biolegend.com/en-us/spectra-analyzer"
        
        self.ids = abstract.AbstractCollection()
        self.fluorophores = DataCollection()

    def scrape_ids(self) -> None:
        """
        placeholder - BioLegends spectra can be directly scraped, no need to build a list of ids first
            raises NotImplementedError: -
        """
        NotImplementedError("biolegend.Scraper doesnt need ids")

    def scrape_fluorophores(self, begin: Union[None, int]=None, end: Union[None, int]=None) -> None:
        """
        Performs the scraping of the fluorophores
            :param begin: not used, as each run only 1 request is necessary
            :param end: not used, as each run only 1 request is necessary
            :raises ScrapeError: when scraping failes (example: ids are missing) / html errors
        """
        try:
            self.fluorophores.parse(requests.get(self.url_spectra))
        except Exception as error:
            raise ScrapeError("failure scraping fluorophores") from error

        # Fill ids, although in principle unnecessary, keeps the scraper interface consistent
        for key in self.fluorophores.keys():
            self.ids[key] = abstract.AbstractID(Source.biolegend, key)
        
if __name__ == "__main__":
    save_dir = os.path.dirname(os.path.realpath(__file__))
    save_file = "BioLegend"

    scraper = Scraper()
    scraper.scrape_fluorophores()

    scraper.export(save_dir, save_file, Format.json)
