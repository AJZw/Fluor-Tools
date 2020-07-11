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
The Fluor scraper of FPBase Fluorescence Spectra Viewer.

FPbase requests a json container containing all identifiers (named slug) and names
of all fluorophores. This request is used to uncover all identifiers.
Each identifier (slug) can contain multiple id's each refering to a specific
spectrum (absorption etc).
Each of these id's are subsequently used to scrape all spectra data
Secondly a slug of category "p" (protein) also has a FPbase reference page.
These pages contain paper references, alternative names, etc. The url to
these pages can be found using the url specifier.

:class ID:
FPbase identifier class, parses ID information

:class IDCollection:
FPbase identifier collection class, parses the entire identifier response

:class: Data:
FPbase data container, parses the Data responses

:class: Scraper:
FPbase general scraper class, contains all relevant/scraped information
"""

from __future__ import annotations
from typing import Union, List, Tuple, Dict, Any

import requests

from lxml import etree
from io import StringIO
from .. import Format, Source
from . import ParseError, ScrapeError, abstract

import time
import os.path
import datetime

class ID(abstract.AbstractID):
    """
    Identifier for FPBase data
        :param data: parent/owner data
        :raises ParseError: if parent/owner data is incomplete/invalid
    """
    def __init__(self, source: Source, data: dict) -> None:
        super().__init__(source, data["slug"])
        self.id = None
        self.name = None
        self.category = None
        self.url = None

        # Note: id cannot be the identifier as different source (dyes/protein) can have identical id's
        try:
            self.id = data["id"]
        except KeyError:
            raise ParseError("parent/owner data must have a defined id")

        try:
            self.name = data["name"]
        except KeyError:
            raise ParseError("parent/owner data must have a defined name")

        try:
            self.url = data["url"]
        except KeyError:
            self.url = None
            pass

    def parse(self, data: dict) -> None:
        """
        Parses the basic spectrum slug
            :param data[dict]: the slug dictionary
            :raises ParseError: if the slug is missing vital information
        """
        # check for the required keys
        if not all(item in data.keys() for item in ["owner", "category", "subtype", "id", "owner"]):
            raise ParseError("data dictionary is missing required keys")
        if not all(item in data["owner"].keys() for item in ["slug", "id"]):
            raise ParseError("data dictionary is missing required keys")

        if self._identifier != data["owner"]["slug"]:
            raise ParseError("data does not belong to the same owner slug")

        if self.id != data["owner"]["id"]:
            raise ParseError("data does not belong to the same owner id")

        # only needs to happen once
        if not self.category:
                self.category = data["category"]
        else:
            if self.category != data["category"]:
                raise ParseError("data does not belong to the same category")

        if data["subtype"] == "ab":
            if "ab" in self.spectra.keys():
                raise ParseError("fluorophore already contains identifier for subtype ab")
            self.spectra["ab"] = data["id"]
        elif data["subtype"] == "ex":
            if "ex" in self.spectra.keys():
                raise ParseError("fluorophore already contains identifier for subtype ex")
            self.spectra["ex"] = data["id"]
        elif data["subtype"] == "em":
            if "em" in self.spectra.keys():
                raise ParseError("fluorophore already contains identifier for subtype em")
            self.spectra["em"] = data["id"]
        elif data["subtype"] == "2p":
            if "2p" in self.spectra.keys():
                raise ParseError("fluorophore already contains identifier for subtype 2p")
            self.spectra["2p"] = data["id"]

        else:
            raise ParseError(f"Unknown subtype: {data['subtype']}")

    def _export_json(self) -> dict():
        output = super()._export_json()

        #no need to json export this. Most data is moved to the relevant data entrees during Data.__init__()
        #output["id2"] = self.id
        #output["name"] = self.name
        #output["category"] = self.category
        #output["url"] = self.url

        return output

class IDCollection(abstract.AbstractCollection):
    """
    Collection of fpbase ids
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
            json = response.json()["data"]["spectra"]
        except:
            print("parsing error")
            raise

        for slug in json:
            # check for mandatory keys
            if not all(item in slug.keys() for item in ["category", "owner"]):
                raise ParseError("data dictionary is missing required keys")
            if not all(item in slug["owner"].keys() for item in ["slug"]):
                raise ParseError("data dictionary is missing required keys")

            # Only parse dyes (d) and protein (p) slugs
            if slug["category"] != "d" and slug["category"] != "p":
                continue

            owner_id = slug["owner"]["slug"]
            if owner_id not in self.collection:
                self.collection[owner_id] = ID(Source.fpbase, slug["owner"])

            try:
                self.collection[owner_id].parse(slug)
            except:
                print(f"parsing error: {owner_id}")
                raise

