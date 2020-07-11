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
The Fluor scraper of BDBiosciences Spectrum Viewer

BD spectra viewer retreives the fluorophores id's by requesting a overview csv file.
This csv files contains the fluorophore ids with an appended 'SPEC.txt'.
After retreiving the fluorophore id's, you can directly request the spectra data
(SPEC.txt) and metadata (INFO.csv) from the server. The spectra data is a base64 
encoded TripleDES encrypted csv file. The metadata is a basic csv file.  

:class IDCollection:
Data container forming a collection of fluorophore ids

:class Data:
Main fluorophore data container

:class Scraper:
BD specific scraper
"""

from __future__ import annotations
from typing import Union, List, Tuple, Dict, Any

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
import binascii
import base64

import requests

import os.path
import time

import datetime

from .. import Format, Source
from . import abstract, ParseError, ScrapeError

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

        # One entree is separated with a "\n" instead of "\r\n", therefore:
        fluorophore_ids = response.text.replace("\r\n", "\n")
        fluorophore_ids = fluorophore_ids.split("\n")[:-1]

        # All entree have "SPEC.txt" appended, remove that to get the fluorophore id's
        fluorophore_ids = [x[:-8] for x in fluorophore_ids]

        for fluorophore_id in fluorophore_ids:
            self.collection[fluorophore_id] = abstract.AbstractID(Source.bd, fluorophore_id)

class Data(abstract.AbstractData):
    def __init__(self, identifier: abstract.AbstractID) -> None:
        """
        Initiates the Data object based on the identifier. Also loads the category data
        """
        super().__init__(identifier)
        self.source = "BDBiosciences"
        self.names.append(identifier.identifier)

    def parse(self, response: requests.Response) -> None:
        """
        Parse the fluorophore data (encrypted in SPEC.txt)
            :param response: the response containing the data
            :raises HTTPError: upon any html error during response request
            :raises ParseError: if json contains invalid/missing data
        """
        try:
            response.raise_for_status()
        except:
            print(f"parsing error: {self.data_id}")
            raise

        data = self.decrypt_spec_response(response.text)
        rows = data.split("\r\n")

        for row in rows[1:-1]:
            items = row.split(",")

            ex_w = items[0]
            ex_i = items[1]

            if ex_w != "" and ex_i != "":
                self.excitation_wavelength.append(float(ex_w))
                self.excitation_intensity.append(float(ex_i))
            elif ex_w == "" and ex_i == "":
                # Both values are empty so can be ignored
                pass
            else:
                # Rarely (PerCP-Cy5.5 i look at you) there are 'wavelength 0' rows padded to the end, ignore those
                if ex_w != "0" and ex_w != "":
                    raise ParseError("both excitation wavelength and intensity have to be declared")

            em_w = items[2]
            em_i = items[3]
    
            if em_w != "" and em_i != "":
                self.emission_wavelength.append(float(em_w))
                self.emission_intensity.append(float(em_i))
            elif em_w == "" and em_i == "":
                # Both values are empty so can be ignored
                pass
            else:
                # One of the value is undeclared -> Error
                if em_w != "0" and em_w != "":
                    raise ParseError("both emission wavelength and intensity have to be declared")

    def parse_references(self, response: requests.Response) -> None:
        """
        Parse the fluorophores metadata reference (INFO.csv)
            :param response: the requests get response
            :raises HTMLError: upon any html error during response request
            :raises ParseError: if json contains invalid/missing data 
        """
        try:
            response.raise_for_status()
        except:
            print(f"parsing error: {self.data_id}")
            raise

        rows = response.text.split("\r\n")

        # Splitting by , seperator doesnt work (see Eosin) as , is rarely used as thousand-separator
        row = rows[8]
        if row[:3] != "mE,":
            raise ParseError("unknown info format")
        else:
            value = row[3:]
            if value:
                value = value.strip('"')
                value = value.replace(",", "")
                self.extinction_coefficient = int(value)

        row = rows[9].split(",")
        if row[0] != "qY":
            raise ParseError("unknown info format")
        elif row[1] != "":
            self.quantum_yield = float(row[1])

        if self.extinction_coefficient is not None and self.quantum_yield is not None:
            self.brightness = (self.extinction_coefficient / 1000) * self.quantum_yield

    @staticmethod
    def decrypt_spec_response(response):
        """
        Decrypts the BD Biosciences Spectrum Viewer v9.0.0.9 Fluorophore request response payload
        The payload is a base64 encoded string which contains a header + TripleDES encoded data + Initiation Vector
        If the function fails, bd likely updated the encryption key, check that first :).
            :param response[str]: the SPEC response
            :returns: the decoded data (is in csv format) of the response
        """
        # The javascript decrypting code
        # var bw = 5; 
        # var bx = 2; 
        # var bv = CryptoJS.enc.Base64.parse(bz).toString();
        # var bt = parseInt(String.fromCharCode("0x" + bv.substring(bx * 2, (bx + 1) * 2)));
        # var bs = CryptoJS.enc.Hex.parse(bv.substring(bw * 2, (bv.length - (bt * 2)))).toString(CryptoJS.enc.Base64); 
        # var by = CryptoJS.enc.Hex.parse(aT);
        # var bq = CryptoJS.enc.Hex.parse(bv.substring(bv.length - (bt * 2)));
        # var bo = CryptoJS.TripleDES.decrypt(bs, by, { iv: bq, mode: CryptoJS.mode.CBC, padding: CryptoJS.pad.Pkcs7 });
        # var bp = d3.csv.parseRows(bo.toString(CryptoJS.enc.Utf8)).slice(1).map(function (bA) { return { xEx: bA[0], yEx: bA[1], xEm: b[2], # yEm: bA[3] } });

        #BLOCK_SIZE = 8
        IV_SIZE_INDEX = 2    # var bx
        DATA_INDEX = 5       # var bw
        KEY = binascii.unhexlify("9c9500243eedbe26f598bea49487b2106ef08a0817f72cf3")    # var aT

        response_binary = base64.b64decode(response)

        iv_size = int(chr(response_binary[IV_SIZE_INDEX]))

        data = response_binary[DATA_INDEX:len(response_binary) - iv_size]
        iv = response_binary[len(response_binary) - iv_size:]

        cipher = Cipher(algorithms.TripleDES(KEY), modes.CBC(iv), backend=default_backend())
        decoded = cipher.decryptor().update(data)

        decoded_text = str(decoded, "utf-8")

        # Looks like the utf-8 text is Pkcs7 padded, padding should happen after encryption, but oke, this is how it is.
        # Quick and dirty just remove the padding bits, with a block size of 8, max padding is 7, so this should be safe ^_^.
        decoded_text = decoded_text.rstrip("\x08\x07\x06\x05\x04\x03\x02\x01\x00")

        return decoded_text

class Scraper(abstract.AbstractScraper):
    def __init__(self) -> None:
        """
        Instantiates the BD scraper
        """
        super().__init__()
        self.date = datetime.date(2020, 5, 19)

        self.url_ids = "http://static.bdbiosciences.com/spectrumviewer_v9.0.0.9/data/fluorochromes.txt"
        self.url_spectra = "http://static.bdbiosciences.com/spectrumviewer_v9.0.0.9/data/Spec/"
        self.url_reference = "http://static.bdbiosciences.com/spectrumviewer_v9.0.0.9/data/Info/"
        
        self.ids = IDCollection()
        self.fluorophores = abstract.AbstractCollection()

    def scrape_ids(self) -> None:
        """
        Performs the scraping of the ids
            :raises ScrapeError: upon scraping failure
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
            :raises ParseError: when parsing failes
        """
        if not self.ids:
            raise ScrapeError("missing ids, please call scrape_ids() first")

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
                fluorophore.parse(requests.get(f"{self.url_spectra}{fluorophore_id.identifier}SPEC.txt"))
            except Exception as error: 
                raise ScrapeError(f"error scraping spectra data {i}:{fluorophore_id.identifier}") from error

            try:
                fluorophore.parse_references(requests.get(f"{self.url_reference}{fluorophore_id.identifier}INFO.csv"))
            except Exception as error: 
                raise ScrapeError(f"error scraping reference data {i}:{fluorophore_id.identifier}") from error

            self.fluorophores[fluorophore_id.identifier] = fluorophore

            print(f"{i}:{fluorophore_id.identifier}")
            time.sleep(self.timeout)

if __name__ == "__main__":
    save_dir = os.path.dirname(os.path.realpath(__file__))
    save_file = "BDBiosciences"

    scraper = Scraper()
    scraper.scrape_ids()
    scraper.scrape_fluorophores()

    scraper.export(save_dir, save_file, Format.json)
