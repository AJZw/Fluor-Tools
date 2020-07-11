# -*- coding: utf-8 -*-

## Fluor Tools Scraper #######################################################
# Author:     AJ Zwijnenburg
# Version:    v2.0
# Date:       2020-02-17
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
The Fluor scraper of Chroma Spectra Viewer.

Chroma's fluorochrome entity id's can be scraped from the viewer options. Each
fluorochrome has two additional id's referring to the excitation and emission data.
These id's can only be found by re-requesting the chroma viewer with additional
specification of the entity id's. With the additional id's in hand, I build a very
specific request body and header. Eventually leading to the server returning the 
precious requested data.

:class ID:
Chroma identifier class, parses ID information

:class IDCollection:
Chroma identifier collection class, parses the entire identifier response

:class: Data:
Chroma data container, parses the Data responses

:class: Scraper:
Chroma general scraper class, contains all relevant/scraped information

"""

from __future__ import annotations
from typing import Union

import requests
import urllib.parse
from lxml import etree
from io import StringIO

from .. import Format, Source
from . import abstract, ParseError, ScrapeError

import datetime
import time

class ID(abstract.AbstractID):
    """
    Identifier for chroma data
        :param identifier: identifier
        :param name: fluorophore name
        :raises ParseError: if parent/owner data is incomplete/invalid
    """
    def __init__(self, source: Source, identifier: int, name: str) -> None:
        super().__init__(source, identifier)
        self.name: str = name

    def _export_json(self) -> dict():
        output = super()._export_json()

        #output["name"] = self.name
        #output["spectra"] = self.spectra

        return output

class IDCollection(abstract.AbstractCollection):
    """
    Collection of chroma ids
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

        try:
            page = etree.parse(StringIO(response.content.decode("utf-8")), parser=etree.HTMLParser())
        except:
            print("parsing error")
            raise

        data_options = page.xpath('//div[@class="resp-tabs-container"]//tr[@class="plot-item"]')

        # get all options
        for data_option in data_options:
            data = data_option.xpath('./td/input')

            # We are only interested in the fluorophore options, ignore the rest
            if data[0].get("id").split("-")[0] != "fluor":
                continue
            
            identifier = int(data[0].get("value"))
            
            data = data_option.xpath('./td')
            if len(data) != 4:
                raise ParseError(f"unaccountable children in plot-item: {identifier}")

            name = data_option.xpath('./td')[1].text
            self.collection[identifier] = ID(Source.chroma, identifier, name)

    def parse_spectra(self, response: request.Response) -> None:
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

        try:
            page = etree.parse(StringIO(response.content.decode("utf-8")), parser=etree.HTMLParser())
        except:
            print("parsing error")
            raise

        data_options = page.xpath('//tr[@class="row plot-item"]/td[@class="checkbox center"]')
        
        for data_option in data_options:
            identifier = int(data_option.xpath('./input[@class="plot-item-entity"]')[0].get("value"))
            spectra_type = data_option.xpath('./input[@class="plot-item-parttype"]')[0].get("value")
            spectra_id = int(data_option.xpath('./input[@class="plot-item-toggle"]')[0].get("value"))
            
            self.collection[identifier].spectra[spectra_type] = spectra_id

class Data(abstract.AbstractData):
    def __init__(self, identifier: ID) -> None:
        """
        Initiates the Data object based on the identifier. Also loads the category data
        """
        super().__init__(identifier)
        self.source = "Chroma"
        self.names.append(identifier.name)

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
            json = response.json()
        except:
            print(f"parsing error: {self.data_id}")
            raise

        # check for mandatory keys
        try:
            spectrum = json["plot"]["objects"]["plot-item-0-0-0-0"]
        except Exception:
            raise ParseError("data dictionary is missing required keys") from None

        if not all(item in spectrum.keys() for item in ["title", "data"]):
            raise ParseError("data dictionary is missing required keys")

        name = spectrum["title"]
        if len(name.split("Excitation")) == 2:
            spectrum_type = "EX"
            name = name.split("Excitation")[0]
        elif len(name.split("Emission")) == 2:
            spectrum_type = "EM"
            name = name.split("Emission")[0]
        else:
            raise ParseError("unknown spectrum type")
 
        if self.names[0] != name:
            raise ParseError("name missmatch, do these spectra belong together?")

        spectrum_data = spectrum["data"]

        wavelength = [float(x[0]) for x in spectrum_data]
        intensity = [float(x[1]) for x in spectrum_data]

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

class Scraper(abstract.AbstractScraper):
    def __init__(self) -> None:
        """
        Instantiates the chroma scraper
        """
        super().__init__()
        self.date = datetime.date(2020, 5, 20)

        self.url_ids = "https://www.chroma.com/spectra-viewer"
        self.url_spectra = "https://www.chroma.com/plot/data"
        
        self.ids = IDCollection()
        self.fluorophores = abstract.AbstractCollection()

    def scrape_ids(self) -> None:
        """
        Performs the scraping of the ids
            :raises ScrapeError: upon scraping failure
        """
        # First get all the fluorophore ids
        try:
            self.ids.parse(requests.get(self.url_ids))
        except Exception as error:
            raise ScrapeError("scraping of fluorophore ids failed") from error

        # Now we have to get the spectra ids (in groups of 15)
        keys = self.ids.collection.keys()
        for i in range(0, len(keys), 15):
            to_request = []
            for j in range(i, i+15, 1):
                try:
                    to_request.append(str(self.ids[j].identifier))
                except IndexError:
                    break
            
            url = f"{self.url_ids}?fluorochromes={','.join(to_request)}"
            
            try:
                self.ids.parse_spectra(requests.get(url))
            except Exception as error:
                raise ScrapeError("scraping of spectra ids failed")

            # Wait to not overload the server / give yourself an ip ban
            time.sleep(self.timeout)

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
            for spectra_id in fluorophore_id.spectra:
                # Construct request body
                if spectra_id == "EX":
                    title = f"{fluorophore_id.name}Excitation Spectra"
                elif spectra_id == "EM":
                    title = f"{fluorophore_id.name}Emission Spectra"
                request_body = {"jsonData":{"data":[{"id":fluorophore_id.spectra[spectra_id],"color":"#fffff","title":title,"type":"fluorochrome","parttype":spectra_id,"entity":fluorophore_id.identifier,"label":"plot-item-0-0-0-0"}],"controls":{"view":"T","waveMin":200,"waveMax":200,"action":"init"}}}
                request_body = urllib.parse.urlencode(request_body, quote_via=urllib.parse.quote)
                request_body = request_body.replace("%27", "%22")

                header = {
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "X-Requested-With": "XMLHttpRequest",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Pragma": "no-cache",
                    "Cache-Control": "no-cache"
                }

                try:
                    fluorophore.parse(requests.post(self.url_spectra, data=request_body, headers=header))
                except Exception as error: 
                    raise ScrapeError(f"error scraping spectra data {i}:{fluorophore_id.identifier}") from error

            self.fluorophores[str(fluorophore_id.identifier)] = fluorophore

            print(f"{i}:{fluorophore_id.identifier}")
            time.sleep(self.timeout)

if __name__ == "__main__":
    save_dir = os.path.dirname(os.path.realpath(__file__))
    save_file = "Chroma"

    scraper = Scraper()
    scraper.scrape_ids()
    scraper.scrape_fluorophores()

    scraper.export(save_dir, save_file, Format.json)
