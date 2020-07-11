# -*- coding: utf-8 -*-

## Fluor Tools Viewer ########################################################
# Author:     AJ Zwijnenburg
# Version:    v2.0
# Date:       2020-06-28
# Copyright:  Copyright (C) 2020 - AJ Zwijnenburg
# License:    GPL v3
##############################################################################

## Copyright notice ##########################################################
# Copyright 2020 AJ Zwijnenburg
#
# This file is part of the Fluor viewer tools
#
# Fluor viewer tool is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Fluor viewer tool is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Fluor viewer tool. If not, see <https://www.gnu.org/licenses/>.
##############################################################################

"""
Reader and parser for ini and json stored fluorophore data
These classes differ from the general variants as these implement additional
properties for further manipulation and presenting of the data

:class Reference:
    A type alias to AbstractReference

:class: Data
    Fluorophore data container with additional modification functions

:class: Reader
    Parser for fluorophore data stored

:class: _DataOld
    Fluorophore data container for the reading of the 'old' fluorophore ini format
    Obviously deprecated. Re-defined from tools.reader as the viewer version needs  
    the data manipulation tools to be defined.

:class: ReaderOld
    Parser for 'old' format ini stored fluorophore data. Re-defined from tools.reader 
    as the viewer version needs the data manipulation tools to be defined.
"""

from __future__ import annotations
from typing import List, Dict, Union, Tuple, Set

from .. import json, Format, Source
from ..abstract import AbstractData, AbstractID, AbstractCollection, AbstractReference
from ..mapper import Identifier, Header

import os.path
import copy

import math
from scipy.signal import savgol_filter

# Type alias
Reference = AbstractReference

