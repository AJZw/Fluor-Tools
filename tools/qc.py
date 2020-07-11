# -*- coding: utf-8 -*-

## Fluor Tools Viewer ########################################################
# Author:     AJ Zwijnenburg
# Version:    v1.0
# Date:       2020-07-11
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
Fluor requires the dataset to adhere to a certain set of rules. This class
checks if the data adheres to the rules.

The rules:
- wavelength has stepsize of 1.0
- all names are unique

:class: QC
Checks the quality of the loaded data

"""

from __future__ import annotations
from typing import Union

from .reader import Reader

class QC(Reader):
    """
    Class that checks the loaded data for the data properties as expected by Fluor. 
    """
    def __init__(self, path: Union[None, str]=None) -> None:
        super().__init__()
        self.passed: bool = False
        self.issues: List[str] = []
        
        if path is not None:
            self.load(path)

    def load(self, path: str, import_format: Union[None, Format]=None) -> None:
        """
        Loads the specified file into the internal collection and checks the quality
            :param path: path to the file
            :param export_format: function will auto detect the format based on extension (if none), otherwise forces that format
            :raises ValueError: when path doesnt point to a valid file
        """
        super().load(path, import_format)
        self.check()

    def check(self) -> None:
        """
        Runs the checker on the loaded data
        """
        self.passed = True
        self.issues = []

        names = set()

        for key in self.collection:
            data = self.collection[key]
            header = data.header

            # Check the names
            if not data:
                self.issues.append(f"{header}: missing name")
            else:
                for name in data.names:
                    if name in names:
                        self.issues.append(f"{header}: duplicate name '{name}'")
                    names.add(name)
               
            # Check the spectra
            if data.absorption_wavelength and data.absorption_intensity:
                result = self._check_spectra(data.absorption_wavelength, data.absorption_intensity)
                if result:
                    self.issues.append(f"{header}: absorption {result}")

                if not data.absorption_max:
                    self.issues.append(f"{header}: absorption max missing")

            if data.excitation_wavelength and data.excitation_intensity:
                result = self._check_spectra(data.excitation_wavelength, data.excitation_intensity)
                if result:
                    self.issues.append(f"{header}: excitation {result}")
                
                if not data.excitation_max:
                    self.issues.append(f"{header}: excitation max missing")

            if data.two_photon_wavelength and data.two_photon_intensity:
                result = self._check_spectra(data.two_photon_wavelength, data.two_photon_intensity)
                if result:
                    self.issues.append(f"{header}: two photon {result}")
                
                if not data.two_photon_max:
                    self.issues.append(f"{header}: two photon max missing")
                
            if data.emission_wavelength and data.emission_intensity:
                result = self._check_spectra(data.emission_wavelength, data.emission_intensity)
                if result:
                    self.issues.append(f"{header}: emission {result}")
                
                if not data.emission_max:
                    self.issues.append(f"{header}: emission max missing")

        if self.issues:
            self.passed = False

    @staticmethod
    def _check_spectra(wavelength: List[float], intensity: List[float]) -> Union[None, str]:
        """
        Checks the quality of the spectra. 
        :returns: None if all is correct. An error message if not.
        """
        if len(wavelength) < 2:
            return None

        start = wavelength[0]

        if float(start) != int(start):
            return f"non-whole wavelenghts"

        for i in range(1, len(wavelength)):
            stepsize = wavelength[i] - start
            if stepsize != 1.0:
                return f"stepsize of {stepsize}"
            start = wavelength [i]

        return None

    def __str__(self) -> str:
        if self.passed:
            return "Quality Control Passed"
        else:
            text = "Quality Control Failed, with following issues:"
            for issue in self.issues:
                text += "\n> " + issue
            return text

    def _export_ini(self) -> str:
        """
        Exports the contents of this container in an ini format. List are saved as comma separated strings.
            :returns: data representation in ini format. This is limited to one reference and text without comma's
        """
        export = ""

        for key in self.collection:
            export += f"[{key}]\n"
            export += self.collection[key].export(Format.ini)
            export += "\n"

        return export

    def _export_json(self) -> dict:
        """
        Exports the contents of this container in a json format
        """
        output = dict()

        for key in self.collection:
            output[key] = self.collection[key].export(Format.json)
        
        return output

