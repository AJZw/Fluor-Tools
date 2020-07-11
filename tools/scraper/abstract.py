# -*- coding: utf-8 -*-

## Fluor Tools ###############################################################
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
The scrapers abstract containers, adds the scraping parse interface

:class: AbstractData
The data container for scraped information of a specified fluorophore

:class: AbstractID
A data container that represents a fluorophore's identification within a spectrum viewer 

:class: AbstractCollection
A data container for AbstractID or AbstractData. Effectively a directly iterable dictionary

:class: AbstractReference
A data container that represents a url/journal reference

:class: AbstractScraper
A template for any scraper
"""

from __future__ import annotations
from typing import Union, List, Tuple, Dict, Any
from requests import Response

from .. import json, Format
from ..abstract import AbstractData as _AbstractData, AbstractID as _AbstractID, AbstractCollection as _AbstractCollection, AbstractReference as _AbstractReference
from ..reader import Reader as _Reader

import os.path
import datetime

class AbstractData(_AbstractData):
    """
    Abstract container for all available data of a fluorophore
    """    
    def parse(self, response: Response) -> None:
        """
        Parse the response of the fluorophore id.
        Depending on the fluophore id, can be called multiple times with different parts of data
            :param response: the server response
        """
        raise NotImplementedError

class AbstractID(_AbstractID):
    """
    Abstract container representing the identifier of a fluorophore
    """
    def parse(self, data: Any) -> None:
        """
        Parses the text into a ID. This function must define the fluorophore_identifier
            :param text: to be parsed
        """
        raise NotImplementedError

class AbstractCollection(_AbstractCollection):
    """
    Abstract collection of fluorophore id's or data. Allows for direct iteration over the collection
    The collection requires str key's
    You can request an entree by key index, but this is unstable! No guarantee that the key order is stable upon modification of the internal collection
    """
    def parse(self, response: Response) -> None:
        """
        Parses the response into a collection of ID's or Data 
            :param reponse: the get response
        """
        raise NotImplementedError

class AbstractReference(_AbstractReference):
    """
    Abstract container representing a url/journal reference
    """
    def parse(self, text: str) -> None:
        """
        Parses the text into the reference object
            :param text: the text to parse (utf-8 encoded)
        """
        raise NotImplementedError("")

class AbstractScraper():
    """
    Scraper template. Inherits Reader for its exporting functions (and ease to compare)
    """
    def __init__(self) -> None:
        super().__init__()
        self.ids: AbstractCollection = None
        self.fluorophores: AbstractCollection = AbstractCollection()

        self.date = datetime.date(1, 1, 1)
        self.timeout: float = 0.25

    def export(self, directory: str, name: str, export_format: Format=Format.json) -> None:
        """
        Writes a file to the directory. The file contains data in the format as specified encoded in utf-8
            :param directory: the directory to save the file to
            :param name: the file name without extension
            :param export_format: the file format
            :raises ValueError: when directory doesnt exists or when file already exists in the directory
        """
        if not os.path.isdir(directory):
            raise ValueError("directory doesnt exist")

        if export_format == Format.ini:
            name += ".txt"
            output = self.fluorophores._export_ini()
        elif export_format == Format.json:
            name += ".json"
            output = self.fluorophores._export_json()
            #output = json.dumps(output, indent=2, separators=(",", ": "), sort_keys=False)
            output = json.dumps_pretty(output)
        else:
            NotImplementedError("Unimplemented export format")

        path = os.path.join(directory, name)
        if os.path.isfile(path):
            raise ValueError("file already exists")

        with open(path, "w", encoding="utf-8") as f:
            f.write(output)

    def scrape_ids(self) -> None:
        """
        Abstract function to be called for scraping of the ids (if relevant)
            :raises: NotImplementedError
        """
        raise NotImplementedError

    def scrape_fluorophores(self, begin: Union[None, int]=None, end: Union[None, int]=None) -> None:
        """
        Abstract function to be called for scraping of the fluorophores
            :raises: NotImplementedError
        """
        raise NotImplementedError

    def date(self) -> datetime.date:
        """
        Returns the latest date the scraper has been tested for validity
        """
        return self.date