class Data(AbstractData):
    """
    Fluorophore data container with additional function for modification of the data
    """
    def construct_header(self, header_format: Format) -> None:
        """
        Constructs a header for use with the specified format
            :param header_format: the format to be used (eg ini: [HEAD:ER] or json: "HEAD:ER")
        """
        if header_format == Format.ini:
            self._construct_header_ini()
        elif header_format == Format.json:
            self._construct_header_json()
        else:
            raise ValueError("unknown header_format")

    def _construct_header_ini(self) -> None:
        """
        Generates a header from the names parameter. Assumes that everything within brackets is a state.
        If no names are defined defaults to data_id.identifier
        """
        if self.names:
            data = self.names[0]
        else:
            data = self.data_id.identifier

        # Remove special characters and capitilize everything
        name_id = ""
        for letter in data:
            if letter in "aA":
                name_id += "A"
            elif letter in "bB":
                name_id += "B"
            elif letter in "cC":
                name_id += "C"
            elif letter in "dD":
                name_id += "D"
            elif letter in "eE":
                name_id += "E"
            elif letter in "fF":
                name_id += "F"
            elif letter in "gG":
                name_id += "G"
            elif letter in "hH":
                name_id += "H"
            elif letter in "iI":
                name_id += "I"
            elif letter in "jJ":
                name_id += "J"
            elif letter in "kK":
                name_id += "K"
            elif letter in "lL":
                name_id += "L"
            elif letter in "mM":
                name_id += "M"
            elif letter in "nN":
                name_id += "N"
            elif letter in "oO":
                name_id += "O"
            elif letter in "pP":
                name_id += "P"
            elif letter in "qQ":
                name_id += "Q"
            elif letter in "rR":
                name_id += "R"
            elif letter in "sS":
                name_id += "S"
            elif letter in "tT":
                name_id += "T"
            elif letter in "uU":
                name_id += "U"
            elif letter in "vV":
                name_id += "V"
            elif letter in "wW":
                name_id += "W"
            elif letter in "xX":
                name_id += "X"
            elif letter in "yY":
                name_id += "Y"
            elif letter in "zZ":
                name_id += "Z"
            elif letter in "0123456789":
                name_id += letter
            elif letter in "(,":
                name_id += ":"
            else:
                pass

        self.header = name_id

    def _construct_header_json(self) -> None:
        """
        Generates a header from the names parameter. Assumes that everything within brackets is a state.
        If no names are defined defaults to data_id.identifier
        """
        if self.names:
            data = self.names[0]
        else:
            data = self.data_id.identifier

        # Remove special characters and capitilize everything
        name_id = ""
        for letter in data:
            if letter in "aA":
                name_id += "A"
            elif letter in "bB":
                name_id += "B"
            elif letter in "cC":
                name_id += "C"
            elif letter in "dD":
                name_id += "D"
            elif letter in "eE":
                name_id += "E"
            elif letter in "fF":
                name_id += "F"
            elif letter in "gG":
                name_id += "G"
            elif letter in "hH":
                name_id += "H"
            elif letter in "iI":
                name_id += "I"
            elif letter in "jJ":
                name_id += "J"
            elif letter in "kK":
                name_id += "K"
            elif letter in "lL":
                name_id += "L"
            elif letter in "mM":
                name_id += "M"
            elif letter in "nN":
                name_id += "N"
            elif letter in "oO":
                name_id += "O"
            elif letter in "pP":
                name_id += "P"
            elif letter in "qQ":
                name_id += "Q"
            elif letter in "rR":
                name_id += "R"
            elif letter in "sS":
                name_id += "S"
            elif letter in "tT":
                name_id += "T"
            elif letter in "uU":
                name_id += "U"
            elif letter in "vV":
                name_id += "V"
            elif letter in "wW":
                name_id += "W"
            elif letter in "xX":
                name_id += "X"
            elif letter in "yY":
                name_id += "Y"
            elif letter in "zZ":
                name_id += "Z"
            elif letter in "0123456789":
                name_id += letter
            elif letter in "(,":
                name_id += ":"
            else:
                pass

        self.header = name_id

    @staticmethod
    def calculate_brightness(extinction_coefficient: Union[None, int], quantum_yield: Union[None, float]) -> float:
        """
        Calculate the brightness value from the extinction coefficient and quantum yield
            :param extinction_coefficient: the extinction coefficient (/M/cm)
            :param quantum_yield: the quantum yield (unitless)
            :returns: brightness or None if it cannot calculate the value
        """
        if extinction_coefficient and quantum_yield:
            return ( extinction_coefficient / 1000 ) * quantum_yield
        else:
            return None
            
    @staticmethod
    def parse_list(data: List[Union[int, str]]) -> List[float]:
        """
        Tries to parse a list of strings into a list of floats
            :param data[list(str)]: input list to convert, if the list is empty returns the empty list
            :returns: a list of integers or floats
            :raises: ValueError, upon unconvertable string
        """
        if not data:
            return data

        for i, string in enumerate(data):
            try:
                data[i] = float(string)
            except ValueError:
                raise ValueError("Input list entree: {} is unconvertable to float".format(string))

        return data

    @staticmethod
    def interpolate(wavelength: List[float], intensity: List[float]) -> Tuple[List[float], List[float]]:
        """
        Converts the input wavelength to a stepsize of 1, starting at real value
            :param wavelength[list(float)]: a list of wavelenghts, 
            :param intensity[list(float)]: a list of intensities, combined with input_wavelength
            :returns: tuple(wavelength[list(float)], intensity[list(float)])
        """
        output_w = []
        output_i = []

        index_current = 0   # current iteration index
        index_after = 0     # first index after value_next
        
        # manual starting value
        value_next = math.ceil(wavelength[index_after])  # next value as to be interpolated

        while value_next <= wavelength[-1]:
            # next value is rational?
            if wavelength[index_current] == value_next:
                output_w.append(wavelength[index_current])
                output_i.append(intensity[index_current])
                
                value_next += 1

            else:
                # Find indexes in between which the next value is passed (or equal)
                #for i, value in enumerate(wavelength):
                for i in range(index_current, len(wavelength), 1):
                    if wavelength[i] >= value_next:
                        index_after = i
                        break
                    else:
                        # This increases preciseness upon index distances <1
                        index_current = i
                
                # Maybe that next value index is rational
                if wavelength[index_after] == value_next:
                    output_w.append(wavelength[index_after])
                    output_i.append(intensity[index_after])
                    value_next += 1.0
                
                # Or not, in that case we need to calculate interpolation(s)
                else:
                    while value_next <= wavelength[index_after]:
                        fraction = (value_next - wavelength[index_current]) / (wavelength[index_after] - wavelength[index_current])
                        diff = intensity[index_after] - intensity[index_current]
                        interpolation = intensity[index_current] + (diff * fraction)

                        output_w.append(value_next)
                        output_i.append(interpolation)

                        value_next += 1.0

        return (output_w, output_i)

    @staticmethod
    def round(input_list: List[float], ndigits: int=1) -> List[float]:
        """
        Rounds all values of the input list to a specific digit. Any ndigits >0 will floatify the container values.
            :param input[list(int/float)]: list to round
            :param ndigits[int]: (optional) number of rounding digits
            :returns[list(int/float)]: rounded list
        """
        output = []
        for item in input_list:
            output.append(round(item, ndigits=ndigits))

        return output

    @staticmethod
    def normalize(input_list: List[float], max_value: float=None, min_value: float=None) -> List[float]:
        """
        Fits the values in input between max and min
            :param input_list[list(int/float)]: input list
            :param max_value[int]: maximum value, None normalizes to 100, but keeps relative distribution of max_value <-> 100 intact
            :param min_value[int]: minimum value, None normalizes from 0, but keeps relative distribution of min_value <-> 0 intact
            :returns[list(int/float)]: the normalized input list
        """

        input_min = input_list[0]
        input_max = input_list[0]

        # Get min and max value
        for value in input_list:
            if value < input_min:
                input_min = value
            
            elif value > input_max:
                input_max = value

        # Get start value
        if min_value is None:
            start = 0
            norm_start = 0
        else:
            start = input_min
            norm_start = min_value

        # Get original width
        if max_value is None and min_value is None:
            width = 100 - 0
            norm_width = 100 - 0 
        elif max_value is None:
            width = 100 - input_min
            norm_width = 100 - min_value
        elif min_value is None:
            width = input_max - 0
            norm_width = max_value - 0
        else:
            width = input_max - input_min
            norm_width = max_value - min_value

        output = []
        for value in input_list:
            norm = value - start 
            norm /= width
            norm *= norm_width
            norm += norm_start

            output.append(norm)

        return output

    @staticmethod
    def cutoff_min(input_list: List[float], min_value: Union[float]) -> List[float]:
        """
        Turns any value below the min_value into the min_value
            :param input_list: the list to adjust
            :param min_value: the minimum value 
            :returns: copy of the input_list with cutoff applied
        """
        output = []

        for value in input_list:
            if value < min_value:
                output.append(min_value)
            else:
                output.append(value)

        return output

    @staticmethod
    def cutoff_max(input_list: List[float], max_value: Union[float]) -> List[float]:
        """
        Turns any value above the max_value into the max_value
            :param input_list: the list to adjust
            :param max_value: the minimum value 
            :returns: copy of the input_list with cutoff applied
        """
        output = []

        for value in input_list:
            if value > max_value:
                output.append(max_value)
            else:
                output.append(value)

        return output

    @staticmethod
    def strip(wavelength: List[float], intensity: List[float], strip_value: float=0.0) -> Tuple[List[float], List[float]]:
        """
        Strips intensity value below or equal to strip_value. 
            :param wavelength: wavelength values
            :param intensity: equivalent intensity values
            :param strip_value: strip threshold in wavelength
            :returns[tuple(wavelength list, intensity list)]: stripped list
        """
        index_start = 0

        for i, value in enumerate(intensity):
            if value <= strip_value:
                index_start = (i + 1)
            else:
                break
        
        index_end = len(intensity)
        for i, value in enumerate(reversed(intensity)):
            if value <= strip_value:
                index_end = index_end - (i + 1)
            else:
                break
        
        output_w = wavelength[index_start:index_end]
        output_i = intensity[index_start:index_end]
        
        return (output_w, output_i)

    @staticmethod
    def get_max(intensity: List[float]) -> float:
        """
        Finds the highest value in intensity
            :param intensity[list(double)]: intensity
            :returns[double]: the maximum value
        """
        return max(intensity)

    @staticmethod
    def get_min(intensity: List[float]) -> float:
        """
        Finds all wavelenghts with the highest intensity value
            :param intensity[list(double)]: intensity data
            :returns [double/int]: the minimum intensity
        """
        return min(intensity)

    @staticmethod
    def get_max_wavelengths(wavelength: List[float], intensity: List[float]) -> List[float]:
        """
        Finds all wavelenghts with the highest intensity value
            :param intensity[list(double)]: wavelength data
            :param intensity[list(double)]: intensity data
            :returns [list(double)]: the maximum wavelengths
        """
        try:
            max_value = max(intensity)
        except:
            return [0.0]

        max_wavelengths = []
        for i, item in enumerate(intensity):
            if item == max_value:
                max_wavelengths.append(wavelength[i])

        return max_wavelengths
    
    @staticmethod
    def get_min_wavelengths(wavelength: List[float], intensity: List[float]) -> List[float]:
        """
        Finds all wavelenghts with the lowest intensity value
            :param intensity[list(double)]: wavelength data
            :param intensity[list(double)]: intensity data
            :returns [list(double)]: the minimum wavelengths
        """
        try:
            min_value = min(intensity)
        except:
            return [0.0]

        min_wavelengths = []
        for i, item in enumerate(intensity):
            if item == min_value:
                min_wavelengths.append(wavelength[i])

        return min_wavelengths

    @staticmethod
    def get_peaks(wavelength: List[float], intensity: List[float]) -> List[float]:
        """
        Builds a list of wavelengths at which the intensity is >= i-1 and > i+1. i can be repeated, then returns the last wavelength of i
            :returns [list[float(wavelengths)]]
        """
        indexes = []

        prev_value = 0
        for i, value in enumerate(intensity):
            # Cannot make the comparison in the first and last value
            if i == 0 or i == len(intensity) - 1:
                prev_value = value
                continue
            
            if value == intensity[i-1]:
                if prev_value < value and intensity[i+1] < value:
                    indexes.append(i)
            else:
                if intensity[i-1] < value and intensity[i+1] < value:
                    indexes.append(i)

            if value != intensity[i+1]:
                prev_value = value
        
        values = []
        for i in indexes:
            values.append(wavelength[i])

        return values
    
    @staticmethod
    def get_dales(wavelength: List[float], intensity: List[float]) -> List[float]:
        """
        Builds a list of wavelengths at which the intensity is <= i-1 and < i+1. i can be repeated, then returns the last wavelength of i
            :returns [list[floats(wavelengths)]]
        """
        indexes = []

        prev_value = 0
        for i, value in enumerate(intensity):
            # Cannot make the comparison in the first and last value
            if i == 0 or i == len(intensity) - 1:
                continue
            
            if value == intensity[i-1]:
                if prev_value > value and intensity[i+1] > value:
                    indexes.append(i)
            else:
                if intensity[i-1] > value and intensity[i+1] > value:
                    indexes.append(i)
            
            if value != intensity[i+1]:
                prev_value = value
        
        values = []
        for i in indexes:
            values.append(wavelength[i])

        return values

    @staticmethod
    def strip_return(wavelength: List[float], intensity: List[float]) -> Tuple[List[float], List[float]]:
        """
        Forces the wavelength to be ordered from low-to-high by removing entrees of lower wavelength
            :param wavelength[list(double)]: wavelength data in nanometers
            :param intensity[list(double)]: intensity data in percentage
            :returns[(list(double), list(double))]: tuple of the stripped wavelength and intensity
        """
        output_wavelength = []
        output_intensity = []

        prev_point = wavelength[0] - 1.0

        for i in range(0, len(wavelength)):
            if wavelength[i] > prev_point:
                output_wavelength.append(wavelength[i])
                output_intensity.append(intensity[i])
                prev_point = wavelength[i]

        return (output_wavelength, output_intensity)

    @staticmethod
    def strip_exact(wavelength: List[float], intensity: List[float], baseline: float=0.0) -> Tuple[List[float], List[float]]:
        """
        Removes the baseline padding of the data. Only removes the baseline value on the start and end of the wavelength
            :param wavelength [list(float)]: wavelength in nanometers
            :param intensity [list(float)]: intensity in percentage
            :param baseline [float]: baseline value
        """
        # Find baseline cutoffs
        index_left = -1
        for i in range(0, len(intensity)):
            if intensity[i] == baseline:
                index_left = i
            else:
                break

        index_right = -1
        for i in reversed(list(range(0, len(intensity)))):
            if intensity[i] == baseline:
                index_right = i
            else:
                break

        # Correct the index cutoffs
        if index_left < 0:
            index_left = 0
        else:
            index_left += 1

        if index_right < 0:
            index_right = len(wavelength)

        # Cutoff the input lists
        output_wavelength = wavelength[index_left:index_right]
        output_intensity = intensity[index_left:index_right]

        return (output_wavelength, output_intensity)

    @staticmethod
    def multiply_curve(intensity: List[float], factor: float=100.0) -> List[float]:
        """
        Multiply each individual value in intensity by the given factor
            :param intensity[list(double)]: intensity values
            :param factor[double]: multiplication factor
            :returns [list(double)]: multiplied intensity
        """
        for i in range(0, len(intensity)):
            intensity[i] = intensity[i] * factor

        return intensity

    @staticmethod
    def smooth_intensity_savgol(intensity: List[float], width: int, degree: int=0) -> List[float]:
        """
        Smooths the intensity curve using Scipy's Savitzky-Golay smoothing
        """
        window = 2 * width + 1
        filtered = savgol_filter(intensity, window, degree)

        return filtered.tolist()

    @staticmethod
    def remove_gaps(wavelength: List[float], intensity: List[float], gap: float=0.0) -> Tuple[List[float], List[float]]:
        """
        Detects gaps in the intensity and removes those values from the return wavelength, intensity
            :param wavelength[list(double)]: wavelength corresponding to the intensity param
            :param intensity[list(double)]: intensity corresponding to the wavelength param
            :param gap[double]: any value lower-or-equal then this parameter is removed, but NOT on the edges of the wavelength, intensity line
            :returns (wavelength, intensity): gap-removed curve data
            :raises ValueError: if no curve is detectable
        """
        # to ignore lower-equal then gap on the left and right sides of the curve we have to detect the 'proper' start of the curves
        curve_start_index = len(wavelength)
        curve_end_index = 0

        for i, value in enumerate(intensity):
            if value > gap:
                curve_start_index = i
                break

        for i, value in enumerate(reversed(intensity)):
            if value > gap:
                curve_end_index = len(wavelength) - i
                break
        
        # check if valid
        if curve_start_index >= curve_end_index:
            raise ValueError("DataAbstractReader.remove_gaps: invalid curve")

        output_w = wavelength[:curve_start_index]
        output_i = intensity[:curve_start_index]

        # Remove gaps
        for index in range(curve_start_index, curve_end_index, 1):
            if intensity[index] <= gap:
                pass
            else:
                output_w.append(wavelength[index])
                output_i.append(intensity[index])

        output_w += wavelength[curve_end_index:]
        output_i += intensity[curve_end_index:]

        return (output_w, output_i)

