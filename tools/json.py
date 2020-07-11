# -*- coding: utf-8 -*-

## Fluor Tools Scraper #######################################################
# Author:     AJ Zwijnenburg
# Version:    v1.0
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
Extends the python standard library json module with function definition for
pretty printing of fluorophore data

:def: dumps_pretty
Serializes a dictionary into a pretty human readable compact json string
"""

from json import *

def dumps_pretty(data: dict) -> str:
    """
    Serializes dictionary into a pretty human readable compact json dump. 
    Multilines all container types, except lists.

    Doesnt escape non-ASCII encoding
    """

    def indentation(indent_level, indent_size=2):
        return " " * indent_level * indent_size

    def dump_dict(data: dict, indent_level=0) -> str:
        indent = indentation(indent_level)
        output = "{\n"
        for i, key in enumerate(data):
            if data[key] is None:
                output += indent + '"' + str(key) + '":null'
            elif isinstance(data[key], bool):
                output += indent + '"' + str(key) + '":'
                if data[key] is True:
                    output += "true"
                else:
                    output += "false"
            elif isinstance(data[key], (int, float)):
                output += indent + '"' + str(key) + '":' + str(data[key])
            elif isinstance(data[key], str):
                output += indent + '"' + str(key) + '":"' + str(data[key]) + '"'
            elif isinstance(data[key], list):
                output += indent + '"' + str(key) + '":' + dump_list(data[key], indent_level + 1)
            elif isinstance(data[key], dict):
                output += indent + '"' + str(key) + '":' + dump_dict(data[key], indent_level + 1)
            else:
                raise ValueError(f"unserializable type: {type(data[key])}")
            
            if i < len(data) - 1:
                output += ",\n"
            else:
                output += "\n"
        output += indentation(indent_level - 1) + "}"

        return output

    def dump_list(data: list, indent_level=0) -> str:
        output = "["
        for i, item in enumerate(data):
            if item is None:
                output += "null"
            elif isinstance(item, bool):
                if item is True:
                    output += "true"
                else:
                    output += "false"
            elif isinstance(item, (int, float)):
                output += str(item)
            elif isinstance(item, str):
                output += '"' + item + '"'
            elif isinstance(item, list):
                output += dump_list(item, indent_level+1)
            elif isinstance(item, dict):
                output += dump_dict(item, indent_level+1)
            else:
                raise ValueError(f"unserializable type: {type(item)}")

            if i < len(data) -1:
                output += ","
        output += "]"

        return output

    # Start parsing
    output = dump_dict(data, 1)

    return output
