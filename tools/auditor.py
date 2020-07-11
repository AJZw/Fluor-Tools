# -*- coding: utf-8 -*-

## Fluor Tools Viewer ########################################################
# Author:     AJ Zwijnenburg
# Version:    v2.0
# Date:       2020-03-16
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
Classes that audit the different compoments of fluorophore data. The auditor
will check the entire fluorophore Data class, while each individual audit class
checks their specified part of the data

:class: Auditor
Audits an instance of fluorophore Data. Results can be retreived using this classes
attributes, while a new Data instance can be checked using .audit()

:class: AbstractAudit
The audit abstract base class. Provides the .audit() function to audit a new set of 
data, while the classes attributes can be used to retreive the results (.valid, .errors)

:class: AbstractAuditList
THe audit abstract base class for parameters that are stored within a list. The .audit()
function should be performed on the items in the data list and a summary result of the 
performed audits is provided by this item

... and then all the individual Audit classes. 

of note: AuditReference and AuditSpectrum are specialized classes to handle the 
multiple data structures needed for their purpose.

"""

from __future__ import annotations
from typing import List, Union, Tuple

from .abstract import AbstractData as Data, AbstractReference as Reference

class Auditor():
    """
    Audits the fluorophore Data for validity of the data
        :param data: (optional) the data to audit
    """
    def __init__(self, data: Union[None, Data]=None):
        # Data&
        self.data: Data = None

        self.header: AuditHeader = AuditHeader()
        self.enable: AuditEnable = AuditEnable()
        
        self.source: AuditSource = AuditSource()
        self.categories: AuditCategories = AuditCategories()
        self.names: AuditNames = AuditNames()
        
        self.extinction_coefficient: AuditExtinctionCoefficient = AuditExtinctionCoefficient()
        self.quantum_yield: AuditQuantumYield = AuditQuantumYield()
        self.cross_section: AuditCrossSection = AuditCrossSection()
        self.brightness: AuditBrightness = AuditBrightness()
        self.brightness_bin: AuditBrightnessBin = AuditBrightnessBin()
        
        self.url: AuditUrl = AuditUrl()
        self.references: AuditReferences = AuditReferences()
        
        self.absorption: AuditSpectrum = AuditSpectrum()
        self.excitation: AuditSpectrum = AuditSpectrum()
        self.emission: AuditSpectrum = AuditSpectrum()
        self.two_photon: AuditSpectrum = AuditSpectrum()

        if data:
            self.audit(data)
    
    def audit(self, data: Data) -> None:
        """
        Loads new data into the checker, and automatically reruns the checks
            :param data: new input data
        """
        self.data = data

        self.header.audit(data.header)
        self.enable.audit(data.enable)

        self.source.audit(data.source)
        self.categories.audit(data.categories)
        self.names.audit(data.names)

        self.extinction_coefficient.audit(data.extinction_coefficient)
        self.quantum_yield.audit(data.quantum_yield)
        self.cross_section.audit(data.cross_section)
        self.brightness.audit(data.brightness)
        
        brightness_calc = self.data.calculate_brightness(data.extinction_coefficient, data.quantum_yield)
        self.brightness.audit_brightness(data.brightness, brightness_calc)

        self.brightness_bin.audit(data.brightness_bin)

        self.url.audit(data.url)
        self.references.audit(data.references)

        self.absorption.audit(data.absorption_wavelength, data.absorption_intensity)
        self.excitation.audit(data.excitation_wavelength, data.excitation_intensity)
        self.emission.audit(data.emission_wavelength, data.emission_intensity)
        self.two_photon.audit(data.two_photon_wavelength, data.two_photon_intensity)

    def reset(self) -> None:
        """
        Resets all audits to unchecked
        """
        self.header.reset()
        self.enable.reset()

        self.source.reset()
        self.categories.reset()
        self.names.reset()

        self.extinction_coefficient.reset()
        self.quantum_yield.reset()
        self.cross_section.reset()
        self.brightness.reset()
        self.brightness_bin.reset()

        self.url.reset()
        self.references.reset()

        self.absorption.reset()
        self.excitation.reset()
        self.emission.reset()
        self.two_photon.reset()

    def __str__(self) -> str:
        return f"(Audit:\n{self.serialize(True)}\n)"

    def serialize(self, ignore_valid=False) -> str:
        text = ""
        for key in ["header", "enable", "source", "categories", "names", "extinction_coefficient", "quantum_yield", "cross_section", "brightness", "brightness_bin", "url", "references", "absorption", "excitation", "emission", "two_photon"]:
            audit = getattr(self, key)
            if text:
                subtext = "\n"
            else:
                subtext = ""

            if audit.valid and ignore_valid:
                continue

            elif audit.valid:
                subtext += f"T:{key}"

            else:
                if isinstance(audit, (AbstractAuditList, AuditReference, AuditSpectrum)):
                    subtext += f"F:{key}:"
                    ssubtext = f"\n{audit.serialize(ignore_valid)}"
                    ssubtext = ssubtext.replace("\n", "\n> ")
                    subtext += ssubtext
                else:
                    subtext += f"F:{key}:{audit.serialize(ignore_valid)}"
            
            text += subtext 

        return text

class AbstractAudit():
    """
    Abstract class for the auditing of fluorophore data attributes
        :param data: (optional) the data to audit
    """
    def __init__(self, data: Union[None, str]=None) -> None:
        self.valid: bool = False
        self.errors: List[str] = ["unchecked"]

        if data:
            self.audit(data)

    def reset(self) -> None:
        """
        Resets the audit to default
        """
        valid = False
        errors.clear()
        errors.append("unchecked")

    def audit(self, data: Any) -> None:
        """
        Audits the data and store the audit results
            :raises NotImplementedError: to be implemented in inherited class
        """
        raise NotImplementedError

    def __repr__(self) -> str:
        if self.valid:
            return "(T)"
        else:
            return "(F)"

    def __str__(self) -> str:
        if self.valid:
            return "(T)"
        else:
            text = f"(F:{self.serialize(False)})"
        return text

    def serialize(self, ignore_valid=False) -> str:
        """
        Text output for serialising the output
        """
        if ignore_valid and self.valid:
            return ""

        text = ""
        if len(self.errors) > 0:
            text += "["
            for i, error in enumerate(self.errors):
                text += error
                if i < len(self.errors) - 1:
                    text += ","
            text += "]"

        return text

class AbstractAuditList():
    """
    Abstract class containing a list of audits
        :param data: (optional) the data to audit
    """
    def __init__(self, data: Union[None, List[str]]=None) -> None:
        self.valid: bool = False
        self.errors: List[str] = ["unchecked"]

        self.audits: List[AbstractAudit] = []

        if data:
            self.audit(data)
    
    def reset(self) -> None:
        self.valid = False
        self.errors.clear()
        self.errors.append("unchecked")
        self.audits.clear()
    
    def audit(self, data: List[str]) -> None:
        raise NotImplementedError
    
    def audit_list(self) -> None:
        """
        Checks and measure the audit results in the internal list
        """
        if not self.audits:
            self.valid = False
            self.errors = ["missing"]
            return

        errors = []
        valid = True
        for i, audit in enumerate(self.audits):
            if not audit.valid:
                valid = False
                errors.extend([f"[{i}]:{error}" for error in audit.errors])

        if not valid:
            self.valid = False
            self.errors = errors
        else:
            self.valid = True
            self.errors = []

    # Make it function as a list
    def __len__(self) -> int:
        return self.audits.__len__()

    def __iter__(self) -> AbstractAudit:
        return self.audits.__iter__()
    
    def __next__(self) -> AbstractAudit:
        return self.audits.__next__()

    def __getitem__(self, key: Any) -> AbstractAudit:
        return self.audits.__getitem__(key)

    def __delitem__(self, key: Any) -> None:
        return self.audits.__delitem__(key)

    def __setitem__(self, key: Any, value: AbstractAudit) -> None:
        return self.audits.__setitem__(key, value)

    def __contains__(self, key: Any) -> bool:
        return self.audits.__contains__(key)

    def __repr__(self) -> str:
        if self.valid:
            return "[T]"
        else:
            return f"[F:{self.errors[0]}]"
    
    def __str__(self) -> str:
        if self.valid:
            return "[T]"
        else:
            return f"[F:{self.errors[0]}:\n{self.serialize()}\n]"

    def serialize(self, ignore_valid=False) -> str:
        text = ""

        for i, item in enumerate(self.audits):
            if text:
                subtext = "\n"
            else:
                subtext = ""
            
            if item.valid and ignore_valid:
                continue
            elif item.valid:
                subtext += f"T:[{i}]"
            else:
                if isinstance(item, (AbstractAuditList, AuditReference, AuditSpectrum)):
                    subtext += f"F:{i}:"
                    ssubtext = f"\n{item.serialize(ignore_valid)}"
                    ssubtext = ssubtext.replace("\n", "\n> ")
                    subtext += ssubtext
                else:
                    subtext += f"F:[{i}]:"
                    subtext += item.serialize()

            text += subtext

        return text

class AuditHeader(AbstractAudit):
    """
    Audits the fluorophore header parameter
    """
    def audit(self, data: Union[None, str]) -> None:
        """
        Audit the header data
            :param data: the header data
        """
        error_missing = 0
        error_char_lower = 0
        error_char_illegal = 0
        error_char_last = 0
        error_colon_multiple = 0

        if not data:
            error_missing += 1
        else:
            colon_count = 0
            for i, letter in enumerate(data):
                if letter == ":":
                    if colon_count >= 1:
                        error_colon_multiple += 1
                    colon_count += 1
                elif letter in "abcdefghijklmnopqrstuvwxyz":
                    error_char_lower += 1
                elif letter not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
                    error_char_illegal += 1
                elif i == len(data) - 1 and letter == ":":
                    error_char_last += 1

        errors = []
        if error_missing:
            errors.append("illegal missing header")
        if error_char_lower:
            errors.append(f"{error_char_lower} illegal lower key characters")
        if error_char_illegal:
            errors.append(f"{error_char_illegal} illegal characters")
        if error_char_last:
            errors.append(f"{error_char_last} illegal final characters (:)")
        if error_colon_multiple:
            errors.append(f"{error_colon_multiple} illegal multiple colons")

        if errors:
            self.valid = False
        else:
            self.valid = True
        
        self.errors = errors

class AuditNames(AbstractAuditList):
    """
    Audits a list of fluorophore names
    """
    def audit(self, data: Union[None, List[str]]) -> None:
        self.audits.clear()
        if data:
            for item in data:
                self.audits.append(AuditName(item))
        self.audit_list()

class AuditName(AbstractAudit):
    """
    Audits the fluorophore name
    """
    def audit(self, data: Union[None, str]) -> None:
        """ Checks validity of names """
        error_missing = 0
        error_char_illegal = 0
        error_bracket_missing_open = 0
        error_bracket_missing_close = 0
        error_bracket_double_open = 0

        if not data:
            error_missing += 1
        else:
            bracket_round_open = False
            for letter in data:
                if letter in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ":
                    pass
                elif letter in "0123456789":
                    pass
                elif letter == "(":
                    if bracket_round_open is True:
                        error_bracket_double_open += 1
                    bracket_round_open = True
                elif letter == ")":
                    if bracket_round_open is False:
                        error_bracket_missing_open += 1
                    else:
                        bracket_round_open = False
                elif letter in " .,+-/":
                        pass
                else:
                    error_char_illegal += 1

            if bracket_round_open is True:
                error_bracket_missing_close += 1
        
        errors = []
        if error_missing:
            errors.append("illegal missing name")
        if error_char_illegal:
            errors.append(f"{error_char_illegal} illegal character")
        if error_bracket_missing_open:
            errors.append(f"{error_bracket_missing_open} illegal closing of round brackets")
        if error_bracket_missing_close:
            errors.append(f"{error_bracket_missing_close} illegal opening of round brackets")
        if error_bracket_double_open:
            errors.append(f"{error_bracket_missing_open} illegal nesting of round brackets")

        if errors:
            self.valid = False
        else:
            self.valid = True
        
        self.errors = errors

class AuditEnable(AbstractAudit):
    """
    Audits the fluorophore enable parameter
    """
    def audit(self, data: Union[None, bool]) -> None:
        """ Checks validity of enable"""
        error_missing = 0
        error_enable = 0

        if data is None:
            error_missing += 1
        elif not isinstance(data, bool):
            error_enable += 1
        
        errors = []
        if error_missing:
            errors.append("missing")
        if error_enable:
            errors.append("invalid non-boolean enable (how?)")

        if errors:
            self.valid = False
        else:
            self.valid = True

        self.errors = errors

class AuditSource(AbstractAudit):
    """
    Audits the fluorophore source parameter
    """
    def audit(self, data: Union[None, str]) -> None:
        """ Checks validity of source """
        error_missing = 0
        error_char_invalid = 0

        if not data:
            error_missing += 1
        else:
            for letter in data:
                if letter not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ- ":
                    error_char_invalid += 1
        
        errors = []
        if error_missing:
            errors.append("missing source")
        if error_char_invalid:
            errors.append(f"{error_char_invalid} invalid characters")

        if errors:
            self.valid = False
        else:
            self.valid = True
        
        self.errors = errors

class AuditCategories(AbstractAudit):
    """
    Audits the fluorophore categories
    """
    def audit(self, data: Union[None, List[str]]):
        """
        Audit so far not implemented, something for later when I implement categories
        """
        self.valid = True
        self.errors = []

class AuditUrl(AbstractAudit):
    """
    Audits the fluorophore url parameter
    """
    def audit(self, data: Union[None, str]) -> None:
        """ Checks validity of the url """
        address = data

        if not data:
            self.valid = False
            self.errors = ["missing url"]
            return

        if len(address) >= 7 and address[:7] == "http://":
            address = address[8:]
        elif len(address) >= 8 and address[:8] == "https://":
            address = address[9:]
        else:
            self.valid = False
            self.errors = ["missing http(s)://"]
            return

        address = address.split("/")

        if len(address) <= 1:
            self.valid = False
            self.errors = ["address too general"]
            return

        address_host = address[0].split(".")

        if len(address_host) <= 1:
            self.valid = False
            self.errors = ["incorret hostname"]
            return
        else:
            if address_host[-1] == "arpa":
                self.valid = False
                self.errors = ["arpa domain is not allowed"]
                return
            elif len(address_host[-1]) > 3 or len(address_host[-1]) <= 1:
                self.valid = False
                self.errors = ["impossible address domain"]
                return

        for address_part in address:
            if len(address_part) == 0:
                self.valid = False
                self.errors = ["missing section in domain"]
                return

        if "?" in address:
            self.valid = False
            self.errors = ["query's not allowed in address"]
            return
        if "#" in address:
            self.valid = False
            self.errors = ["fragment's not allowed in address"]
            return
        
        self.valid = True
        self.errors = []

class AuditAuthor(AbstractAudit):
    """
    Audits an authors name representation
    """
    def audit(self, data: Union[None, str]) -> None:
        """
        Checks the validity of a persons name (or et al)
            :param name[str]: name to check
            :returns: returns validity, and error-messages
        """
        name = data

        if not data:
            self.valid = False
            self.errors = "missing author"
            return

        if name == "et al":
            self.valid = True
            self.errors = ""
            return

        parts = name.split(" ")

        valid = True
        errors = []
        for i, part in enumerate(reversed(parts)):
            if i == 0:
                # last part must be initials
                for letter in part:
                    if letter in ".,":
                        valid = False
                        errors.append("initials must have no seperator")
                    elif letter in "abcdefghijklmnopqrstuvwxyz":
                        valid = False
                        errors.append("initials must be uppercase")
                    elif letter not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ-":
                        valid = False
                        errors.append("invalid character in initials")

            elif i == 1:
                # part before initials must be family name
                # multiple family names mostly be connected with "-"    <- can be false positive
                capital_expected = True
                for letter in part:
                    if capital_expected:
                        if letter not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                            valid = False
                            errors.append("family name must start with capital")
                        capital_expected = False
                    else:
                        if letter == "-":
                            capital_expected = True
                        elif letter not in "abcdefghijklmnopqrstuvwxyz":
                            valid = False
                            errors.append("invalid character in family name")

            elif i >= 2:
                # Connecting words in some names, check for them otherwise return error
                if part not in ["de", "van", "der", "De", "Van", "Der"]:
                    valid = False
                    errors.append("unknown family name connecting word")

        self.valid = valid
        self.errors = errors

class AuditAuthors(AbstractAuditList):
    """
    Audits an author list
    """
    def audit(self, data: Union[None, List[str]]) -> None:
        self.audits.clear()
        if data:
            for item in data:
                self.audits.append(AuditAuthor(item))
        self.audit_list()

class AuditTitle(AbstractAudit):
    """
    Audits a title
    """
    def audit(self, data: Union[None, str]) -> None:
        title = data
        
        valid = True
        errors = []

        if not title:
            valid = False
            errors.append("missing title")
        else:
            title_split = title.strip(" ").split(" ")
            for i, part in enumerate(title_split):
                if len(part) < 1:
                    valid = False
                    errors.append("title contains double spaces")
                for letter in part:
                    if letter not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ -,:()0123456789":
                        valid = False
                        errors.append(f"illegal character in title '{letter}'")
                #elif i != 0 and part[0] in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                #    valid = False
                #    errors.append("invalid reference: multiple words in title start with capital")

        self.valid = valid
        self.errors = errors

class AuditYear(AbstractAudit):
    """
    Audits a year
    """
    def audit(self, data: Union[None, str]) -> None:
        year = data
        
        valid = True
        errors = []
        if not year:
            valid = False
            errors.append("missing year")
            self.valid = valid
            self.errors = errors
            return

        try:
            year = int(year)
        except ValueError:
            valid = False
            errors.append("unconvertable to int")
            self.valid = valid
            self.errors = errors
            return

        if year < 1900:
            valid = False
            errors.append("year before 1900")
        if year > 2020:
            valid = False
            errors.append("year after 2020")

        self.valid = valid
        self.errors = errors
        return

class AuditJournal(AbstractAudit):
    """
    Audits a journal name
    """
    def audit(self, data: Union[None, str]) -> None:
        journal = data
        
        if not journal:
            self.valid = False
            self.errors = ["missing journal name"]
            return

        valid = True
        errors = []

        # Check abbreviation
        journal_split = journal.strip(" ").split(" ")
        for i, part in enumerate(journal_split):
            if len(part) < 1:
                valid = False
                errors.append("journal contains double spaces")
            for letter in part:
                if letter not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ ":
                    valid = False
                    errors.append(f"illegal character in journal '{letter}'")

        self.valid = valid
        self.errors = errors

class AuditVolume(AbstractAudit):
    """
    Audits a journal volume
    """
    def audit(self, data: Union[None, str]) -> None:
        volume = data
        
        if not volume:
            self.valid = False
            self.errors = ["missing volume"]
            return

        valid = True
        errors = []

        try:
            volume = int(volume)
        except ValueError:
            valid = False
            errors.append("unconvertable to int")

        if volume < 0:
            valid = False
            errors.append("negative volume")
        
        self.valid = valid
        self.errors = errors

class AuditIssue(AbstractAudit):
    """
    Audits a journal issue
    """
    def audit(self, data: Union[None, str]) -> None:
        issue = data
        
        if not issue:
            self.valid = False
            self.errors = ["missing journal issue"]
            return

        valid = True
        errors = []

        try:
            issue = int(issue)
        except ValueError:
            valid = False
            errors.append("unconvertable to int")

            self.valid = valid
            self.errors = errors
            return

        if issue < 0:
            valid = False
            errors.append("negative issue")
        
        self.valid = valid
        self.errors = errors

class AuditPages(AbstractAudit):
    """
    Audits a journal pages
    """
    def audit(self, data: Union[None, str]) -> None:
        valid = True
        errors = []

        if not data:
            self.valid = False
            self.errors = ["missing pages"]
            return

        pages = data.split("-")

        if len(pages) == 1:
            try:
                _ = int(pages[0])
            except ValueError:
                valid = False
                errors.append("unconvertable to int")

        elif len(pages) == 2:
            try:
                _ = int(pages[0])
            except ValueError:
                valid = False
                errors.append("unconvertable first page")
            try:
                _ = int(pages[1])
            except ValueError:
                valid = False
                errors.append("unconvertable final page")
        else:
            valid = False
            errors.append("pages should just be first-final page")

        self.valid = valid
        self.errors = errors

class AuditDOI(AbstractAudit):
    """
    Audits a journal doi
    """
    def audit(self, data: Union[None, str]) -> None:
        valid = True
        errors = []

        if not data:
            self.valid = False
            self.errors = ["missing doi"]
            return
        
        doi = data.split("/")

        if len(doi) != 2:
            valid = False
            errors.append("missing prefix/postfix")
        
        prefix = doi[0].split(".")
        if len(prefix) < 2:
            valid = False
            errors.append("missing prefix namespace")

        self.valid = valid
        self.errors = errors

class AuditUrlPubmed(AbstractAudit):
    """
    Audits a journal pubmed url
    """
    def audit(self, data: Union[None, str]) -> None:
        url = data

        valid = True
        errors = []

        if not data:
            self.valid = False
            self.errors = ["missing pubmed url"]
            return

        if url[:36] != "https://www.ncbi.nlm.nih.gov/pubmed/":
            valid = False
            errors.append("incorrect pubmed url")

        audit = AuditUrl()
        audit.audit(data)

        if not audit.valid:
            valid = False
            errors.extend(audit.errors)

        self.valid = valid
        self.errors = errors

class AuditUrlDOI(AbstractAudit):
    """
    Audits a journal DOI url
    """
    def audit(self, data: Union[None, str]) -> None:
        url = data

        valid = True
        errors = []

        if not data:
            self.valid = False
            self.errors = ["missing doi url"]
            return

        if url[:16] != "https://doi.org/":
            valid = False
            errors.append("incorrect doi url")

        audit = AuditUrl()
        audit.audit(data)

        if not audit.valid:
            valid = False
            errors.extend(audit.errors)

        self.valid = valid
        self.errors = errors
    
    def audit_doi(self, data: Union[None, str], doi: Union[None, str]) -> None:
        """
        Check doi with url
            :param data: the doi_url
            :param doi: the doi 
        """
        if not data and not doi:
            return

        if not data:
            self.valid = False
            self.errors.append("known doi, unknown url")
        elif not doi:
            self.valid = False
            self.errors.append("known url, unknown doi")
        elif data[16:] != doi:
            self.valid = False
            self.errors.append("doi unequal between doi and url")

class AuditReferences(AbstractAuditList):
    """
    Audits the fluorophore's references
    """
    def audit(self, data: Union[None, List[Reference]]) -> None:
        self.audits.clear()
        if data:
            for ref in data:
                self.audits.append(AuditReference(ref))
        self.audit_list()

class AuditReference(AbstractAudit):
    """
    Audits a fluorophore's reference (can be an url or a paper reference)
    """
    def __init__(self, data: Union[None, Reference]=None):
        super().__init__()
        self.is_url: bool = False

        self.url: AuditUrl = AuditUrl()
        self.title: AuditTitle = AuditTitle()
        self.authors: AuditAuthors = AuditAuthors()
        self.year: AuditYear = AuditYear()
        self.journal: AuditJournal = AuditJournal()
        self.volume: AuditVolume = AuditVolume()
        self.issue: AuditIssue = AuditIssue()
        self.pages: AuditPages = AuditPages()
        self.doi: AuditDOI = AuditDOI()
        self.url_pubmed: AuditUrlPubmed = AuditUrlPubmed()
        self.url_doi: AuditUrlDOI = AuditUrlDOI()

        if data:
            self.audit(data)
    
    def reset(self) -> None:
        self.valid = False
        self.errors = []
        
        self.is_url = False
        self.url.reset()
        self.title.reset()
        self.authors = []
        self.year.reset()
        self.journal.reset()
        self.volume.reset()
        self.issue.reset()
        self.pages.reset()
        self.doi.reset()
        self.url_pubmed.reset()
        self.url_doi.reset()

    def audit(self, data: Union[None, Reference]) -> None:
        """ Checks validity of the references """
        if not data:
            self.valid = False
            self.errors = "missing reference"
            return
        
        if data.url:
            self.is_url = True
            self.url.audit(data.url)
            return

        self.is_url = False

        self.title.audit(data.title)
        self.authors.audit(data.authors)
        self.year.audit(data.year)
        self.journal.audit(data.journal)
        self.volume.audit(data.volume)
        self.issue.audit(data.issue)
        self.pages.audit(data.pages)
        self.doi.audit(data.doi)
        self.url_pubmed.audit(data.url_pubmed)
        self.url_doi.audit(data.url_doi)
        self.url_doi.audit_doi(data.url_doi, data.doi)

        valid = True
        errors = []
        if self.is_url:
            if not self.url.valid:
                valid = False
                errors.extend([f"url:{error}" for error in self.url.errors])
        else:
            if not self.title.valid:
                valid = False
                errors.extend([f"title:{error}" for error in self.title.errors])
            
            for i, author in enumerate(self.authors):
                if not author.valid:
                    valid = False
                    errors.extend([f"author[{i}]:{error}" for error in author.errors])
            
            if not self.year.valid:
                valid = False
                errors.extend([f"year:{error}" for error in self.year.errors])

            if not self.journal.valid:
                valid = False
                errors.extend([f"journal:{error}" for error in self.journal.errors])

            if not self.volume.valid:
                valid = False
                errors.extend([f"volume:{error}" for error in self.volume.errors])

            if not self.issue.valid:
                valid = False
                errors.extend([f"issue:{error}" for error in self.issue.errors])

            if not self.pages.valid:
                valid = False
                errors.extend([f"pages:{error}" for error in self.pages.errors])

            if not self.doi.valid:
                valid = False
                errors.extend([f"doi:{error}" for error in self.doi.errors])

            if not self.url_doi.valid:
                valid = False
                errors.extend([f"url_doi:{error}" for error in self.url_doi.errors])

            if not self.url_pubmed.valid:
                valid = False
                errors.extend([f"url_pubmed:{error}" for error in self.url_pubmed.errors])
        
        if not valid:
            self.valid = False
            self.errors = errors
        else:
            self.valid = True
            self.errors = []

    def __repr__(self) -> str:
        if self.valid:
            return "(T)"
        else:
            return f"(F:{self.errors[0]})"
    
    def __str__(self) -> str:
        if self.valid:
            return "(T)"
        else:
            text = f"(F:{self.errors[0]}:\n> "
            subtext = self.serialize()
            text += subtext + "\n)"
            return text

    def serialize(self, ignore_valid=False) -> str:
        if self.valid and ignore_valid:
            return ""

        text = ""
        if self.is_url:
            text += self.url.serialize(ignore_valid)
            return text

        for key in ["title", "authors", "year", "journal", "volume", "issue", "pages", "doi", "url_pubmed", "url_doi"]:
            audit = getattr(self, key)
            if text:
                subtext = "\n"
            else:
                subtext = ""

            if audit.valid and ignore_valid:
                continue

            elif audit.valid:
                subtext += f"T:{key}"

            else:
                if isinstance(audit, (AbstractAuditList, AuditReference, AuditSpectrum)):
                    subtext += f"F:{key}:"
                    ssubtext = f"\n{audit.serialize(ignore_valid)}"
                    ssubtext = ssubtext.replace("\n", "\n> ")
                    subtext += ssubtext
                else:
                    subtext += f"F:{key}:{audit.serialize(ignore_valid)}"
            
            text += subtext 

        return text

class AuditExtinctionCoefficient(AbstractAudit):
    """
    Audits the fluorophore enable parameter
    """
    def audit(self, data: Union[None, int]) -> None:
        """ Checks validity of extinction coefficient """
        if not data:
            if data == 0:
                self.valid = False
                self.errors = ["value is 0"]
                return

            self.valid = False
            self.errors = ["missing"]
            return

        try:
            _ = int(data)
        except ValueError:
            self.valid = False
            self.errors = ["non int"]
        else:
            self.valid = True
            self.errors = []

class AuditQuantumYield(AbstractAudit):
    """
    Audits the fluorophore quantum yield parameter
    """
    def audit(self, data: Union[None, float]) -> None:
        """ Checks validity of quantum yield """
        if not data:
            if data == 0:
                self.valid = False
                self.errors = ["value is 0"]
                return
            self.valid = False
            self.errors = ["missing"]
            return

        try:
            _ = float(data)
        except ValueError:
            self.valid = False
            self.errors = ["non float"]
        else:
            self.valid = True
            self.errors = []

class AuditCrossSection(AbstractAudit):
    """
    Audits the fluorophore cross section parameter
    """
    def audit(self, data: Union[None, float]) -> None:
        """ Checks validity of cross section """
        if not data:
            if data == 0:
                self.valid = False
                self.errors = ["value is 0"]
                return
            self.valid = False
            self.errors = ["missing"]
            return

        try:
            _ = float(data)
        except ValueError:
            self.valid = False
            self.errors = ["non float"]
        else:
            self.valid = True
            self.errors = []

class AuditBrightness(AbstractAudit):
    """
    Audits the fluorophore brightness parameter
    """
    def audit(self, data: Union[None, float]) -> None:
        """ Checks validity of brightness """
        if not data:
            if data == 0:
                self.valid = False
                self.errors = ["value is 0"]
                return
            self.valid = False
            self.errors = ["missing"]
            return

        try:
            _ = float(data)
        except ValueError:
            self.valid = False
            self.errors = ["non float"]
        else:
            self.valid = True
            self.errors = []

    def audit_brightness(self, data: Union[None, float], data_calc: Union[None, float]) -> None:
        if not data or not data_calc:
            return
        
        # Keep in mind floatpoint operations have small imperfections
        substract = abs(data - data_calc)
        if substract > 0.00001:
            self.valid = False
            self.errors.append("ec * qy is unequal to this brightness")

class AuditBrightnessBin(AbstractAudit):
    """
    Audits the fluorophore brightness parameter
    """
    def audit(self, data: Union[None, int]) -> None:
        """ Checks validity of the brightness bin """
        if not data:
            if data == 0:
                self.valid = False
                self.errors = ["value is 0"]
                return
            self.valid = False
            self.errors = ["missing"]
            return

        if data < 1 or data > 5:
            self.valid = False
            self.errors = ["must be a value between 1-5"]
        else:
            self.valid = True
            self.errors = []

class AuditSpectrumWavelength(AbstractAudit):
    """
    Audits the fluorophore spectrum wavelength parameter
    """
    def audit(self, data: Union[None, List[float]]) -> None:
        valid = True
        errors = []

        if not data:
            self.valid = False
            self.errors = ["missing wavelength"]
            return
        
        if len(data) <= 2:
            valid = False
            errors.append("wavelength contains <= 2 data points")
        
        # Check wavelength ordering and stepsize
        valid_stepsize = True
        valid_value_min = True
        valid_value_max = True
        valid_double = True
        valid_order = True
        prev_point = data[0] - 1.0
        stepsize = 1
        for point in data:
            if point < 0:
                valid_value_min = False
            if point > 2000:
                valid_value_max = False
            if point == prev_point:
                valid_double = False
            if point < prev_point:
                valid_order = False
            if point - prev_point != 1:
                valid_stepsize = False
                stepsize = point - prev_point
            prev_point = point

        if not valid_stepsize:
            valid = False
            errors.append(f"illegal stepsize {stepsize}")
        if not valid_value_min:
            valid = False
            errors.append("contains entree <0")
        if not valid_value_max:
            valid = False
            errors.append("contains entree >2000")
        if not valid_double:
            valid = False
            errors.append("contains double entrees")
        if not valid_order:
            valid = False
            errors.append("order not from low-to-high")

        self.valid = valid
        self.errors = errors

class AuditSpectrumIntensity(AbstractAudit):
    """
    Audits the fluorophore spectrum intensity parameter
    """
    def audit(self, data: Union[None, List[float]]) -> None:
        valid = True
        errors = []

        if not data:
            self.valid = False
            self.errors = ["missing intensity"]
            return

        if len(data) <= 2:
            valid = False
            errors.append("intensity contains <= 2 data points")

        # Check intensity values
        valid_value_min = True
        valid_value_max = True
        max_intensity_value = data[0]
        min_intensity_value = data[0]
        for point in data:
            if point < 0:
                valid_value_min = False
            if point > 100:
                valid_value_max = False
            if point > max_intensity_value:
                max_intensity_value = point
            elif point < min_intensity_value:
                min_intensity_value = point

        if not valid_value_min:
            valid = False
            errors.append("contains entree <0")
        if not valid_value_max:
            valid = False
            errors.append("contains entree >100")
        if max_intensity_value != 100:
            valid = False
            errors.append(f"maximum intensity value is {max_intensity_value}, should be 100")
        if min_intensity_value != 0:
            valid = False
            errors.append(f"minimum intensity value is {min_intensity_value}, should be 0")

        self.valid = valid
        self.errors = errors

class AuditSpectrum(AbstractAudit):
    """
    Audits the fluorophore spectrum parameter
    """
    def __init__(self, wavelength: Union[None, List[float]]=None, intensity: Union[None, List[float]]=None) -> None:
        super().__init__()

        if (not wavelength) ^ (not intensity):
            raise ValueError("none or both wavelength and intensity has to be declared")

        self.wavelength_missing = True
        self.wavelength: AuditSpectrumWavelength = AuditSpectrumWavelength()
        
        self.intensity_missing = True
        self.intensity: AuditSpectrumIntensity = AuditSpectrumIntensity()

        if wavelength and intensity:
            self.audit(wavelength, intensity)

    def reset(self) -> None:
        self.valid = False
        self.errors.clear()
        self.errors.append("unchecked")

        self.wavelength_missing = True
        self.wavelength.reset()
        self.intensity_missing = True
        self.intensity.reset()

    def audit(self, wavelength: Union[None, List[float]], intensity: Union[None, List[float]]) -> None:
        """
        checks the validity of the absorption curve
        """
        valid = True
        errors = []

        # Check for missing data
        if not wavelength:
            self.wavelength_missing = True
            errors.append("missing wavelength data")
        else:
            self.wavelength_missing = False
        
        if not intensity:
            self.intensity_missing = True
            errors.append("missing intensity data")
        else:
            self.intensity_missing = False
        
        if self.intensity_missing or self.wavelength_missing:
            self.valid = False
            self.errors = errors
            return

        # Check length
        if len(intensity) != len(wavelength):
            valid = False
            errors.append("wavelength and intensity arent of equal length")

        self.wavelength.audit(wavelength)
        self.intensity.audit(intensity)

        if not self.wavelength.valid or not self.intensity.valid:
            self.valid = False
            errors.extend(self.wavelength.errors)
            errors.extend(self.intensity.errors)
        else:
            self.valid = valid

        self.errors = errors
    
    def __repr__(self) -> str:
        if self.valid:
            return "(T)"
        else:
            if self.wavelength_missing or self.intensity_missing:
                return "(F:missing data)"
            else:
                errors = len(self.wavelength.errors) + len(self.intensity.errors)
                return f"(F:{errors} errors)"
    
    def __str__(self) -> str:
        if self.valid:
            return "(T)"
        else:
            if self.wavelength_missing or self.intensity_missing:
                return "(F:missing data)"
            else:
                text = f"(F:\n> "
                subtext = self.serialize()
                subtext = subtext.replace("\n", "\n> ")
                text += subtext + "\n)"
            return text

    def serialize(self, ignore_valid=False) -> str:
        if self.valid and ignore_valid:
            return ""

        if self.valid:
            return "T:wavelength\nT:intensity"

        text = ""
        if self.wavelength_missing:
            text += "F:wavelength:[missing]\n"
        elif self.wavelength.valid and ignore_valid:
            pass
        elif self.wavelength.valid:
            text += "T:wavelength\n"
        else:
            text += f"F:wavelength:{self.wavelength.serialize(ignore_valid)}\n"

        if self.intensity_missing:
            text += "F:intensity:[missing]"
        elif self.intensity.valid and ignore_valid:
            pass
        elif self.intensity.valid:
            text += "T:intensity"
        else:
            text += f"F:intensity:{self.intensity.serialize(ignore_valid)}"

        return text
