# -*- coding: utf-8 -*-

## Fluor Tools Scraper #######################################################
# Author:     AJ Zwijnenburg
# Version:    v1.0
# Date:       2020-03-02
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
Compares two fluorophore collections and creates a difference of the two collections.
Provides iterative serialisation methods for visualising the comparison results.

:class: Difference
    Enumeration of the difference 

:class: Comparer
    Compares scraped / stored fluorophore collections. Checks for missing entrees in either collection
    and compares the identical entrees.

:class: ClassComparison
    Compares classes with attribute __dict__. Compares each __dict__ attribute and generates a differences
    dictionary.

:class: ListComparison
    Compares list instances and iteratively the components within the list. Generates a differences list

:class: Comparison
    Compares buildin types. Container classes are accepted but there is no further iterative comparison of
    the contained items

"""

from __future__ import annotations
from typing import Any, Union, Dict

from enum import Enum

from .abstract import AbstractCollection, AbstractData, AbstractID, AbstractReference

class Difference(Enum):
    """
    Comparison difference possibilities
    """
    none = 0,
    missing = 1,
    type = 2,
    value = 3,
    size = 4,
    key = 5,
    attribute = 6,
    type_key = 7,
    type_value = 8,
    value_dict = 9,
    value_list = 10,
    value_tuple = 11,
    value_set = 12

    def __repr__(self) -> str:
        return self._name_

class Comparer:
    """
    A class providing the interface for comparing fluorophore collections
        :param collection_a: fluorophore collection a
        :param collection_b: fluorophore collection b
    """
    def __init__(self, collection_a: Union[None, AbstractCollection], collection_b: Union[None, AbstractCollection]) -> None:
        super().__init__()

        # Data
        self._a: AbstractCollection = None
        self._b: AbstractCollection = None

        if collection_a is not None:
            if isinstance(collection_a, AbstractCollection):
                self._a = collection_a
            else:
                raise TypeError("collection must inherit an AbstractCollection")

        if collection_b is not None:
            if isinstance(collection_b, AbstractCollection):
                self._b = collection_b
            else:
                raise TypeError("collection must inherit an AbstractCollection")

        # Comparison results
        self.identical: bool = None
        self.count: int = 0

        self.keys_in_a: List[str] = None
        self.keys_in_b: List[str] = None
        self.keys_in_both: List[str] = None
        self.differences: Dict[str, ClassComparison] = dict()

        self._compare()

    def compare(self) -> None:
        """
        Compares the loaded collections. Class will normally auto-compare when appropiate collections are loaded. Function provided just-in-case.
        Function checks whether comparison is possible
            :raises ValueError: when the collections do not allow for comparison
        """
        if self._a is None or self._b is None:
            self.identical = None
            self.keys_a = None
            self.keys_b = None
            self.keys_both = None
            raise ValueError("two collections needed for comparison")
        
        self._compare()

    def _compare(self) -> None:
        """
        Compares the loaded collections. Silently failes if there are no collections to compare
        """
        if self._a is None or self._b is None:
            self.identical = None
            self.keys_a = None
            self.keys_b = None
            self.key_both = None
            return

        keys_a = self._a.collection.keys()
        keys_b = self._b.collection.keys()

        self.keys_in_b = [x for x in keys_b if x not in keys_a]
        self.keys_in_a = [x for x in keys_a if x not in keys_b]
        self.keys_in_both = [x for x in keys_a if x in keys_b]

        for key in self.keys_in_both:
            self.differences[key] = ClassComparison(self._a[key], self._b[key])

        self._count()

        if self.count != 0 or self.keys_in_a or self.keys_in_b:
            self.identical = False
        else:
            self.identical = True
    
    def _count(self) -> None:
        """
        Counts the amount of unequal keys
        """
        self.count = 0
        for key in self.differences:
            if not self.differences[key].identical:
                self.count += 1

    @property
    def a(self) -> AbstractCollection:
        """
        Getter for collection_a
        """
        return self._a
    
    @property
    def b(self) -> AbstractCollection:
        """
        Getter for collection_b
        """
        return self._b

    @a.setter
    def a(self, collection: Union[None, AbstractCollection]) -> None:
        """
        Sets the fluorophore collection a.
            :param collection: the collection or scraper to set
            :raises TypeError: when improper collection type is used
        """
        if collection is None:
            self._a = None

        if isinstance(collection, AbstractCollection):
            self._a = collection
        else:
            raise TypeError("collection must inherit an AbstractCollection")

        self._compare()
    
    @b.setter
    def b(self, collection: Union[None, AbstractCollection]) -> None:
        """
        Sets the fluorophore collection b.
            :param collection: the collection or scraper to set
            :raises TypeError: when improper collection type is used
        """
        if collection is None:
            self._b = None

        if isinstance(collection, AbstractCollection):
            self._b = collection
        else:
            raise TypeError("collection must inherit an AbstractCollection")

        self._compare()

    def __repr__(self) -> str:
        if self.identical:
            return "[T]"
        else:
            return f"[F:{len(self.keys_in_a)}<{self.count}>{len(self.keys_in_b)}]"

    def __str__(self) -> str:
        if self.identical:
            return "[T]"
        else:
            return f"[F:{len(self.keys_in_a)}<{self.count}>{len(self.keys_in_b)}:\n{self.serialize(True)}\n]"

    def serialize(self, ignore_identical=False):
        if self.identical and ignore_identical:
            return "T"
        
        text = ""
        for i, key in enumerate(list(self.differences)):
            comparison = self.differences[key]

            subtext = ""
            if comparison.identical and ignore_identical:
                continue
            elif comparison.identical:
                subtext += f"T:{key}"
            else:
                if isinstance(comparison, (ClassComparison, ListComparison)):
                    subtext += f"F:{key}:\n{comparison.serialize(ignore_identical)}"
                    subtext = subtext.replace("\n", "\n> ")
                else:
                    subtext += f"F:{key}:\t{comparison.serialize(ignore_identical)}"
            
            text += subtext

            if i < len(self.differences) - 1:
                text += "\n"

        if self.keys_in_a:
            subtext = "\nmissing in B:["
            for i, key in enumerate(self.keys_in_a):
                subtext += key

                if i < len(self.keys_in_a) - 1:
                    subtext += ","

            subtext += "]"
            text += subtext

        if self.keys_in_b:
            subtext = "\nmissing in A:["
            for i, key in enumerate(self.keys_in_b):
                subtext += key

                if i < len(self.keys_in_b) - 1:
                    subtext += ","

            subtext += "]"
            text += subtext
        
        # Not always clear when to add a newline, so just replace double newlines
        # absolutely not a nice way to do it, but it works...
        text = text.replace("\n\n", "\n")

        return text

class ClassComparison:
    """
    Helper class for comparing class attributes
    Implemented in a broader sense, as it can accept all classes that implement (__dict__)
    """
    def __init__(self, a: AbstractData, b: AbstractData) -> None:
        self.identical: bool = True
        self.differences: Dict[str, Union[ClassComparison, ListComparison, Comparison]] = dict()
        self.count: int = 0

        self.a = a
        self.b = b

        self._compare()
        self._count()

        if self.count != 0:
            self.identical = False

    def _compare(self) -> None:
        """
        Compares the Data of a and b
        """
        # Compare attributes of the two classes, see if any has been added
        # Shouldnt be different, but creates a nice agnostic view into AbstractData, 
        # so if parameters are added they are automatically handled
        keys_a = self.a.__dict__.keys()
        keys_b = self.b.__dict__.keys()

        # First compare the tying and attributes
        keys_in_a = [x for x in keys_a if x not in keys_b]
        keys_in_b = [x for x in keys_b if x not in keys_a]
        keys_in_both = [x for x in keys_a if x in keys_b]

        if keys_in_a:
            comparison = Comparison()
            comparison.identical = False
            comparison.difference = Difference.attribute

            comparison.hint = "["
            for i, key in enumerate(keys_in_a):
                comparison.hint += key
                if i < (len(keys_in_a) - 1):
                    comparison.hint += ","
                else:
                    comparison.hint += "]"
            self.differences["only_a"] = comparison
        
        if keys_in_b:
            comparison = Comparison()
            comparison.identical = False
            comparison.difference = Difference.attribute

            comparison.hint = "["
            for i, key in enumerate(keys_in_b):
                comparison.hint += key
                if i < (len(keys_in_b) - 1):
                    comparison.hint += ","
                else:
                    comparison.hint += "]"
            self.differences["only_b"] = comparison
        
        for key in keys_in_both:
            object_a = self.a.__dict__[key]
            object_b = self.b.__dict__[key]

            if hasattr(object_a, "__dict__"):
                self.differences[key] = ClassComparison(object_a, object_b)

            else:
                if not object_a and not object_b:
                    continue

                # Filter out References for further checking
                if isinstance(object_a, list) and len(object_a) > 0 and isinstance(object_a[0], AbstractReference):
                    self.differences[key] = ListComparison(object_a, object_b)
                    continue
                elif isinstance(object_b, list) and len(object_b) > 0 and isinstance(object_b[0], AbstractReference):
                    self.differences[key] = ListComparison(object_a, object_b)
                    continue
                self.differences[key] = Comparison(object_a, object_b)

    def _count(self) -> None:
        """
        Recursively counts to total issues
        """
        count = 0
        for key in self.differences:
            item = self.differences[key]
            if isinstance(item, ClassComparison):
                count += item.count
            else:
                if not item.identical:
                    count += 1
        
        self.count = count

    def __repr__(self) -> str:
        if self.identical:
            return "(T)"
        else:
            return f"(F:{self.count})"
    
    def __str__(self) -> str:
        if self.identical:
            return "(T)"
        else:
            text = f"(F:{self.count}:\n> "
            subtext = self.serialize()
            text += subtext + "\n)"
            return text

    def serialize(self, ignore_identical=False) -> str:
        if self.identical and ignore_identical:
            return ""

        text = ""

        for key in list(self.differences):
            comparison = self.differences[key]
            if text:
                subtext = "\n"
            else:
                subtext = ""

            if comparison.identical and ignore_identical:
                continue

            elif comparison.identical:
                subtext += f"T:{key}"

            else:
                if isinstance(comparison, (ClassComparison, ListComparison)):
                    subtext += f"F:{key}:\n{comparison.serialize(ignore_identical)}"
                    subtext = subtext.replace("\n", "\n> ")
                else:
                    subtext += f"F:{key}:\t{comparison.serialize(ignore_identical)}"
            
            text += subtext 

        return text

class ListComparison:
    """
    Helper class for comparing a lists subitems, for general list comparison use Comparison
    """
    def __init__(self, a: list, b: list) -> None:
        self.identical: bool = True
        self.differences: List[Union[ClassComparison, ListComparison, Comparison]] = []
        self.count: int = 0

        self.a: list = a
        self.b: list = b

        self._compare()
        self._count()

        if self.count != 0:
            self.identical = False

    def _compare(self) -> None:
        # List can be of unequal length, so get longest length
        length = 0
        if len(self.a) > length:
            length = len(self.a)
        if len(self.b) > length:
            length = len(self.b)

        for i in range(0, length):
            # Get objects (or replacement)
            try:
                object_a = self.a[i]
            except IndexError:
                comparison = Comparison()
                comparison.identical = False
                comparison.difference = Difference.missing
                comparison.hint = "?<->!"
                self.differences.append(comparison)
                continue
            
            try:
                object_b = self.b[i]
            except IndexError:
                comparison = Comparison()
                comparison.identical = False
                comparison.difference = Difference.missing
                comparison.hint = "!<->?"
                self.differences.append(comparison)
                continue

            if hasattr(object_a, "__dict__"):
                comparison = ClassComparison(object_a, object_b)
            else:
                comparison = Comparison(object_a, object_b)
            self.differences.append(comparison)

    def _count(self) -> None:
        self.count = 0
        for item in self.differences:
            if not item.identical:
                self.count += 1

    def __repr__(self) -> str:
        if self.identical:
            return "[T]"
        else:
            return f"[F:{self.count}]"
    
    def __str__(self) -> str:
        if self.identical:
            return "[T]"
        else:
            return f"[F:{self.count}:\n{self.serialize()}\n]"

    def serialize(self, ignore_identical=False) -> str:
        text = ""

        for i, item in enumerate(self.differences):
            if text:
                subtext = "\n"
            else:
                subtext = ""
            
            if item.identical and ignore_identical:
                continue
            elif item.identical:
                subtext += f"T:[{i}]"
            else:
                subtext += f"F:[{i}]:"

                if isinstance(item, (ClassComparison, ListComparison)):
                    ssubtext = f"\n{item.serialize(ignore_identical)}"
                    ssubtext = ssubtext.replace("\n", "\n> ")
                    subtext += ssubtext
                else:
                    subtext += item.serialize()

            text += subtext

        return text

class Comparison:
    """
    Compares two parameters.
        :param a: comparison one side
        :param b: comparison other side
    """
    def __init__(self, a: Any=None, b: Any=None) -> None:
        self.identical: bool = True
        self.difference: Difference = Difference.none
        self.hint: Union[None, str] = None

        self.a: Any = a
        self.b: Any = b

        self._compare()

    def _compare(self) -> None:
        """
        Comparator for different types. In case of container types, does not check individual elements
            :raises TypeError: if type comparison is not implemented
        """
        self._compare_type()
        
        if not self.identical:
            return

        # skip None type
        if self.a is None:
            return
        
        elif isinstance(self.a, (bool, int, float, str)):
            self._compare_primitives()
            return

        elif isinstance(self.a, list):
           self._compare_list()
           return

        elif isinstance(self.a, dict):
            self._compare_dict()
            return

        elif isinstance(self.a, tuple):
            self._compare_tuple()
            return

        elif isinstance(self.a, set):
            self._compare_set()

        # Fallbacks
        else:
            self.identical = self.a == self.b
            self.difference = Difference.value
            self.hint = "fallback"

    def _compare_type(self) -> None:
        """
        Compares types
        """
        if type(self.a) is not type(self.b):
            self.identical = False
            self.difference = Difference.type
            self.hint = f"{type(self.a).__name__}<->{type(self.b).__name__}"
            return

    def _compare_primitives(self) -> None:
        """
        Function to compare ints
        """
        if self.a != self.b:
            self.identical = False
            self.difference = Difference.value
            self.hint = f"{str(self.a)}<->{str(self.b)}"
        return

    def _compare_list(self) -> None:
        """
        Function to compare list
        """
        # Assumes a list only contains object of a single type
        if not self.a and not self.b:
            return
        elif not self.a or not self.b:
            self.identical = False
            self.difference = Difference.size
            self.hint = f"{len(self.a)}<->{len(self.b)}"
            return
        
        if type(self.a[0]) is not type(self.b[0]):
            self.identical = False
            self.difference = Difference.type_value
            self.hint = f"{type(self.a[0]).__name__}<->{type(self.b[0]).__name__}"
            return
        
        if len(self.a) != len(self.b):
            self.identical = False
            self.difference = Difference.size
            self.hint = f"{len(self.a)}<->{len(self.b)}"
            return

        # Now check if all items in the list are equal, 
        # As a list is per definition ordered, i just check direct indexes
        for i in range(0, len(self.a)):
            unequal_entrees = 0
            if self.a[i] != self.b[i]:
                unequal_entrees += 1

            if unequal_entrees:
                self.identical = False
                self.difference = Difference.value_list
                self.hint = f"{unequal_entrees}/{len(self.a)}"
                return
        
        return

    def _compare_dict(self) -> None:
        """
        Function to compare dictionaries
        """
        if not self.a and not self.b:
            return
        elif not self.a or not self.b:
            self.identical = False
            self.difference = Difference.size
            self.hint = f"{len(self.a)}<->{len(self.b)}"
            return

        keys_a = self.a.keys()
        keys_b = self.b.keys()

        if type(list(keys_a)[0]) != type(list(keys_b)[0]):
            self.identical = False
            self.difference = Difference.type_key
            self.hint = f"{type(list(keys_a)[0]).__name__}<->{type(list(keys_b)[0]).__name__}"
            return
        
        if len(self.a) != len(self.b):
            self.identical = False
            self.difference = Difference.size
            self.hint = f"{len(self.a)}<->{len(self.b)}"
            return

        keys_in_a = list(keys_a - keys_b)
        keys_in_b = list(keys_b - keys_a)
        keys_in_both = list(keys_a & keys_b)

        if keys_in_a or keys_in_b:
            self.identical = False
            self.difference = Difference.key
            self.hint = f"{len(keys_in_a)}<-{len(keys_in_both)}->{len(keys_in_b)}"
            return
        
        unequal_key_values = 0
        for key in self.a.keys():
            if self.a[key] != self.b[key]:
                unequal_key_values += 1
        
        if unequal_key_values:
            self.identical = False
            self.difference = Difference.value_dict
            self.hint = f"{unequal_key_value}/{len(self.a)}"
        return

    def _compare_tuple(self) -> None:
        """
        Compares two tuples
        """
        if not self.a and not self.b:
            return

        if len(self.a) != len(self.b):
            self.identical = False
            self.difference = Difference.size
            self.hint = f"{len(self.a)}<->{len(self.b)}"
            return

        # Now check if all items in the list are equal, 
        # As a tuple is per definition ordered, i just check direct indexes
        for i in range(0, len(self.a)):
            unequal_entrees = 0
            if self.a[i] != self.b[i]:
                unequal_entrees += 1

            if unequal_entrees:
                self.identical = False
                self.difference = Difference.value_tuple
                self.hint = f"{unequal_entrees}/{len(self.a)}"
                return
        
        return

    def _compare_set(self) -> None:
        """
        Function to compare sets
        """
        if not self.a and not self.b:
            return
        elif not self.a or not self.b:
            self.identical = False
            self.difference = Difference.size
            self.hint = f"{len(self.a)}<->{len(self.b)}"
            return
      
        if len(self.a) != len(self.b):
            self.identical = False
            self.difference = Difference.size
            self.hint = f"{len(self.a)}<->{len(self.b)}"
            return

        value_in_a = list(self.a - self.b)
        value_in_b = list(self.b - self.a)
        value_in_both = list(self.a & self.b)

        if value_in_a or value_in_b:
            self.identical = False
            self.difference = Difference.value_set
            self.hint = f"{len(value_in_a)}<-{len(value_in_both)}->{len(value_in_b)}"
            return
        
        return

    def __repr__(self) -> str:
        if self.identical:
            return "(T)"
        else:
            return "(F)"

    def __str__(self) -> str:
        if self.identical:
            return "(T)"
        else:
            text = f"(F:{self.serialize(False)})"
        return text

    def serialize(self, ignore_identical=False) -> str:
        """
        Text output for serialising the output
        """
        if ignore_identical and self.identical:
            return ""

        text = f"{repr(self.difference)}"
        if self.hint:
            text += ":" + self.hint

        return text
