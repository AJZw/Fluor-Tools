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
The abstract containers

:class: AbstractData
The data container for the data of a specific fluorophore

:class: AbstractID
A data container that represents a fluorophore's identification. Tends to be specific for
the scraping source.

:class: AbstractCollection
A data container for AbstractID or AbstractData. Effectively a directly iterable dictionary

:class: AbstractReference
A data container that represents a url/journal reference

"""

from __future__ import annotations
from typing import Union, List, Tuple, Dict, Any

from . import Format, Source, json

import os

class AbstractData:
    """
    Abstract container for all available data of a fluorophore
    """
    def __init__(self, identifier: AbstractID) -> None:
        # Basic spectrum information
        self.data_id: AbstractID = identifier
        self.header = None
        self.source: str = None
        self.enable: bool = None
        self.names: List[str]  = []
        self.categories: List[str] = []

        # Intensity properties
        self.extinction_coefficient: int = None     # Molar Extinction coefficient (/M/cm)
        self.quantum_yield: float = None            # Quantum Yield (unitless)
        self.cross_section: float = None            # Two photon cross-section in Goeppert-Mayer units
        self.brightness: float = None               # Brightness (extinction coefficient (/M/m) * quantum yield)
        self.brightness_bin: int = None             # Binned brightness values 0-5

        # References
        self.url: str = None
        self.references: List[AbtractReference] = []

        # Max wavelengths
        self.absorption_max: float = None
        self.excitation_max: float = None
        self.emission_max: float = None
        self.two_photon_max: float = None

        # Spectra
        self.absorption_wavelength: List[float] = []
        self.absorption_intensity: List[float] = []
        self.excitation_wavelength: List[float] = []
        self.excitation_intensity: List[float] = []
        self.emission_wavelength: List[float] = []
        self.emission_intensity: List[float] = []
        self.two_photon_wavelength: List[float] = []
        self.two_photon_intensity: List[float] = []
    
    def load(self, data: Union[List[str], dict], load_format: Format) -> None:
        """
        Imports the data and loads the relevant data attributes
            :param data: the data of a single fluorophore
            :param format: the data format
        """
        if load_format == Format.ini:
            self._load_ini(data)
        elif load_format == Format.json:
            self._load_json(data)
        else:
            raise ValueError("unimplemented load_format")

    def _load_ini(self, data: List[str]) -> None:
        """
        Imports a ini datafile
            :param data: data of a single fluorophore, split into lines without newline characters
            :raises ValueError: if parsing of certain lines failes
        """
        # A reference might have missing data attributes, so construct, load if applicable, and check if valid to see if it is in use
        temp_reference = AbstractReference()
        for line in data:
            if not line:
                continue
            if line[:1] == "[":
                if not self.data_id:
                    self.data_id = AbstractID(line[1:-1])
                self.header = line[1:-1]
            if line[:3] == "id=":
                temp_id = line[3:].split(":")
                self.data_id = AbstractID(Source[temp_id[0]], temp_id[1])
            elif line[:7] == "header=":
                self.header = line[7:]
            elif line[:7] == "source=":
                self.source = line[7:]
            elif line[:7] == "enable=":
                if line[7:] == "true":
                    self.enable = True
                elif line[7:] == "false":
                    self.enable = False
                else:
                    raise ValueError("unknown enable identifier")
            elif line[:6] == "names=":
                self.names = line[6:].split(",")
            elif line[:11] == "categories=":
                self.categories = line[11:].split(",")
            elif line[:23] == "extinction_coefficient=":
                self.extinction_coefficient = int(line[23:])
            elif line[:14] == "quantum_yield=":
                self.quantum_yield = float(line[14:])
            elif line[:14] == "cross_section=":
                self.cross_section = float(line[14:])
            elif line[:11] == "brightness=":
                self.brightness = float(line[11:])
            elif line[:15] == "brightness_bin=":
                self.brightness_bin = int(line[15:])
            elif line[:4] == "url=":
                self.url = line[4:]
            elif line[:8] == "ref_url=":
                temp_reference.url = line[8:]
            elif line[:10] == "ref_title=":
                temp_reference.title = line[10:]
            elif line[:12] == "ref_authors=":
                temp_reference.authors = line[12:].split(",")
            elif line[:9] == "ref_year=":
                temp_reference.year = line[9:]
            elif line[:12] == "ref_journal=":
                temp_reference.journal = line[12:]
            elif line[:11] == "ref_volume=":
                temp_reference.volume = line[11:]
            elif line[:10] == "ref_issue=":
                temp_reference.issue = line[10:]
            elif line[:10] == "ref_pages=":
                temp_reference.pages = line[10:]
            elif line[:8] == "ref_doi=":
                temp_reference.doi = line[8:]
            elif line[:15] == "ref_url_pubmed=":
                temp_reference.url_pubmed = line[15:]
            elif line[:12] == "ref_url_doi=":
                temp_reference.url_doi = line[12:]
            elif line[:15] == "absorption_max=":
                self.absorption_max = float(line[15:])
            elif line[:22] == "absorption_wavelength=":
                self.absorption_wavelength = [float(x) for x in line[22:].split(",")]
            elif line[:21] == "absorption_intensity=":
                self.absorption_intensity = [float(x) for x in line[21:].split(",")]
            elif line[:15] == "excitation_max=":
                self.excitation_max = float(line[15:])
            elif line[:22] == "excitation_wavelength=":
                self.excitation_wavelength = [float(x) for x in line[22:].split(",")]
            elif line[:21] == "excitation_intensity=":
                self.excitation_intensity = [float(x) for x in line[21:].split(",")]
            elif line[:13] == "emission_max=":
                self.emission_max = float(line[13:])
            elif line[:20] == "emission_wavelength=":
                self.emission_wavelength = [float(x) for x in line[20:].split(",")]
            elif line[:19] == "emission_intensity=":
                self.emission_intensity = [float(x) for x in line[19:].split(",")]
            elif line[:15] == "two_photon_max=":
                self.two_photon_max = float(line[15:])
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
        keys = data.keys()
        if "id" in keys:
            self.data_id = AbstractID(Source[data["id"]["source"]], data["id"]["identifier"])
        if "header" in keys:
            self.header = data["header"]
        if "source" in keys:
            self.source = data["source"]
        if "enable" in keys:
            self.enable = data["enable"]
        if "names" in keys:
            self.names = data["names"]
        if "categories" in keys:
            self.categories = data["categories"]
        if "extinction_coefficient" in keys:
            self.extinction_coefficient = data["extinction_coefficient"]
        if "quantum_yield" in keys:
            self.quantum_yield = data["quantum_yield"]
        if "cross_section" in keys:
            self.cross_section = data["cross_section"]
        if "brightness" in keys:
            self.brightness = data["brightness"]
        if "brightness_bin" in keys:
            self.brightness_bin = data["brightness_bin"]
        if "url" in keys:
            self.url = data["url"]
        if "references" in keys:
            for ref_data in data["references"]:
                reference = AbstractReference()
                reference._load_json(ref_data)
                self.references.append(reference)

        if "absorption_max" in keys:
            self.absorption_max = data["absorption_max"]
        if "absorption_wavelength" in keys:
            self.absorption_wavelength = data["absorption_wavelength"]
        if "absorption_intensity" in keys:
            self.absorption_intensity = data["absorption_intensity"]
        
        if "excitation_max" in keys:
            self.excitation_max = data["excitation_max"]
        if "excitation_wavelength" in keys:
            self.excitation_wavelength = data["excitation_wavelength"]
        if "excitation_intensity" in keys:
            self.excitation_intensity = data["excitation_intensity"]
        
        if "emission_max" in keys:
            self.emission_max = data["emission_max"]
        if "emission_wavelength" in keys:
            self.emission_wavelength = data["emission_wavelength"]
        if "emission_intensity" in keys:
            self.emission_intensity = data["emission_intensity"]

        if "two_photon_max" in keys:
            self.two_photon_max = data["two_photon_max"]
        if "two_photon_wavelength" in keys:
            self.two_photon_wavelength = data["two_photon_wavelength"]
        if "two_photon_intensity" in keys:
            self.two_photon_intensity = data["two_photon_intensity"]
        
    def export(self, export_format: Format) -> Union[str, dict]:
        """
        Exports the spectrum as the specified format
            :param export_format: the format to export
            :raises NotImplementedError: when the export format has not yet been implemented
            :returns: types depends on the export_format, see __export functions for further information
        """
        if export_format == Format.ini:
            return self._export_ini()
        elif export_format == Format.json:
            return self._export_json()
        else:
            raise NotImplementedError(f"Export of format {export_format} has yet to be implemented")

    def _export_ini(self) -> str:
        """
        Exports the contents of this container in an ini format. List are saved as comma separated strings.
            :returns: data representation in ini format. This is limited to one reference and text without comma's
        """
        export = ""

        if self.data_id:
            export += self.data_id._export_ini()

        if self.header:
            export += "header=" + self.header + "\n"

        if self.source:
            export += "source=" + self.source + "\n"

        if self.enable:
            if self.enable:
                export += "enable=true\n"
            else:
                export += "enable=false\n"

        if self.names:
            export += "names=" 
            for i, name in enumerate(self.names):
                export += name
                if i < (len(self.names) - 1):
                    export += ","
                else:
                    export += "\n"

        if self.categories:
            export += "categories="
            for i, category in enumerate(self.categories):
                export += category
                if i < (len(self.categories) - 1):
                    export += ","
                else:
                    export += "\n"

        if self.extinction_coefficient:
            export += "extinction_coefficient=" + str(self.extinction_coefficient) + "\n"

        if self.quantum_yield:
            export += "quantum_yield=" + str(self.quantum_yield) + "\n"
        
        if self.cross_section:
            export += "cross_section=" + str(self.cross_section) + "\n"

        if self.brightness:
            export += "brightness=" + str(self.brightness) + "\n"

        if self.brightness_bin:
            export += "brightness_bin=" + str(self.brightness_bin) + "\n"

        if self.url:
            export += "url=" + self.url + "\n"

        if self.references:
            # Can only export first reference
                export += self.references[0].export(Format.ini)

        if self.absorption_wavelength and self.absorption_intensity:
            if self.absorption_max:
                export += "absorption_max=" + str(self.absorption_max) + "\n"

            export += "absorption_wavelength="
            for i, wav in enumerate(self.absorption_wavelength):
                if i < (len(self.absorption_wavelength) - 1):
                    export += str(wav) + ","
                else:
                    export += str(wav) + "\n"

            export += "absorption_intensity="
            for i, wav in enumerate(self.absorption_intensity):
                if i < (len(self.absorption_intensity) - 1):
                    export += str(wav) + ","
                else:
                    export += str(wav) + "\n"  

        if self.excitation_wavelength and self.excitation_intensity:
            if self.excitation_max:
                export += "excitation_max=" + str(self.excitation_max) + "\n"

            export += "excitation_wavelength="
            for i, wav in enumerate(self.excitation_wavelength):
                if i < (len(self.excitation_wavelength) - 1):
                    export += str(wav) + ","
                else:
                    export += str(wav) + "\n"

            export += "excitation_intensity="
            for i, wav in enumerate(self.excitation_intensity):
                if i < (len(self.excitation_intensity) - 1):
                    export += str(wav) + ","
                else:
                    export += str(wav) + "\n"  
        
        if self.emission_wavelength and self.emission_intensity:
            if self.emission_max:
                export += "emission_max=" + str(self.emission_max) + "\n"

            export += "emission_wavelength="
            for i, wav in enumerate(self.emission_wavelength):
                if i < (len(self.emission_wavelength) - 1):
                    export += str(wav) + ","
                else:
                    export += str(wav) + "\n"

            export += "emission_intensity="
            for i, wav in enumerate(self.emission_intensity):
                if i < (len(self.emission_intensity) - 1):
                    export += str(wav) + ","
                else:
                    export += str(wav) + "\n"

        if self.two_photon_wavelength and self.two_photon_intensity:
            if self.two_photon_max:
                export += "two_photon_max=" + str(self.two_photon_max) + "\n"
            
            export += "two_photon_wavelength="
            for i, wav in enumerate(self.two_photon_wavelength):
                if i < (len(self.two_photon_wavelength) - 1):
                    export += str(wav) + ","
                else:
                    export += str(wav) + "\n"

            export += "two_photon_intensity="
            for i, wav in enumerate(self.two_photon_intensity):
                if i < (len(self.two_photon_intensity) - 1):
                    export += str(wav) + ","
                else:
                    export += str(wav) + "\n"  

        return export

    def _export_json(self) -> dict:
        """
        Exports the contents of this container in a json format
        """
        output = dict()

        if self.data_id:
            output["id"] = self.data_id._export_json()

        if self.header:
            output["header"] = self.header
        
        if self.source:
            output["source"] = self.source

        if self.enable is not None:
            output["enable"] = self.enable
        
        if self.names:
            output["names"] = self.names

        if self.categories:
            output["categories"] = self.categories

        if self.extinction_coefficient:
            output["extinction_coefficient"] = self.extinction_coefficient
       
        if self.quantum_yield:
            output["quantum_yield"] = self.quantum_yield

        if self.cross_section:
            output["cross_section"] = self.cross_section

        if self.brightness:
            output["brightness"] = self.brightness

        if self.brightness_bin:
            output["brightness_bin"] = self.brightness_bin

        if self.url:
            output["url"] = self.url

        if self.references:
            output["references"] = []
            for reference in self.references:
                output["references"].append(reference.export(Format.json))

        if self.absorption_wavelength and self.absorption_intensity:
            if self.absorption_max:
                output["absorption_max"] = self.absorption_max

            output["absorption_wavelength"] = self.absorption_wavelength
            output["absorption_intensity"] = self.absorption_intensity

        if self.excitation_wavelength and self.excitation_intensity:
            if self.excitation_max:
                output["excitation_max"] = self.excitation_max
            
            output["excitation_wavelength"] = self.excitation_wavelength
            output["excitation_intensity"] = self.excitation_intensity
        
        if self.emission_wavelength and self.emission_intensity:
            if self.emission_max:
                output["emission_max"] = self.emission_max
            
            output["emission_wavelength"] = self.emission_wavelength
            output["emission_intensity"] = self.emission_intensity
        
        if self.two_photon_wavelength and self.two_photon_intensity:
            if self.two_photon_max:
                output["two_photon_max"] = self.two_photon_max
            
            output["two_photon_wavelength"] = self.two_photon_wavelength
            output["two_photon_intensity"] = self.two_photon_intensity

        return output

    def file_name(self, export_format: Format) -> str:
        """
        Constructs and returns (Windows) valid file name 
            :param export_format: export files extension
            :raises AttributeError: if filename cannot be generated
            :raises NotImplementedError: if the Format is not implemented
            :returns: file name including extension
        """
        if not self.names:
            raise AttributeError("Missing name, cannot generate a file_name")

        file_name = ""
        for letter in self.names[0]:
            if letter in "0123456789":
                file_name += letter
            elif letter in "abcdefghijklmnopqrstuvwxyz":
                file_name += letter
            elif letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                file_name += letter
            elif letter in " ,.()-_":
                file_name += letter

        if export_format == Format.ini:
            file_name += ".txt"
        elif export_format == Format.json:
            file_name += ".json"
        else:
            raise NotImplementedError(f"Not implemented export format {export_format}")

        return file_name

    def __bool__(self) -> bool:
        """
        Returns whether the data object contains any data (excluding the identifier)
        """
        if self.source or self.names or self.categories:
            return True
        elif self.extinction_coefficient or self.quantum_yield or self.cross_section or self.brightness or self.brightness_bin:
            return True
        elif self.url or self.references:
            return True
        elif self.absorption_wavelength or self.absorption_intensity:
            return True
        elif self.excitation_wavelength or self.excitation_intensity:
            return True
        elif self.emission_wavelength or self.emission_intensity:
            return True
        elif self.two_photon_wavelength or self.two_photon_intensity:
            return True

        return False

    def __repr__(self) -> str:
        return f"{self.data_id.identifier}({len(self.absorption_intensity)}:{len(self.excitation_intensity)}:{len(self.emission_intensity)}:{len(self.two_photon_intensity)})"

class AbstractID:
    """
    Abstract container representing the identifier of a fluorophore
    """
    def __init__(self, source: Source, identifier: str) -> None:
        self.source: Source = source
        self._identifier: str = identifier

        # For the scraping purposes, multiple spectra can belong to the same identifier, therefor a spectra dict is provided
        self.spectra: Dict[str, str] = dict()

        self.iter_keys: List[str] = None
        self.iter_index = 0

    @property
    def identifier(self) -> str:
        """
        Returns the fluorophore identifier 
            :raises AttributeError: if identifier has not been set
        """
        if not self._identifier:
            raise AttributeError("Missing identifier")

        return self._identifier

    def export(self, export_format: Format) -> Union[str, dict]:
        """
        Exports the spectrum as the specified format
            :param export_format: the format to export
            :raises NotImplementedError: when the export format has not yet been implemented
            :returns: types depends on the export_format, see __export functions for further information
        """
        if export_format == Format.ini:
            return self._export_ini()
        elif export_format == Format.json:
            return self._export_json()
        else:
            raise NotImplementedError(f"Export of format {export_format} has yet to be implemented")

    def _export_ini(self) -> str:
        """
        Exports the contents of this container in an ini format. List are saved as comma separated strings.
            :returns: data representation in ini format. This is limited to one reference and text without comma's
        """
        export = ""

        export += f"id={repr(self.source)}:{self.identifier}\n"

        return export

    def _export_json(self) -> dict:
        """
        Exports the contents of this container in a json format
        """
        output = dict()
        output["source"] = repr(self.source)

        # Force string output to force adherence to interface between abstract.AbstractID and mapper.Identifier
        output["identifier"] = str(self.identifier)

        return output

    def __bool__(self) -> bool:
        if self._identifier:
            return True
        else:
            return False

    def __iter__(self) -> AbstractID:
        self.iter_keys = list(self.spectra.keys())
        self.iter_index = 0
        return self

    def __next__(self) -> str:
        self.iter_index += 1

        if self.iter_index > len(self.iter_keys):
            raise StopIteration

        return self.spectra[self.iter_keys[self.iter_index - 1]]

    def __repr__(self) -> str:
        return f"{repr(self.source)}:{self.identifier}({len(self.spectra)})"

class AbstractCollection:
    """
    Abstract collection of AbstractID's or AbstractData. Allows for direct iteration over the collection
    The collection requires str key's
    You can request an entree by key index, but this is unstable! No guarantee that the key order is stable upon modification of the internal collection
    """
    def __init__(self) -> None:
        self.collection: Dict[str, Union[AbstractID, AbstractData]] = dict()

        self.iter_keys: List[str] = None
        self.iter_index = 0

    def empty(self) -> bool:
        """
        Whether the collection contains an entree
        """
        if len(self.collection) == 0:
            return True
        else:
            return False

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
            name += ".ini"
            output = self._export_ini()
        elif export_format == Format.json:
            name += ".json"
            output = self._export_json()
            #output = json.dumps(output, indent=2, separators=(",", ": "), sort_keys=False)
            output = json.dumps_pretty(output)
        else:
            NotImplementedError("Unimplemented export format")

        path = os.path.join(directory, name)
        if os.path.isfile(path):
            raise ValueError("file already exists")

        with open(path, "w", encoding="utf-8") as f:
            f.write(output)

    def _export_ini(self) -> str:
        """
        Exports the contents of this container in an ini format. List are saved as comma separated strings.
            :returns: data representation in ini format. This is limited to one reference and text without comma's
        """
        export = ""

        for key in self.collection:
            # If header is known use header, otherwise use identifier
            if self.collection[key].header:
                export_key = self.collection[key].header
            else:
                export_key = key.identifier

            export += f"[{export_key}]\n"
            export += self.collection[key].export(Format.ini)
            export += "\n"

        return export

    def _export_json(self) -> dict:
        """
        Exports the contents of this container in a json format
        """
        output = dict()

        for key in self.collection:
            # If header is known use header, otherwise use identifier
            if self.collection[key].header:
                export_key = self.collection[key].header
            else:
                export_key = key.identifier

            output[key.identifier] = self.collection[key].export(Format.json)
        
        return output

    def load(self, path: str, import_format: Union[None, Format]=None) -> None:
        """
        Loads the specified file into the internal collection
            :param path: path to the file
            :param export_format: function will auto detect the format based on extension (if none), otherwise forces that format
            :raises ValueError: when path doesnt point to a valid file
        """
        if not os.path.isfile(path):
            raise ValueError("file does not exist")

        if import_format is None:
            _, ex = os.path.splitext(path)

            if ex == ".ini":
                import_format = Format.ini
            elif ex == ".json":
                import_format = Format.json
            else:
                raise ValueError("unknown extension")

        if import_format == Format.ini:
            self._load_ini(path)
        elif import_format == Format.json:
            self._load_json(path)
        else:
            raise ValueError("unknown file format")

    def _load_ini(self, path: str) -> None:
        """
        (Pure virtual) Loads and parses an ini formatted file
            :param path: path to the file
        """
        raise NotImplementedError

    def _load_json(self, path: str) -> None:
        """
        (Pure virtual) Loads and parses a json formatted file
            :param path: path to the file
        """
        raise NotImplementedError

    def keys(self) -> List[str]:
        """
        Returns the keys of the collection
        """
        return list(self.collection.keys())

    def __len__(self) -> int:
        return self.collection.__len__()

    def __iter__(self) -> AbstractCollection:
        self.iter_keys = list(self.collection.keys())
        self.iter_index = 0
        return self
    
    def __next__(self) -> Union[AbstractID, AbstractData]:
        self.iter_index += 1

        if self.iter_index > len(self.iter_keys):
            raise StopIteration

        return self.collection[self.iter_keys[self.iter_index-1]]

    def __getitem__(self, key: Union[int, str]) -> Union[AbstractID, AbstractData]:
        if isinstance(key, int):
            if key < 0:
                key = len(self.collection.keys()) + key
            if key < 0 or key >= len(self.collection.keys()):
                raise IndexError("collection index out of range")

            key = list(self.collection.keys())[key]
            return self.collection.__getitem__(key)
        elif isinstance(key, str):
            return self.collection.__getitem__(key)
        else:
            raise TypeError("invalid key type. key must be of type int or str")

    def __delitem__(self, key: Union[int, str]) -> None:
        if isinstance(key, int):
            if key < 0:
                key = len(self.collection.keys()) - key
            if key < 0 or key >= len(self.collection.keys()):
                raise IndexError("collection index out of range")
            key = list(self.collection.keys())[key]
            self.collection.__delitem__(key)
        elif isinstance(key, str):
            self.collection.__delitem__(key)
        else:
            raise TypeError("invalid key type. key must be of type int or str")

    def __setitem__(self, key: str, value) -> None:
        if isinstance(key, str):
            self.collection.__setitem__(key, value)
        else:
            raise TypeError("invalid key type. key must be of type str")

    def __contains__(self, key: str) -> bool:
        if isinstance(key, str):
            return self.collection.__contains__(key)
        else:
            raise TypeError("invalid key type. key must be of type str")

    def __repr__(self) -> str:
        return f"(Collection:{len(self.collection)})"

class AbstractReference:
    """
    Abstract container representing a url/journal reference
    """
    def __init__(self) -> None:
        self.url: str = None
        self.title: str = None
        self.authors: List[str] = []
        self.year: str = None
        self.journal: str = None
        self.volume: str = None
        self.issue: str = None
        self.pages: str = None
        self.doi: str = None
        self.url_pubmed: str = None
        self.url_doi: str = None

    def _load_ini(self, data: str) -> None:
        """
        Import a ini reference string
            :param data: the json data
        """
        for line in data:
            if not line:
                pass
            elif line[:8] == "ref_url=":
                self.url = line[8:]
            elif line[:10] == "ref_title=":
                self.title = line[10:]
            elif line[:12] == "ref_authors=":
                self.authors = line[12:].split(",")
            elif line[:9] == "ref_year=":
                self.year = line[9:]
            elif line[:12] == "ref_journal=":
                self.journal = line[12:]
            elif line[:11] == "ref_volume=":
                self.volume = line[11:]
            elif line[:10] == "ref_issue=":
                self.issue = line[10:]
            elif line[:10] == "ref_pages=":
                self.pages = line[10:]
            elif line[:8] == "ref_doi=":
                self.doi = line[8:]
            elif line[:15] == "ref_url_pubmed=":
                self.url_pubmed = line[15:]
            elif line[:12] == "ref_url_doi=":
                self.url_doi = line[12:]

    def _load_json(self, data: Dict) -> None:
        """
        Import a json reference dictionary
            :param data: the json data
        """
        ref_keys = data.keys()
        if "url" in ref_keys:
            self.url = data["url"]
        if "title" in ref_keys:
            self.title = data["title"]
        if "authors" in ref_keys:
            self.authors = data["authors"]
        if "year" in ref_keys:
            self.year = data["year"]
        if "journal" in ref_keys:
            self.journal = data["journal"]
        if "volume" in ref_keys:
            self.volume = data["volume"]
        if "issue" in ref_keys:
            self.issue = data["issue"]
        if "pages" in ref_keys:
            self.pages = data["pages"]
        if "doi" in ref_keys:
            self.doi = data["doi"]
        if "url_doi" in ref_keys:
            self.url_doi = data["url_doi"]
        if "url_pubmed" in ref_keys:
            self.url_pubmed = data["url_pubmed"]

    # Export functions
    def export(self, export_format: Format) -> Union[str, dict]:
        """
        Exports the reference as the specified format
            :param export_format: the format to export
            :raises NotImplementedError: when the export format has not yet been implemented
            :returns: types depends on the export_format, see __export functions for further information
        """
        if export_format == Format.ini:
            return self._export_ini()
        elif export_format == Format.json:
            return self._export_json()
        else:
            raise NotImplementedError(f"Export of format {export_format} has yet to be implemented")

    def _export_ini(self) -> str:
        """
        Exports the contents of this container in an ini format. List are saved as comma separated strings.
        """
        export = ""

        if self.url:
            export += "ref_url=" + self.url + "\n"

        if self.title:
            export += "ref_title=" + self.title + "\n"

        if self.authors:
            export += "ref_authors="
            for i, author in enumerate(self.authors):
                export += author
                if i < len(self.authors) - 1:
                    export += ","
                else:
                    export += "\n"
        
        if self.year:
            export += "ref_year=" + self.year + "\n"

        if self.journal:
            export += "ref_journal=" + self.journal + "\n"

        if self.volume:
            export += "ref_volume=" + self.volume + "\n"
        
        if self.issue:
            export += "ref_issue=" + self.issue + "\n"
        
        if self.pages:
            export += "ref_pages=" + self.pages + "\n"
        
        if self.doi:
            export += "ref_doi=" + self.doi + "\n"

        if self.url_pubmed:
            export += "ref_url_pubmed=" + self.url_pubmed + "\n"
        
        if self.url_doi:
            export += "ref_url_doi=" + self.url_doi + "\n"

        return export
    
    def _export_json(self) -> dict:
        """
        Exports the contents of this container in a json (dict) format
        """
        export = dict()

        if self.url:
            export["url"] = self.url

        if self.title:
            export["title"] = self.title

        if self.authors:
            export["authors"] = self.authors
        
        if self.year:
            export["year"] = self.year

        if self.journal:
            export["journal"] = self.journal

        if self.volume:
            export["volume"] = self.volume
        
        if self.issue:
            export["issue"] = self.issue
        
        if self.pages:
            export["pages"] = self.pages
        
        if self.doi:
            export["doi"] = self.doi
        
        if self.url_doi:
            export["url_doi"] = self.url_doi

        if self.url_pubmed:
            export["url_pubmed"] = self.url_pubmed

        return export

    def __bool__(self) -> bool:
        """
        Whether the object contains any reference data
        """
        if self.url:
            return True
        elif self.title:
            return True
        elif self.authors:
            return True
        elif self.year:
            return True
        elif self.journal:
            return True
        elif self.volume:
            return True
        elif self.issue:
            return True
        elif self.pages:
            return True
        elif self.doi:
            return True
        elif self.url_pubmed:
            return True
        elif self.url_doi:
            return True
        
        return False

    def __repr__(self) -> str:
        """
        Returns a unambiguous reference of the data
        """
        if self.url:
            return "Reference(url)"
        elif self.title:
            return "Reference(paper)"
        else:
            return "Reference(empty)"

    def __str__(self) -> str:
        """
        Returns a styled reference of the data
        """
        if self.url:
            ref = self.url
        else:
            ref = ""
            if self.authors:
                ref += self.authors[0]
                if len(self.authors) > 1:
                    ref += ", et al"
            ref += ". "
            
            ref += self.title if self.title else ""
            ref += ". "
            ref += self.journal if self.journal else ""
            ref += " "
            ref += self.volume if self.volume else ""
            ref += " ("
            ref += self.year if self.year else ""
            ref += "), "
            ref += f"doi: {self.doi}" if self.doi else ""
            ref += "."

        return ref
