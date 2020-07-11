# -*- coding: utf-8 -*-

## Fluor Tools Viewer ########################################################
# Author:     AJ Zwijnenburg
# Version:    v2.0
# Date:       2020-03-26
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
Here I provide objects to map spectra from multiple sources to a Fluor Spectrum ID (header).
Thereby giving an overview of all the (duplicated) data that exists for a specified 
fluorophore. The map allows for the appending of a Reader's identifiers to the map.
If an identifier is already in the map, nothing happens. If the identifiers is new, the
map tries to add it to a known header by comparing the identifiers fluorophore names
with the mapped fluorophore names. The name must match perfectly for automatic assigned
to happen. All unasignable identifiers are placed in the .unresolved attribute. If the 
map contains identifiers that are missing in the Reader those identifiers will be placed
in the .dangled attribute. A script interface exists for the managing of the unresolved
and dangled attributes, call respective manage_unresolved() or manage_dangled()

:class: Identifer
    A struct that contains the source, the identifier, and optionally a note, describing
    an identifier

:class: Header
    A Header (= Fluor Spectrum Viewer ID) with its names, and a list of all Identifier
    describing that headers. Some sources describe unexisting spectra, these are marked
    as invalid headers. On top of that, the header stores which identifiers is used as
    main data source.

:class: Map
    A dictionary containing the Header instances. Creates a interface for appending, 
    managing, loading, and exporting of the mapped data.