class Reader(AbstractCollection):
    """
    A class providing an interface for reading the stored fluorophore data
        :param path: path to the data files to read, if None no files are read, use load() instead.
    """
    def __init__(self, path: Union[None, str]=None) -> None:
        super().__init__()
        
        if path is not None:
            self.load(path)

    def _load_ini(self, path: str) -> None:
        """
        Loads and parses an ini formatted file
            :param path: path to the file
        """
        with open(path, mode="r", encoding="utf-8", newline=None) as file:
            data = file.readlines()

        # Grap single fluorophore and forward those to their respective parsers
        fluorophore_data = []
        for line in data:
            line = line.rstrip("\n")
            if not line:
                continue
            elif line[0] == "[":
                if fluorophore_data:
                    fluorophore = Data(AbstractID(""))
                    fluorophore.load(fluorophore_data, Format.ini)
                    
                    if not fluorophore.enable:
                        fluorophore.enable = True
                    
                    self.collection[fluorophore.data_id.identifier] = fluorophore
                fluorophore_data = []
                fluorophore_data.append(line)
            else:
                fluorophore_data.append(line)
            
    def _load_json(self, path: str) -> None:
        """
        Loads and parses a json formatted file
            :param path: path to the file
        """
        with open(path, mode="r", encoding="utf-8") as file:
            data = file.read()
        
        data = json.loads(data, encoding="utf-8")
        for key in data:
            fluorophore = Data(AbstractID(Source.none, key)) # load in a placeholder source, gets properly set during Data.load().
            fluorophore.load(data[key], Format.json)

            if fluorophore.enable is None:
                fluorophore.enable = True

            self.collection[fluorophore.data_id.identifier] = fluorophore

    def __repr__(self) -> str:
        return f"(Reader:{len(self.collection)})"