class Data(abstract.AbstractData):
    def __init__(self, identifier: ID) -> None:
        """
        Initiates the Data object based on the identifier. Also loads the category data
        """
        super().__init__(identifier)
        self.source = "FPbase"

        if identifier.category == "d":
            self.categories.append("dyes")
        elif identifier.category == "p":
            self.categories.append("protein")
        else:
            raise ParseError("Unknown category")

        self.url = identifier.url

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

        meta = json["data"]["spectrum"]["owner"]
 
        if not self.names:
            self.names.append(meta["name"])
        elif self.names[0] != meta["name"]:
            raise ParseError("Name missmatch, do these spectra belong together?")

        if self.extinction_coefficient is None:
            self.extinction_coefficient = meta["extCoeff"]
        
        if self.quantum_yield is None:
            self.quantum_yield = meta["qy"]

        if self.brightness is None:
            if self.extinction_coefficient is not None and self.quantum_yield is not None:
                self.brightness = (self.extinction_coefficient / 1000) * self.quantum_yield

        if self.cross_section is None:
            self.cross_section = meta["twopPeakgm"]

        spectrum = json["data"]["spectrum"]
        spectrum_type = spectrum["subtype"]
        spectrum_data = spectrum["data"]

        wavelength = [x[0] for x in spectrum_data]
        intensity = [x[1] for x in spectrum_data]

        if spectrum_type == "AB":
            self.absorption_wavelength = wavelength
            self.absorption_intensity = intensity
        elif spectrum_type == "EX":
            self.excitation_wavelength = wavelength
            self.excitation_intensity = intensity
        elif spectrum_type == "EM":
            self.emission_wavelength = wavelength
            self.emission_intensity = intensity
        elif spectrum_type == "A_2P":
            self.two_photon_wavelength = wavelength
            self.two_photon_intensity = intensity
        else:
            raise ParseError(f"Unknown subtype {spectrum_type}:{self.data_id}")

    def parse_references(self, data: requests.Response) -> None:
        """
        Parse the fluorophores html reference data
            :param response: the requests get response
            :raises HTMLError: upon any html error during response request
            :raises ParseError: if json contains invalid/missing data 
        """
        try:
            data.raise_for_status()
        except:
            print(f"parsing error: {self.data_id}")
            raise

        try:
            parse_tree = etree.parse(StringIO(data.content.decode("utf-8")), parser=etree.HTMLParser())
        except:
            print(f"parsing error: {self.data_id}")
            raise

        # Get alternative names
        container = parse_tree.xpath('//div[@class="container protein mt-4"]/p[@class="text-center aliases pb-2"]')
        if len(container) == 0:
            pass
        elif len(container) > 2:
            raise ParseError(f"parsing error alternative names: {self.data_id}")
        else:
            try:
                self.names.extend(self._parse_alt_names(container[0]))
            except:
                print(f"parsing error alternative names: {self.data_id}")
                raise

        # Get main reference
        container = parse_tree.xpath('//div[@class="primary-ref references mt-2"]/div[@class="reference"]')
        for item in container:
            try:
                self.references.append(self._parse_reference(item))
            except:
                print(f"parsing error primary reference: {self.data_id}")
                raise

        # Get additional references
        container = parse_tree.xpath('//div[@class="additional-ref references"]//div[@class="reference"]')
        for item in container:
            try:
                self.references.append(self._parse_reference(item))
            except:
                print(f"parsing error additional reference: {self.data_id}")
                raise

    @staticmethod
    def _parse_alt_names(data: etree.Element) -> List[str]:
        """
        Parse the alternative names string into a list of names
            :param data: the data element to parse, eg <p class=...>
        """
        data = data.text
        data = data.replace("\n", "")
        data = data.replace("\t", "")
        data = data.lstrip("a.k.a.")
        data = data.split(",")
        
        return data

    def _parse_reference(self, data: etree.Element) -> AbstractReference:
        """
        Parses the reference from the reference node, eg <div class='reference'>
            :param data: the reference node of a reference
            :raise ParseError: if reference parsing failes
            :returns: the reference
        """
        reference = abstract.AbstractReference()

        # Get title
        title = data.xpath("./h4/a")
        if not title:
            raise ParseError("Missing title")
        reference.title = title[0].text

        # Get authorlist
        authors = data.xpath('./p[@class="authorlist"]/a')
        if not authors:
            raise ParseError("Missing authorlist")
        for author in authors:
            reference.authors.append(author.text)

        # Get details:
        details = data.xpath('./p[@class="reference-details"]')
        if not details:
            raise ParseError("Missing reference details")
        
        reference.year = self._parse_year(details[0].text)
        reference.journal, reference.volume = self._parse_journal(details[0].getchildren()[0].text)
        reference.issue, reference.pages, reference.doi = self._parse_doi(details[0].getchildren()[0].tail)

        # Get webpages
        links = details[0].xpath('./a')
        for link in links:
            url = link.attrib["href"]
            url_type = link.getchildren()[0].tail
            if url_type == "Article":
                reference.url_doi = url
            elif url_type == "Pubmed":
                reference.url_pubmed = url
            else:
                raise ParseError("Unknown url type")
            
        return reference

    @staticmethod
    def _parse_year(text: str) -> int:
        """
        Parse the reference-details year string
            :param text: string to parse into a year
            :raises ParseError: if string is empty
            :returns: the integer literal representation of the text
        """
        if not text:
            raise ParseError("No text to parse")

        text = text.strip("\n\t")
        text = text.lstrip(" (")
        text = text.rstrip("). ")

        return text

    @staticmethod
    def _parse_journal(text: str) -> Tuple[str, str]:
        """
        Parse the reference-details journal string
            :raises ParseError: if string is empty or cannot be parsed
            :param text: string to parse into journal, volume
            :returns: tuple of (journal, volume)
        """
        if not text:
            raise ParseError("No text to parse")

        text = text.split(",")

        # journal can technically contain a comma
        if len(text) < 2:
            raise ParseError("Cannot parse the journal representing string")

        # Retreive volume
        volume = text[-1]
        volume = volume.strip(" ")

        # Journal
        journal = "".join(text[:-1])
        
        return (journal, volume)

    @staticmethod
    def _parse_doi(text: str) -> Tuple[str, str, str]:
        """
        Parse the reference-details doi string
            :param text: string to parse into issue, pages and doi
            :raises ParseError: if string is empty or cannot be parsed
            :returns: tuple of (issue, (page begin, page end), doi)
        """
        if not text:
            raise ParseError("No text to parse")

        text = text.split("doi:")
        if len(text) != 2:
            raise ParseError("Cannot parse the doi representing string")
        
        doi = text[1].strip(" .")

        text = text[0].split(",")
        if len(text) != 2:
            raise ParseError("Cannot parse the doi representing string")

        issue = text[0].strip("() ")

        pages = text[1].strip(". ")
        
        return (issue, pages, doi)

