# -*- coding: utf-8 -*-

## Fluor Tools Viewer ########################################################
# Author:     AJ Zwijnenburg
# Version:    v2.0
# Date:       2020-06-29
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
This module provides a framework for default modification of spectra sources.
The modifications are lists of lambda's that are structured per AbstractData
attribute and can be applied to an AbstractData object.

:class: Modifyer
Baseclass containing the overloadable modifyers. The baseclass applies the modification
if the data exists to the input AbstractData object

:class: BD
Modification class for BD data

:class: BioLegend
Modification class for BioLegend data

:class: Biotium
Modification class for Biotium data

:class: Chroma
Modification class for Chroma data

:class: FluoroFinder
Modification class for FluoroFinder data

:class: FPbase
Modification class for FPbase data

:class: ThermoFisher
Modification class for ThermoFisher data

"""

from __future__ import annotations

from . import Source
from .viewer.reader import Data as _Data  # To be able to use the reader.Data manipulation functions

import copy

class Modifyer:
    """
    A container for modifications of AbstractData attributes
    """
    def __init__(self):
        self.source: Source = Source.none

    def apply(self, data: AbstractData) -> AbstractData:
        """
        Applies the modifiers to the data (if the parameter is in the data). Exception safe
            :param data: data to modify
            :returns: modified data
        """
        temp = copy.deepcopy(data)

        if temp.data_id:
            temp = self.modify_data_id(temp)
        
        if temp.header:
            temp = self.modify_header(temp)

        if temp.enable:
            temp = self.modify_enable(temp)
        
        if temp.names:
            temp = self.modify_names(temp)
        
        if temp.categories:
            temp = self.modify_categories(temp)
        
        if temp.extinction_coefficient:
            temp = self.modify_extinction_coefficient(temp)
        
        if temp.quantum_yield:
            temp = self.modify_quantum_yield(temp)
        
        if temp.cross_section:
            temp = self.modify_cross_section(temp)

        if temp.brightness:
            temp = self.modify_brightness(temp)

        if temp.brightness_bin:
            temp = self.modify_brightness_bin(temp)
        
        if temp.url:
            temp = self.modify_url(temp)
        
        if temp.references:
            temp = self.modify_references(temp)
        
        if temp.absorption_max:
            temp = self.modify_absorption_max(temp)
        
        if temp.excitation_max:
            temp = self.modify_excitation_max(temp)
        
        if temp.emission_max:
            temp = self.modify_emission_max(temp)
        
        if temp.two_photon_max:
            temp = self.modify_two_photon_max(temp)

        if temp.absorption_wavelength and temp.absorption_intensity:
            temp = self.modify_absorption(temp)
        
        if temp.excitation_wavelength and temp.excitation_intensity:
            temp = self.modify_excitation(temp)
        
        if temp.emission_wavelength and temp.emission_intensity:
            temp = self.modify_emission(temp)
        
        if temp.two_photon_wavelength and temp.two_photon_intensity:
            temp = self.modify_two_photon(temp)
        
        return temp

    # Modification functions, overload for modifyer to work
    @staticmethod
    def modify_data_id(data: AbstractData) -> AbstractData:
        """
        Function that modified the data_id parameter of an AbstractData object
            :param data: data to modify
            :returns: modified data
        """
        return data

    @staticmethod
    def modify_header(data: AbstractData) -> AbstractData:
        """
        Function that modified the header parameter of an AbstractData object
            :param data: data to modify
            :returns: modified data
        """
        return data

    @staticmethod
    def modify_enable(data: AbstractData) -> AbstractData:
        """
        Function that modified the enable parameter of an AbstractData object
            :param data: data to modify
            :returns: modified data
        """
        return data

    @staticmethod
    def modify_names(data: AbstractData) -> AbstractData:
        """
        Function that modified the names parameter of an AbstractData object
            :param data: data to modify
            :returns: modified data
        """
        return data

    @staticmethod
    def modify_categories(data: AbstractData) -> AbstractData:
        """
        Function that modified the categories parameter of an AbstractData object
            :param data: data to modify
            :returns: modified data
        """
        return data

    @staticmethod
    def modify_extinction_coefficient(data: AbstractData) -> AbstractData:
        """
        Function that modified the extinction_coefficient parameter of an AbstractData object
            :param data: data to modify
            :returns: modified data
        """
        return data

    @staticmethod
    def modify_quantum_yield(data: AbstractData) -> AbstractData:
        """
        Function that modified the quantum_yield parameter of an AbstractData object
            :param data: data to modify
            :returns: modified data
        """
        return data
    
    @staticmethod
    def modify_cross_section(data: AbstractData) -> AbstractData:
        """
        Function that modified the cross_section parameter of an AbstractData object
            :param data: data to modify
            :returns: modified data
        """
        return data
        
    @staticmethod
    def modify_brightness(data: AbstractData) -> AbstractData:
        """
        Function that modified the brightness parameter of an AbstractData object
            :param data: data to modify
            :returns: modified data
        """
        return data    

    @staticmethod
    def modify_brightness_bin(data: AbstractData) -> AbstractData:
        """
        Function that modified the brightness_bin parameter of an AbstractData object
            :param data: data to modify
            :returns: modified data
        """
        return data

    @staticmethod
    def modify_url(data: AbstractData) -> AbstractData:
        """
        Function that modified the url parameter of an AbstractData object
            :param data: data to modify
            :returns: modified data
        """
        return data

    @staticmethod
    def modify_references(data: AbstractData) -> AbstractData:
        """
        Function that modified the references parameter of an AbstractData object
            :param data: data to modify
            :returns: modified data
        """
        return data

    @staticmethod
    def modify_absorption_max(data: AbstractData) -> AbstractData:
        """
        Function that modified the absorption_max parameter of an AbstractData object
            :param data: data to modify
            :returns: modified data
        """
        return data

    @staticmethod
    def modify_excitation_max(data: AbstractData) -> AbstractData:
        """
        Function that modified the excitation_max parameter of an AbstractData object
            :param data: data to modify
            :returns: modified data
        """
        return data

    @staticmethod
    def modify_emission_max(data: AbstractData) -> AbstractData:
        """
        Function that modified the emission_max parameter of an AbstractData object
            :param data: data to modify
            :returns: modified data
        """
        return data

    @staticmethod
    def modify_two_photon_max(data: AbstractData) -> AbstractData:
        """
        Function that modified the two_photon_max parameter of an AbstractData object
            :param data: data to modify
            :returns: modified data
        """
        return data

    @staticmethod
    def modify_absorption(data: AbstractData) -> AbstractData:
        """
        Function that modified the absorption_wavelength and absorption_intensity parameter of an AbstractData object
            :param data: data to modify
            :returns: modified data
        """
        return data

    @staticmethod
    def modify_excitation(data: AbstractData) -> AbstractData:
        """
        Function that modified the excitation_wavelength and excitation_intensity parameter of an AbstractData object
            :param data: data to modify
            :returns: modified data
        """
        return data

    @staticmethod
    def modify_emission(data: AbstractData) -> AbstractData:
        """
        Function that modified the emission_wavelength and emission_intensity parameter of an AbstractData object
            :param data: data to modify
            :returns: modified data
        """
        return data

    @staticmethod
    def modify_two_photon(data: AbstractData) -> AbstractData:
        """
        Function that modified the two_photon_wavelength and two_photon_intensity parameter of an AbstractData object
            :param data: data to modify
            :returns: modified data
        """
        return data

class BD(Modifyer):
    """
    Modifyer for BD data
    It corrects:
        wavelength stepsize
    """
    def __init__(self):
        self.source = Source.bd

    @staticmethod
    def modify_excitation(data: AbstractData) -> AbstractData:
        data.excitation_wavelength, data.excitation_intensity = _Data.interpolate(data.excitation_wavelength, data.excitation_intensity)
        return data

    @staticmethod
    def modify_emission(data: AbstractData) -> AbstractData:
        data.emission_wavelength, data.emission_intensity = _Data.interpolate(data.emission_wavelength, data.emission_intensity)
        return data

class BioLegend(Modifyer):
    """
    Modifyer for BioLegend data
    It corrects:
        wavelength stepsize
    """
    def __init__(self):
        self.source = Source.biolegend

    @staticmethod
    def modify_excitation(data: AbstractData) -> AbstractData:
        data.excitation_wavelength, data.excitation_intensity = _Data.interpolate(data.excitation_wavelength, data.excitation_intensity)
        return data

    @staticmethod
    def modify_emission(data: AbstractData) -> AbstractData:
        data.emission_wavelength, data.emission_intensity = _Data.interpolate(data.emission_wavelength, data.emission_intensity)
        return data

class Biotium(Modifyer):
    """
    Modifyer for Biotium data
    It corrects:
        wavelength intensity from 0-1 scale to 0-100 scale
    """
    def __init__(self):
        self.source = Source.biotium

    @staticmethod
    def modify_absorption(data: AbstractData) -> AbstractData:
        data.absorption_intensity = [x * 100 for x in data.absorption_intensity]
        return data

    @staticmethod
    def modify_emission(data: AbstractData) -> AbstractData:
        data.emission_intensity = [x * 100 for x in data.emission_intensity]
        return data

class Chroma(Modifyer):
    """
    Modifyer for Chroma data
    It corrects:
        Nothing to correct
    """
    def __init__(self):
        self.source = Source.chroma

class FluoroFinder(Modifyer):
    """
    Modifyer for FluoroFinder data
    It corrects:
        removes padded 0 intensities
    """
    def __init__(self):
        self.source = Source.fluorofinder

    @staticmethod
    def modify_excitation(data: AbstractData) -> AbstractData:
        data.excitation_wavelength, data.excitation_intensity = _Data.strip_exact(data.excitation_wavelength, data.excitation_intensity, baseline=0.0)
        return data

    @staticmethod
    def modify_emission(data: AbstractData) -> AbstractData:
        data.emission_wavelength, data.emission_intensity = _Data.strip_exact(data.emission_wavelength, data.emission_intensity, baseline=0.0)
        return data

class FPbase(Modifyer):
    """
    Modifyer for FPbase data
    It corrects:
        uppercases all reference author initials
        wavelength intensity from 0-1 scale to 0-100 scale
    """
    def __init__(self):
        self.source = Source.fpbase

    @staticmethod
    def modify_references(data: AbstractData) -> AbstractData:
        for reference in data.references:
            for i, author in enumerate(reference.authors):
                if author == "et al":
                    continue

                # Some specific error to correct
                if author == "Ai H-":
                    reference.authors[i] = "Ai H"
                    continue

                if author == "Orm  M":
                    reference.authors[i] = "Ormö M"
                    continue

                # Capitalize all initials
                parts = author.split(" ")

                for j, part in enumerate(reversed(parts)):
                    if j == 0:
                        # last part must be initials
                        parts[-1] = part.upper()

                    elif j == 1:
                        # part before initials must be family name
                        pass

                    elif j >= 2:
                        # Connecting words in some names
                        pass

                reference.authors[i] = " ".join(parts)

        return data

    @staticmethod
    def modify_absorption(data: AbstractData) -> AbstractData:
        data.absorption_intensity = [x * 100 for x in data.absorption_intensity]
        return data

    @staticmethod
    def modify_excitation(data: AbstractData) -> AbstractData:
        data.excitation_intensity = [x * 100 for x in data.excitation_intensity]
        return data

    @staticmethod
    def modify_emission(data: AbstractData) -> AbstractData:
        data.emission_intensity = [x * 100 for x in data.emission_intensity]
        return data

    @staticmethod
    def modify_two_photon(data: AbstractData) -> AbstractData:
        data.two_photon_intensity = [x * 100 for x in data.two_photon_intensity]
        return data

class ThermoFisher(Modifyer):
    """
    Modifyer for ThermoFisher data
    It corrects:
        nothing to correct
    """
    def __init__(self):
        self.source = Source.thermofisher
