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
This postprocesses the main database into the requirements for Fluor

:class: PostProcessor
Removes the unused data and makes the data ready for use by Fluor version >= v0.8.6

:class: PostProcessorOld
Removes the unused data nad makes the data ready for use by Fluor version =< v0.8.5

"""

from __future__ import annotations
from typing import Union

from .reader import Reader
from . import Format

import copy

class PostProcessor(Reader):
    """
    Post-processes the data for use in Fluor
    """
    def process(self) -> None:
        """
        Runs the post processor on the data
        """
        for key in self.collection:
            data = self.collection[key]
            
            # Do not remove header, necessary for proper exporting

            # Remove unused data
            if data.data_id:
                data.data_id = None

            if data.categories:
                data.categories = None

            if data.extinction_coefficient:
                data.extinction_coefficient = None

            if data.quantum_yield:
                data.quantum_yield = None

            if data.cross_section:
                data.cross_section = None

            if data.brightness:
                data.brightness = None

            if data.brightness_bin:
                data.brightness_bin = None

            if data.url:
                data.url = None

            if data.references:
                data.references = None

            # Round all spectra data to max 1 decimal
            if data.absorption_wavelength and data.absorption_intensity:
                data.absorption_intensity = [round(float(x), ndigits=1) for x in data.absorption_intensity]
                data.absorption_max = int(data.absorption_max)

                #if not data.excitation_wavelength or not data.excitation_intensity:
                #    data.excitation_max = int(data.absorption_max)
                #    data.excitation_wavelength = data.absorption_wavelength
                #    data.excitation_intensity = data.absorption_intensity
                #    data.absorption_max = None
                #    data.absorption_wavelength = []
                #    data.absorption_intensity = []

            if data.excitation_wavelength and data.excitation_intensity:
                data.excitation_intensity = [round(float(x), ndigits=1) for x in data.excitation_intensity]
                data.excitation_max = int(data.excitation_max)
                
            if data.two_photon_wavelength and data.two_photon_intensity:
                data.two_photon_intensity = [round(float(x), ndigits=1) for x in data.two_photon_intensity]
                data.two_photon_max = int(data.two_photon_max)
                
            if data.emission_wavelength and data.emission_intensity:
                data.emission_intensity = [round(float(x), ndigits=1) for x in data.emission_intensity]
                data.emission_max = int(data.emission_max)

    def remove_disabled(self) -> None:
        """
        Remove all attribute 'enable'=False from the dataset
        """
        delete_later = []
        for key in self.collection:
            if not self.collection[key].enable:
                delete_later.append(key)

        for key in delete_later:
            del self.collection[key]

    def remove_source(self) -> None:
        """
        Remove the source attribute from the dataset
        """
        for key in self.collection:
            self.collection[key].source = None

    def _export_ini(self) -> str:
        """
        Exports the contents of this container in an ini format. List are saved as comma separated strings.
            :returns: data representation in ini format. This is limited to one reference and text without comma's
        """
        export = ""

        for key in self.collection:
            # Make deepcopy, otherwise a saving will delete the header info, permanently disabling proper saving
            data = copy.deepcopy(self.collection[key])
            
            # If header is known use header, otherwise use identifier
            if data.header:
                export_key = data.header
                data.header = None
            else:
                export_key = key.identifier

            export += f"[{export_key}]\n"
            export += data.export(Format.ini)
            export += "\n"

        return export

    def _export_json(self) -> dict:
        """
        Exports the contents of this container in a json format
        """
        output = dict()

        for key in self.collection:
            # Make deepcopy, otherwise a saving will delete the header info, permanently disabling proper saving
            data = copy.deepcopy(self.collection[key])

            # If header is known use header, otherwise use identifier
            if data.header:
                export_key = data.header
                data.header = None
            else:
                export_key = key.identifier

            output[export_key] = data.export(Format.json)
        
        return output

class PostProcessorOld(PostProcessor):
    """
    Post-processes the data for use in Fluor. Builds data in a format expected by v0.8
    """
    def process(self) -> None:
        """
        Runs the post processor on the data
        """
        for key in self.collection:
            data = self.collection[key]
            
            # Do not remove header, necessary for proper exporting

            # Remove unused data
            if data.data_id:
                data.data_id = None

            # The method for multiple fluorophore names changed in the new version.
            # Easiest is not to take it along. Old version is deprecated anyway
            if data.names:
                data.names = None

            if data.categories:
                data.categories = None

            if data.extinction_coefficient:
                data.extinction_coefficient = None

            if data.quantum_yield:
                data.quantum_yield = None

            if data.cross_section:
                data.cross_section = None

            if data.brightness:
                data.brightness = None

            if data.brightness_bin:
                data.brightness_bin = None

            if data.url:
                data.url = None

            if data.references:
                data.references = None

            # Round all spectra data to max 1 decimal
            if data.absorption_wavelength and data.absorption_intensity:
                data.absorption_wavelength = [int(x) for x in data.absorption_wavelength]
                data.absorption_intensity = [round(float(x), ndigits=2) for x in data.absorption_intensity]

                if not data.excitation_wavelength or not data.excitation_intensity:
                    data.excitation_max = int(data.absorption_max)
                    data.excitation_wavelength = data.absorption_wavelength
                    data.excitation_intensity = data.absorption_intensity
                    data.absorption_max = None
                    data.absorption_wavelength = []
                    data.absorption_intensity = []

            if data.excitation_wavelength and data.excitation_intensity:
                data.excitation_wavelength = [int(x) for x in data.excitation_wavelength]
                data.excitation_intensity = [round(float(x), ndigits=2) for x in data.excitation_intensity]
                data.excitation_max = int(data.excitation_max)
                
            if data.two_photon_wavelength and data.two_photon_intensity:
                data.two_photon_intensity = []
                data.two_photon_wavelength = []
                data.two_photon_max = None
                
            if data.emission_wavelength and data.emission_intensity:
                data.emission_wavelength = [int(x) for x in data.emission_wavelength]
                data.emission_intensity = [round(float(x), ndigits=2) for x in data.emission_intensity]
                data.emission_max = int(data.emission_max)

            # The old version uses a shared wavelength list for excitation and emission, so add the correct padding.
            if data.excitation_wavelength and data.emission_wavelength:
                wave_min = min((data.excitation_wavelength[0], data.emission_wavelength[0]))
                wave_max = max((data.excitation_wavelength[-1], data.emission_wavelength[-1]))

                padding_left = data.excitation_wavelength[0] - wave_min
                padding_right = wave_max - data.excitation_wavelength[-1]

                temp = [0.0] * padding_left
                temp.extend(data.excitation_intensity)
                temp.extend([0.0] * padding_right)
                data.excitation_intensity = temp
        
                padding_left = data.emission_wavelength[0] - wave_min
                padding_right = wave_max - data.emission_wavelength[-1]

                temp = [0.0] * padding_left
                temp.extend(data.emission_intensity)
                temp.extend([0.0] * padding_right)
                data.emission_intensity = temp

                data.excitation_wavelength = range(wave_min, wave_max + 1, 1)
                data.emission_wavelength = data.excitation_wavelength