class Scraper(abstract.AbstractScraper):
    def __init__(self) -> None:
        """
        Instantiates the FPBase scraper
        """
        super().__init__()
        self.date = datetime.date(2020, 5, 20)

        self.url_ids = "https://www.fpbase.org/api/proteins/spectraslugs/"
        self.url_spectra = "https://www.fpbase.org/graphql/"
        self.url_reference = "https://www.fpbase.org/protein/"
        
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
            raise ScrapeError() from error

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
            for spectra_id in fluorophore_id:
                request_body = {"operationName":"Spectrum","variables":{"id":spectra_id},"query":"query Spectrum($id: Int!) {\n  spectrum(id: $id) {\n    id\n    data\n    category\n    color\n    subtype\n    owner {\n      slug\n      name\n      id\n      ... on State {\n        ...FluorophoreParts\n        __typename\n      }\n      ... on Dye {\n        ...FluorophoreParts\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment FluorophoreParts on FluorophoreInterface {\n  qy\n  extCoeff\n  twopPeakgm\n  exMax\n  emMax\n  __typename\n}\n"}
                
                try:
                    fluorophore.parse(requests.get(self.url_spectra, json=request_body))
                except Exception as error: 
                    raise ScrapeError(f"Error scraping spectra data {i}:{fluorophore_id.identifier}") from error

            if fluorophore_id.category == "p":
                try:
                    # url is ONLY the local FPBase page in the 'p' entrees!
                    fluorophore.parse_references(requests.get(f"{self.url_reference}{fluorophore_id.url}/"))
                except Exception as error: 
                    raise ScrapeError(f"Error scraping reference data {i}:{fluorophore_id.identifier}") from error

            self.fluorophores[fluorophore_id.identifier] = fluorophore

            print(f"{i}:{fluorophore_id.identifier}")
            time.sleep(self.timeout)

if __name__ == "__main__":
    save_dir = os.path.dirname(os.path.realpath(__file__))
    save_file = "FPBase"

    scraper = Scraper()
    scraper.scrape_ids()
    scraper.scrape_fluorophores()

    scraper.export(save_dir, save_file, Format.json)
