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
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, 
# modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the 
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE 
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR 
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, 
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
##############################################################################

"""
The Fluor spectra viewer python toolkit.
Provides scrapers to retreive spectrum information from the main online spectra viewers.
Provides viewer to curate the spectrum information.

:class: Format
Enumeration for the implemented export formats

:class: Source
Enumeration defining the scraping origin
"""

from enum import Enum

class Format(Enum):
    """
    Enumerations defining the scrapers export formats
    """
    ini = 0
    json = 1

class Source(Enum):
    """
    Enumerations defining the scraping source
        Source.none is a special case. Signifies a not properly instantiated source.
        Source.source is a special case. Indicates the final modified and annotated data.
    """
    none = 0
    source = 1
    bd = 2
    biolegend = 3
    biotium = 4
    chroma = 5
    fluorofinder = 6
    fpbase = 7
    thermofisher = 8

    def __repr__(self) -> str:
        return self._name_
