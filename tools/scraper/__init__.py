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
The Fluor spectra viewer scrapers.
Provides abstract scraping object and specifized scrapers for the main spectrum viewers:
- BDBiosciences Spectrum Viewer
- BioLegend Fluorescence Spectra Analyzer
- Biotium Fluorescence Spectra Viewer
- Chroma Spectra Viewer
- FluoroFinder Spectra Viewer
- FPBase Fluorescence Spectra Viewer
- ThermoFisher SpectraViewer

:class: ParseError
Parsing error, raised upon parsing failure

:class: ScrapeError
Parsing error, raised upon scraping failure
"""

class ParseError(Exception):
    """
    Raised when data parsing failes
    """
    pass

class ScrapeError(Exception):
    """
    Raised when data scraping failes
    """
    pass