class _DataOld(Data):
    """
    Fluorophore data container for old data
    """
    def _load_ini(self, data: List[str]) -> None:
        """
        Imports a ini datafile
            :param data: data of a single fluorophore, split into lines without newline characters
        """
        # A reference might have missing data attributes, so construct, load if applicable, and check if valid to see if it is in use
        temp_reference = AbstractReference()
        for line in data:
            if not line:
                continue
            if line[:1] == "[":
                self.data_id = AbstractID(line[1:-1])
                self.header = line[1:-1]

            elif line[:9] == "database=":
                self.source = line[9:]
            elif line[:6] == "names=":
                self.names = line[6:].split(",")

            elif line[:23] == "extinction_coefficient=":
                self.extinction_coefficient = int(line[23:])
            elif line[:14] == "quantum_yield=":
                self.quantum_yield = float(line[14:])
            elif line[:10] == "intensity=":
                self.brightness = float(line[10:])
            elif line[:14] == "intensity_bin=":
                self.brightness_bin = int(line[14:])
    
            elif line[:10] == "reference=":
                reference = line[10:]

                if reference[:4] == "http":
                    ref = Reference()
                    ref.url = reference
                    self.references.append(ref)
                else:
                    ref = Reference()
                    ref.title = reference
                    self.references.append(ref)

            elif line[:22] == "absorption_wavelength=":
                self.absorption_wavelength = [float(x) for x in line[22:].split(",")]
            elif line[:21] == "absorption_intensity=":
                self.absorption_intensity = [float(x) for x in line[21:].split(",")]
            elif line[:22] == "excitation_wavelength=":
                self.excitation_wavelength = [float(x) for x in line[22:].split(",")]
            elif line[:21] == "excitation_intensity=":
                self.excitation_intensity = [float(x) for x in line[21:].split(",")]
            elif line[:20] == "emission_wavelength=":
                self.emission_wavelength = [float(x) for x in line[20:].split(",")]
            elif line[:19] == "emission_intensity=":
                self.emission_intensity = [float(x) for x in line[19:].split(",")]
            elif line[:22] == "two_photon_wavelength=":
                self.two_photon_wavelength = [float(x) for x in line[22:].split(",")]
            elif line[:21] == "two_photon_intensity=":
                self.two_photon_intensity = [float(x) for x in line[21:].split(",")]

        if temp_reference:
            self.references.append(temp_reference)

    def _load_json(self, data: Dict) -> None:
        """
        Import a json dictionary
            :param data: the json data
        """
        raise NotImplementedError("the old data type is always stored in ini format")