"""

from __future__ import annotations
from typing import List

from . import json, Source
from .reader import Reader

import os.path

class Identifier():
    """
    A identifier specifying the scraping identifier of a specific source
    """
    def __init__(self, source: Source=Source.none, identifier: str=None) -> None:
        self.source: Source = source
        self.identifier: str = identifier
        self.note: str = None

    def valid(self) -> bool:
        """
        Checks whether the identifier is valid (assumes type correctness)
        """
        if self.source == Source.none:
            return False
        if self.identifier is None:
            return False
        
        return True

    def dumps(self) -> str:
        """
        Creates a json formatted string of self
            :raises NotImplementedError: if self.identifier type is not implemented
        """
        if self.identifier is None:
            identifier = 'null'
        elif isinstance(self.identifier, str):
            identifier = f'"{self.identifier}"'
        else:
            raise NotImplementedError(f"json dump implementation cannot handle this type: {self.identifier.__class__}")
        
        if self.note is None:
            return f'{{"source":"{repr(self.source)}","identifier":{identifier}}}'
        else:
            return f'{{"source":"{repr(self.source)}","identifier":{identifier},"note":"{self.note}"}}'

    def load_json(self, data: dict) -> None:
        """
        Loads a json dictionary into this Identifier instance
            :param data: the json parsing dictionary result of this object
            :raises ValueError: if source is unknown
        """
        self.source = Source[data["source"]]

        if self.source == Source.none:
            raise ValueError("unknown source type")

        self.identifier = data["identifier"]
        
        try:
            self.note = data["note"]
        except KeyError:
            self.note = None

    def __repr__(self) -> str:
        return f"{repr(self.source)}:{self.identifier}"

    def __eq__(self, other: Identifier) -> bool:
        if self.source != other.source:
            return False
        if self.identifier != other.identifier:
            return False
        return True

    def __lt__(self, other: Identifier) -> bool:
        if self.source != other.source:
            return self.source < other.source

        return self.identifier < other.identifier

    def __hash__(self) -> int:
        return hash(repr(self.source) + str(self.identifier))

class Header():
    """
    The header with its header specifier and all sources
    """
    def __init__(self, header: str) -> None:
        self.valid: bool = True
        self.header: str = header
        self.source: Identifier = None
        self.names: List[str] = []
        self.identifiers: List[Identifier] = []

    def dumps(self) -> str:
        if self.valid:
            valid = 'true'
        else:
            valid = 'false'
        
        if self.source is None:
            source = 'null'
        else:
            source = self.source.dumps()

        dump = '{\n'
        dump += f'  "valid":{valid},\n'
        dump += f'  "header":"{self.header}",\n'
        dump += f'  "source":{source},\n'
        dump += f'  "names":['
        for i, item in enumerate(self.names):
            dump += f'"{item}"'
            if i < len(self.names) -1:
                dump +=','
        dump += f'],\n'
        dump += f'  "identifiers":[\n'
        for i, item in enumerate(self.identifiers):
            dump += f'    {item.dumps()}'
            if i < len(self.identifiers) -1:
                dump +=',\n'
            else:
                dump +='\n'
        dump += f'  ]\n'
        dump += "}"

        return dump
    
    def load_json(self, data: dict) -> None:
        self.valid = data["valid"]
        self.header = data["header"]
    
        if data["source"] is None:
            self.source = None
        else:
            self.source = Identifier()
            self.source.load_json(data["source"])

        self.names = data["names"]
        self.identifiers = []

        for item in data["identifiers"]:
            identifier = Identifier()
            identifier.load_json(item)
            self.identifiers.append(identifier)

    def __repr__(self) -> str:
        text = self.header
        if self.valid:
            text += ":T:"
        else:
            text += ":F:"
        text += f"{repr(self.source)}/{len(self.identifiers)}"

        return text

    def __eq__(self, other: Header) -> bool:
        # The header should be unique!
        return self.header == other.header

    def __hash__(self) -> int:
        return hash(self.header)

class Map():
    """
    Overview map (dictionary) of fluorophore headers and the scraper identifiers that
    belong to this header.
    Contains additional properties for adding new headers/identifiers
        :param path: (optional) path to the header_map json file
    """
    def __init__(self, path: Union[None, str]=None) -> None:
        self.map: Dict[str, Header] = dict()

        # Temporaries, only stores the results of the most recent append() call
        self.source: Source = Source.none
        self.unresolved: List[Identifier] = []     # Identifiers that are missing in the map
        self.dangled: List[Identifier] = []        # Identifiers that are in the map but not in the append() data

        if path is not None:
            self.load(path)

    # Make it function as a dict
    def __len__(self) -> int:
        return self.map.__len__()

    def __iter__(self) -> Header:
        return self.map.__iter__()
    
    def __next__(self) -> Header:
        return self.map.__next__()

    def __getitem__(self, key: str) -> Header:
        return self.map.__getitem__(key)

    def __delitem__(self, key: str) -> None:
        return self.map.__delitem__(key)

    def __setitem__(self, key: str, value: Header) -> None:
        return self.map.__setitem__(key, value)

    def __contains__(self, key: str) -> bool:
        return self.map.__contains__(key)

    # Printable
    def __repr__(self) -> str:
        return f"(Map:{len(self.map)})"

    # Exporting / Importing
    def dumps(self) -> str:
        dump = "{"
        i = 0
        for item in self.map:
            dump += f'\n  "{item}":'
            sub_dump = self.map[item].dumps()
            sub_dump = sub_dump.replace("\n", "\n  ")
            dump += sub_dump
            if i < len(self.map) - 1:
                dump += ","
            i += 1
        dump += "\n}"

        return dump

    def load_json(self, data: dict) -> None:
        """
        Load a dictionary of a json loaded file
        """
        for item in data:
            header = Header(item)
            header.load_json(data[item])
            self.map[item] = header

    def load(self, path: str) -> None:
        """
        Loads a json file as specified in path
            :param path: path to json map
        """
        if not os.path.isfile(path):
            raise ValueError("file does not exist")

        _, ex = os.path.splitext(path)

        if ex != ".json":
            raise ValueError("can only load file with json format")

        with open(path, "r") as file:
            self.load_json(json.loads(file.read()))

    def export(self, path: str) -> None:
        """
        Exports the map in json format to path
            :param path: path to (new) json file
        """
        if os.path.isfile(path):
            raise ValueError("file already exists")

        _, ex = os.path.splitext(path)

        if ex != ".json":
            raise ValueError("can only save file in json format")

        with open(path, "w") as file:
            file.write(self.dumps())

    # Manipulation
    def append(self, data: Reader) -> None:
        """
        Tries to append the Data identifiers to the header->id map data
            :param data: the scraped data, must be from a single source!!!
            :raises ValueError: when source is none or unknown or if multiple source are contained in the data
        """
        # Wipe previous result
        self.source = None
        self.unresolved = []
        self.dangled = []

        # Get source
        if not data:
            return
        else:
            source = data[0].data_id.source
            if not source or source == Source.none:
                raise ValueError("no spectra source specified")
            self.source = source

        # Build lookup dictionaries
        # Lookup dictionaries are limited to a single source, otherwise dangling identifiers cannot be determined.
        name_to_header = dict()
        map_identifiers = set()
        data_identifiers = set()
        for header in self.map:
            for name in self.map[header].names:
                name_to_header[name.lower()] = header
    
            for identifier in self.map[header].identifiers:
                if identifier.source == source:
                    map_identifiers.add(identifier)

        # Now try to resolve the header<->id by using the fluorophores names
        for item in data:
            if item.data_id.source != self.source:
                raise ValueError("all data's spectra must be of identical source")


            identifier = Identifier(source, item.data_id.identifier)
            # Add identifier to data_identifiers to be able to later find dangling identifiers in the map
            data_identifiers.add(identifier)

            # Check if the identifier already in the map
            if identifier in map_identifiers:
                continue

            # Assign based on name
            found = False
            for name in item.names:              
                try:
                    header = name_to_header[name.lower()]
                    found = True
                except KeyError:
                    pass

                if found:
                    self.map[header].identifiers.append(identifier)
                    break
                
            if not found:
                self.unresolved.append(identifier)      
        
        # Finally check for dangling identifiers
        dangling = map_identifiers - data_identifiers
        for identifier in dangling:
            self.dangled.append(identifier)

    def append_to(self, header: str, identifier: Identifier) -> None:
        """
        Appends the identifier to the specified header
            :param header: the header
            :param identifier: the identifier to add
            :raises KeyError: when header does not exist
        """
        self.map[header].identifiers.append(identifier)

    def new(self, header: str, identifier: Identifier, valid: bool=True) -> None:
        """
        Add a new header with identifier to the map.
            :param header: the new header, must be unique
            :param identifier: the identifier of the new header
            :param valid: (optional) headers validity
            :raises KeyError: when header already exists
        """
        if header in self.map.keys():
            raise KeyError("header key already exists")

        self.map[header] = Header(header)
        self.map[header].identifiers.append(identifier)
        self.map[header].valid = valid

    def delete(self, header: str, identifier: Identifier) -> None:
        """
        Remove the identifier from the header. If the header is now void of identifiers
        it will be removed from the map
            :param header: the header
            :param identifier: the identifier
        """
        is_modified = False
        # Remove all identical identifiers from Fluorophore container
        for i in range(len(self.map[header].identifiers), 0, -1):
            if self.map[header].identifiers[i-1] == identifier:
                is_modified = True
                del self.map[header].identifiers[i-1]

        # Only adjust source / remove map entree if modification happened
        if not is_modified:
            return

        # If this specific identifier is source, also clear source
        if self.map[header].source is not None and self.map[header].source == identifier:
            self.map[header].source = None

        # If fluorophore container is now devoid of identifiers, remove completely
        if len(self.map[header].identifiers) == 0:
            del self.map[header]

    def delete_identifier(self, identifier: Identifier) -> None:
        """
        Deletes all occurences of the specified identifier
            :param identifier: the identifier to delete
        """
        for header in list(self.map):
            self.delete(header, identifier)

    def sort(self) -> None:
        """
        Sorts the internal map in case-insensitive alfabetical order.
        Eventhough dict's are officially unordered, the default implementation is ordered
        """
        keys = list(self.map.keys())
        keys = [(key.lower(),key) for key in keys]
        keys.sort(key=lambda key: key[0])
        
        new_map = dict()
        for key in keys:
            new_map[key[1]] = self.map[key[1]]

        self.map = new_map

    # Interactive manipulation
    def manage_unresolved(self, data: Reader=None) -> None:
        """
        Manage all unresolved identifiers using an interactive python command line interface
            :param data: (optional) provides additional information of the identifier
        """
        if not self.unresolved:
            print("No unresolved identifiers to manage")
            return

        # Keep track of managed entrees, to cleanup self.unresolved later
        managed = []

        print(f"Manage unresolved identifiers ({len(self.unresolved)})")
        print("Options: 0=ignore, 1=append_to, 2=new, 3=new(invalid)")
        for i, item in enumerate(self.unresolved):
            while True:
                if data:
                    text = f"[{i}] "
                    for j, name in enumerate(data[item.identifier].names):
                        text += name
                        if j < len(data[item.identifier].names) -1:
                            text += "|"
                    print(text)
                response = input(f"[{i}] {item} :")

                if response == "0":
                    break
                elif response == "1":
                    header_response = input("Specify append_to header:")
                    if header_response == "":
                        print("unknown input, please retry")
                    else:
                        try:
                            self.append_to(header_response, item)
                            managed.append(item)
                            break
                        except KeyError:
                            print("unknown header, please retry")
    
                elif response == "2" or response == "3":
                    header_response = input("Specify the new header:")
                    if header_response == "":
                        print("unknown input, please retry")
                    else:
                        try:
                            if response == "2":
                                self.new(header_response, item, valid=True)
                            else:
                                note_response = input("Invalidity note:")
                                if note_response:
                                    item_note = Identifier(item.source, item.identifier)
                                    item_note.note = note_response
                                self.new(header_response, item_note, valid=False)
                            managed.append(item)
                            break
                        except KeyError:
                            print("header already in use, please retry")

                elif response == "exit":
                    # Cleanup dangled list
                    for item in managed:
                        self.unresolved.remove(item)

                    return
                else:
                    print("unknown input, please try again")

        # Cleanup dangled list
        for item in managed:
            self.unresolved.remove(item)

    def manage_dangled(self) -> None:
        """
        Manage all dangled identifiers using an interactive python command line interface
        """
        if not self.dangled:
            print("No dangled identifiers to manage")
            return

        # Keep track of handled entrees, to cleanup self.dangled later
        managed = []

        print(f"Manage dangled identifiers ({len(self.dangled)})")
        print("Options: 0=ignore, 1=delete:")
        for i, item in enumerate(self.dangled):
            while True:
                response = input(f"[{i}] {item} :")

                if response == "0":
                    break
                elif response == "1":
                    self.delete_identifier(item)
                    managed.append(item)
                    break
                elif response == "exit":
                    # Cleanup dangled list
                    for item in managed:
                        self.dangled.remove(item)

                    return
                else:
                    print("unknown input, please try again")

        # Cleanup dangled list
        for item in managed:
            self.dangled.remove(item)
