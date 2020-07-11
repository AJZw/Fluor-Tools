# -*- coding: utf-8 -*-

## Fluor Tools Scraper #######################################################
# Author:     AJ Zwijnenburg
# Version:    v2.0
# Date:       2020-02-16
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
The Fluor scraper of ThermoFisher SpectraViewer.

The fluorophore identifiers are encoded as json file within a javascript script.
After extracting the json table, we need to undo HTML escaping. This still keeps
unicode character escaping. Havent found a way around it, but we can safely 
ignore it, as we do not make use of these specific strings during scraping.
This leaves us with the fluorophore identifiers, which we can use to directly
request the spectra csv tables. The tables are rather messy, so special care
is taken to work around additional empty rows, and additional comma separators.

:class ID:
ThermoFisher identifier class, parses ID information

:class IDCollection:
ThermoFisher identifier collection class, parses the entire identifier response

:class: Data:
ThermoFisher data container, parses the Data responses

:class: Scraper:
ThermoFisher general scraper class, contains all relevant/scraped information

"""

from __future__ import annotations
from typing import Union

from .. import json, Format, Source
from . import abstract, ParseError, ScrapeError

import requests

import html
import datetime
import time

class ID(abstract.AbstractID):
    """
    Identifier for Thermofisher data
        :param data: parent/owner data
        :raises ParseError: if parent/owner data is incomplete/invalid
    """
    def __init__(self, source: Source, identifier: str) -> None:
        super().__init__(source, identifier)
        self.name = None
        self.categories = []
        self.spectra_files = []

    def parse(self, data: dict) -> None:
        """
        Parses the thermofisher fluorophore identifier json dictionary. Can be called multiple times with different categories
            :param data[dict]: the id dictionary
            :raises ParseError: if the id dictionary is missing vital information
        """
        if not all(item in data.keys() for item in ["uid", "spectraName", "spectraCategory", "spectraFileList"]):
            raise ParseError("data dictionary is missing required keys")
        
        if not self._identifier:
            self._identifier = data["uid"]
        else:
            if self._identifier != data["uid"]:
                raise ParseError("identifier are not similar")

        if not self.name:
            self.name = data["spectraName"]
        
        self.categories.append(data["spectraCategory"])
        
        if not self.spectra_files:
            self.spectra_files = data["spectraFileList"]
        else:
            if self.spectra_files != data["spectraFileList"]:
                raise ParseError("spectra file list unidentical")

    def _export_json(self) -> dict():
        output = super()._export_json()

        # No need to store this data in the identifier as this data is moved to Data object during Data.__init__()
        #output["name"] = self.name
        #output["categories"] = self.categories
        #output["spectra_files"] = self.spectra_files

        return output

class IDCollection(abstract.AbstractCollection):
    """
    Collection of thermofisher ids
    """
    def __init__(self) -> None:
        super().__init__()

    def parse(self, response: requests.Response) -> None:
        """
        Parse the response and extract the different fluorophore ids
            :param response: the get response
            :raises HTTPError: any error from requests
            :raises ValueError: if response contains undetectable spectra data
            :raises JSONDecodeError: if response data cannot be transformed into proper json
            :raises ParseError: if json contains invalid/missing data
        """
        try:
            response.raise_for_status()
        except:
            print("response error")
            raise

        data =  response.content.decode("iso-8859-1")
        data = data.split("var sv_spectra_data = ")
        if len(data) != 2:
            raise ValueError("unable to extract spectra data")
        data = data[1].split(", \\r\\napp_server_home")
        if len(data) != 2:
            raise ValueError("unable to extract spectra data")
        data = data[0]

        # The json data is html escaped and also unicode escaped
        data = html.unescape(data)

        # Havent found a proper way to decode the unicode mess, but this allows json.loads to work
        data = data.replace("\\\\", "\\")

        try:
            data = json.loads(data)
        except:
            print("json parsing error")
            raise

        for category in data:
            for spectrum in data[category]:
                if not all(item in spectrum.keys() for item in ["uid"]):
                    raise ParseError("json dictionary is missing required keys")
                fluorophore_id = spectrum["uid"]
                if fluorophore_id not in self.collection:
                    self.collection[fluorophore_id] = ID(Source.thermofisher, fluorophore_id)

                self.collection[fluorophore_id].parse(spectrum)

class Data(abstract.AbstractData):
    def __init__(self, identifier: ID) -> None:
        """
        Initiates the Data object based on the identifier. Also loads the category data
        """
        super().__init__(identifier)
        self.source = "ThermoFisher"
        self.names.append(identifier.name)
        self.categories.extend(identifier.categories)

    def parse(self, response: requests.Response) -> None:
        """
        Parse the thermofisher data, a csv file, with addition copyright column in the first row
        The headers (ex, em) can be append with state (eg '/high Ca')
            :param response: the response containing the data
            :raises HTTPError: upon any html error during response request
            :raises ParseError: if csv contains invalid/missing data
        """
        try:
            response.raise_for_status()
        except:
            print(f"parsing error: {self.data_id}")
            raise

        rows = response.text.split("\r\n")
        # Properly split the csv response into columns
        # Not all samples have ex/abs and em spectra
        meta = []
        section = ""
        accented = False
        for letter in rows[0]:
            if letter == ",":
                if accented:
                    section += letter
                else:
                    meta.append(section)
                    section = ""
            elif letter == '"':
                if accented:
                    accented = False
                else:
                    accented = True
            else:
                section += letter
        meta.append(section)
        print(f"{self.names}{meta}")

        # Error check/detect the columns data types / additional copyright information
        column_a_type = None
        column_b_type = None
        
        if len(meta) >= 4:
            if meta[0].strip(" ") != "wl" or meta[2].strip(" ") != "wl":
                raise ParseError("unknown wavelength column")
            
            # Sometimes metadata is added between brackets, after forward slash, or space
            column_a_type = meta[1].split(" ", maxsplit=1)[0]
            column_a_type = column_a_type.split("/", maxsplit=1)[0]
            column_a_type = column_a_type.split("(", maxsplit=1)[0]
            if column_a_type not in ("abs", "ex", "em"):
                raise ParseError(f"unknown column intensity type: {column_a_type}")
            
            column_b_type = meta[3].split(" ", maxsplit=1)[0]
            column_b_type = column_b_type.split("/", maxsplit=1)[0]
            column_b_type = column_b_type.split("(", maxsplit=1)[0]
            if column_b_type not in ("abs", "ex", "em"):
                raise ParseError(f"unknown column intensity type: {column_b_type}")

            if len(meta) > 4:
                if meta[4][:14] == "Data copyright" or meta[4][:14] == "Data Copyright":
                    copy = meta[4][14:].strip(" ")
                    if copy:
                        self.source += " - " + copy

        elif len(meta) >= 2:
            column_a_type = meta[1].split(" ", maxsplit=1)[0]
            column_a_type = column_a_type.split("/", maxsplit=1)[0]
            column_a_type = column_a_type.split("(", maxsplit=1)[0]
            if column_a_type not in ("abs", "ex", "em"):
                raise ParseError(f"unknown column intensity type: {column_a_type}")

            if len(meta) > 2:
                if meta[2][:14] == "Data copyright" or meta[2][:14] == "Data Copyright":
                    copy = meta[2][14:].strip(" ")
                    if copy:
                        self.source += " - " + copy

        else:
            raise ParseError("no data to parse")

        for row in rows[1:-1]:
            items = row.split(",")

            # Sometimes there are rows without any characters or with just one ',' ignore those rows
            if len(items) <= 1:
                continue

            column_a_w = items[0]
            column_a_i = items[1]

            if column_a_w != "" and column_a_i != "":
                if column_a_type == "abs":
                    self.absorption_wavelength.append(float(column_a_w))
                    self.absorption_intensity.append(float(column_a_i))
                elif column_a_type == "ex":
                    # One entree (12353lip) has an appended string with comma (so splits in 2 columns), 
                    # this passes all checks, i cannot think of a different way to filter it out,
                    # this can enable data-that-should-be-parsed to fall through accidently...
                    try:
                        self.excitation_wavelength.append(float(column_a_w))
                        self.excitation_intensity.append(float(column_a_i))
                    except ValueError:
                        print("Warning: fallthrough - false positve if this happens with '12353lip'")
                        pass
                elif column_a_type == "em":
                    self.emission_wavelength.append(float(column_a_w))
                    self.emission_intensity.append(float(column_a_i))
                else:
                    raise ParseError("unknown column intensity type")

            elif column_a_w == "" and column_a_i == "":
                # Both values are empty so can be ignored
                pass
            else:
                raise ParseError("both excitation wavelength and intensity have to be declared")

            # The row might contain a leading ',' so 5 columns are possible.... (why? oh why?)
            if len(items) >= 4:
                column_b_w = items[2]
                column_b_i = items[3]
            elif len(items) == 2:
                column_b_w = ""
                column_b_i = ""
            else:
                raise ParseError("unparsable column count")
    
            if column_b_w != "" and column_b_i != "":
                if column_b_type == "em":
                    self.emission_wavelength.append(float(column_b_w))
                    self.emission_intensity.append(float(column_b_i))
                elif column_a_type == "abs":
                    self.absorption_wavelength.append(float(column_b_w))
                    self.absorption_intensity.append(float(column_b_i))
                elif column_a_type == "ex":
                    self.excitation_wavelength.append(float(column_b_w))
                    self.excitation_intensity.append(float(column_b_i))
                else:
                    raise ParseError("unknown column intensity type")

            elif column_b_w == "" and column_b_i == "":
                # Both values are empty so can be ignored
                pass
            else:
                raise ParseError("both emission wavelength and intensity have to be declared")

class Scraper(abstract.AbstractScraper):
    def __init__(self) -> None:
        """
        Instantiates the Thermofisher scraper
        """
        super().__init__()
        self.date = datetime.date(2020, 5, 20)

        self.url_ids = "https://www.thermofisher.com/order/spectra-viewer/embeddedApp"
        self.url_spectra = "https://www.thermofisher.com/content/dam/LifeTech/Documents/spectra/plotfiles/"
        
        self.ids = IDCollection()
        self.fluorophores = abstract.AbstractCollection()

    def scrape_ids(self) -> None:
        """
        Performs the scraping of the ids
            :raises ScrapeError: when scraping failes
        """
        try:
            self.ids.parse(requests.get(self.url_ids))
        except Exception as error:
            raise ScrapeError("error scraping fluorophore ids")

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

            # Retreive all spectral data and most metadata
            fluorophore = Data(fluorophore_id)
            
            try:
                fluorophore.parse(requests.get(f"{self.url_spectra}{fluorophore_id.identifier}.txt"))

            except Exception as error: 
                raise ScrapeError(f"error scraping spectra data {i}:{fluorophore_id.identifier}") from error

            self.fluorophores[fluorophore_id.identifier] = fluorophore

            print(f"{i}:{fluorophore_id.identifier}")
            time.sleep(self.timeout)

if __name__ == "__main__":
    save_dir = os.path.dirname(os.path.realpath(__file__))
    save_file = "ThermoFisher"

    scraper = Scraper()
    scraper.scrape_ids()
    scraper.scrape_fluorophores()

    scraper.export(save_dir, save_file, Format.json)