class ReaderOld(AbstractCollection):
    """
    A class providing an interface for reading the outputs generated by the old (v1) analysis
        :param path: path to the data files to read, if 'None' no files are read, use load() instead.
    """
    def __init__(self, path: Union[None, str]=None) -> None:
        super().__init__()
        
        if path is not None:
            self.load(path)

    def _load_ini(self, path: str) -> None:
        """
        Loads and parses an ini formatted file
            :param path: path to the file
        """
        with open(path, mode="r", encoding="utf-8", newline=None) as file:
            data = file.readlines()

        # Grap single fluorophore and forward those to their respective parsers
        fluorophore_data = []
        for line in data:
            line = line.rstrip("\n")
            if not line:
                continue
            elif line[0] == "[":
                if fluorophore_data:
                    # ID's are not stored in the old format, so make a placeholder.
                    fluorophore = _DataOld(Source.none, AbstractID("")) 
                    fluorophore.load(fluorophore_data, Format.ini)
                    self.collection[fluorophore.header] = fluorophore
                fluorophore_data = []
                fluorophore_data.append(line)
            else:
                fluorophore_data.append(line)
            
    def _load_json(self, path: str) -> None:
        """
        Loads and parses a json formatted file
            :param path: path to the file
        """
        raise NotImplementedError("The old data type is always stored as ini format")

    def __repr__(self) -> str:
        return f"(ReaderOld:{len(self.collection)})"

class MappedReader:
    """
    Provides a reader-like class interface for identifier mapped (see mapper.py) data.
        :param path_map: path to the identifier mapped json file (Source_map.json)
    """
    def __init__(self, path_map: str=None):
        self.collection: Dict[Identifier, Data] = dict()
        self.headers: Dict[str, Header] = dict()

        # for iteration
        self.iter_keys: List[Identifier] = []
        self.iter_index: int = 0

        if path_map:
            self.load_map(path_map)

    def valid(self, print_invalid: bool=True) -> bool:
        """
        Checks the validity of the dataset. Effectively iterates through the collection and headers to find missing data
            :param print_invalid: whether to print the invalid data
        """
        missing_data: List[Identifier] = []
        missing_header: List[Identifier] = []

        lookup_identifier: Set[Identifier] = set()

        for header in self.headers:
            for identifier in self.headers[header].identifiers:
                lookup_identifier.add(identifier)
                if identifier not in self.collection.keys():
                    missing_data.append(identifier)
        
        for identifier in list(self.collection.keys()):
            if identifier not in lookup_identifier:
                missing_header.append(identifier)

        if not missing_data and not missing_header:
            return True

        if print_invalid:
            text = ""
            if missing_data:
                text += "Identifier mapped, no spectra data:\n"
                for data in missing_data:
                    text += f"  {repr(data)}\n"
            
            if missing_header:
                text += "Spectra data, no mapped identifier:\n"
                for data in missing_header:
                    text += f"  {repr(data)}\n"

            print(text)
  
        return False

    def set_source(self, header: str, identifier: Identifier) -> None:
        """
        Sets the Headers source
            :param header: the Header's header defining whos source is to be set
            :param identifier: the identifier to set the source to, has to be in the identifiers list
        """
        found = False
        for item in self.headers[header].identifiers:
            if item == identifier:
                found = True
                break
        
        if not found:
            raise ValueError("identifier is not part of the header, so cannot be set as source")

        self.headers[header].source = identifier

    def load_map(self, path: str) -> None:
        """
        Loads the map into self.headers. Exception safe, state only changed upon succesful loading.
            :param path: path to the source_map file
            :raises ValueError: if file loading failes
        """
        if not os.path.isfile(path):
            raise ValueError("file does not exist")

        _, ex = os.path.splitext(path)

        if ex != ".json":
            raise ValueError("can only load file with json format")

        with open(path, "r") as file:
            data = json.loads(file.read())

        # For exception safety, swap after parsing
        temp_headers: Dict[str, Header] = dict()

        # Note, invalid headers are loaded into the self.headers to make sure that all Identifier linkage is correct (see self.valid())
        # Ignore, invalid later in the GUI during ListView model building.
        for item in data:
            header = Header(item)
            
            try:
                header.load_json(data[item])
            except KeyError as error:
                raise ValueError(f"unparseable source map '{item}', are you sure you are loading a source map") from error

            temp_headers[header.header] = header

        self.headers = temp_headers

    def load_data(self, path: str) -> None:
        """
        Loads the spectral data into self.collection. Exception safe.
        Use load_source_data to load source data!
            :param path: path to the spectrum data to be loaded
            :raises ValueError: if the spectra data source is none or source
        """
        temp_reader = Reader(path)

        temp_collection: Dict[Identifier, Data] = dict()

        for item in temp_reader:
            if item.data_id.source == Source.none or item.data_id.source == Source.source:
                raise ValueError("source must not be Source.none or Source.source")

            identifier = Identifier(item.data_id.source, item.data_id.identifier)
            temp_collection[identifier] = item

        self.collection.update(temp_collection)

    def load_modifyer(self, modifyer: Modifyer) -> None:
        """
        Applies the modifyer to the loaded(!) data based on the Modifyer.source
        Make sure the first load all data, then apply the modifyer
            :param modifyer: the modifyer to apply to the collection
        """
        for identifier in self.collection:
            if identifier.source == modifyer.source:
                self.collection[identifier] = modifyer.apply(self.collection[identifier])

    def load_source_data(self, path: str, warnings: bool=True) -> None:
        """
        Loads the spectra data of the header.source exported data. It does so by adding a 
        special Identifyer referring to Source.source and the header into the datasets.
        Error checking works best if all data is loaded before source_data. Not exception safe.
            :param path: path to the spectrum data to be loaded
            :param warnings: whether to print warnings for potential header mismatches
            :raises KeyError: if header data cannot be found (did you load the map?)
        """
        temp_reader = Reader(path)

        for item in temp_reader:
            # -> only one Source.source / header allowed, so Identifier(Source.source, header.header)
            
            # I need to link this data to the mapped header. There are two ways:
            # If the data.header is stored I can use that. Otherwise I need to search for the identifier.
            # As only the identifier is stored I need to find the header first

            raw_identifier = Identifier(item.data_id.source, item.data_id.identifier)

            try:
                header = self.headers[item.header]
            except KeyError:
                # header is not found or missing, so use a iterative strategy to find the header
                header = None
                for header_key in self.headers:
                    for identifier in self.headers[header_key].identifiers:
                        if identifier == raw_identifier:
                            header = self.headers[header_key]
                            break

                if not header:
                    raise KeyError(f"header corresponding to '{repr(item.data_id)}' cannot be found")

            # header is detected, check the header information
            
            if not header.source:
                if warnings:
                    print(f"source data contains spectrum pointing to a header without a specified source '{repr(item.data_id)}' - forcing source")
                header.source = raw_identifier
            elif header.source != raw_identifier:
                if warnings:
                    print(f"header source does not correspond to the data source'{repr(item.data_id)}' - forcing source")
                header.source = raw_identifier

            found = False
            for identifier in header.identifiers:
                if identifier == raw_identifier:
                    found = True

            if not found and warnings:
                print(f"header doesnt contain the original source identifier'{repr(item.data_id)}'")

            # data has been checked, now add the source data to the header and the data itself
            identifier = Identifier(Source.source, header.header)
            header.identifiers.append(identifier)

            self.collection[identifier] = item    

    def dumps_map(self) -> str:
        """
        Construct a json dump of the map data
        """
        # I need to remove all source identifiers before dumping
        headers_cleaned = copy.deepcopy(self.headers)
        for header in headers_cleaned:
            for identifier in reversed(headers_cleaned[header].identifiers):
                if identifier.source == Source.source:
                    headers_cleaned[header].identifiers.remove(identifier)

        # Now dump
        dump = "{"
        i = 0
        for header in headers_cleaned:
            dump += f'\n  "{header}":'
            sub_dump = headers_cleaned[header].dumps()
            sub_dump = sub_dump.replace("\n", "\n  ")
            dump += sub_dump
            if i < len(headers_cleaned) - 1:
                dump += ","
            i += 1
        dump += "\n}"

        return dump

    def dumps_data(self, warnings: bool = True) -> str:
        """
        Construct a json dump of the sourced spectra data
        """
        output = dict()
        for header in self.headers:
            header_data = self.headers[header]
            if header_data.valid:
                if not header_data.source:
                    if warnings:
                        print(f"{header}:undefined source")
                else:
                    output_data = self.collection[Identifier(Source.source, header_data.header)]

                    # Add the data from the header
                    if not output_data.header:
                        output_data.header = header_data.header
                    output_data.names = header_data.names

                    output[header] = output_data._export_json()

        return json.dumps_pretty(output)

    def export_map(self, path: str) -> None:
        """
        Exports the map in json format to path
            :param path: path to (new) json file
            :raises ValueError: upon saving errors
        """
        if os.path.isfile(path):
            raise ValueError("file already exists")

        _, ex = os.path.splitext(path)

        if ex != ".json":
            raise ValueError("can only save file in json format")

        with open(path, "w", encoding="utf-8") as file:
            file.write(self.dumps_map())
    
    def export_data(self, path: str) -> None:
        """
        Exports the map in json format to path
            :param path: path to (new) json file
            :raises ValueError: upon saving errors
        """
        if os.path.isfile(path):
            raise ValueError("file already exists")

        _, ex = os.path.splitext(path)

        if ex != ".json":
            raise ValueError("can only save file in json format")

        with open(path, "w", encoding="utf-8") as file:
            file.write(self.dumps_data())

    def purge(self) -> None:
        """
        Remove identifiers/headers without corresponding spectra data.
        Useful if you are only interested in a subsection of the source_map
        """
        headers_to_remove = []

        for header in self.headers:
            header = self.headers[header]
            for i, identifier in enumerate(reversed(header.identifiers)):
                if identifier not in self.collection:
                    header.identifiers.remove(identifier)
            
            if header.source not in self.collection:
                # Might have a Source.source loaded, set that as source if available
                if Identifier(Source.source, header.header) in header.identifiers:
                    header.source = Identifier(Source.source, header.header)
                else:
                    header.source = None

            if not header.identifiers:
                headers_to_remove.append(header.header)

        for header in headers_to_remove:
            del self.headers[header]

    def keys(self) -> List[Header]:
        """
        Returns the keys of the collection
        """
        return list(self.collection.keys())

    def __len__(self) -> int:
        return self.collection.__len__()

    def __iter__(self) -> dict:
        self.iter_keys = list(self.collection.keys())
        self.iter_index = 0
        return self
    
    def __next__(self) -> Data:
        self.iter_index += 1

        if self.iter_index > len(self.iter_keys):
            raise StopIteration

        return self.collection[self.iter_keys[self.iter_index-1]]

    def __getitem__(self, key: Identifier) -> Data:
        return self.collection.__getitem__(key)

    def __delitem__(self, key: Identifier) -> None:
        self.collection.__delitem__(key)

    def __setitem__(self, key: Identifier, value: Data) -> None:
        self.collection.__setitem__(key, value)

    def __contains__(self, key: Identifier) -> bool:
        return self.collection.__contains__(key)
