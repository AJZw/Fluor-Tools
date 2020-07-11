# -*- coding: utf-8 -*-

## Fluor Tools Viewer ########################################################
# Author:     AJ Zwijnenburg
# Version:    v1.0
# Date:       2019-06-27
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

from __future__ import annotations
from typing import Dict

from PyQt5 import QtCore, QtGui, QtWidgets
from enum import Enum

import os
import time
import copy

from tools.viewer._widgets_graph import GraphPlotLayout

from .. import json, Format, Source
from ..auditor import Auditor, AuditNames, AuditHeader
from .reader import MappedReader, Identifier, Header, Data, Reference

class LineType(Enum):
    Absorption = 0,
    Excitation = 1,
    TwoPhoton = 2,
    Emission = 3

class SpecialFunctionType(Enum):
    Invalid = 0
    Normalize = 1
    CutoffMin = 2
    CutoffMax = 3
    Strip = 4
    StripExact = 5
    RemoveGap = 6
    SmoothSG = 7

class FolderDialog(QtWidgets.QFileDialog):
    """
    The dialog for setting the import folder
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFileMode(QtWidgets.QFileDialog.Directory)
        self.setViewMode(QtWidgets.QFileDialog.List)
        self.setDirectory(QtCore.QDir.homePath())

class SaveDialog(QtWidgets.QFileDialog):
    """
    The dialog for setting the import folder
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFileMode(QtWidgets.QFileDialog.AnyFile)
        self.setViewMode(QtWidgets.QFileDialog.List)
        self.setDirectory(QtCore.QDir.homePath())
        self.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        self.setNameFilters(["Javascript object notation (*.json)"]) #, "Configuration file (*.ini)"])

class ActiveButton(QtWidgets.QPushButton):
    """
    Button with an active and inactive state
        :param text[str]: text of the button
        :param parent[QWidget]: parent
    """
    sendActivated = QtCore.pyqtSignal(bool)

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.active = False
        self.setActive(self.active)

        self.clicked.connect(self.toggleActive)

    def toggleActive(self, enabled):
        """
        Receives clicked signal, and activates stylesheet change
            :param enabled[bool]: (unused) whether the button is enabled or not
        """
        # enabled is necessary for signal slot mechanism
        del enabled

        self.setActive(not self.active)
        self.sendActivated.emit(self.active)

    def setActive(self, active=False):
        """
        Set the button active/inactive state
            :param active[bool]: state
        """
        if active != self.active:
            self.active = active

            if self.active is True:
                self.setStyleSheet("font-weight: bold")
            else:
                self.setStyleSheet("font-weight: italic")

class QCButton(QtWidgets.QPushButton):
    """
    A 'button' to show whether a value passed or failed quality control
        :param parent[QtWidget]: (optional) parent
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEnabled(False)
        self.setText("")
        self.passed = None

        # Stylesheets
        self.style_passed = """
            padding: 2px;
            background-color: #00CC00;
            border-style: solid;
            border-width: 1;
            border-color: #00B300;
            margin-left: 0;
            width: 2px;
            """
        
        self.style_failed = """
            padding: 2px;
            background-color: #FF4D4D;
            border-style: solid;
            border-width: 1;
            border-color: #FF0000;
            margin-left: 0;
            width: 2px;
            """
        
        self.fail_reasons = []

        self.setPassed(False)

    @QtCore.pyqtSlot(bool, list)
    def setPassed(self, passed, reasons=[]):
        """
        Sets the style based on whether the QC is passed of failed
            :param passed[bool]: passed = True, failed = False
            :param reasons[list[str]]: the reasons QC failed
        """
        self.passed = passed
        self.fail_reasons = reasons

        if passed:
            self.setStyleSheet(self.style_passed)
            self.setToolTip("Quality Control: Passed")
        else:
            self.setStyleSheet(self.style_failed)

            fail = "Quality Control: Failed"
            for reason in self.fail_reasons:
                fail += "\n " + reason
            
            self.setToolTip(fail)

class SpecialPopup(QtWidgets.QDialog):
    """
    Popup (if you do not give it a parent). For specialised function selection and parameter input.
        :parent [QWidget]: parent
    """
    sendFunction = QtCore.pyqtSignal(SpecialFunctionType, object, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)

        # Build layout
        self.setWindowTitle("Special Functions")
        self.widget_layout = QtWidgets.QGridLayout()
        self.widget_layout.setColumnStretch(0, 0)
        self.widget_layout.setColumnStretch(1, 1)
        self.widget_layout.setColumnStretch(2, 1)
        
        self.setLayout(self.widget_layout)

        # Label
        self.label = QtWidgets.QLabel(self)
        self.label.setText(" Select a function to perform:")
        self.widget_layout.addWidget(self.label, 1, 0, 1, -1)

        # Normalize function
        self.norm_widget = QtWidgets.QPushButton(self)
        self.norm_widget.setText("Normalize")
        self.norm_widget.setToolTip("Normalizes the curve so that its intensity fits in between min-max")
        self.norm_widget.clicked.connect(lambda: self.parse_norm())
        self.norm_input_a = QtWidgets.QLineEdit(self)
        self.norm_input_a.setText("none")
        self.norm_input_a.setToolTip("Minimum value")
        self.norm_input_a.textEdited.connect(lambda: self.check_norm())
        self.norm_input_b = QtWidgets.QLineEdit(self)
        self.norm_input_b.setText("none")
        self.norm_input_b.setToolTip("Maximum value")
        self.norm_input_b.textEdited.connect(lambda: self.check_norm())
        self.widget_layout.addWidget(self.norm_widget, 2, 0)
        self.widget_layout.addWidget(self.norm_input_a, 2, 1)
        self.widget_layout.addWidget(self.norm_input_b, 2, 2)

        # Cutoff min
        self.cutoff_min_widget = QtWidgets.QPushButton(self)
        self.cutoff_min_widget.setText("Cutoff min")
        self.cutoff_min_widget.setToolTip("Cutoffs all values below the value")
        self.cutoff_min_widget.clicked.connect(lambda: self.parse_cutoff_min())
        self.cutoff_min_input = QtWidgets.QLineEdit(self)
        self.cutoff_min_input.setText("0.0")
        self.cutoff_min_input.setToolTip("Minimum cutoff")
        self.cutoff_min_input.textEdited.connect(lambda: self.check_cutoff_min())
        self.widget_layout.addWidget(self.cutoff_min_widget, 3, 0)
        self.widget_layout.addWidget(self.cutoff_min_input, 3, 1)
        
        # Cutoff max
        self.cutoff_max_widget = QtWidgets.QPushButton(self)
        self.cutoff_max_widget.setText("Cutoff max")
        self.cutoff_max_widget.setToolTip("Cutoffs all values above the value")
        self.cutoff_max_widget.clicked.connect(lambda: self.parse_cutoff_max())
        self.cutoff_max_input = QtWidgets.QLineEdit(self)
        self.cutoff_max_input.setText("100.0")
        self.cutoff_max_input.setToolTip("Maximum cutoff")
        self.cutoff_max_input.textEdited.connect(lambda: self.check_cutoff_max())
        self.widget_layout.addWidget(self.cutoff_max_widget, 4, 0)
        self.widget_layout.addWidget(self.cutoff_max_input, 4, 1)
        
        # Strip
        self.strip_widget = QtWidgets.QPushButton(self)
        self.strip_widget.setText("Strip below")
        self.strip_widget.setToolTip("Removes all values below the value on both side of the curve")
        self.strip_widget.clicked.connect(lambda: self.parse_strip())
        self.strip_input = QtWidgets.QLineEdit(self)
        self.strip_input.setText("0.0")
        self.strip_input.setToolTip("Minimum strip value")
        self.strip_input.textEdited.connect(lambda: self.check_strip())
        self.widget_layout.addWidget(self.strip_widget, 5, 0)
        self.widget_layout.addWidget(self.strip_input, 5, 1)
        
        # Strip exact
        self.strip_exact_widget = QtWidgets.QPushButton(self)
        self.strip_exact_widget.setText("Strip exact")
        self.strip_exact_widget.setToolTip("Removes all values exactly of value on both side of the curve")
        self.strip_exact_widget.clicked.connect(lambda: self.parse_strip_exact())
        self.strip_exact_input = QtWidgets.QLineEdit(self)
        self.strip_exact_input.setText("0.0")
        self.strip_exact_input.setToolTip("Strip value")
        self.strip_exact_input.textEdited.connect(lambda: self.check_strip_exact())
        self.widget_layout.addWidget(self.strip_exact_widget, 6, 0)
        self.widget_layout.addWidget(self.strip_exact_input, 6, 1)

        # Remove gap
        self.remove_gap_widget = QtWidgets.QPushButton(self)
        self.remove_gap_widget.setText("Remove gaps")
        self.remove_gap_widget.setToolTip("Removes gaps of the specified value from the curve")
        self.remove_gap_widget.clicked.connect(lambda: self.parse_remove_gap())
        self.remove_gap_input = QtWidgets.QLineEdit(self)
        self.remove_gap_input.setText("0.0")
        self.remove_gap_input.setToolTip("Gap value")
        self.remove_gap_input.textEdited.connect(lambda: self.check_remove_gap())
        self.widget_layout.addWidget(self.remove_gap_widget, 7, 0)
        self.widget_layout.addWidget(self.remove_gap_input, 7, 1)


        # Smooth savgol
        self.smooth_sg_widget = QtWidgets.QPushButton(self)
        self.smooth_sg_widget.setText("Smooth (savgol)")
        self.smooth_sg_widget.setToolTip("Smooths the curve using Savitsky-Golay filtering")
        self.smooth_sg_widget.clicked.connect(lambda: self.parse_smooth_sg())
        self.smooth_sg_input_a = QtWidgets.QLineEdit(self)
        self.smooth_sg_input_a.setText("6")
        self.smooth_sg_input_a.setToolTip("Width")
        self.smooth_sg_input_a.textEdited.connect(lambda: self.check_smooth_sg())
        self.smooth_sg_input_b = QtWidgets.QLineEdit(self)
        self.smooth_sg_input_b.setText("2")
        self.smooth_sg_input_b.setToolTip("Degree")
        self.smooth_sg_input_b.textEdited.connect(lambda: self.check_smooth_sg())
        self.widget_layout.addWidget(self.smooth_sg_widget, 8, 0)
        self.widget_layout.addWidget(self.smooth_sg_input_a, 8, 1)
        self.widget_layout.addWidget(self.smooth_sg_input_b, 8, 2)

        # Cancel
        self.cancel = QtWidgets.QPushButton(self)
        self.cancel.setText("Cancel")
        self.cancel.clicked.connect(lambda: self.hide())
        self.widget_layout.addWidget(self.cancel, 9, 0, 1, -1)

    def hide(self):
        """ Overload: restore the widget to default after hiding it """
        super().hide()

        self.reset_norm()
        self.reset_cutoff_min()
        self.reset_cutoff_max()
        self.reset_strip()
        self.reset_strip_exact()
        self.reset_smooth_sg()
    
    def closeEvent(self, event):
        """ Overload: close event, to reset the widget after closing it"""
        super().closeEvent(event)

        self.reset_norm()
        self.reset_cutoff_min()
        self.reset_cutoff_max()
        self.reset_strip()
        self.reset_strip_exact()
        self.reset_smooth_sg()

    def reset_norm(self):
        """ Restores the normalize widget to default """
        self.norm_widget.setEnabled(True)
        self.norm_input_a.setText("none")
        self.norm_input_b.setText("none")

    def reset_cutoff_min(self):
        """ Restores the cutoff min widget to default """
        self.cutoff_min_widget.setEnabled(True)
        self.cutoff_min_input.setText("0.0")

    def reset_cutoff_max(self):
        """ Restores the cutoff max widget to default """
        self.cutoff_max_widget.setEnabled(True)
        self.cutoff_max_input.setText("100.0")
    
    def reset_strip(self):
        """ Restores the strip widget to default """
        self.strip_widget.setEnabled(True)
        self.strip_input.setText("0.0")
    
    def reset_strip_exact(self):
        """ Restores the strip exact widget to default """
        self.strip_exact_widget.setEnabled(True)
        self.strip_exact_input.setText("0.0")
    
    def reset_smooth_sg(self):
        """ Restores the strip exact widget to default """
        self.smooth_sg_widget.setEnabled(True)
        self.smooth_sg_input_a.setText("6")
        self.smooth_sg_input_b.setText("2")

    def check_norm(self):
        """ Checks validity of input values for normalisation. Enables/Disables the button based on validity"""
        text_a = self.norm_input_a.text()
        valid_a = False
        if text_a == "none" or text_a == "None" or text_a == "":
            valid_a = True
        else:
            try:
                float(text_a)
            except:
                pass
            else:
                valid_a = True
        
        text_b = self.norm_input_b.text()
        valid_b = False
        if text_b == "none" or text_b == "None" or text_b == "":
            valid_b = True
        else:
            try:
                float(text_b)
            except:
                pass
            else:
                valid_b = True

        if not valid_a or not valid_b:
            self.norm_widget.setEnabled(False)
        else:
            self.norm_widget.setEnabled(True)

    def check_cutoff_min(self):
        """ Checks validty of input values for cutoff minimum. Enables/Disables the button based on validity"""
        text = self.cutoff_min_input.text()
        valid = False

        try:
            float(text)
        except:
            pass
        else:
            valid = True
        
        if not valid:
            self.cutoff_min_widget.setEnabled(False)
        else:
            self.cutoff_min_widget.setEnabled(True)

    def check_cutoff_max(self):
        """ Checks validty of input values for cutoff minimum. Enables/Disables the button based on validity"""
        text = self.cutoff_max_input.text()
        valid = False

        try:
            float(text)
        except:
            pass
        else:
            valid = True
        
        if not valid:
            self.cutoff_max_widget.setEnabled(False)
        else:
            self.cutoff_max_widget.setEnabled(True)
    
    def check_strip(self):
        """ Checks validty of input values for strip. Enables/Disables the button based on validity"""
        text = self.strip_input.text()
        valid = False

        try:
            float(text)
        except:
            pass
        else:
            valid = True
        
        if not valid:
            self.strip_widget.setEnabled(False)
        else:
            self.strip_widget.setEnabled(True)
    
    def check_strip_exact(self):
        """ Checks validty of input values for strip exact. Enables/Disables the button based on validity"""
        text = self.strip_exact_input.text()
        valid = False

        try:
            float(text)
        except:
            pass
        else:
            valid = True
        
        if not valid:
            self.strip_exact_widget.setEnabled(False)
        else:
            self.strip_exact_widget.setEnabled(True)

    def check_remove_gap(self):
        """ Checks validty of input values for remove gap. Enables/Disables the button based on validity"""
        text = self.remove_gap_input.text()
        valid = False

        try:
            float(text)
        except:
            pass
        else:
            valid = True
        
        if not valid:
            self.remove_gap_widget.setEnabled(False)
        else:
            self.remove_gap_widget.setEnabled(True)

    def check_smooth_sg(self):
        """ Checks validity of input values for smooth savgol. Enables/Disables the button based on validity"""
        text_a = self.smooth_sg_input_a.text()
        valid_a = False
        if "." in text_a:
            valid_a = False
        else:
            try:
                as_int = int(text_a)
            except:
                pass
            else:
                if as_int < 1:
                    valid_a = False
                else:
                    valid_a = True
        
        text_b = self.smooth_sg_input_b.text()
        valid_b = False
        if "." in text_b:
            valid_b = False
        else:
            try:
                as_int = int(text_b)
            except:
                pass 
            else:
                if as_int < 1:
                    valid_b = False
                else:
                    valid_b = True

        if not valid_a or not valid_b:
            self.smooth_sg_widget.setEnabled(False)
        else:
            self.smooth_sg_widget.setEnabled(True)

    def parse_norm(self):
        """ parses and emits normalisation input """
        text_a = self.norm_input_a.text()
        input_a = 0.0
        if text_a == "none" or text_a == "None" or text_a == "":
            input_a = None
        else:
            input_a = float(text_a)

        text_b = self.norm_input_b.text()
        input_b = 0.0
        if text_b == "none" or text_b == "None" or text_b == "":
            input_b = None
        else:
            input_b = float(text_b)

        self.sendFunction.emit(SpecialFunctionType.Normalize, input_a, input_b)
        self.hide()

    def parse_cutoff_min(self):
        """ parses and emits cutoff min input """
        input_a = float(self.cutoff_min_input.text())

        self.sendFunction.emit(SpecialFunctionType.CutoffMin, input_a, None)
        self.hide()
    
    def parse_cutoff_max(self):
        """ parses and emits cutoff max input """
        input_a = float(self.cutoff_max_input.text())

        self.sendFunction.emit(SpecialFunctionType.CutoffMax, input_a, None)
        self.hide()
    
    def parse_strip(self):
        """ parses and emits strip input """
        input_a = float(self.strip_input.text())

        self.sendFunction.emit(SpecialFunctionType.Strip, input_a, None)
        self.hide()
    
    def parse_strip_exact(self):
        """ parses and emits strip exact input """
        input_a = float(self.strip_exact_input.text())

        self.sendFunction.emit(SpecialFunctionType.StripExact, input_a, None)
        self.hide()

    def parse_remove_gap(self):
        """ parses and emits remove gap input """
        input_a = float(self.remove_gap_input.text())

        self.sendFunction.emit(SpecialFunctionType.RemoveGap, input_a, None)
        self.hide()

    def parse_smooth_sg(self):
        """ parses and emits strip exact input """
        input_a = int(self.smooth_sg_input_a.text())
        input_b = int(self.smooth_sg_input_b.text())

        self.sendFunction.emit(SpecialFunctionType.SmoothSG, input_a, input_b)
        self.hide()

class SelectPushButton(QtWidgets.QPushButton):
    """
    Custom QPushButton to show non-interactive wavelength data.
        :param parent: calls parent's callPushButton() function upon pressedEvent()
    """
    pressedButton = QtCore.pyqtSignal()
    def __init__(self, parent):
        super().__init__(parent)
        self.setMinimumWidth(2)
        self.setText("")
        self.pressed.connect(self.pressedEvent)

    def pressedEvent(self):
        """
        Runs upon pressed QEvent; calls parents callPushButton() function
        """
        self.pressedButton.emit()

    def resetSelf(self):
        """ resets LaserPushButton back to 'new' """
        self.setText("")

    @QtCore.pyqtSlot()
    def mainWindowMousePressEvent(self):
        """
        Gets triggered upon a MousePressEvent in the MainWindow, resets text
        """
        self.resetSelf()

class SelectLineEdit(QtWidgets.QLineEdit):
    """
    QLineEdit with a limited texteditor; only accepts decimals in a specific location
        :param parent: parent
    """
    editingFinished = QtCore.pyqtSignal(object)

    def __init__(self, parent):
        super().__init__(parent)
        self.in_focus = False
        # Parameters for proper event handling
        self._eat_focus_out = True
        # Texteditor parameters
        self.text_before = ""
        self.text_after = ""
        self.text_write_length = 9
        self.text_write_start = len(self.text_before)
        self.text_write_end = self.text_write_start + self.text_write_length

        self.setMinimumWidth(2)
        self.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
        self.installEventFilter(self)

        self.setText("{b}{m:_<{l}}{a}".format(b=self.text_before, m="", l=self.text_write_length, a=self.text_after))
        self.setCursorPosition(self.text_write_start)

        self.popup = SelectPopup(self, shape=self.parent().parent())
        self.setProperty("popup", False)

    def setTextParameters(self, before, after, length):
        """
        Sets the texteditor parameters and updates
            :param before[str]: Uneditable text before the edit section
            :param after[str]: Uneditable text after the edit section
            :param length[int]: The length of the edit section
        """
        self.text_before = before
        self.text_after = after
        self.text_write_length = length
        self.text_write_start = len(self.text_before)
        self.text_write_end = self.text_write_start + self.text_write_length

        self.setText("{b}{m:_<{l}}{a}".format(b=self.text_before, m="", l=self.text_write_length, a=self.text_after))
        self.setCursorPosition(self.text_write_start)

    # Texteditor functions
    def eventKeyPress(self, key):
        """
        Adds the key to self.text() taking into account the texteditor limitations. Doesnt check key input.
            :param key[str]: key(s) to be added
        """
        text = self.text()[self.text_write_start:self.text_write_end]
        cursor = self.cursorPosition()
        if cursor < self.text_write_start:
            cursor = self.text_write_start
        elif cursor > self.text_write_end:
            cursor = self.text_write_end

        if self.selectionStart() != -1:
            sel_start = self.selectionStart()
            if sel_start < self.text_write_start:
                sel_start = self.text_write_start
            elif sel_start > self.text_write_end:
                sel_start = self.text_write_end
            sel_end = self.selectionEnd()
            if sel_end <= sel_start:
                sel_end = sel_start
            elif sel_end > self.text_write_end:
                sel_end = self.text_write_end

            cursor = sel_start
            sel_start = sel_start - self.text_write_start
            sel_end = sel_end - self.text_write_start

            text = "{m:_<{l}}".format(m=text[:sel_start] + text[sel_end:], l=self.text_write_length)

        if cursor < self.text_write_end and cursor >= self.text_write_start:
            cursor_loc = cursor - self.text_write_start
            if text[self.text_write_length - 1] == "_":
                text = text[:cursor_loc] + key + text[cursor_loc:-len(key)]
            else:
                text = text[:cursor_loc] + key + text[cursor_loc + len(key):]
            # set text while making sure it doesnt extend past text_write_end
            if len(text) > self.text_write_length:
                text = text[:self.text_write_length]
            self.setText("{b}{m:_<{l}}{a}".format(b=self.text_before, m=text, l=self.text_write_length, a=self.text_after))
            cursor = cursor + len(key)
            if cursor > self.text_write_end:
                cursor = self.text_write_end
            self.setCursorPosition(cursor)

    def setTextValue(self, text):
        """
        Overwrites the texteditors text. Removes non-valid letters and adheres to texteditors limitations.
            :param text[str]: string to be written to the texteditor
        """
        if text:
            text_decimal = ""
            for letter in text:
                if letter.isdecimal():
                    text_decimal = text_decimal + letter
            if len(text_decimal) > self.text_write_length:
                cursor = self.text_write_end
                text_decimal = text_decimal[:self.text_write_length]
            else:
                cursor = self.text_write_start + len(text_decimal)
            self.setText("{b}{m:_<{l}}{a}".format(b=self.text_before, m=text_decimal, l=self.text_write_length, a=self.text_after))
            self.setCursorPosition(cursor)
        else:
            self.clearTextValue()

    def clearTextValue(self):
        """
        Removes all editable text from the texteditor
        """
        self.setText("{b}{m:_<{l}}{a}".format(b=self.text_before, m="", l=self.text_write_length, a=self.text_after))
        self.setCursorPosition(12)

    # Popup functions
    def showPopup(self):
        """
        Shows the popup.
        """
        self._eat_focus_out = True
        self.popup.setCurrentIndex(QtCore.QModelIndex())
        self.popup.show()
        self._eat_focus_out = False

    def hidePopup(self):
        """
        Hides the popup
        """
        self.popup.hide()

    # Functions to connect with parent
    def setWavelength(self, text):
        """
        Transforms text into a wavelength float, emits editingFinished
            :param text[str]: text to be transformed into a float
        """
        wavelength = ""
        for letter in text:
            if letter.isdecimal():
                wavelength += letter
            elif letter == ".":
                wavelength += letter

        if wavelength == "":
            wavelength = None
        else:
            wavelength = float(wavelength)

        self.editingFinished.emit(wavelength)

    def setModel(self, wavelengths):
        """
        Propagates wavelengths to the popup and construct the popup model 
            :param wavelengths[list(floats)]:
        """
        self.popup.buildModel(wavelengths)

    # Set stylesheet state
    def toggleState(self, popup=None):
        """
        Toggle popup property and forces style repainting
            :param popup[bool]: (optional) if defined forces the specified state
        """
        if popup is not None:
            if popup is self.property("popup"):
                return

        # Gets and Sets Toggle state property
        self.setProperty("popup", not self.property("popup"))

        # Reloads stylesheet for the button
        self.style().unpolish(self)
        self.style().polish(self)

    # Event management
    def resetSelf(self):
        """ resets LaserLineEdit back to original status"""
        self.clearTextValue()
        self.popup.buildModel()

    def mainWindowMousePressEvent(self, source, event):
        """
        Gets triggered upon a MousePressEvent in the MainWindow, clears the focus of the widget.
        """
        # Check if click was from within the widget
        if event.type() != QtCore.QEvent.MouseButtonRelease:
            return
        
        if self.rect().contains(self.mapFromGlobal(event.globalPos())):
            return

        if self.popup.rect().contains(self.popup.mapFromGlobal(event.globalPos())):
            return

        if self.in_focus is True:
            self.clearFocus()
        self.editingFinished.emit(None)

    def eventFilter(self, source, event):
        """
        eventFilter() for FocusIn, FocusIN, MouseButtonPress, MouseMove, MouseButtonDblClick, MouseButtonRelase, KeyPress.
            :param source: event's source widget
            :param event: event's QEvent
        """
        #print("LE:", event.type(), flush=True)
        if event.type() == QtCore.QEvent.FocusIn and source is self:
            self.in_focus = True
            return False
        elif event.type() == QtCore.QEvent.FocusOut and source is self:
            if self._eat_focus_out is False:
                if self.popup.isVisible() is True:
                    self.hidePopup()
                self.in_focus = False
            return True

        elif event.type() == QtCore.QEvent.MouseButtonPress:
            if self.popup.isVisible() is False:
                self.showPopup()

            cursor_pos = self.cursorPositionAt(QtCore.QPoint(event.x(), event.y()))
            if cursor_pos < self.text_write_start:
                cursor_pos = self.text_write_start
            elif cursor_pos > self.text_write_end:
                text_count = self.text()[self.text_write_start:self.text_write_end].count("_")
                cursor_pos = self.text_write_end - text_count
            self.setCursorPosition(cursor_pos)
            return True
        elif event.type() == QtCore.QEvent.MouseMove:
            if event.buttons() == QtCore.Qt.LeftButton:
                cursor_pos = self.cursorPosition()
                mouse_pos = self.cursorPositionAt(QtCore.QPoint(event.x(), event.y()))

                if mouse_pos < self.text_write_start:
                    mouse_pos = self.text_write_start
                elif mouse_pos > self.text_write_end:
                    mouse_pos = self.text_write_end

                if self.selectionStart() == -1:
                    self.setSelection(cursor_pos, mouse_pos - cursor_pos)
                else:
                    if self.selectionEnd() == cursor_pos:
                        self.setSelection(self.selectionStart(), mouse_pos - self.selectionStart())
                    elif self.selectionStart() == cursor_pos:
                        self.setSelection(self.selectionEnd(), mouse_pos - self.selectionEnd())
                    else:
                        self.setCursorPosition(mouse_pos)
            return True
        elif event.type() == QtCore.QEvent.MouseButtonDblClick:
            if event.button() == QtCore.Qt.LeftButton:
                self.setSelection(self.text_write_start, self.text_write_length)
            return True
        elif event.type() == QtCore.QEvent.MouseButtonRelease:
            return True
        elif event.type() == QtCore.QEvent.KeyPress:
            if self.popup.isVisible() is False:
                self.showPopup()

            # Implementation of all decimal keys
            if event.key() == QtCore.Qt.Key_0:
                self.eventKeyPress(event.text())
                return True
            elif event.key() == QtCore.Qt.Key_1:
                self.eventKeyPress(event.text())
                return True
            elif event.key() == QtCore.Qt.Key_2:
                self.eventKeyPress(event.text())
                return True
            elif event.key() == QtCore.Qt.Key_3:
                self.eventKeyPress(event.text())
                return True
            elif event.key() == QtCore.Qt.Key_4:
                self.eventKeyPress(event.text())
                return True
            elif event.key() == QtCore.Qt.Key_5:
                self.eventKeyPress(event.text())
                return True
            elif event.key() == QtCore.Qt.Key_6:
                self.eventKeyPress(event.text())
                return True
            elif event.key() == QtCore.Qt.Key_7:
                self.eventKeyPress(event.text())
                return True
            elif event.key() == QtCore.Qt.Key_8:
                self.eventKeyPress(event.text())
                return True
            elif event.key() == QtCore.Qt.Key_9:
                self.eventKeyPress(event.text())
                return True

            # Selection keys
            elif event.key() == QtCore.Qt.Key_Enter or event.key() == QtCore.Qt.Key_Return:
                text = self.text()[self.text_write_start:self.text_write_end]
                self.setWavelength(text)
                self.clearFocus()
                return True
            elif event.key() == QtCore.Qt.Key_Backspace:
                if self.selectionStart() == -1:
                    cursor_pos = self.cursorPosition()
                    if cursor_pos > self.text_write_start and cursor_pos <= self.text_write_end:
                        text = self.text()[self.text_write_start:self.text_write_end]
                        cursor = cursor_pos - self.text_write_start
                        text = text[:cursor-1] + text[cursor:]
                        self.setText("{b}{m:_<{l}}{a}".format(b=self.text_before, m=text, l=self.text_write_length, a=self.text_after))
                        self.setCursorPosition(cursor_pos - 1)
                else:
                    text = self.text()[self.text_write_start:self.text_write_end]
                    sel_start = 0 if self.selectionStart() < self.text_write_start else self.selectionStart() - self.text_write_start
                    sel_end = self.text_write_length if self.selectionEnd() > self.text_write_end else self.selectionEnd() - self.text_write_start
                    text = text[:sel_start] + text[sel_end:]
                    self.setText("{b}{m:_<{l}}{a}".format(b=self.text_before, m=text, l=self.text_write_length, a=self.text_after))
                    self.setCursorPosition(sel_start + self.text_write_start)
                return True
            elif event.key() == QtCore.Qt.Key_Delete:
                if self.selectionStart() == -1:
                    cursor_pos = self.cursorPosition()
                    if cursor_pos >= self.text_write_start and cursor_pos < self.text_write_end:
                        text = self.text()[self.text_write_start:self.text_write_end]
                        cursor = cursor_pos - self.text_write_start
                        text = text[:cursor] + text[cursor + 1:]
                        self.setText("{b}{m:_<{l}}{a}".format(b=self.text_before, m=text, l=self.text_write_length, a=self.text_after))
                        self.setCursorPosition(cursor_pos)
                else:
                    text = self.text()[self.text_write_start:self.text_write_end]
                    sel_start = 0 if self.selectionStart() < self.text_write_start else self.selectionStart() - self.text_write_start
                    sel_end = self.text_write_length if self.selectionEnd() > self.text_write_end else self.selectionEnd() - self.text_write_start
                    text = text[:sel_start] + text[sel_end:]
                    self.setText("{b}{m:_<{l}}{a}".format(b=self.text_before, m=text, l=self.text_write_length, a=self.text_after))
                    self.setCursorPosition(sel_start + self.text_write_start)
                return True
            elif event.key() == QtCore.Qt.Key_Escape:
                self.setText("{b}{m:_<{l}}{a}".format(b=self.text_before, m="", l=self.text_write_length, a=self.text_after))
                self.clearFocus()
                return True
            elif event.key() == QtCore.Qt.Key_Left:
                cursor_pos = self.cursorPosition()
                if cursor_pos > self.text_write_start:
                    if event.modifiers() == QtCore.Qt.ShiftModifier:
                        if self.selectionStart() == -1:
                            self.setSelection(cursor_pos, -1)
                        elif self.selectionStart() == cursor_pos -1:
                            self.setCursorPosition(cursor_pos - 1)
                        elif self.selectionStart() < cursor_pos-1:
                            self.setSelection(self.selectionStart(), self.selectionLength() - 1)
                        else:
                            self.setSelection(self.selectionEnd(), -self.selectionLength() - 1)
                    else:
                        if self.selectionStart() == -1:
                            self.setCursorPosition(cursor_pos - 1)
                        else:
                            self.setCursorPosition(self.selectionStart())
                if cursor_pos == self.text_write_start:
                    if self.selectionStart() != -1 and event.modifiers() != QtCore.Qt.ShiftModifier:
                        self.setCursorPosition(self.text_write_start)

                return True
            elif event.key() == QtCore.Qt.Key_Right:
                cursor_pos = self.cursorPosition()
                if cursor_pos < self.text_write_end:
                    if event.modifiers() == QtCore.Qt.ShiftModifier:
                        if self.selectionStart() == -1:
                            self.setSelection(cursor_pos, 1)
                        elif self.selectionEnd() == cursor_pos + 1:
                            self.setCursorPosition(cursor_pos + 1)
                        elif self.selectionEnd() > cursor_pos + 1:
                            self.setSelection(self.selectionEnd(), -self.selectionLength() + 1)
                        else:
                            self.setSelection(self.selectionStart(), self.selectionLength() + 1)
                    else:
                        if self.selectionStart() == -1:
                            self.setCursorPosition(cursor_pos + 1)
                        else:
                            self.setCursorPosition(self.selectionEnd())
                if cursor_pos == self.text_write_end:
                    if self.selectionStart() != -1 and event.modifiers() != QtCore.Qt.ShiftModifier:
                        self.setCursorPosition(self.text_write_end)
                return True
            elif event.key() == QtCore.Qt.Key_Home:
                self.setCursorPosition(self.text_write_start)
                return True
            elif event.key() == QtCore.Qt.Key_End:
                text = self.text()[self.text_write_start:self.text_write_end].count("_")
                self.setCursorPosition(self.text_write_end - text)
                return True

            # Shortcuts
            elif event.key() == QtCore.Qt.Key_A:
                if event.modifiers() == QtCore.Qt.ControlModifier:
                    self.setSelection(self.text_write_start, self.text_write_length)
                    return True
            elif event.key() == QtCore.Qt.Key_C:
                if event.modifiers() == QtCore.Qt.ControlModifier:
                    if self.selectionStart() != -1:
                        text = self.text()[self.text_write_start:self.text_write_end]
                        sel_start = 0 if self.selectionStart() < self.text_write_start else self.selectionStart() - self.text_write_start
                        sel_end = self.text_write_length if self.selectionEnd() > self.text_write_end else self.selectionEnd() - self.text_write_start
                        QtWidgets.QApplication.clipboard().setText(text[sel_start:sel_end])
                    return True
            elif event.key() == QtCore.Qt.Key_X:
                if event.modifiers() == QtCore.Qt.ControlModifier:
                    if self.selectionStart() != -1:
                        text = self.text()[self.text_write_start:self.text_write_end]
                        sel_start = 0 if self.selectionStart() < self.text_write_start else self.selectionStart() - self.text_write_start
                        sel_end = self.text_write_length if self.selectionEnd() > self.text_write_end else self.selectionEnd() - self.text_write_start
                        QtWidgets.QApplication.clipboard().setText(text[sel_start:sel_end])
                        text = text[:sel_start] + text[sel_end:]
                        self.setText("{b}{m:_<{l}}{a}".format(b=self.text_before, m=text, l=self.text_write_length, a=self.text_after))
                        self.setCursorPosition(sel_start + self.text_write_start)
                    return True
            elif event.key() == QtCore.Qt.Key_V:
                if event.modifiers() == QtCore.Qt.ControlModifier:
                    # Get text from QClipboard and transform into 3 integers -> paste those into the text after the cursor!
                    cursor_pos = self.cursorPosition()

                    if cursor_pos < self.text_write_start or cursor_pos > self.text_write_end:
                        return True

                    clipboard = QtWidgets.QApplication.clipboard().text()
                    text_decimal = ""
                    for letter in clipboard:
                        if letter.isdecimal():
                            text_decimal = text_decimal + letter

                    self.eventKeyPress(text_decimal)
                    return True

            # Ignore other keys
            return True
        elif event.type() == QtCore.QEvent.Show and source is self.popup:
            self.toggleState(popup=True)
            return True
        elif event.type() == QtCore.QEvent.Hide and source is self.popup:
            self.toggleState(popup=False)
            return True
        return super().event(event)

class SelectPopup(QtWidgets.QListView):
    """
    A popup QWidget, alines to parent, and can be shaped inside a layout
        :param parent[QWidget]: parent, QWidget that opens the popup upon activation
        :param data[Data]: Data object
        :param shape[QWidget]: (optional) if None fits inside screen geometry, if defined fits inside QWidget geometry
    """
    def __init__(self, parent, shape=None):
        super().__init__(parent)
        self.shape = shape

        self.max_visible_items = 50
        self.wrap = True
        self._eat_focus_out = True
        self._mouse_pressed = False    # necessary for proper mouse event propagation

        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

        self.setWindowModality(QtCore.Qt.NonModal)

        self.buildModel()
        self.hide()

        self.setParent(self.parent(), QtCore.Qt.Popup)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setFocusPolicy(self.parent().focusPolicy())
        self.setFocusProxy(self.parent())
        self.installEventFilter(self)

        self.setWindowFlag(QtCore.Qt.NoDropShadowWindowHint)
        self.setItemDelegate(QtWidgets.QStyledItemDelegate(self))

        self.clicked.connect(self.signalClicked)

    # Size and painting
    def show(self):
        """
        Adds x, y, width and height correction to show() function.
        Corrects the popup geometry to self.shape, or if self.shape is None to QScreen
        Based upon QCompleterPrivate::showPopup
        """
        if self.shape is None:
            screen_id = QtWidgets.QApplication.desktop().screenNumber(self.parent())
            screen = QtWidgets.QApplication.screens()[screen_id].geometry()
        else:
            screen = self.shape.geometry()
            screen.moveTopLeft(self.shape.mapToGlobal(QtCore.QPoint(0, 0)))

            if self.shape.layout() != 0:
                screen_margins = self.shape.layout().contentsMargins()
                screen = screen.marginsRemoved(screen_margins)

        # set height of the QListView -> +14 depends on padding stylesheet parameter
        height = self.sizeHintForRow(0) * min(self.max_visible_items, self.model().rowCount()) +14

        horizontal_scrollbar = self.horizontalScrollBar()
        if horizontal_scrollbar is True and horizontal_scrollbar.isVisible():
            height += horizontal_scrollbar.sizeHint().height()

        height_parent = self.parent().height()
        pos = self.parent().mapToGlobal(QtCore.QPoint(0, height_parent - 2))
        width = self.parent().width()

        # Adjust x and width to fit in screen QRect
        if width > screen.width():
            width = screen.width()
        if (pos.x() + width) > (screen.x() + screen.width()):
            pos.setX(screen.x() + screen.width() - width)
        if pos.x() < screen.x():
            pos.setX(screen.x())

        # Adjust y and height to fit most efficient in screen QRect
        top = pos.y() - height_parent - screen.top() + 2
        bottom = screen.y() + screen.height() - pos.y()
        height = max(height, self.minimumHeight())
        if height > bottom:
            height = min(max(top, bottom), height)
            if top > bottom:
                pos.setY(pos.y() - height - height_parent + 2)

        self.setGeometry(pos.x(), pos.y(), width, height)
        super().show()

    # ItemModel
    def buildModel(self, wavelengths=None):
        """ 
        Builds and sets model based on list
            :param wavelengths [list(floats)]
        """
        item_model = QtGui.QStandardItemModel()

        if not wavelengths:
            tag = ""
            item = QtGui.QStandardItem(tag)
            item_model.appendRow(item)
        else:
            for wavelength in wavelengths:
                tag = str(round(wavelength, ndigits=1))
                item = QtGui.QStandardItem(tag)
                item_model.appendRow(item)
        
        old_model = self.model()
        self.setModel(item_model)
        if old_model:
            old_model.setParent(None)
            old_model.deleteLater()

    # Signal, slot, and  event handling
    def signalClicked(self, index):
        """
        Runs upon clicked.emit(); calls parent.removeLaser() or setWavelength() and clears parent's focus
            :param index[QModelIndex]: the clicked QModelIndex
        """
        if index.data() == "Remove Laser":
            self.parent().removeLaser()
        else:
            text = index.data()
            self.parent().setWavelength(text)

        self.parent().clearFocus()

    def selectionChanged(self, new_selection, old_selection):
        """
        Gets called by the ItemModel when the selection is changed.
            :param new_selection[QModelIndex]: the new item index
            :param old_selection[QModelIndex]: the previous item index
        """
        del old_selection
        index = new_selection.indexes()
        if index:
            index = index[0]
            if index.data() == "Remove Laser":
                self.parent().clearTextValue()
            else:
                text = index.data()[:3]
                self.parent().setTextValue(text)
        else:
            self.parent().clearTextValue()

    def eventFilter(self, source, event):
        """
        Event filter; Checks if event has to be handled by Popupmenu, otherwise forwards it to self.parent().eventFilter()
        Finally if everything fails, there are some fallback methods.
        Based upon QCompleter::eventFilter.
            :param source: event's source widget
            :param event[QEvent]: event's QEvent
        """
        if event.type() == QtCore.QEvent.Hide or event.type() == QtCore.QEvent.Show:
            self.parent().eventFilter(source, event)
            return True

        if event.type() == QtCore.QEvent.MouseButtonPress:
            if self.underMouse() is False:
                if self.parent().rect().contains(self.parent().mapFromGlobal(event.globalPos())):
                    self._mouse_pressed = True
                    self.parent().eventFilter(source, event)
                else:
                    self.hide()
                return True
            return False
        elif event.type() == QtCore.QEvent.MouseMove:
            if self.underMouse() is False:
                self.parent().eventFilter(source, event)
                return True
            return False
        elif event.type() == QtCore.QEvent.MouseButtonDblClick:
            if self.underMouse() is False:
                if self.parent().rect().contains(self.parent().mapFromGlobal(event.globalPos())):
                    self.parent().eventFilter(source, event)
                return True
            return False
        elif event.type() == QtCore.QEvent.MouseButtonRelease:
            if self._mouse_pressed is True:
                self.parent().eventFilter(source, event)
                self._mouse_pressed = False
                return True
            return False

        if event.type() == QtCore.QEvent.KeyPress and source == self:
            if event.key() == QtCore.Qt.Key_Return or event.type() == QtCore.Qt.Key_Enter:
                index = self.currentIndex()
                self.activated.emit(index)
                if index.isValid():
                    if index.data() == "Remove Laser":
                        self.parent().removeLaser()
                        self.parent().clearFocus()
                        return True

        # Implementation based on C++ source, if you ever want to use a master class keep everything after this:
        if self._eat_focus_out is True and source == self.parent() and event.type() == QtCore.QEvent.FocusOut:
            if self.isVisible() is True:
                return True

        if source != self:
            return False

        if event.type() == QtCore.QEvent.KeyPress:
            key_event = QtGui.QKeyEvent(event)
            cur_index = self.currentIndex()
            # Removed UnFilteredPopup mode stuff

            if key_event.key() == QtCore.Qt.Key_End:
                if event.modifiers() == QtCore.Qt.ControlModifier:
                    return False
            elif key_event.key() == QtCore.Qt.Key_Home:
                if event.modifiers() == QtCore.Qt.ControlModifier:
                    return False
            elif key_event.key() == QtCore.Qt.Key_Up:
                if cur_index.isValid() is False:
                    row_count = self.model().rowCount()
                    last_index = self.model().index(row_count-1, 0)
                    self.setCurrentIndex(last_index)
                    return True
                elif cur_index.row() == 0:
                    if self.wrap is True:
                        self.setCurrentIndex(QtCore.QModelIndex())
                    return True
                return False
            elif key_event.key() == QtCore.Qt.Key_Down:
                if cur_index.isValid() is False:
                    first_index = self.model().index(0, 0)
                    self.setCurrentIndex(first_index)
                    return True
                elif cur_index.row() == self.model().rowCount() - 1:
                    if self.wrap is True:
                        self.setCurrentIndex(QtCore.QModelIndex())
                    return True
                return False
            elif key_event.key() == QtCore.Qt.Key_PageUp:
                return False
            elif key_event.key() == QtCore.Qt.Key_PageDown:
                return False

            # Send event to widget. If accepted, do nothing. Otherwise provide default implementation
            # Modified to sent to eventFilter()
            self._eat_focus_out = False
            accepted = self.parent().eventFilter(source, event)
            self._eat_focus_out = True
            return True
            if accepted is True or self.isVisible() is False:
                if self.parent().hasFocus() is False:
                    self.hide()
                if accepted is True:
                    return True

            if key_event.matches(QtGui.QKeySequence.Cancel):
                self.hide()
                return True

            if key_event.key() == QtCore.Qt.Key_Return:
                self.hide()
            elif key_event.key() == QtCore.Qt.Key_Enter:
                self.hide()
            elif key_event.key() == QtCore.Qt.Key_Tab:
                self.hide()
            elif key_event.key() == QtCore.Qt.Key_F4:
                if key_event.modifiers() == QtCore.Qt.AltModifier:
                    self.hide()
            elif key_event.key() == QtCore.Qt.Key_Backtab:
                self.hide()
            return True

        elif event.type() == QtCore.QEvent.MouseButtonPress:
            if self.underMouse() is False:
                self.hide()
                return True
            return False

        elif event.type() == QtCore.QEvent.InputMethod:
            QtWidgets.QApplication.sendEvent(self.parent(), event)
        elif event.type() == QtCore.QEvent.ShortcutOverride:
            QtWidgets.QApplication.sendEvent(self.parent(), event)

        return False

class ListTab(QtWidgets.QWidget):
    """
    QWidget containing two listviews
        :param parent[QWidget]: parent widget
    """
    sendActivatedData = QtCore.pyqtSignal(Identifier)
    sendActivatedHeader = QtCore.pyqtSignal(str)
    sendExportData = QtCore.pyqtSignal(str, Format)
    sendExportMap = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.data_index: Identifier = None
        self.data_original: Dict[Identifier, Data] = None
        self.data_modified: Dict[Identifier, Data] = None
        self.header_index: str = None
        self.header_map: Dict[str, Header] = None

        #self.installEventFilter(self)

        self.file_path = os.path.dirname(os.path.realpath(__file__))

        self.widget_layout = QtWidgets.QVBoxLayout(self)

        # Header meta data
        self.widget_layout_meta = QtWidgets.QGridLayout()
        self.widget_layout_meta.setColumnStretch(0, 0)
        self.widget_layout_meta.setColumnStretch(1, 1)
        self.widget_layout_meta.setColumnStretch(2, 1)
        self.widget_layout_meta.setHorizontalSpacing(2)

        self.meta_label = QtWidgets.QLabel(self)
        self.meta_label.setText("Header - Metadata:")
        self.widget_layout_meta.addWidget(self.meta_label, 0, 0, 1, -1)

        # Meta - Line A
        self.meta_line_a = QtWidgets.QFrame(self)
        self.meta_line_a.setFrameShape(QtWidgets.QFrame.HLine)
        self.meta_line_a.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.widget_layout_meta.addWidget(self.meta_line_a, 1, 0, 1, -1)
        
        # Meta - Header 
        self.meta_header_label = QtWidgets.QLabel(self)
        self.meta_header_label.setText("Header:")
        self.meta_header_lineedit = QtWidgets.QLineEdit(self)
        self.meta_header_lineedit.setText("")
        self.meta_header_lineedit.setEnabled(False)
        self.meta_header_lineedit.textEdited.connect(lambda: self.update_header(self.meta_header_lineedit.text(), False))
        self.meta_header_lineedit.editingFinished.connect(lambda: self.update_header(self.meta_header_lineedit.text(), True))
        self.meta_header_qc = QCButton(self)
        self.widget_layout_meta.addWidget(self.meta_header_label, 2, 0)
        self.widget_layout_meta.addWidget(self.meta_header_lineedit, 2, 1, 1, 2)
        self.widget_layout_meta.addWidget(self.meta_header_qc, 2, 4)

        # Meta - Names
        self.meta_names_label = QtWidgets.QLabel(self)
        self.meta_names_label.setText("Names:")
        self.meta_names_lineedit = QtWidgets.QLineEdit(self)
        self.meta_names_lineedit.setText("")
        self.meta_names_lineedit.setEnabled(False)
        self.meta_names_lineedit.textEdited.connect(lambda: self.update_names(self.meta_names_lineedit.text(), False))
        self.meta_names_lineedit.editingFinished.connect(lambda: self.update_names(self.meta_names_lineedit.text(), True))
        self.meta_names_qc = QCButton(self)
        self.widget_layout_meta.addWidget(self.meta_names_label, 3, 0)
        self.widget_layout_meta.addWidget(self.meta_names_lineedit, 3, 1, 1, 2)
        self.widget_layout_meta.addWidget(self.meta_names_qc, 3, 4)

        # Identifiers etc
        self.label_middle = QtWidgets.QLabel(self)
        self.label_middle.setText("Identifiers:")

        self.ids = QtWidgets.QListView(self)
        self.ids.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.ids.currentChanged = self.receiveIdsCurrentChanged

        # Identifier note data
        self.widget_layout_meta_id = QtWidgets.QGridLayout()
        self.widget_layout_meta_id.setColumnStretch(0, 0)
        self.widget_layout_meta_id.setColumnStretch(1, 1)
        self.widget_layout_meta_id.setHorizontalSpacing(2)
     
        # Meta - Header 
        self.meta_notes_label = QtWidgets.QLabel(self)
        self.meta_notes_label.setText("Notes: ")
        self.meta_notes_lineedit = QtWidgets.QLineEdit(self)
        self.meta_notes_lineedit.setText("")
        self.meta_notes_lineedit.setEnabled(False)
        self.meta_notes_lineedit.textEdited.connect(lambda: self.update_notes(self.meta_notes_lineedit.text(), False))
        self.meta_notes_lineedit.editingFinished.connect(lambda: self.update_notes(self.meta_notes_lineedit.text(), True))
        self.widget_layout_meta_id.addWidget(self.meta_notes_label, 0, 0)
        self.widget_layout_meta_id.addWidget(self.meta_notes_lineedit, 0, 1, 1, 2)

        # Meta - Line B
        self.meta_line_b = QtWidgets.QFrame(self)
        self.meta_line_b.setFrameShape(QtWidgets.QFrame.HLine)
        self.meta_line_b.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.widget_layout_meta_id.addWidget(self.meta_line_b, 1, 0, 1, -1)

        # Headers list
        self.label_bottom = QtWidgets.QLabel(self)
        self.label_bottom.setText("Fluorophore Headers:")

        self.headers = QtWidgets.QListView(self)
        self.headers.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.headers.currentChanged = self.receiveHeaderCurrentChanged

        self.button_layout = QtWidgets.QHBoxLayout()

        self.export_map_button = QtWidgets.QPushButton(self)
        self.export_map_button.setText("Export Map")
        self.export_map_button.clicked.connect(self.export_map)
        self.button_layout.addWidget(self.export_map_button)

        self.export_button = QtWidgets.QPushButton(self)
        self.export_button.setText("Export Spectra")
        self.export_button.clicked.connect(self.export_data)
        self.button_layout.addWidget(self.export_button)

        self.widget_layout.addLayout(self.widget_layout_meta)
        self.widget_layout.addWidget(self.label_middle)
        self.widget_layout.addWidget(self.ids)
        self.widget_layout.addLayout(self.widget_layout_meta_id)
        self.widget_layout.addWidget(self.label_bottom)
        self.widget_layout.addWidget(self.headers)
        self.widget_layout.addLayout(self.button_layout)

    # Handles main data exports
    def export_data(self) -> None:
        """
        Opens folder selection
        """
        file_dialog = SaveDialog(self)
        if self.file_path:
            file_dialog.setDirectory(self.file_path)
        directories = None
        if file_dialog.exec():
            directories = file_dialog.selectedFiles()
        
        if not directories:
            return
        
        # get extension
        directory = directories[0]
        self.file_path = directory

        ext = directory.split(".")[-1]

        if ext == "ini":
            ext = Format.ini
        elif ext == "json":
            ext = Format.json
        else:
            return
        
        self.sendExportData.emit(directory, ext)

    def export_map(self) -> None:
        """
        Opens folder selection
        """
        file_dialog = SaveDialog(self)
        if self.file_path:
            file_dialog.setDirectory(self.file_path)
        directories = None
        if file_dialog.exec():
            directories = file_dialog.selectedFiles()
        
        if not directories:
            return
        
        # get extension
        directory = directories[0]
        self.file_path = directory

        self.sendExportMap.emit(directory)

    # Handles main data imports
    @QtCore.pyqtSlot(dict, dict)
    def receiveData(self, data_original: Dict[Identifier, Data], data_modified: Dict[Identifier, Data]) -> None:
        """
        Loads the factory data into the listtab
            :param data_original[Reader]: original data
            :param data_modified[Reader]: modifyable data
        """
        self.data_original = data_original
        self.data_modified = data_modified

    @QtCore.pyqtSlot(dict)
    def receiveHeaders(self, headers: Dict[str, Header]) -> None:
        """
        Loads the header information in the listtab
            :param headers: the MappedReader header data
        """
        self.header_map = headers

        self.buildHeaderModel()

    # Event handling of header and data listviews
    @QtCore.pyqtSlot(str)
    def receiveHeaderIndex(self, index: str) -> None:
        """
        Selects the specified index of the listview model
            :param index: the header index to select
        """
        for i in range(0, self.headers.model().rowCount(), 1):
            model_index = self.headers.model().index(i, 0)
            header_index = model_index.data(QtCore.Qt.UserRole + 1)
            if header_index == index:
                self.headers.setCurrentIndex(self.headers.model().index(i, 0))
                self.buildDataModel(index)
                self.selectDataIndex(None)
                break

    @QtCore.pyqtSlot(QtCore.QModelIndex, QtCore.QModelIndex)
    def receiveHeaderCurrentChanged(self, index_current, index_previous):
        """
        Overloaded currentChanged. Emits activated signal
        """
        del index_previous
        if index_current.isValid():
            self.sendActivatedHeader.emit(index_current.data(QtCore.Qt.UserRole + 1))
    
    @QtCore.pyqtSlot(QtGui.QStandardItem)
    def receiveIdsItemChanged(self, item):
        """
        Receives for QAbstractItemModel::itemChanged signal. Makes sure only 1 header can be selected as the main data container
        """
        if item.checkState() == QtCore.Qt.Unchecked:
            # Potential deselection, screen model to see if any other is still selected, if not send deselection signal
            has_checked = False
            for i in range(0, self.ids.model().rowCount(), 1):
                model_index = self.ids.model().index(i, 0)
                if model_index.flags() == QtCore.Qt.ItemIsUserCheckable and model_index.data(QtCore.Qt.CheckStateRole) != QtCore.Qt.Unchecked:
                    has_checked = True
                    break

            if not has_checked:
                # No item selected, remove source header
                self.header_map[self.header_index].source = None
                # Also remove source identifier
                # (but keep data entree in case of missclicks, will be overwritten if another identifier is selected anyway)
                self.header_map[self.header_index].identifiers.remove(Identifier(Source.source, self.header_index))

                # Rebuild model
                self.buildDataModel(self.header_index)
                self.selectDataIndex(item.data(QtCore.Qt.UserRole + 1))

                # Send deselection signal here
        else:

            # Checking, as only a single item can be selected, deselect the rest
            for i in range(0, self.ids.model().rowCount(), 1):
                model_item = self.ids.model().item(i, 0)

                # When removing listview entree, you can get gaps in the row items
                if not model_item:
                    continue

                if model_item != item and model_item.data(QtCore.Qt.UserRole + 1).source != Source.source:
                    model_item.setData(QtCore.Qt.Unchecked, QtCore.Qt.CheckStateRole)

            # Set the header_map source
            identifier_raw = item.data(QtCore.Qt.UserRole + 1)
            self.header_map[self.header_index].source = identifier_raw
            
            # Add a entree for the new source data
            identifier_source = Identifier(Source.source, self.header_index)
            self.header_map[self.header_index].identifiers.append(identifier_source)

            # Check if data already exists of the identical source.
            try:
                data_source = self.data_modified[identifier_source]
            except KeyError:
                self.data_modified[identifier_source] = copy.deepcopy(self.data_modified[identifier_raw])
            else:
                if data_source.data_id == identifier_raw:
                    # Source is already from the correct source, no changes needed 
                    # (makes sure that mistakes do not fully reset progress)
                    pass
                else:
                    self.data_modified[identifier_source] = copy.deepcopy(self.data_modified[identifier_raw])

            # Rebuild Model
            self.buildDataModel(self.header_index)
            self.selectDataIndex(identifier_source)
            
            # Send selection signal here

    @QtCore.pyqtSlot(QtCore.QModelIndex, QtCore.QModelIndex)
    def receiveIdsCurrentChanged(self, index_current, index_previous):
        """
        Overloaded currentChanged. Emits activated signal
        """
        del index_previous
        if index_current.isValid():
            self.sendActivatedData.emit(index_current.data(QtCore.Qt.UserRole + 1))

            self.data_index = index_current.data(QtCore.Qt.UserRole + 1)
            self.place_notes()

    # Manual setting of indexes
    def selectDataIndex(self, identifier: Union[Identifier, None]) -> None:
        """
        Select a specific identifier data entree
            :param identifier: if identifier is specific will select that specific identifier (if available)
                               if None will select the first entree (if available)
        """
        # Reset index first to also handle improper inputs
        self.data_index = None

        if not identifier:
            if self.ids.model().rowCount() > 0:
                self.ids.setCurrentIndex(self.ids.model().index(0,0))
                self.data_index = self.ids.model().index(0,0).data(QtCore.Qt.UserRole + 1)
            self.place_notes()
            return

        for i in range(0, self.ids.model().rowCount(), 1):
            model_index = self.ids.model().index(i, 0)
            if model_index.data(QtCore.Qt.UserRole + 1) == identifier:
                self.ids.setCurrentIndex(self.ids.model().index(i, 0))
                self.data_index = model_index.data(QtCore.Qt.UserRole + 1)
                break

        self.place_notes()

    # Construct Models
    def buildDataModel(self, header: str):
        """
        Builds a model for the listview widget. 
            :param header: the header identifyer specifying which headers identifiers to load into the model
        """
        self.header_index = header

        item_model = QtGui.QStandardItemModel()
        for identifier in self.header_map[header].identifiers:
            if identifier.source == Source.source:
                text = f"      {repr(identifier)}"
            else:
                text = repr(identifier)
            if identifier.note:
                text += ":" + identifier.note
            item = QtGui.QStandardItem(text)
            
            # set check(able) state
            if identifier.source == Source.source:
                item.setCheckable(False)
            else:
                item.setCheckable(True)
                if self.header_map[header].source and identifier == self.header_map[header].source:
                    item.setData(QtCore.Qt.Checked, QtCore.Qt.CheckStateRole)
                else:
                    item.setData(QtCore.Qt.Unchecked, QtCore.Qt.CheckStateRole)

            item.setData(identifier, QtCore.Qt.UserRole + 1)
            
            if identifier.source == Source.source:
                item_model.insertRow(0, item)
            else:
                item_model.appendRow(item)

        # Connect to change signal to be able to detect checking
        item_model.itemChanged.connect(self.receiveIdsItemChanged)

        # Delete old model as setting a new model doesnt automatically delete the previous one
        old_model = self.ids.model()
        self.ids.setModel(item_model)
        if old_model:
            old_model.disconnect()
            old_model.setParent(None)
            old_model.deleteLater()

        # Also load the header data into the metadata fields
        self.place_header()
        self.place_names()

    def buildHeaderModel(self) -> None:
        """
        Build the model for the header listview
        """
        item_model = QtGui.QStandardItemModel()
        for header in self.header_map:
            if self.header_map[header].valid:
                item = QtGui.QStandardItem(header)
                item.setData(header, QtCore.Qt.UserRole + 1)
                item_model.appendRow(item)
        
        # Delete old model as setting a new model doesnt automatically delete the previous one
        old_model = self.headers.model()
        self.headers.setModel(item_model)
        if old_model:
            old_model.setParent(None)
            old_model.deleteLater()

    # Handling and checking of Header lineedits
    def place_header(self):
        """ Places the header.header in the correct widget """
        data = self.header_map[self.header_index]
        self.meta_header_lineedit.setText(data.header)
        self.meta_header_lineedit.setEnabled(False)

        checker = AuditHeader(data.header)
        self.meta_header_qc.setPassed(checker.valid, checker.errors)

    def place_names(self):
        """ Places the names data in the correct widget """
        data = self.header_map[self.header_index]
        if data.names:
            value = ""
            for name in data.names:
                value += name + "|"
            value = value[:-1]
            self.meta_names_lineedit.setText(value)
        else:
            self.meta_names_lineedit.setText("")
        self.meta_names_lineedit.setEnabled(True)

        checker = AuditNames(data.names)
        self.meta_names_qc.setPassed(checker.valid, checker.errors)

    def place_notes(self):
        """ Places the identifier notes data in the correct widget """
        data = self.header_map[self.header_index]
        if self.data_index:
            i = data.identifiers.index(self.data_index)
            note = data.identifiers[i].note

            if not note:
                note = ""

            self.meta_notes_lineedit.setText(note)
            self.meta_notes_lineedit.setEnabled(True)
        else:
            self.meta_notes_lineedit.setText("")
            self.meta_notes_lineedit.setEnabled(False)

    def update_header(self, text, update=False):
        """
        updates the modified header.header with text and reruns the checker
            :param text[str]: new text
            :param update[bool]: whether to update the showing widget
        """
        data = self.header_map[self.header_index]
        text = text.strip(" ")
        if text:
            data.header = text
        else:
            data.header = None

        if update:
            self.place_header()
        else:
            checker = AuditHeader(data.header)
            self.meta_header_qc.setPassed(checker.valid, checker.errors)

    def update_names(self, text, update=False):
        """
        updates the modified header.names. Transforms it into a list of names, updates the widget, and reruns the checker
            :param text[str]: new text
            :param update[bool]: whether to update the showing widget
        """
        data = self.header_map[self.header_index]
        names = text.split("|")
        for i, name in enumerate(names):
            names[i] = name.strip(" ")
        
        if names:
            data.names = names
        else:
            data.names = None

        if update:
            self.place_names()
        else:
            # Rerun checker
            checker = AuditNames(data.names)
            self.meta_names_qc.setPassed(checker.valid, checker.errors)

    def update_notes(self, text, update=False):
        """
        updates the modified Identifier.note with text
            :param text[str]: new text
            :param update[bool]: whether to update the showing widget
        """
        data = self.header_map[self.header_index]
        i = data.identifiers.index(self.data_index)
        
        text = text.strip(" ")
        if text:
            if data.identifiers[i].source == Source.source:
                data.source.note = text
            data.identifiers[i].note = text
        else:
            if data.identifiers[i].source == Source.source:
                data.source.note = None
            data.identifiers[i].note = None

        if update:
            self.place_notes()
            self.buildDataModel(self.header_index)

    # Widget event filter
    def eventFilter(self, object, event):
        """
        Capture all events to this widget.
            :param object[QObject]: source object
            :param event[QEvent]: event
        """
        if event.type() == QtCore.QEvent.KeyPress:
            if event.key() == QtCore.Qt.Key_Delete:
                pass

        return super().eventFilter(object, event)

class AdjustTab(QtWidgets.QWidget):
    """
    QWidget containing the modification buttons
        :param parent[QWidget]: parent widget
    """
    sendDataModified = QtCore.pyqtSignal(Identifier, LineType)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.data_original: Reader = None         # Data to reset to
        self.data_modified: Reader = None         # Shown data
        self.data_index: Identifier = None
        self.data_check: Auditor = Auditor()

        # Popups
        self.special_popup = SpecialPopup(self)
        self.special_line_type = None
        self.special_popup.sendFunction.connect(self.receiveSpecialFunction)

        self.widget_layout = QtWidgets.QVBoxLayout(self)

        self.widget_layout_top = QtWidgets.QGridLayout()
        self.widget_layout_top.setColumnStretch(0, 0)
        self.widget_layout_top.setColumnStretch(1, 1)
        self.widget_layout_top.setColumnStretch(2, 1)

        #self.widget_layout_top.setContentsMargins(0, 12, 0, 0)
        #self.widget_layout_top.setSpacing(2)
        self.widget_layout_top.setHorizontalSpacing(2)

        # Label
        self.label = QtWidgets.QLabel(self)
        self.label.setText("Adjust Fluorophore Data")
        self.widget_layout_top.addWidget(self.label, 0, 0, 1, -1)

        # Line A
        self.line_a = QtWidgets.QFrame(self)
        self.line_a.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_a.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.widget_layout_top.addWidget(self.line_a, 1, 0, 1, -1)
        # ID 
        self.id_label = QtWidgets.QLabel(self)
        self.id_label.setText("Header:")
        self.id_lineedit = QtWidgets.QLineEdit(self)
        self.id_lineedit.setText("")
        self.id_lineedit.setEnabled(False)
        self.id_lineedit.textEdited.connect(lambda: self.update_id(self.id_lineedit.text(), False))
        self.id_lineedit.editingFinished.connect(lambda: self.update_id(self.id_lineedit.text(), True))
        self.id_qc = QCButton(self)
        self.widget_layout_top.addWidget(self.id_label, 2, 0)
        self.widget_layout_top.addWidget(self.id_lineedit, 2, 1, 1, 2)
        self.widget_layout_top.addWidget(self.id_qc, 2, 4)
        # Line B
        self.line_b = QtWidgets.QFrame(self)
        self.line_b.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_b.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.widget_layout_top.addWidget(self.line_b, 3, 0, 1, -1)        
        # names 
        self.names_label = QtWidgets.QLabel(self)
        self.names_label.setText("Names:")
        self.names_lineedit = QtWidgets.QLineEdit(self)
        self.names_lineedit.setText("")
        self.names_lineedit.setEnabled(False)
        self.names_lineedit.textEdited.connect(lambda: self.update_names(self.names_lineedit.text(), False))
        self.names_lineedit.editingFinished.connect(lambda: self.update_names(self.names_lineedit.text(), True))
        self.names_qc= QCButton(self)
        self.widget_layout_top.addWidget(self.names_label, 4, 0)
        self.widget_layout_top.addWidget(self.names_lineedit, 4, 1, 1, 2)
        self.widget_layout_top.addWidget(self.names_qc, 4, 4)
        # enable
        self.enable_label = QtWidgets.QLabel(self)
        self.enable_label.setText("Enable:")
        self.enable_true = ActiveButton("true", self)
        self.enable_false = ActiveButton("false", self)
        self.enable_true.setEnabled(False)
        self.enable_false.setEnabled(False)
        self.enable_qc = QCButton(self)
        self.widget_layout_top.addWidget(self.enable_label, 5, 0)
        self.widget_layout_top.addWidget(self.enable_true, 5, 1, 1, 1)
        self.widget_layout_top.addWidget(self.enable_false, 5, 2, 1, 1)
        self.widget_layout_top.addWidget(self.enable_qc, 5, 4)
        self.enable_true.sendActivated.connect(self.receiveActivatedEnableTrue)
        self.enable_false.sendActivated.connect(self.receiveActivatedEnableFalse)
        # database
        self.database_label = QtWidgets.QLabel(self)
        self.database_label.setText("Database:")
        self.database_label.setToolTip("source of the fluorophore database")
        self.database_lineedit = QtWidgets.QLineEdit(self)
        self.database_lineedit.setText("")
        self.database_lineedit.setEnabled(False)
        self.database_lineedit.textEdited.connect(lambda: self.update_database(self.database_lineedit.text(), False))
        self.database_lineedit.editingFinished.connect(lambda: self.update_database(self.database_lineedit.text(), True))
        self.database_qc = QCButton(self)
        self.widget_layout_top.addWidget(self.database_label, 6, 0)
        self.widget_layout_top.addWidget(self.database_lineedit, 6, 1, 1, 2)
        self.widget_layout_top.addWidget(self.database_qc, 6, 4)
        # reference
        self.reference_label = QtWidgets.QLabel(self)
        self.reference_label.setText("Reference:")
        self.reference_label.setToolTip("Reference to the original author")
        #self.reference_lineedit = QtWidgets.QLineEdit(self)
        self.reference_lineedit = QtWidgets.QPlainTextEdit(self)    # To be able to see the entire referene in multiple lines
        self.reference_lineedit.setFixedHeight(150)
        self.reference_lineedit.setPlainText("")
        self.reference_lineedit.setEnabled(False)
        self.reference_lineedit.textChanged.connect(lambda: self.update_reference(self.reference_lineedit.toPlainText(), False))
        self.reference_qc = QCButton(self)
        self.reference_qc.setFixedHeight(150)
        self.widget_layout_top.addWidget(self.reference_label, 7, 0)
        self.widget_layout_top.addWidget(self.reference_lineedit, 7, 1, 1, 2)
        self.widget_layout_top.addWidget(self.reference_qc, 7, 4)
        # Line C
        # self.line_c = QtWidgets.QFrame(self)
        # self.line_c.setFrameShape(QtWidgets.QFrame.HLine)
        # self.line_c.setFrameShadow(QtWidgets.QFrame.Sunken)
        # self.widget_layout_top.addWidget(self.line_c, 8, 0, 1, -1)
        # Molar Extinction Coefficient:
        self.ec_label = QtWidgets.QLabel(self)
        self.ec_label.setText("ε (/M/cm):")
        self.ec_label.setToolTip("Molar Extinction Coefficient")
        self.ec_lineedit = QtWidgets.QLineEdit(self)
        self.ec_lineedit.setText("")
        self.ec_lineedit.setEnabled(False)
        self.ec_lineedit.textEdited.connect(lambda: self.update_ec(self.ec_lineedit.text(), False))
        self.ec_lineedit.editingFinished.connect(lambda: self.update_ec(self.ec_lineedit.text(), True))
        self.ec_qc = QCButton(self)
        self.widget_layout_top.addWidget(self.ec_label, 9, 0)
        self.widget_layout_top.addWidget(self.ec_lineedit, 9, 1, 1, 2)
        self.widget_layout_top.addWidget(self.ec_qc, 9, 4)
        # Quantum Yield
        self.qy_label = QtWidgets.QLabel(self)
        self.qy_label.setText("Φ:")
        self.qy_label.setToolTip("Quantum Yield")
        self.qy_lineedit = QtWidgets.QLineEdit(self)
        self.qy_lineedit.setText("")
        self.qy_lineedit.setEnabled(False)
        self.qy_lineedit.textEdited.connect(lambda: self.update_qy(self.qy_lineedit.text(), False))
        self.qy_lineedit.editingFinished.connect(lambda: self.update_qy(self.qy_lineedit.text(), True))
        self.qy_qc = QCButton(self)
        self.widget_layout_top.addWidget(self.qy_label, 10, 0)
        self.widget_layout_top.addWidget(self.qy_lineedit, 10, 1, 1, 2)
        self.widget_layout_top.addWidget(self.qy_qc, 10, 4)
        # Intensity
        self.intensity_label = QtWidgets.QLabel(self)
        self.intensity_label.setText("Brightness:")
        self.intensity_label.setToolTip("Molar Extinction Coefficient * Quantum Yield")
        self.intensity_lineedit = QtWidgets.QLineEdit(self)
        self.intensity_lineedit.setText("")
        self.intensity_lineedit.setEnabled(False)
        self.intensity_lineedit.textEdited.connect(lambda: self.update_intensity(self.intensity_lineedit.text(), False))
        self.intensity_lineedit.editingFinished.connect(lambda: self.update_intensity(self.intensity_lineedit.text(), True))
        self.intensity_qc = QCButton(self)
        self.widget_layout_top.addWidget(self.intensity_label, 11, 0)
        self.widget_layout_top.addWidget(self.intensity_lineedit, 11, 1, 1, 2)
        self.widget_layout_top.addWidget(self.intensity_qc, 11, 4)
        # Intensity binned
        self.intensity_bin_label = QtWidgets.QLabel(self)
        self.intensity_bin_label.setText("Brightness (b):")
        self.intensity_bin_label.setToolTip("Binned Brightness (1-5)")
        self.intensity_bin_lineedit = QtWidgets.QLineEdit(self)
        self.intensity_bin_lineedit.setText("")
        self.intensity_bin_lineedit.setEnabled(False)
        self.intensity_bin_lineedit.textEdited.connect(lambda: self.update_intensity_bin(self.intensity_bin_lineedit.text(), False))
        self.intensity_bin_lineedit.editingFinished.connect(lambda: self.update_intensity_bin(self.intensity_bin_lineedit.text(), True))
        self.intensity_bin_qc = QCButton(self)
        self.widget_layout_top.addWidget(self.intensity_bin_label, 12, 0)
        self.widget_layout_top.addWidget(self.intensity_bin_lineedit, 12, 1, 1, 2)
        self.widget_layout_top.addWidget(self.intensity_bin_qc, 12, 4)
        # Line D
        self.line_d = QtWidgets.QFrame(self)
        self.line_d.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_d.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.widget_layout_top.addWidget(self.line_d, 13, 0, 1, -1)

        self.label_reset = QtWidgets.QLabel(self)
        self.label_reset.setText("Reset Metadata:")
        self.widget_layout_top.addWidget(self.label_reset, 14, 0)
        self.reset_button = QtWidgets.QPushButton(self)
        self.reset_button.setText("Reset")
        self.reset_button.setEnabled(False)
        self.reset_button.clicked.connect(lambda: self.reset_metadata())
        self.widget_layout_top.addWidget(self.reset_button, 14, 1, 1, -1)

        # Line DD
        self.line_dd = QtWidgets.QFrame(self)
        self.line_dd.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_dd.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.widget_layout_top.addWidget(self.line_dd, 15, 0, 1, -1)

        self.widget_layout.addLayout(self.widget_layout_top)

        # Curve quality control widgets
        self.widget_layout_curve_qc = QtWidgets.QGridLayout()
        self.widget_layout_curve_qc.setColumnStretch(0, 0)
        self.widget_layout_curve_qc.setColumnStretch(1, 1)
        self.widget_layout_curve_qc.setColumnStretch(2, 1)
        self.widget_layout_curve_qc.setColumnStretch(3, 1)
        self.widget_layout_curve_qc.setColumnStretch(4, 1)
        self.widget_layout_curve_qc.setColumnMinimumWidth(0, 90)
        self.widget_layout_curve_qc.setHorizontalSpacing(4)

        # Labels
        self.label_ab = QtWidgets.QLabel(self)
        self.label_ab.setText("Ab:")
        self.label_ab.setToolTip("Absorption")
        self.label_ex = QtWidgets.QLabel(self)
        self.label_ex.setText("Ex:")
        self.label_ex.setToolTip("Excitation")
        self.label_2p = QtWidgets.QLabel(self)
        self.label_2p.setText("2p:")
        self.label_2p.setToolTip("Two Photon")
        self.label_em = QtWidgets.QLabel(self)
        self.label_em.setText("Em:")
        self.label_em.setToolTip("Emission")
        self.widget_layout_curve_qc.addWidget(self.label_ab, 0, 1)
        self.widget_layout_curve_qc.addWidget(self.label_ex, 0, 2)
        self.widget_layout_curve_qc.addWidget(self.label_2p, 0, 3)
        self.widget_layout_curve_qc.addWidget(self.label_em, 0, 4)

        # Missing Wavelength
        self.label_wav_missing = QtWidgets.QLabel(self)
        self.label_wav_missing.setText("Data (x):")
        self.missing_wav_ab = QCButton(self)
        self.missing_wav_ex = QCButton(self)
        self.missing_wav_2p = QCButton(self)
        self.missing_wav_em = QCButton(self)
        self.widget_layout_curve_qc.addWidget(self.label_wav_missing, 1, 0)
        self.widget_layout_curve_qc.addWidget(self.missing_wav_ab, 1, 1)
        self.widget_layout_curve_qc.addWidget(self.missing_wav_ex, 1, 2)
        self.widget_layout_curve_qc.addWidget(self.missing_wav_2p, 1, 3)
        self.widget_layout_curve_qc.addWidget(self.missing_wav_em, 1, 4)
        
        # Missing Intensity
        self.label_int_missing = QtWidgets.QLabel(self)
        self.label_int_missing.setText("Data (y):")
        self.missing_int_ab = QCButton(self)
        self.missing_int_ex = QCButton(self)
        self.missing_int_2p = QCButton(self)
        self.missing_int_em = QCButton(self)
        self.widget_layout_curve_qc.addWidget(self.label_int_missing, 2, 0)
        self.widget_layout_curve_qc.addWidget(self.missing_int_ab, 2, 1)
        self.widget_layout_curve_qc.addWidget(self.missing_int_ex, 2, 2)
        self.widget_layout_curve_qc.addWidget(self.missing_int_2p, 2, 3)
        self.widget_layout_curve_qc.addWidget(self.missing_int_em, 2, 4)

        # Line f
        # self.line_e = QtWidgets.QFrame(self)
        # self.line_e.setFrameShape(QtWidgets.QFrame.HLine)
        # self.line_e.setFrameShadow(QtWidgets.QFrame.Sunken)
        # self.widget_layout_curve_qc.addWidget(self.line_e, 3, 0, 1, -1)

        # Spectra properties
        self.label_spectra = QtWidgets.QLabel(self)
        self.label_spectra.setText("Wavelength:")
        self.spectra_ab = QCButton(self)
        self.spectra_ex = QCButton(self)
        self.spectra_2p = QCButton(self)
        self.spectra_em = QCButton(self)
        self.widget_layout_curve_qc.addWidget(self.label_spectra, 5, 0)
        self.widget_layout_curve_qc.addWidget(self.spectra_ab, 5, 1)
        self.widget_layout_curve_qc.addWidget(self.spectra_ex, 5, 2)
        self.widget_layout_curve_qc.addWidget(self.spectra_2p, 5, 3)
        self.widget_layout_curve_qc.addWidget(self.spectra_em, 5, 4)

        # Line f
        self.line_f = QtWidgets.QFrame(self)
        self.line_f.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_f.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.widget_layout_curve_qc.addWidget(self.line_f, 7, 0, 1, -1)

        self.widget_layout.addLayout(self.widget_layout_curve_qc)

        # Curve info
        self.widget_layout_curve_info = QtWidgets.QGridLayout()
        self.widget_layout_curve_info.setColumnStretch(0, 0)
        self.widget_layout_curve_info.setColumnStretch(1, 1)
        self.widget_layout_curve_info.setColumnStretch(2, 1)
        self.widget_layout_curve_info.setColumnStretch(3, 1)
        self.widget_layout_curve_info.setColumnStretch(4, 1)
        self.widget_layout_curve_info.setColumnMinimumWidth(0, 91)
        self.widget_layout_curve_info.setHorizontalSpacing(2)

        # max value label
        self.max_label = QtWidgets.QLabel(self)
        self.max_label_ab = QtWidgets.QLabel(self)
        self.max_label_ex = QtWidgets.QLabel(self)
        self.max_label_2p = QtWidgets.QLabel(self)
        self.max_label_em = QtWidgets.QLabel(self)
        self.max_label.setText("Max:")
        self.max_label_ab.setText("")
        self.max_label_ex.setText("")
        self.max_label_2p.setText("")
        self.max_label_em.setText("")
        self.max_label_ab.setAlignment(QtCore.Qt.AlignHCenter)
        self.max_label_ex.setAlignment(QtCore.Qt.AlignHCenter)
        self.max_label_2p.setAlignment(QtCore.Qt.AlignHCenter)
        self.max_label_em.setAlignment(QtCore.Qt.AlignHCenter)
        self.widget_layout_curve_info.addWidget(self.max_label, 1, 0)
        self.widget_layout_curve_info.addWidget(self.max_label_ab, 1, 1)
        self.widget_layout_curve_info.addWidget(self.max_label_ex, 1, 2)
        self.widget_layout_curve_info.addWidget(self.max_label_2p, 1, 3)
        self.widget_layout_curve_info.addWidget(self.max_label_em, 1, 4)
        
        # min value label
        self.min_label = QtWidgets.QLabel(self)
        self.min_label_ab = QtWidgets.QLabel(self)
        self.min_label_ex = QtWidgets.QLabel(self)
        self.min_label_2p = QtWidgets.QLabel(self)
        self.min_label_em = QtWidgets.QLabel(self)
        self.min_label.setText("Min:")
        self.min_label_ab.setText("")
        self.min_label_ex.setText("")
        self.min_label_2p.setText("")
        self.min_label_em.setText("")
        self.min_label_ab.setAlignment(QtCore.Qt.AlignHCenter)
        self.min_label_ex.setAlignment(QtCore.Qt.AlignHCenter)
        self.min_label_2p.setAlignment(QtCore.Qt.AlignHCenter)
        self.min_label_em.setAlignment(QtCore.Qt.AlignHCenter)
        self.widget_layout_curve_info.addWidget(self.min_label, 2, 0)
        self.widget_layout_curve_info.addWidget(self.min_label_ab, 2, 1)
        self.widget_layout_curve_info.addWidget(self.min_label_ex, 2, 2)
        self.widget_layout_curve_info.addWidget(self.min_label_2p, 2, 3)
        self.widget_layout_curve_info.addWidget(self.min_label_em, 2, 4)

        # max wavelength selection
        self.max_select_label = QtWidgets.QLabel(self)
        self.max_select_label.setText("Max Wavelength:")
        self.max_select_lineedit_ab = SelectLineEdit(self)
        self.max_select_lineedit_ex = SelectLineEdit(self)
        self.max_select_lineedit_2p = SelectLineEdit(self)
        self.max_select_lineedit_em = SelectLineEdit(self)
        self.max_select_lineedit_ab.hide()
        self.max_select_lineedit_ex.hide()
        self.max_select_lineedit_2p.hide()
        self.max_select_lineedit_em.hide()
        self.max_select_button_ab = SelectPushButton(self)
        self.max_select_button_ex = SelectPushButton(self)
        self.max_select_button_2p = SelectPushButton(self)
        self.max_select_button_em = SelectPushButton(self)
        self.max_select_button_ab.setEnabled(False)
        self.max_select_button_ex.setEnabled(False)
        self.max_select_button_2p.setEnabled(False)
        self.max_select_button_em.setEnabled(False)

        self.max_select_button_ab.pressedButton.connect(self.receiveClickedButtonAb)
        self.max_select_lineedit_ab.editingFinished.connect(self.receiveEditingFinishedAb)
        self.max_select_button_ex.pressedButton.connect(self.receiveClickedButtonEx)
        self.max_select_lineedit_ex.editingFinished.connect(self.receiveEditingFinishedEx)
        self.max_select_button_2p.pressedButton.connect(self.receiveClickedButton2p)
        self.max_select_lineedit_2p.editingFinished.connect(self.receiveEditingFinished2p)
        self.max_select_button_em.pressedButton.connect(self.receiveClickedButtonEm)
        self.max_select_lineedit_em.editingFinished.connect(self.receiveEditingFinishedEm)

        Application.instance().globalClicked.connect(self.globalClicked)

        self.widget_layout_curve_info.addWidget(self.max_select_label, 3, 0)
        self.widget_layout_curve_info.addWidget(self.max_select_lineedit_ab, 3, 1)
        self.widget_layout_curve_info.addWidget(self.max_select_lineedit_ex, 3, 2)
        self.widget_layout_curve_info.addWidget(self.max_select_lineedit_2p, 3, 3)
        self.widget_layout_curve_info.addWidget(self.max_select_lineedit_em, 3, 4)
        self.widget_layout_curve_info.addWidget(self.max_select_button_ab, 3, 1)
        self.widget_layout_curve_info.addWidget(self.max_select_button_ex, 3, 2)
        self.widget_layout_curve_info.addWidget(self.max_select_button_2p, 3, 3)
        self.widget_layout_curve_info.addWidget(self.max_select_button_em, 3, 4)

        # Line g
        self.line_g = QtWidgets.QFrame(self)
        self.line_g.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_g.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.widget_layout_curve_info.addWidget(self.line_g, 4, 0, 1, -1)

        self.widget_layout.addLayout(self.widget_layout_curve_info)

        # Curve manipulation
        self.widget_layout_curve_manip = QtWidgets.QGridLayout()
        self.widget_layout_curve_manip.setColumnStretch(0, 0)
        self.widget_layout_curve_manip.setColumnStretch(1, 1)
        self.widget_layout_curve_manip.setColumnStretch(2, 1)
        self.widget_layout_curve_manip.setColumnStretch(3, 1)
        self.widget_layout_curve_manip.setColumnStretch(4, 1)
        self.widget_layout_curve_manip.setColumnMinimumWidth(0, 91)
        self.widget_layout_curve_manip.setHorizontalSpacing(2)

        # Interpolate buttons
        self.label_interpolate = QtWidgets.QLabel(self)
        self.label_interpolate.setText("Interpolate:")
        self.interpolate_ab = QtWidgets.QPushButton(self)
        self.interpolate_ex = QtWidgets.QPushButton(self)
        self.interpolate_2p = QtWidgets.QPushButton(self)
        self.interpolate_em = QtWidgets.QPushButton(self)
        self.interpolate_ab.setEnabled(False)
        self.interpolate_ex.setEnabled(False)
        self.interpolate_2p.setEnabled(False)
        self.interpolate_em.setEnabled(False)
        self.interpolate_ab.clicked.connect(lambda: self.interpolate_curve(LineType.Absorption))
        self.interpolate_ex.clicked.connect(lambda: self.interpolate_curve(LineType.Excitation))
        self.interpolate_2p.clicked.connect(lambda: self.interpolate_curve(LineType.TwoPhoton))
        self.interpolate_em.clicked.connect(lambda: self.interpolate_curve(LineType.Emission))
        self.widget_layout_curve_manip.addWidget(self.label_interpolate, 0, 0)
        self.widget_layout_curve_manip.addWidget(self.interpolate_ab, 0, 1)
        self.widget_layout_curve_manip.addWidget(self.interpolate_ex, 0, 2)
        self.widget_layout_curve_manip.addWidget(self.interpolate_2p, 0, 3)
        self.widget_layout_curve_manip.addWidget(self.interpolate_em, 0, 4)
        
        # Normalize up buttons
        self.label_normalize_up = QtWidgets.QLabel(self)
        self.label_normalize_up.setText("Normalize Up:")
        self.normalize_up_ab = QtWidgets.QPushButton(self)
        self.normalize_up_ex = QtWidgets.QPushButton(self)
        self.normalize_up_2p = QtWidgets.QPushButton(self)
        self.normalize_up_em = QtWidgets.QPushButton(self)
        self.normalize_up_ab.setEnabled(False)
        self.normalize_up_ex.setEnabled(False)
        self.normalize_up_2p.setEnabled(False)
        self.normalize_up_em.setEnabled(False)
        self.normalize_up_ab.clicked.connect(lambda: self.normalize_up_curve(LineType.Absorption))
        self.normalize_up_ex.clicked.connect(lambda: self.normalize_up_curve(LineType.Excitation))
        self.normalize_up_2p.clicked.connect(lambda: self.normalize_up_curve(LineType.TwoPhoton))
        self.normalize_up_em.clicked.connect(lambda: self.normalize_up_curve(LineType.Emission))
        self.widget_layout_curve_manip.addWidget(self.label_normalize_up, 1, 0)
        self.widget_layout_curve_manip.addWidget(self.normalize_up_ab, 1, 1)
        self.widget_layout_curve_manip.addWidget(self.normalize_up_ex, 1, 2)
        self.widget_layout_curve_manip.addWidget(self.normalize_up_2p, 1, 3)
        self.widget_layout_curve_manip.addWidget(self.normalize_up_em, 1, 4)
        
        # Normalize down buttons
        self.label_normalize_do = QtWidgets.QLabel(self)
        self.label_normalize_do.setText("Normalize Down:")
        self.normalize_do_ab = QtWidgets.QPushButton(self)
        self.normalize_do_ex = QtWidgets.QPushButton(self)
        self.normalize_do_2p = QtWidgets.QPushButton(self)
        self.normalize_do_em = QtWidgets.QPushButton(self)
        self.normalize_do_ab.setEnabled(False)
        self.normalize_do_ex.setEnabled(False)
        self.normalize_do_2p.setEnabled(False)
        self.normalize_do_em.setEnabled(False)
        self.normalize_do_ab.clicked.connect(lambda: self.normalize_down_curve(LineType.Absorption))
        self.normalize_do_ex.clicked.connect(lambda: self.normalize_down_curve(LineType.Excitation))
        self.normalize_do_2p.clicked.connect(lambda: self.normalize_down_curve(LineType.TwoPhoton))
        self.normalize_do_em.clicked.connect(lambda: self.normalize_down_curve(LineType.Emission))
        self.widget_layout_curve_manip.addWidget(self.label_normalize_do, 2, 0)
        self.widget_layout_curve_manip.addWidget(self.normalize_do_ab, 2, 1)
        self.widget_layout_curve_manip.addWidget(self.normalize_do_ex, 2, 2)
        self.widget_layout_curve_manip.addWidget(self.normalize_do_2p, 2, 3)
        self.widget_layout_curve_manip.addWidget(self.normalize_do_em, 2, 4)
        
        # Cutoff at 0 buttons
        self.label_cutoff = QtWidgets.QLabel(self)
        self.label_cutoff.setText("Cutoff at 0:")
        self.cutoff_ab = QtWidgets.QPushButton(self)
        self.cutoff_ex = QtWidgets.QPushButton(self)
        self.cutoff_2p = QtWidgets.QPushButton(self)
        self.cutoff_em = QtWidgets.QPushButton(self)
        self.cutoff_ab.setEnabled(False)
        self.cutoff_ex.setEnabled(False)
        self.cutoff_2p.setEnabled(False)
        self.cutoff_em.setEnabled(False)
        self.cutoff_ab.clicked.connect(lambda: self.cutoff_curve(LineType.Absorption))
        self.cutoff_ex.clicked.connect(lambda: self.cutoff_curve(LineType.Excitation))
        self.cutoff_2p.clicked.connect(lambda: self.cutoff_curve(LineType.TwoPhoton))
        self.cutoff_em.clicked.connect(lambda: self.cutoff_curve(LineType.Emission))
        self.widget_layout_curve_manip.addWidget(self.label_cutoff, 3, 0)
        self.widget_layout_curve_manip.addWidget(self.cutoff_ab, 3, 1)
        self.widget_layout_curve_manip.addWidget(self.cutoff_ex, 3, 2)
        self.widget_layout_curve_manip.addWidget(self.cutoff_2p, 3, 3)
        self.widget_layout_curve_manip.addWidget(self.cutoff_em, 3, 4)
        
        # remove return buttons
        self.label_remove_r = QtWidgets.QLabel(self)
        self.label_remove_r.setText("Remove return:")
        self.remove_r_ab = QtWidgets.QPushButton(self)
        self.remove_r_ex = QtWidgets.QPushButton(self)
        self.remove_r_2p = QtWidgets.QPushButton(self)
        self.remove_r_em = QtWidgets.QPushButton(self)
        self.remove_r_ab.setEnabled(False)
        self.remove_r_ex.setEnabled(False)
        self.remove_r_2p.setEnabled(False)
        self.remove_r_em.setEnabled(False)
        self.remove_r_ab.clicked.connect(lambda: self.remove_return_curve(LineType.Absorption))
        self.remove_r_ex.clicked.connect(lambda: self.remove_return_curve(LineType.Excitation))
        self.remove_r_2p.clicked.connect(lambda: self.remove_return_curve(LineType.TwoPhoton))
        self.remove_r_em.clicked.connect(lambda: self.remove_return_curve(LineType.Emission))
        self.widget_layout_curve_manip.addWidget(self.label_remove_r, 4, 0)
        self.widget_layout_curve_manip.addWidget(self.remove_r_ab, 4, 1)
        self.widget_layout_curve_manip.addWidget(self.remove_r_ex, 4, 2)
        self.widget_layout_curve_manip.addWidget(self.remove_r_2p, 4, 3)
        self.widget_layout_curve_manip.addWidget(self.remove_r_em, 4, 4)
        
        # remove padding buttons
        self.label_remove_p = QtWidgets.QLabel(self)
        self.label_remove_p.setText("Remove padding:")
        self.remove_p_ab = QtWidgets.QPushButton(self)
        self.remove_p_ex = QtWidgets.QPushButton(self)
        self.remove_p_2p = QtWidgets.QPushButton(self)
        self.remove_p_em = QtWidgets.QPushButton(self)
        self.remove_p_ab.setEnabled(False)
        self.remove_p_ex.setEnabled(False)
        self.remove_p_2p.setEnabled(False)
        self.remove_p_em.setEnabled(False)
        self.remove_p_ab.clicked.connect(lambda: self.remove_baseline_curve(LineType.Absorption))
        self.remove_p_ex.clicked.connect(lambda: self.remove_baseline_curve(LineType.Excitation))
        self.remove_p_2p.clicked.connect(lambda: self.remove_baseline_curve(LineType.TwoPhoton))
        self.remove_p_em.clicked.connect(lambda: self.remove_baseline_curve(LineType.Emission))
        self.widget_layout_curve_manip.addWidget(self.label_remove_p, 5, 0)
        self.widget_layout_curve_manip.addWidget(self.remove_p_ab, 5, 1)
        self.widget_layout_curve_manip.addWidget(self.remove_p_ex, 5, 2)
        self.widget_layout_curve_manip.addWidget(self.remove_p_2p, 5, 3)
        self.widget_layout_curve_manip.addWidget(self.remove_p_em, 5, 4)

        # Line h
        # self.line_h = QtWidgets.QFrame(self)
        # self.line_h.setFrameShape(QtWidgets.QFrame.HLine)
        # self.line_h.setFrameShadow(QtWidgets.QFrame.Sunken)
        # self.widget_layout_curve_manip.addWidget(self.line_h, 6, 0, 1, -1)

        self.widget_layout.addLayout(self.widget_layout_curve_manip)

        # Curve manipulation
        self.widget_layout_curve_smooth = QtWidgets.QGridLayout()
        self.widget_layout_curve_smooth.setColumnStretch(0, 0)
        self.widget_layout_curve_smooth.setColumnStretch(1, 1)
        self.widget_layout_curve_smooth.setColumnStretch(2, 1)
        self.widget_layout_curve_smooth.setColumnStretch(3, 1)
        self.widget_layout_curve_smooth.setColumnStretch(4, 1)
        self.widget_layout_curve_smooth.setColumnMinimumWidth(0, 91)
        self.widget_layout_curve_smooth.setHorizontalSpacing(2)

        # Smooth curve
        self.label_smooth_sb = QtWidgets.QLabel(self)
        self.label_smooth_sb.setText("Smooth (SB):")
        self.smooth_sb_ab = QtWidgets.QPushButton(self)
        self.smooth_sb_ex = QtWidgets.QPushButton(self)
        self.smooth_sb_2p = QtWidgets.QPushButton(self)
        self.smooth_sb_em = QtWidgets.QPushButton(self)
        self.smooth_sb_ab.setEnabled(False)
        self.smooth_sb_ex.setEnabled(False)
        self.smooth_sb_2p.setEnabled(False)
        self.smooth_sb_em.setEnabled(False)
        self.smooth_sb_ab.clicked.connect(lambda: self.smooth_savgol_curve(LineType.Absorption))
        self.smooth_sb_ex.clicked.connect(lambda: self.smooth_savgol_curve(LineType.Excitation))
        self.smooth_sb_2p.clicked.connect(lambda: self.smooth_savgol_curve(LineType.TwoPhoton))
        self.smooth_sb_em.clicked.connect(lambda: self.smooth_savgol_curve(LineType.Emission))
        self.widget_layout_curve_smooth.addWidget(self.label_smooth_sb, 0, 0)
        self.widget_layout_curve_smooth.addWidget(self.smooth_sb_ab, 0, 1)
        self.widget_layout_curve_smooth.addWidget(self.smooth_sb_ex, 0, 2)
        self.widget_layout_curve_smooth.addWidget(self.smooth_sb_2p, 0, 3)
        self.widget_layout_curve_smooth.addWidget(self.smooth_sb_em, 0, 4)

        # Line i
        self.line_i = QtWidgets.QFrame(self)
        self.line_i.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_i.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.widget_layout_curve_smooth.addWidget(self.line_i, 1, 0, 1, -1)
        
        # Specials
        self.label_special = QtWidgets.QLabel(self)
        self.label_special.setText("Special:")
        self.special_ab = QtWidgets.QPushButton(self)
        self.special_ex = QtWidgets.QPushButton(self)
        self.special_2p = QtWidgets.QPushButton(self)
        self.special_em = QtWidgets.QPushButton(self)
        self.special_ab.setEnabled(False)
        self.special_ex.setEnabled(False)
        self.special_2p.setEnabled(False)
        self.special_em.setEnabled(False)
        self.special_ab.clicked.connect(lambda: self.special(LineType.Absorption))
        self.special_ex.clicked.connect(lambda: self.special(LineType.Excitation))
        self.special_2p.clicked.connect(lambda: self.special(LineType.TwoPhoton))
        self.special_em.clicked.connect(lambda: self.special(LineType.Emission))
        self.widget_layout_curve_smooth.addWidget(self.label_special, 2, 0)
        self.widget_layout_curve_smooth.addWidget(self.special_ab, 2, 1)
        self.widget_layout_curve_smooth.addWidget(self.special_ex, 2, 2)
        self.widget_layout_curve_smooth.addWidget(self.special_2p, 2, 3)
        self.widget_layout_curve_smooth.addWidget(self.special_em, 2, 4)

        # Line j
        self.line_j = QtWidgets.QFrame(self)
        self.line_j.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_j.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.widget_layout_curve_smooth.addWidget(self.line_j, 3, 0, 1, -1)

        self.widget_layout.addLayout(self.widget_layout_curve_smooth)

        # Reset curve, reset data
        # Data rest
        self.widget_layout_curve_reset = QtWidgets.QGridLayout()
        self.widget_layout_curve_reset.setColumnStretch(0, 0)
        self.widget_layout_curve_reset.setColumnStretch(1, 1)
        self.widget_layout_curve_reset.setColumnStretch(2, 1)
        self.widget_layout_curve_reset.setColumnStretch(3, 1)
        self.widget_layout_curve_reset.setColumnStretch(4, 1)
        self.widget_layout_curve_reset.setColumnMinimumWidth(0, 91)
        self.widget_layout_curve_reset.setHorizontalSpacing(2)

        self.label_reset_c = QtWidgets.QLabel(self)
        self.label_reset_c.setText("Reset Curve:")
        self.reset_ab = QtWidgets.QPushButton(self)
        self.reset_ex = QtWidgets.QPushButton(self)
        self.reset_2p = QtWidgets.QPushButton(self)
        self.reset_em = QtWidgets.QPushButton(self)
        self.reset_ab.setEnabled(False)
        self.reset_ex.setEnabled(False)
        self.reset_2p.setEnabled(False)
        self.reset_em.setEnabled(False)
        self.reset_ab.clicked.connect(lambda: self.reset_curve(LineType.Absorption))
        self.reset_ex.clicked.connect(lambda: self.reset_curve(LineType.Excitation))
        self.reset_2p.clicked.connect(lambda: self.reset_curve(LineType.TwoPhoton))
        self.reset_em.clicked.connect(lambda: self.reset_curve(LineType.Emission))
        self.widget_layout_curve_reset.addWidget(self.label_reset_c, 0, 0)
        self.widget_layout_curve_reset.addWidget(self.reset_ab, 0, 1)
        self.widget_layout_curve_reset.addWidget(self.reset_ex, 0, 2)
        self.widget_layout_curve_reset.addWidget(self.reset_2p, 0, 3)
        self.widget_layout_curve_reset.addWidget(self.reset_em, 0, 4)

        self.widget_layout.addLayout(self.widget_layout_curve_reset)

    def loadIndex(self):
        """
        Loads the data from the index into the widgets
        """
        # Load properties
        self.place_id()
        self.place_names()
        self.place_enable()
        self.place_database()
        self.place_reference()
        self.place_ec()
        self.place_qy()
        self.place_intensity()
        self.place_intensity_bin()
        self.place_reset()

        # Activate / deactive modification buttons
        self.place_absorption()
        self.place_two_photon()
        self.place_excitation()
        self.place_emission()
        
    def loadChecker(self):
        """
        Checks the data and forwards to data to the
        """
        self.data_check.audit(self.data_modified[self.data_index])

        self.id_qc.setPassed(self.data_check.header.valid, self.data_check.header.errors)
        self.names_qc.setPassed(self.data_check.names.valid, self.data_check.names.errors)
        self.enable_qc.setPassed(self.data_check.enable.valid, self.data_check.enable.errors)
        self.database_qc.setPassed(self.data_check.source.valid, self.data_check.source.errors)
        self.reference_qc.setPassed(self.data_check.references.valid, self.data_check.references.errors)
        self.ec_qc.setPassed(self.data_check.extinction_coefficient.valid, self.data_check.extinction_coefficient.errors)
        self.qy_qc.setPassed(self.data_check.quantum_yield.valid, self.data_check.quantum_yield.errors)
        self.intensity_qc.setPassed(self.data_check.brightness.valid, self.data_check.brightness.errors)
        self.intensity_bin_qc.setPassed(self.data_check.brightness_bin.valid, self.data_check.brightness_bin.errors)

        self.missing_wav_ab.setPassed(not self.data_check.absorption.wavelength_missing, ["Missing wavelength data"])
        self.missing_wav_ex.setPassed(not self.data_check.excitation.wavelength_missing, ["Missing wavelength data"])
        self.missing_wav_2p.setPassed(not self.data_check.two_photon.wavelength_missing, ["Missing wavelength data"])
        self.missing_wav_em.setPassed(not self.data_check.emission.wavelength_missing, ["Missing wavelength data"])

        self.missing_int_ab.setPassed(not self.data_check.absorption.intensity_missing, ["Missing intensity data"])
        self.missing_int_ex.setPassed(not self.data_check.excitation.intensity_missing, ["Missing intensity data"])
        self.missing_int_2p.setPassed(not self.data_check.two_photon.intensity_missing, ["Missing intensity data"])
        self.missing_int_em.setPassed(not self.data_check.emission.intensity_missing, ["Missing intensity data"])

        self.spectra_ab.setPassed(self.data_check.absorption.valid, self.data_check.absorption.errors)
        self.spectra_ex.setPassed(self.data_check.excitation.valid, self.data_check.excitation.errors)
        self.spectra_2p.setPassed(self.data_check.two_photon.valid, self.data_check.two_photon.errors)
        self.spectra_em.setPassed(self.data_check.emission.valid, self.data_check.emission.errors)
    
    def place_id(self):
        """ Places the header data in the correct widget """
        data = self.data_modified[self.data_index]
        self.id_lineedit.setText(data.header)
        self.id_lineedit.setEnabled(False)

    def place_names(self):
        """ Places the names data in the correct widget """
        data = self.data_modified[self.data_index]
        if data.names:
            value = ""
            for name in data.names:
                value += name + "|"
            value = value[:-1]
            self.names_lineedit.setText(value)
        else:
            self.names_lineedit.setText("")
        self.names_lineedit.setEnabled(True)

    def place_enable(self):
        """ Sets the enable data in the correct widget """
        data = self.data_modified[self.data_index]

        self.enable_true.setEnabled(True)
        self.enable_false.setEnabled(True)

        self.receiveActivatedEnableTrue(data.enable)
        self.receiveActivatedEnableFalse(not data.enable)

    def place_database(self):
        """ Places the database data in the correct widget """
        data = self.data_modified[self.data_index]
        if data.source:
            self.database_lineedit.setText(data.source)
        else:
            self.database_lineedit.setText("")
        self.database_lineedit.setEnabled(True)
    
    def place_reference(self):
        """ Places the reference data in the correct widget """
        data = self.data_modified[self.data_index]
        
        if data.references:
            ref_dict = dict()
            for i, item in enumerate(data.references):
                ref_dict[i] = item._export_json()

            self.reference_lineedit.setPlainText(json.dumps_pretty(ref_dict))
        else:
            self.reference_lineedit.setPlainText("")
        self.reference_lineedit.setEnabled(True)
    
    def place_ec(self):
        """ Places the extinction coefficient data in the correct widget """
        data = self.data_modified[self.data_index]
        if data.extinction_coefficient or data.extinction_coefficient == 0:
            self.ec_lineedit.setText(str(data.extinction_coefficient))
        else:
            self.ec_lineedit.setText("")
        self.ec_lineedit.setEnabled(True)
    
    def place_qy(self):
        """ Places the quantum yield data in the correct widget """
        data = self.data_modified[self.data_index]

        if data.quantum_yield or data.quantum_yield == 0:
            self.qy_lineedit.setText(str(data.quantum_yield))
        else:
            self.qy_lineedit.setText("")
        self.qy_lineedit.setEnabled(True)

    def place_cross_section(self):
        """ Places the quantum yield data in the correct widget """
        data = self.data_modified[self.data_index]

        if data.cross_section or data.cross_section == 0:
            self.cs_lineedit.setText(str(data.cross_section))
        else:
            self.cs_lineedit.setText("")
        self.cs_lineedit.setEnabled(True)
    
    def place_intensity(self):
        """ Places the intensity data in the correct widget """
        data = self.data_modified[self.data_index]
        if data.brightness or data.brightness == 0:
            self.intensity_lineedit.setText(str(data.brightness))
        else:
            self.intensity_lineedit.setText("")
        self.intensity_lineedit.setEnabled(True)
    
    def place_intensity_bin(self):
        """ Places the intensity binned data in the correct widget """
        data = self.data_modified[self.data_index]
        if data.brightness_bin or data.brightness_bin == 0:
            self.intensity_bin_lineedit.setText(str(data.brightness_bin))
        else:
            self.intensity_bin_lineedit.setText("")
        self.intensity_bin_lineedit.setEnabled(True)
    
    def place_reset(self):
        """ Activates the reset button """
        self.reset_button.setEnabled(True)

    def place_absorption(self):
        """ Places and dis/enables the widgets for absorption curve data """
        data = self.data_modified[self.data_index]
        if data.absorption_wavelength and data.absorption_intensity:
            self.max_label_ab.setText(str(round(data.get_max(data.absorption_intensity), 2)))
            self.min_label_ab.setText(str(round(data.get_min(data.absorption_intensity), 2)))

            self.max_select_button_ab.setEnabled(True)
            self.max_select_lineedit_ab.setModel(data.get_peaks(data.absorption_wavelength, data.absorption_intensity))

            if not data.absorption_max:
                data.absorption_max = data.get_max_wavelengths(data.absorption_wavelength, data.absorption_intensity)[0]
            self.max_select_button_ab.setText(str(round(data.absorption_max, ndigits=0)))

            self.interpolate_ab.setEnabled(True)
            self.normalize_up_ab.setEnabled(True)
            self.normalize_do_ab.setEnabled(True)
            self.cutoff_ab.setEnabled(True)
            self.remove_r_ab.setEnabled(True)
            self.remove_p_ab.setEnabled(True)
            self.smooth_sb_ab.setEnabled(True)
            self.reset_ab.setEnabled(True)
            self.special_ab.setEnabled(True)
        else:
            self.max_label_ab.setText("")
            self.min_label_ab.setText("")

            self.max_select_button_ab.setText("")
            self.max_select_button_ab.setEnabled(False)

            self.interpolate_ab.setEnabled(False)
            self.normalize_up_ab.setEnabled(False)
            self.normalize_do_ab.setEnabled(False)
            self.cutoff_ab.setEnabled(False)
            self.remove_r_ab.setEnabled(False)
            self.remove_p_ab.setEnabled(False)
            self.smooth_sb_ab.setEnabled(False)
            self.reset_ab.setEnabled(False)
            self.special_ab.setEnabled(False)

    def place_excitation(self):
        """ Places and dis/enables the widgets for excitation curve data """
        data = self.data_modified[self.data_index]
        if data.excitation_wavelength and data.excitation_intensity:
            self.max_label_ex.setText(str(round(data.get_max(data.excitation_intensity), 2)))
            self.min_label_ex.setText(str(round(data.get_min(data.excitation_intensity), 2)))

            self.max_select_button_ex.setEnabled(True)
            self.max_select_lineedit_ex.setModel(data.get_peaks(data.excitation_wavelength, data.excitation_intensity))

            if not data.excitation_max:
                data.excitation_max = data.get_max_wavelengths(data.excitation_wavelength, data.excitation_intensity)[0]
            self.max_select_button_ex.setText(str(round(data.excitation_max, ndigits=0)))

            self.interpolate_ex.setEnabled(True)
            self.normalize_up_ex.setEnabled(True)
            self.normalize_do_ex.setEnabled(True)
            self.cutoff_ex.setEnabled(True)
            self.remove_r_ex.setEnabled(True)
            self.remove_p_ex.setEnabled(True)
            self.smooth_sb_ex.setEnabled(True)
            self.reset_ex.setEnabled(True)
            self.special_ex.setEnabled(True)
        else:
            self.max_label_ex.setText("")
            self.min_label_ex.setText("")

            self.max_select_button_ex.setEnabled(False)
            self.max_select_button_ex.setText("")

            self.interpolate_ex.setEnabled(False)
            self.normalize_up_ex.setEnabled(False)
            self.normalize_do_ex.setEnabled(False)
            self.cutoff_ex.setEnabled(False)
            self.remove_r_ex.setEnabled(False)
            self.remove_p_ex.setEnabled(False)
            self.smooth_sb_ex.setEnabled(False)
            self.reset_ex.setEnabled(False)
            self.special_ex.setEnabled(False)

    def place_two_photon(self):
        """ Places and dis/enables the widgets for two photon curve data """
        data = self.data_modified[self.data_index]
        if data.two_photon_wavelength and data.two_photon_intensity:
            self.max_label_2p.setText(str(round(data.get_max(data.two_photon_intensity), 2)))
            self.min_label_2p.setText(str(round(data.get_min(data.two_photon_intensity), 2)))

            self.max_select_button_2p.setEnabled(True)
            self.max_select_lineedit_2p.setModel(data.get_peaks(data.two_photon_wavelength, data.two_photon_intensity))

            if not data.two_photon_max:
                data.two_photon_max = data.get_max_wavelengths(data.two_photon_wavelength, data.two_photon_intensity)[0]

            self.max_select_button_2p.setText(str(round(data.two_photon_max, ndigits=0)))

            self.interpolate_2p.setEnabled(True)
            self.normalize_up_2p.setEnabled(True)
            self.normalize_do_2p.setEnabled(True)
            self.cutoff_2p.setEnabled(True)
            self.remove_r_2p.setEnabled(True)
            self.remove_p_2p.setEnabled(True)
            self.smooth_sb_2p.setEnabled(True)
            self.reset_2p.setEnabled(True)
            self.special_2p.setEnabled(True)
        else:
            self.max_label_2p.setText("")
            self.min_label_2p.setText("")

            self.max_select_button_2p.setEnabled(False)
            self.max_select_button_2p.setText("")

            self.interpolate_2p.setEnabled(False)
            self.normalize_up_2p.setEnabled(False)
            self.normalize_do_2p.setEnabled(False)
            self.cutoff_2p.setEnabled(False)
            self.remove_r_2p.setEnabled(False)
            self.remove_p_2p.setEnabled(False)
            self.smooth_sb_2p.setEnabled(False)
            self.reset_2p.setEnabled(False)
            self.special_2p.setEnabled(False)

    def place_emission(self):
        """ Places and dis/enables the widgets for emission curve data """
        data = self.data_modified[self.data_index]
        if data.emission_wavelength and data.emission_intensity:
            self.max_label_em.setText(str(round(data.get_max(data.emission_intensity), 2)))
            self.min_label_em.setText(str(round(data.get_min(data.emission_intensity), 2)))

            self.max_select_button_em.setEnabled(True)
            self.max_select_lineedit_em.setModel(data.get_peaks(data.emission_wavelength, data.emission_intensity))

            if not data.emission_max:
                data.emission_max = data.get_max_wavelengths(data.emission_wavelength, data.emission_intensity)[0]
            self.max_select_button_em.setText(str(round(data.emission_max, ndigits=0)))

            self.interpolate_em.setEnabled(True)
            self.normalize_up_em.setEnabled(True)
            self.normalize_do_em.setEnabled(True)
            self.cutoff_em.setEnabled(True)
            self.remove_r_em.setEnabled(True)
            self.remove_p_em.setEnabled(True)
            self.smooth_sb_em.setEnabled(True)
            self.reset_em.setEnabled(True)
            self.special_em.setEnabled(True)
        else:
            self.max_label_em.setText("")
            self.min_label_em.setText("")

            self.max_select_button_em.setEnabled(False)
            self.max_select_button_em.setText("")

            self.interpolate_em.setEnabled(False)
            self.normalize_up_em.setEnabled(False)
            self.normalize_do_em.setEnabled(False)
            self.cutoff_em.setEnabled(False)
            self.remove_r_em.setEnabled(False)
            self.remove_p_em.setEnabled(False)
            self.smooth_sb_em.setEnabled(False)
            self.reset_em.setEnabled(False)
            self.special_em.setEnabled(False)

    def update_id(self, text, update=False):
        """
        updates the modified data id with text and reruns the checker
            :param text[str]: new text
            :param update[bool]: whether to update the showing widget
        """
        data = self.data_modified[self.data_index]
        text = text.strip(" ")
        if text:
            data.header = text
        else:
            data.header = None

        if update:
            self.place_id()

        self.data_check.header.audit(data.header)
        self.id_qc.setPassed(self.data_check.header.valid, self.data_check.header.errors)
    
    def update_names(self, text, update=False):
        """
        updates the modified data names. Transforms it into a list of names, updates the widget, and reruns the checker
            :param text[str]: new text
            :param update[bool]: whether to update the showing widget
        """
        data = self.data_modified[self.data_index]
        names = text.split("|")
        for i, name in enumerate(names):
            names[i] = name.strip(" ")
        
        if names:
            data.names = names
        else:
            data.names = None

        if update:
            self.place_names()

        # Rerun checker
        self.data_check.names.audit(data.names)
        self.names_qc.setPassed(self.data_check.names.valid, self.data_check.names.errors)

    def update_enable(self, state, update=False):
        """
        updates the modified enable. Sets, and reruns the checker
            :param state[bool]: new state
            :param update[bool]: (no effect) whether to update the showing widget
        """
        del update
        data = self.data_modified[self.data_index]

        data.enable = state

        self.data_check.enable.audit(data.enable)
        self.enable_qc.setPassed(self.data_check.enable.valid, self.data_check.enable.errors)

    def update_database(self, text, update=False):
        """
        updates the modified database. Sets, and reruns the checker
            :param text[str]: new text
            :param update[bool]: whether to update the showing widget
        """
        data = self.data_modified[self.data_index]
        text = text.strip(" ")

        if text:
            data.source = text
        else:
            data.source = None

        if update:
            self.place_database()

        self.data_check.source.audit(data.source)
        self.database_qc.setPassed(self.data_check.source.valid, self.data_check.source.errors)

    def update_reference(self, text, update=False):
        """
        updates the modified reference. Sets, and reruns the checker
            :param text[str]: new text
            :param update[bool]: whether to update the showing widget
        """
        data = self.data_modified[self.data_index]
        text = text.strip(" ")

        if text:
            references = []
            try:
                text_dict = json.loads(text)
            except json.JSONDecodeError:
                # invalid JSON -> Ignore
                self.reference_qc.setPassed(False, ["Invalid JSON"])
                return

            for key in text_dict:
                reference = Reference()

                # reference should be a dictionary object 
                if not isinstance(text_dict[key], dict):
                    self.reference_qc.setPassed(False, [f"Invalid Reference at key: {key}"])
                    return

                reference._load_json(text_dict[key])
                references.append(reference)
            data.references = references
        else:
            data.references = []

        if update:
            self.place_reference()

        self.data_check.references.audit(data.references)
        self.reference_qc.setPassed(self.data_check.references.valid, self.data_check.references.errors)

    def update_ec(self, text, update=False):
        """
        updates the modified extinction coefficient. Sets, and reruns the checker
            :param text[str]: new text
            :param update[bool]: whether to update the showing widget
        """
        data = self.data_modified[self.data_index]

        if not text.strip(" "):
            data.extinction_coefficient = None
        else:
            try:
                data.extinction_coefficient = float(text)
            except ValueError:
                data.extinction_coefficient = None

        if update:
            self.place_ec()

        self.data_check.extinction_coefficient.audit(data.extinction_coefficient)
        self.data_check.brightness.audit(data.brightness)

        if data.quantum_yield and data.extinction_coefficient:
            self.data_check.brightness.audit_brightness(data.brightness, data.calculate_brightness(data.extinction_coefficient, data.quantum_yield))

        self.ec_qc.setPassed(self.data_check.extinction_coefficient.valid, self.data_check.extinction_coefficient.errors)
        self.intensity_qc.setPassed(self.data_check.brightness.valid, self.data_check.brightness.errors)

    def update_qy(self, text, update=False):
        """
        updates the modified quantum yield. Sets, and reruns the checker
            :param text[str]: new text
            :param update[bool]: whether to update the showing widget
        """
        data = self.data_modified[self.data_index]

        if not text.strip(" "):
            data.quantum_yield = None
        else:
            try:
                data.quantum_yield = float(text)
            except ValueError:
                data.quantum_yield = None
 
        if update:
            self.place_qy()

        self.data_check.quantum_yield.audit(data.quantum_yield)
        self.data_check.brightness.audit(data.brightness)

        if data.quantum_yield and data.extinction_coefficient:
            self.data_check.brightness.audit_brightness(data.brightness, data.calculate_brightness(data.extinction_coefficient, data.quantum_yield))

        self.qy_qc.setPassed(self.data_check.quantum_yield.valid, self.data_check.quantum_yield.errors)
        self.intensity_qc.setPassed(self.data_check.brightness.valid, self.data_check.brightness.errors)

    def update_intensity(self, text, update=False):
        """
        updates the modified intensity. Sets, and reruns the checker
            :param text[str]: new text
            :param update[bool]: whether to update the showing widget
        """
        data = self.data_modified[self.data_index]

        if not text.strip(" "):
            data.brightness = None
        else:
            try:
                data.brightness = float(text)
            except ValueError:
                data.brightness = None

        if update:
            self.place_intensity()
        
        self.data_check.brightness.audit(data.brightness)
        self.data_check.brightness_bin.audit(data.brightness_bin)

        if data.quantum_yield and data.extinction_coefficient:
            self.data_check.brightness.audit_brightness(data.brightness, data.calculate_brightness(data.extinction_coefficient, data.quantum_yield))

        self.intensity_qc.setPassed(self.data_check.brightness.valid, self.data_check.brightness.errors)
        self.intensity_bin_qc.setPassed(self.data_check.brightness_bin.valid, self.data_check.brightness_bin.errors)
    
    def update_intensity_bin(self, text, update=False):
        """
        updates the modified intensity. Sets, and reruns the checker
            :param text[str]: new text
            :param update[bool]: whether to update the showing widget
        """
        data = self.data_modified[self.data_index]
        if not text.strip(" "):
            data.brightness_bin = None
        else:
            try:
                data.brightness_bin = int(text)
            except ValueError:
                data.brightness_bin = None
        
        if update:
            self.place_intensity_bin()

        self.data_check.brightness_bin.audit(data.brightness_bin)
        self.intensity_bin_qc.setPassed(self.data_check.brightness_bin.valid, self.data_check.brightness_bin.errors)

    def update_curve(self, line_type):
        """
        Updates the current widget to the new state (and emits the necessary signals)
            :param line_type[LineType]: the modified line
        """
        # Get data reference
        data = self.data_modified[self.data_index]

        # Rerun the checker 
        self.loadChecker()

        # Update the min/max values
        if line_type == LineType.Absorption:
            self.max_label_ab.setText(str(round(data.get_max(data.absorption_intensity), 2)))
            self.min_label_ab.setText(str(round(data.get_min(data.absorption_intensity), 2)))
        elif line_type == LineType.Excitation:
            self.max_label_ex.setText(str(round(data.get_max(data.excitation_intensity), 2)))
            self.min_label_ex.setText(str(round(data.get_min(data.excitation_intensity), 2)))
        elif line_type == LineType.TwoPhoton:
            self.max_label_2p.setText(str(round(data.get_max(data.two_photon_intensity), 2)))
            self.min_label_2p.setText(str(round(data.get_min(data.two_photon_intensity), 2)))
        elif line_type == LineType.Emission:
            self.max_label_em.setText(str(round(data.get_max(data.emission_intensity), 2)))
            self.min_label_em.setText(str(round(data.get_min(data.emission_intensity), 2)))

        # Update the max wavelength
        if line_type == LineType.Absorption:
            self.max_select_lineedit_ab.setModel(data.get_peaks(data.absorption_wavelength, data.absorption_intensity))
            data.absorption_max = data.get_max_wavelengths(data.absorption_wavelength, data.absorption_intensity)[0]
            self.max_select_button_ab.setText(str(data.absorption_max))
        elif line_type == LineType.Excitation:
            self.max_select_lineedit_ex.setModel(data.get_peaks(data.excitation_wavelength, data.excitation_intensity))
            data.excitation_max = data.get_max_wavelengths(data.excitation_wavelength, data.excitation_intensity)[0]
            self.max_select_button_ex.setText(str(data.excitation_max))
        elif line_type == LineType.TwoPhoton:
            self.max_select_lineedit_2p.setModel(data.get_peaks(data.two_photon_wavelength, data.two_photon_intensity))
            data.two_photon_max = data.get_max_wavelengths(data.two_photon_wavelength, data.two_photon_intensity)[0]
            self.max_select_button_2p.setText(str(data.two_photon_max))
        elif line_type == LineType.Emission:
            self.max_select_lineedit_em.setModel(data.get_peaks(data.emission_wavelength, data.emission_intensity))
            data.emission_max = data.get_max_wavelengths(data.emission_wavelength, data.emission_intensity)[0]
            self.max_select_button_em.setText(str(data.emission_max))

        # Update the graphs by sending a signal
        self.sendDataModified.emit(self.data_index, line_type)

    def interpolate_curve(self, line_type):
        """
        Uses interpolate on the specified line_type and replaces
            :param line_type[LineType]: line to modify
        """
        data = self.data_modified[self.data_index]

        if line_type == LineType.Absorption:
            data.absorption_wavelength, data.absorption_intensity = data.interpolate(data.absorption_wavelength, data.absorption_intensity)
        elif line_type == LineType.Excitation:
            data.excitation_wavelength, data.excitation_intensity = data.interpolate(data.excitation_wavelength, data.excitation_intensity)
        elif line_type == LineType.TwoPhoton:
            data.two_photon_wavelength, data.two_photon_intensity = data.interpolate(data.two_photon_wavelength, data.two_photon_intensity)
        elif line_type == LineType.Emission:
            data.emission_wavelength, data.emission_intensity = data.interpolate(data.emission_wavelength, data.emission_intensity)

        self.update_curve(line_type)
    
    def normalize_up_curve(self, line_type):
        """
        Normalizes the max value of the intensity of the specified line_type and replaces
            :param line_type[LineType]: line to modify
        """
        data = self.data_modified[self.data_index]

        if line_type == LineType.Absorption:
            data.absorption_intensity = data.normalize(data.absorption_intensity, max_value=100.0, min_value=None)
        elif line_type == LineType.Excitation:
            data.excitation_intensity = data.normalize(data.excitation_intensity, max_value=100.0, min_value=None)
        elif line_type == LineType.TwoPhoton:
            data.two_photon_intensity = data.normalize(data.two_photon_intensity, max_value=100.0, min_value=None)
        elif line_type == LineType.Emission:
            data.emission_intensity = data.normalize(data.emission_intensity, max_value=100.0, min_value=None)

        self.update_curve(line_type)
    
    def normalize_down_curve(self, line_type):
        """
        Normalizes the min value of the specified line_type and replaces
            :param line_type[LineType]: line to modify
        """
        data = self.data_modified[self.data_index]

        if line_type == LineType.Absorption:
            data.absorption_intensity = data.normalize(data.absorption_intensity, max_value=None, min_value=0.0)
        elif line_type == LineType.Excitation:
            data.excitation_intensity = data.normalize(data.excitation_intensity, max_value=None, min_value=0.0)
        elif line_type == LineType.TwoPhoton:
            data.two_photon_intensity = data.normalize(data.two_photon_intensity, max_value=None, min_value=0.0)
        elif line_type == LineType.Emission:
            data.emission_intensity = data.normalize(data.emission_intensity, max_value=None, min_value=0.0)

        self.update_curve(line_type)

    def cutoff_curve(self, line_type):
        """
        Cutoff any intensity value outside of 0-100 and replaces
            :param line_type[LineType]: line to modify
        """
        data = self.data_modified[self.data_index]

        if line_type == LineType.Absorption:
            data.absorption_intensity = data.cutoff_min(data.absorption_intensity, min_value=0.0)
            data.absorption_intensity = data.cutoff_max(data.absorption_intensity, max_value=100.0)
        elif line_type == LineType.Excitation:
            data.excitation_intensity = data.cutoff_min(data.excitation_intensity, min_value=0.0)
            data.excitation_intensity = data.cutoff_max(data.excitation_intensity, max_value=100.0)
        elif line_type == LineType.TwoPhoton:
            data.two_photon_intensity = data.cutoff_min(data.two_photon_intensity, min_value=0.0)
            data.two_photon_intensity = data.cutoff_max(data.two_photon_intensity, max_value=100.0)
        elif line_type == LineType.Emission:
            data.emission_intensity = data.cutoff_min(data.emission_intensity, min_value=0.0)
            data.emission_intensity = data.cutoff_max(data.emission_intensity, max_value=100.0)

        self.update_curve(line_type)

    def remove_return_curve(self, line_type):
        """
        ordens the curve by removing any wavelength entree smaller then the previous entree, effectively removing the returning part of the curve
            :param line_type[LineType]: line to modify
        """
        data = self.data_modified[self.data_index]

        if line_type == LineType.Absorption:
            data.absorption_wavelength, data.absorption_intensity = data.strip_return(data.absorption_wavelength, data.absorption_intensity)
        elif line_type == LineType.Excitation:
            data.excitation_wavelength, data.excitation_intensity = data.strip_return(data.excitation_wavelength, data.excitation_intensity)
        elif line_type == LineType.TwoPhoton:
            data.two_photon_wavelength, data.two_photon_intensity = data.strip_return(data.two_photon_wavelength, data.two_photon_intensity)
        elif line_type == LineType.Emission:
            data.emission_wavelength, data.emission_intensity = data.strip_return(data.emission_wavelength, data.emission_intensity)

        self.update_curve(line_type)

    def remove_baseline_curve(self, line_type):
        """
        Removes baseline padding (=0.0 value)
            :param line_type[LineType]: line to modify
        """
        data = self.data_modified[self.data_index]

        if line_type == LineType.Absorption:
            data.absorption_wavelength, data.absorption_intensity = data.strip_exact(data.absorption_wavelength, data.absorption_intensity, baseline=0.0)
        elif line_type == LineType.Excitation:
            data.excitation_wavelength, data.excitation_intensity = data.strip_exact(data.excitation_wavelength, data.excitation_intensity, baseline=0.0)
        elif line_type == LineType.TwoPhoton:
            data.two_photon_wavelength, data.two_photon_intensity = data.strip_exact(data.two_photon_wavelength, data.two_photon_intensity, baseline=0.0)
        elif line_type == LineType.Emission:
            data.emission_wavelength, data.emission_intensity = data.strip_exact(data.emission_wavelength, data.emission_intensity, baseline=0.0)

        self.update_curve(line_type)

    def smooth_savgol_curve(self, line_type):
        """
        Smooths the intensity curve using Savitsky-Golay smoothing
            :param line_type[LineType]: line to modify
        """
        data = self.data_modified[self.data_index]

        if line_type == LineType.Absorption:
            data.absorption_intensity = data.smooth_intensity_savgol(data.absorption_intensity, width=6, degree=2)
        elif line_type == LineType.Excitation:
            data.excitation_intensity = data.smooth_intensity_savgol(data.excitation_intensity, width=6, degree=2)
        elif line_type == LineType.TwoPhoton:
            data.two_photon_intensity = data.smooth_intensity_savgol(data.two_photon_intensity, width=6, degree=2)
        elif line_type == LineType.Emission:
            data.emission_intensity = data.smooth_intensity_savgol(data.emission_intensity, width=6, degree=2)

        self.update_curve(line_type)

    def special(self, line_type):
        """ 
        Opens a popup for special function selection 
            :param line_type[LineType]: curve type
        """
        self.special_line_type = line_type
        self.special_popup.show()

    def reset_metadata(self):
        """
        Resets the metadata by copying original data into the modified data
        """
        data = self.data_modified[self.data_index]

        # Not all data have original data (this is the case for sourced data!)
        try:
            data_original = self.data_original[self.data_index]
        except KeyError:
            return

        data.header = copy.deepcopy(data_original.header)
        data.names = copy.deepcopy(data_original.names)
        data.enable = data_original.enable
        data.categories = copy.deepcopy(data_original.categories)
        data.source = copy.deepcopy(data_original.source)
        data.url = copy.deepcopy(data_original.url)
        data.references = copy.deepcopy(data_original.references)
        data.extinction_coefficient = copy.deepcopy(data_original.extinction_coefficient)
        data.quantum_yield = copy.deepcopy(data_original.quantum_yield)
        data.cross_section = copy.deepcopy(data_original.cross_section)
        data.brightness = copy.deepcopy(data_original.brightness)
        data.brightness_bin = copy.deepcopy(data_original.brightness_bin)

        self.place_id()
        self.place_names()
        self.place_enable()
        self.place_database()
        #self.place_categories()
        #self.place_url()
        self.place_reference()
        self.place_ec()
        self.place_qy()
        #self.place_cross_section()
        self.place_intensity()
        self.place_intensity_bin()

        self.loadChecker()

    def reset_curve(self, line_type):
        """
        Resets the curve to original state
            :param line_type[LineType]: line to reset
        """
        data = self.data_modified[self.data_index]

        # Not all data have original data (this is the case for sourced data!)
        try:
            data_original = self.data_original[self.data_index]
        except KeyError:
            return

        if line_type == LineType.Absorption:
            data.absorption_wavelength = copy.deepcopy(data_original.absorption_wavelength)
            data.absorption_intensity = copy.deepcopy(data_original.absorption_intensity)
        elif line_type == LineType.Excitation:
            data.excitation_wavelength = copy.deepcopy(data_original.excitation_wavelength)
            data.excitation_intensity = copy.deepcopy(data_original.excitation_intensity)
        elif line_type == LineType.TwoPhoton:
            data.two_photon_wavelength = copy.deepcopy(data_original.two_photon_wavelength)
            data.two_photon_intensity = copy.deepcopy(data_original.two_photon_intensity)
        elif line_type == LineType.Emission:
            data.emission_wavelength = copy.deepcopy(data_original.emission_wavelength)
            data.emission_intensity = copy.deepcopy(data_original.emission_intensity)

        self.loadChecker()

        self.update_curve(line_type)

    @QtCore.pyqtSlot(dict, dict)
    def receiveData(self, data_original: Dict[Identifier, Data], data_modified: Dict[Identifier, Data]) -> None:
        """
        Loads the factory data into the listtab
            :param data_original[Reader]: list of the unmodified data
            :param data_modifeid[Reader]: list of the modifyable data
        """
        self.data_original = data_original
        self.data_modified = data_modified

    @QtCore.pyqtSlot(Identifier)
    def receiveDataIndex(self, index: Identifier) -> None:
        """
        Slot: set the active index and activates the relevant pushbuttons
        """
        self.data_index = index
        self.loadChecker()
        self.loadIndex()

    @QtCore.pyqtSlot(bool)
    def receiveActivatedEnableTrue(self, active):
        """
        Received when the self.enable_true button is (de)activated
            :param active[bool]: the activated state
        """
        if active is True:
            self.enable_false.setActive(False)
            self.update_enable(True)
        else:
            self.enable_false.setActive(True)
            self.update_enable(False)

    @QtCore.pyqtSlot(bool)
    def receiveActivatedEnableFalse(self, active):
        """
        Received when the self.enable_false button is (de)activated
            :param active[bool]: the activated state
        """
        if active is True:
            self.enable_true.setActive(False)
            self.update_enable(False)
        else:
            self.enable_true.setActive(True)
            self.update_enable(True)
    
    @QtCore.pyqtSlot()
    def receiveClickedButtonAb(self):
        self.max_select_button_ab.hide()
        self.max_select_lineedit_ab.show()
        self.max_select_lineedit_ab.popup.show()

    @QtCore.pyqtSlot(object)
    def receiveEditingFinishedAb(self, wavelength):
        """
        Receives the selection / free-typed wavelength of the lineedit
            :param wavelength[none/float]: wavelength
        """

        if wavelength:
            self.data_modified[self.data_index].absorption_max = wavelength
            self.max_select_button_ab.setText(str(round(wavelength, ndigits=0)))
            self.sendDataModified.emit(self.data_index, LineType.Absorption)

        self.max_select_lineedit_ab.hide()
        self.max_select_lineedit_ab.popup.hide()
        self.max_select_button_ab.show()

    @QtCore.pyqtSlot()
    def receiveClickedButtonEx(self):
        self.max_select_button_ex.hide()
        self.max_select_lineedit_ex.show()
        self.max_select_lineedit_ex.popup.show()

    @QtCore.pyqtSlot(object)
    def receiveEditingFinishedEx(self, wavelength):
        """
        Receives the selection / free-typed wavelength of the lineedit
            :param wavelength[none/float]: wavelength
        """
        if wavelength:
            self.data_modified[self.data_index].excitation_max = wavelength
            self.max_select_button_ex.setText(str(round(wavelength, ndigits=0)))
            self.sendDataModified.emit(self.data_index, LineType.Excitation)
        
        self.max_select_lineedit_ex.hide()
        self.max_select_lineedit_ex.popup.hide()
        self.max_select_button_ex.show()

    @QtCore.pyqtSlot()
    def receiveClickedButton2p(self):
        self.max_select_button_2p.hide()
        self.max_select_lineedit_2p.show()
        self.max_select_lineedit_2p.popup.show()

    @QtCore.pyqtSlot(object)
    def receiveEditingFinished2p(self, wavelength):
        """
        Receives the selection / free-typed wavelength of the lineedit
            :param wavelength[none/float]: wavelength
        """
        if wavelength:
            self.data_modified[self.data_index].two_photon_max = wavelength
            self.max_select_button_2p.setText(str(round(wavelength, ndigits=0)))
            self.sendDataModified.emit(self.data_index, LineType.TwoPhoton)

        self.max_select_lineedit_2p.hide()
        self.max_select_lineedit_2p.popup.hide()
        self.max_select_button_2p.show()

    @QtCore.pyqtSlot()
    def receiveClickedButtonEm(self):
        self.max_select_button_em.hide()
        self.max_select_lineedit_em.show()
        self.max_select_lineedit_em.popup.show()

    @QtCore.pyqtSlot(object)
    def receiveEditingFinishedEm(self, wavelength):
        """
        Receives the selection / free-typed wavelength of the lineedit
            :param wavelength[none/float]: wavelength
        """
        if wavelength:
            self.data_modified[self.data_index].emission_max = wavelength
            self.max_select_button_em.setText(str(round(wavelength, ndigits=0)))
            self.sendDataModified.emit(self.data_index, LineType.Emission)

        self.max_select_lineedit_em.hide()
        self.max_select_lineedit_em.popup.hide()
        self.max_select_button_em.show()

    @QtCore.pyqtSlot(SpecialFunctionType, object, object)
    def receiveSpecialFunction(self, function_type, param_a, param_b):
        """
        Receives and parses a special function call
            :param function_type[SpecialFunctionType]: the function that is called
            :param param_a[object]: (optional) parameter A of the function call
            :param param_b[object]: (optional) parameter B of the function call
        """
        data = self.data_modified[self.data_index]
        line_type = self.special_line_type

        if function_type == SpecialFunctionType.Invalid:
            self.special_line_type = None
            return

        elif function_type == SpecialFunctionType.Normalize:
            if line_type == LineType.Absorption:
                data.absorption_intensity = data.normalize(data.absorption_intensity, max_value=param_b, min_value=param_a)
            elif line_type == LineType.Excitation:
                data.excitation_intensity = data.normalize(data.excitation_intensity, max_value=param_b, min_value=param_a)
            elif line_type == LineType.TwoPhoton:
                data.two_photon_intensity = data.normalize(data.two_photon_intensity, max_value=param_b, min_value=param_a)
            elif line_type == LineType.Emission:
                data.emission_intensity = data.normalize(data.emission_intensity, max_value=param_b, min_value=param_a)

        elif function_type == SpecialFunctionType.CutoffMin:
            if line_type == LineType.Absorption:
                data.absorption_intensity = data.cutoff_min(data.absorption_intensity, min_value=param_a)
            elif line_type == LineType.Excitation:
                data.excitation_intensity = data.cutoff_min(data.excitation_intensity, min_value=param_a)
            elif line_type == LineType.TwoPhoton:
                data.two_photon_intensity = data.cutoff_min(data.two_photon_intensity, min_value=param_a)
            elif line_type == LineType.Emission:
                data.emission_intensity = data.cutoff_min(data.emission_intensity, min_value=param_a)
        
        elif function_type == SpecialFunctionType.CutoffMax:
            if line_type == LineType.Absorption:
                data.absorption_intensity = data.cutoff_max(data.absorption_intensity, max_value=param_a)
            elif line_type == LineType.Excitation:
                data.excitation_intensity = data.cutoff_max(data.excitation_intensity, max_value=param_a)
            elif line_type == LineType.TwoPhoton:
                data.two_photon_intensity = data.cutoff_max(data.two_photon_intensity, max_value=param_a)
            elif line_type == LineType.Emission:
                data.emission_intensity = data.cutoff_max(data.emission_intensity, max_value=param_a)
        
        elif function_type == SpecialFunctionType.Strip:
            if line_type == LineType.Absorption:
                data.absorption_wavelength, data.absorption_intensity = data.strip(data.absorption_wavelength, data.absorption_intensity, strip_value=param_a)
            elif line_type == LineType.Excitation:
                data.excitation_wavelength, data.excitation_intensity = data.strip(data.excitation_wavelength, data.excitation_intensity, strip_value=param_a)
            elif line_type == LineType.TwoPhoton:
                data.two_photon_wavelength, data.two_photon_intensity = data.strip(data.two_photon_wavelength, data.two_photon_intensity, strip_value=param_a)
            elif line_type == LineType.Emission:
                data.emission_wavelength, data.emission_intensity = data.strip(data.emission_wavelength, data.emission_intensity, strip_value=param_a)

        elif function_type == SpecialFunctionType.StripExact:
            if line_type == LineType.Absorption:
                data.absorption_wavelength, data.absorption_intensity = data.strip_exact(data.absorption_wavelength, data.absorption_intensity, baseline=param_a)
            elif line_type == LineType.Excitation:
                data.excitation_wavelength, data.excitation_intensity = data.strip_exact(data.excitation_wavelength, data.excitation_intensity, baseline=param_a)
            elif line_type == LineType.TwoPhoton:
                data.two_photon_wavelength, data.two_photon_intensity = data.strip_exact(data.two_photon_wavelength, data.two_photon_intensity, baseline=param_a)
            elif line_type == LineType.Emission:
                data.emission_wavelength, data.emission_intensity = data.strip_exact(data.emission_wavelength, data.emission_intensity, baseline=param_a)

        elif function_type == SpecialFunctionType.RemoveGap:
            if line_type == LineType.Absorption:
                data.absorption_wavelength, data.absorption_intensity = data.remove_gaps(data.absorption_wavelength, data.absorption_intensity, gap=param_a)
            elif line_type == LineType.Excitation:
                data.excitation_wavelength, data.excitation_intensity = data.remove_gaps(data.excitation_wavelength, data.excitation_intensity, gap=param_a)
            elif line_type == LineType.TwoPhoton:
                data.two_photon_wavelength, data.two_photon_intensity = data.remove_gaps(data.two_photon_wavelength, data.two_photon_intensity, gap=param_a)
            elif line_type == LineType.Emission:
                data.emission_wavelength, data.emission_intensity = data.remove_gaps(data.emission_wavelength, data.emission_intensity, gap=param_a)

        elif function_type == SpecialFunctionType.SmoothSG:
            if line_type == LineType.Absorption:
                data.absorption_intensity = data.smooth_intensity_savgol(data.absorption_intensity, width=param_a, degree=param_b)
            elif line_type == LineType.Excitation:
                data.excitation_intensity = data.smooth_intensity_savgol(data.excitation_intensity, width=param_a, degree=param_b)
            elif line_type == LineType.TwoPhoton:
                data.two_photon_intensity = data.smooth_intensity_savgol(data.two_photon_intensity, width=param_a, degree=param_b)
            elif line_type == LineType.Emission:
                data.emission_intensity = data.smooth_intensity_savgol(data.emission_intensity, width=param_a, degree=param_b)

        self.update_curve(line_type)

    @QtCore.pyqtSlot(object, object)
    def globalClicked(self, source, event):
        """ receives signal if main window is clicked. Is used to cut lineedits short """
        self.max_select_lineedit_ab.mainWindowMousePressEvent(source, event)
        self.max_select_lineedit_ex.mainWindowMousePressEvent(source, event)
        self.max_select_lineedit_2p.mainWindowMousePressEvent(source, event)
        self.max_select_lineedit_em.mainWindowMousePressEvent(source, event)

class GraphTab(QtWidgets.QWidget):
    """
    Widget containing two graphs
        :param parent[QWidget]: parent widget
    """
    sendActivatedAbsorption = QtCore.pyqtSignal(bool)
    sendActivatedExcitation = QtCore.pyqtSignal(bool)
    sendActivatedTwoPhoton = QtCore.pyqtSignal(bool)
    sendActivatedEmission = QtCore.pyqtSignal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.widget_layout = QtWidgets.QVBoxLayout(self)
        self.setLayout(self.widget_layout)

        self.data_original: Dict[Identifier, Data] = None
        self.data_modified: Dict[Identifier, Data] = None
        self.data_index: Identifier = None

        # Add graph type selection buttons here
        self.button_absorption = ActiveButton("Absorption", self)
        self.button_excitation = ActiveButton("Excitation", self)
        self.button_two_photon = ActiveButton("2Photon", self)
        self.button_emission = ActiveButton("Emission", self)
        self.button_absorption.setEnabled(False)
        self.button_excitation.setEnabled(False)
        self.button_two_photon.setEnabled(False)
        self.button_emission.setEnabled(False)
        self.button_absorption.sendActivated.connect(self.receiveActivatedAbsorption)
        self.button_excitation.sendActivated.connect(self.receiveActivatedExcitation)
        self.button_two_photon.sendActivated.connect(self.receiveActivatedTwoPhoton)
        self.button_emission.sendActivated.connect(self.receiveActivatedEmission)

        self.button_layout = QtWidgets.QHBoxLayout()
        self.button_layout.addWidget(self.button_absorption)
        self.button_layout.addWidget(self.button_excitation)
        self.button_layout.addWidget(self.button_two_photon)
        self.button_layout.addWidget(self.button_emission)
        self.layout().addLayout(self.button_layout)

        # Adds graphs
        self.graph = GraphPlotLayout()
        self.layout().addLayout(self.graph)

        self.graph2 = GraphPlotLayout()
        self.layout().addLayout(self.graph2)

    def reset(self):
        """
        Resets the GraphTab class back to original
        """
        self.setActiveAbsorption(False)
        self.setActiveExcitation(False)
        self.setActiveTwoPhoton(False)
        self.setActiveEmission(False)

        self.graph.resetPlot()
        self.graph2.resetPlot()

    def setEnabledAbsorption(self, enable):
        """
        Set enable state
            :param enable[bool]: state
        """
        self.button_absorption.setEnabled(enable)

    def setEnabledExcitation(self, enable):
        """
        Set enable state
            :param enable[bool]: state
        """
        self.button_excitation.setEnabled(enable)

    def setEnabledTwoPhoton(self, enable):
        """
        Set enable state
            :param enable[bool]: state
        """
        self.button_two_photon.setEnabled(enable)

    def setEnabledEmission(self, enable):
        """
        Set enable state
            :param enable[bool]: state
        """
        self.button_emission.setEnabled(enable)

        # Convenience plotting functions
    
    def setActiveAbsorption(self, active):
        """
        Set active state of the absorption button.
            :param active[bool]: active state to set
        """
        self.button_absorption.setActive(active)

    def setActiveExcitation(self, active):
        """
        Set active state of the excitation button.
            :param active[bool]: active state to set
        """
        self.button_excitation.setActive(active)

    def setActiveTwoPhoton(self, active):
        """
        Set active state of the two photon button.
            :param active[bool]: active state to set
        """
        self.button_two_photon.setActive(active)

    def setActiveEmission(self, active):
        """
        Set active state of the emission button.
            :param active[bool]: active state to set
        """
        self.button_emission.setActive(active)

    def plotCurves(self, line_type):
        """
        Plot the original and modified data at graph
            :param line_type[LineType]: line base type
        """
        plot_o = True
        plot_m = True

        try:
            reader_o = self.data_original[self.data_index]
        except KeyError:
            plot_o = False

        try:
            reader_m = self.data_modified[self.data_index]
        except KeyError:
            plot_m = False

        if not plot_o and not plot_m:
            return

        if line_type == LineType.Absorption:
            if plot_o:
                wavelength_o = reader_o.absorption_wavelength
                intensity_o = reader_o.absorption_intensity
            if plot_m:
                wavelength_m = reader_m.absorption_wavelength
                intensity_m = reader_m.absorption_intensity
                max_m = reader_m.absorption_max
        elif line_type == LineType.Excitation:
            if plot_o:
                wavelength_o = reader_o.excitation_wavelength
                intensity_o = reader_o.excitation_intensity
            if plot_m:
                wavelength_m = reader_m.excitation_wavelength
                intensity_m = reader_m.excitation_intensity
                max_m = reader_m.excitation_max
        elif line_type == LineType.TwoPhoton:
            if plot_o:
                wavelength_o = reader_o.two_photon_wavelength
                intensity_o = reader_o.two_photon_intensity
            if plot_m:
                wavelength_m = reader_m.two_photon_wavelength
                intensity_m = reader_m.two_photon_intensity
                max_m = reader_m.two_photon_max
        elif line_type == LineType.Emission:
            if plot_o:
                wavelength_o = reader_o.emission_wavelength
                intensity_o = reader_o.emission_intensity
            if plot_m:
                wavelength_m = reader_m.emission_wavelength
                intensity_m = reader_m.emission_intensity
                max_m = reader_m.emission_max

        # Make sure we can actually plot stuff
        if plot_o:
            if not wavelength_o or not intensity_o:
                plot_o = False

        if plot_m:
            if not wavelength_m or not intensity_m:
                plot_m = False

        # Reset plot
        self.graph.eraseLines(0)
        self.graph.eraseLines(1)
        self.graph.eraseLines(2)
        self.graph.eraseLines(3)

        # Set plots        
        if plot_o:
            self.graph.plotLine(
                0, 
                wavelength_o, 
                intensity_o,
                zorder=2,
                color="#000000",
                line_style="--",
                fill=False,
                rescale=True,
                draw=False
            )

        if plot_m:
            self.graph.plotLine(
                1, 
                wavelength_m, 
                intensity_m,
                zorder=3,
                color="#FF0000",
                line_style="-",
                fill=True,
                rescale=True,
                draw=False
            )

            try:
                peaks_m = reader_m.get_peaks(wavelength_m, intensity_m) 
                dales_m = reader_m.get_dales(wavelength_m, intensity_m)
            except:
                peaks_m = []
                dales_m = []

            for peak in peaks_m:
                self.graph.plotLineVertical(
                    2,
                    peak,
                    zorder=5,
                    color="#FF8C00",
                    line_style="-",
                    draw=False
                )

            for dale in dales_m:
                self.graph.plotLineVertical(
                    2,
                    dale,
                    zorder=5,
                    color="#4169E1",
                    line_style="-",
                    draw=False
                )

            if not max_m:
                try:
                    max_m = reader_m.get_max_wavelengths(wavelength_m, intensity_m)[0]
                except:
                    max_m = 0.0

            self.graph.plotLineVertical(
                3,
                max_m,
                zorder=6,
                color="#FF0000",
                line_style="-",
                draw=False
            )

        # Draw curves
        self.graph.draw()

    def plotCurves2(self, line_type):
        """
        Plot the modified data at graph_2
            :param line_type[LineType]: line base type
        """
        plot_m = True

        try:
            reader_m = self.data_modified[self.data_index]
        except KeyError:
            plot_m = False

        self.graph2.eraseLines(0)
        self.graph2.eraseLines(1)
        self.graph2.eraseLines(2)
        self.graph2.eraseLines(3)

        if not plot_m:
            return

        wavelength_min = 1500
        wavelength_max = 0

        if reader_m.absorption_wavelength and reader_m.absorption_intensity:
            if line_type == LineType.Absorption:
                linecolor = "#FF0000"
            else:
                linecolor ="#000000"
            
            self.graph2.plotLine(
                0, 
                reader_m.absorption_wavelength, 
                reader_m.absorption_intensity,
                zorder=2,
                color=linecolor,
                line_style=":",
                fill=False,
                rescale=False,
                draw=False
            )

            if reader_m.absorption_max:
                self.graph2.plotLineVertical(
                    0,
                    reader_m.absorption_max,
                    zorder=6,
                    color=linecolor,
                    line_style=":",
                    draw=False
                )

            wavelength_min = min(reader_m.absorption_wavelength)
            wavelength_max = max(reader_m.absorption_wavelength)

        if reader_m.excitation_wavelength and reader_m.excitation_intensity:
            if line_type == LineType.Excitation:
                linecolor = "#FF0000"
            else:
                linecolor ="#000000"
            
            self.graph2.plotLine(
                1, 
                reader_m.excitation_wavelength, 
                reader_m.excitation_intensity,
                zorder=2,
                color=linecolor,
                line_style="--",
                fill=False,
                rescale=False,
                draw=False
            )

            if reader_m.excitation_max:
                self.graph2.plotLineVertical(
                    1,
                    reader_m.excitation_max,
                    zorder=6,
                    color=linecolor,
                    line_style="--",
                    draw=False
                )
            
            ex_min = min(reader_m.excitation_wavelength)
            ex_max = max(reader_m.excitation_wavelength)
            if ex_min < wavelength_min:
                wavelength_min = ex_min
            if ex_max > wavelength_max:
                wavelength_max = ex_max
        
        if reader_m.emission_wavelength and reader_m.emission_intensity:
            if line_type == LineType.Emission:
                linecolor = "#FF0000"
            else:
                linecolor ="#000000"

            self.graph2.plotLine(
                2, 
                reader_m.emission_wavelength, 
                reader_m.emission_intensity,
                zorder=2,
                color=linecolor,
                line_style="-",
                fill=False,
                rescale=False,
                draw=False
            )

            if reader_m.emission_max:
                self.graph2.plotLineVertical(
                    2,
                    reader_m.emission_max,
                    zorder=6,
                    color=linecolor,
                    line_style="-",
                    draw=False
                )

            em_min = min(reader_m.emission_wavelength)
            em_max = max(reader_m.emission_wavelength)
            if em_min < wavelength_min:
                wavelength_min = em_min
            if em_max > wavelength_max:
                wavelength_max = em_max
        
        if reader_m.two_photon_wavelength and reader_m.two_photon_intensity:
            if line_type == LineType.TwoPhoton:
                linecolor = "#FF0000"
            else:
                linecolor ="#000000"

            self.graph2.plotLine(
                3, 
                reader_m.two_photon_wavelength,
                reader_m.two_photon_intensity,
                zorder=2,
                color=linecolor,
                line_style="-.",
                fill=False,
                rescale=False,
                draw=False
            )

            if reader_m.two_photon_max:
                self.graph2.plotLineVertical(
                    2,
                    reader_m.two_photon_max,
                    zorder=6,
                    color=linecolor,
                    line_style="-.",
                    draw=False
                )

            p2_min = min(reader_m.two_photon_wavelength)
            p2_max = max(reader_m.two_photon_wavelength)
            if p2_min < wavelength_min:
                wavelength_min = p2_min
            if p2_max > wavelength_max:
                wavelength_max = p2_max

        if wavelength_min > wavelength_max:
            wavelength_min = 0
            wavelength_max = 1500

        # manually rescale
        self.graph2.scaleAxisX(wavelength_min, wavelength_max)
        self.graph2.scaleColorBar(wavelength_min, wavelength_max)

        self.graph2.draw()

    @QtCore.pyqtSlot(dict, dict)
    def receiveData(self, data_original: Dict[Identifier, Data], data_modified: Dict[Identifier, Data]) -> None:
        """
        Loads the factory data into the listtab
            :param data_original: unmodified spectrum data
            :param data_modifeid: modifyable spectrum data
        """
        self.data_original = data_original
        self.data_modified = data_modified

    @QtCore.pyqtSlot(Identifier)
    def receiveDataIndex(self, index: Identifier) -> None:
        """
        Slot: set the active index and activates the relevant pushbuttons
        """
        self.data_index = index

        # New Index so reset the tabs and graphs
        self.reset()

        # Enable the plotting buttons
        default_plot = False

        if self.data_modified[index].absorption_wavelength and self.data_modified[index].absorption_intensity:
            self.button_absorption.setEnabled(True)
            if default_plot is False:
                default_plot = True
                self.setActiveAbsorption(True)
                self.plotCurves(LineType.Absorption)
                self.plotCurves2(LineType.Absorption)
        else:
            self.button_absorption.setEnabled(False)

        if self.data_modified[index].excitation_wavelength and self.data_modified[index].excitation_intensity:
            self.button_excitation.setEnabled(True)
            if default_plot is False:
                default_plot = True
                self.setActiveExcitation(True)
                self.plotCurves(LineType.Excitation)
                self.plotCurves2(LineType.Excitation)
        else:
            self.button_excitation.setEnabled(False)

        if self.data_modified[index].two_photon_wavelength and self.data_modified[index].two_photon_intensity:
            self.button_two_photon.setEnabled(True)
            if default_plot is False:
                default_plot = True
                self.setActiveTwoPhoton(True)
                self.plotCurves(LineType.TwoPhoton)
                self.plotCurves2(LineType.TwoPhoton)
        else:
            self.button_two_photon.setEnabled(False)

        if self.data_modified[index].emission_wavelength and self.data_modified[index].emission_intensity:
            self.button_emission.setEnabled(True)
            if default_plot is False:
                default_plot = True
                self.setActiveEmission(True)
                self.plotCurves(LineType.Emission)
                self.plotCurves2(LineType.Emission)
        else:
            self.button_emission.setEnabled(False)

    @QtCore.pyqtSlot(Identifier, LineType)
    def receiveUpdate(self, index, line_type):
        """
        Slot: replots curve2, as the source data may have changed.
        """
        if self.data_index != index:
            print("Graph is desynced from the curve to update. Nothing happens")
            return

        # I have to update both graphs as some updates may switch the active graph
        if line_type == LineType.Absorption:
            self.setActiveAbsorption(True)
            self.receiveActivatedAbsorption(True)
        elif line_type == LineType.Excitation:
            self.setActiveExcitation(True)
            self.receiveActivatedExcitation(True)
        elif line_type == LineType.TwoPhoton:
            self.setActiveTwoPhoton(True)
            self.receiveActivatedTwoPhoton(True)
        elif line_type == LineType.Emission:
            self.setActiveEmission(True)
            self.receiveActivatedEmission(True)

    @QtCore.pyqtSlot(bool)
    def receiveActivatedAbsorption(self, active):
        """ 
        Activated upon clicking of the absorption button. Propagates signal. 
            :param active[bool]: whether the activated button is active
        """
        self.sendActivatedAbsorption.emit(active)
        self.setActiveExcitation(False)
        self.setActiveTwoPhoton(False)
        self.setActiveEmission(False)

        if active is True:
            self.plotCurves(LineType.Absorption)
            self.plotCurves2(LineType.Absorption)
        else:
            #self.graph.resetPlot()
            self.graph2.resetPlot()

    @QtCore.pyqtSlot(bool)
    def receiveActivatedExcitation(self, active):
        """ 
        Activated upon clicking of the excitation button. Propagates signal.
            :param active[bool]: whether the activated button is active
        """
        self.sendActivatedExcitation.emit(active)
        self.setActiveAbsorption(False)
        self.setActiveTwoPhoton(False)
        self.setActiveEmission(False)

        if active is True:
            self.plotCurves(LineType.Excitation)
            self.plotCurves2(LineType.Excitation)
        else:
            self.graph.resetPlot()
            self.graph2.resetPlot()

    @QtCore.pyqtSlot(bool)
    def receiveActivatedTwoPhoton(self, active):
        """
        Activated upon clicking of the two photon button. Propagates signal.
            :param active[bool]: whether the activated button is active
        """
        self.sendActivatedTwoPhoton.emit(active)
        self.setActiveAbsorption(False)
        self.setActiveExcitation(False)
        self.setActiveEmission(False)

        if active is True:
            self.plotCurves(LineType.TwoPhoton)
            self.plotCurves2(LineType.TwoPhoton)
        else:
            self.graph.resetPlot()
            self.graph2.resetPlot()

    @QtCore.pyqtSlot(bool)
    def receiveActivatedEmission(self, active):
        """
        Activated upon clicking of the emission button. Propagates signal.
            :param active[bool]: whether the activated button is active
        """
        self.sendActivatedEmission.emit(active)
        self.setActiveAbsorption(False)
        self.setActiveExcitation(False)
        self.setActiveTwoPhoton(False)

        if active is True:
            self.plotCurves(LineType.Emission)
            self.plotCurves2(LineType.Emission)
        else:
            self.graph.resetPlot()
            self.graph2.resetPlot()

class MainWindow(QtWidgets.QMainWindow):
    sendData = QtCore.pyqtSignal(dict, dict)
    sendDataIndex = QtCore.pyqtSignal(Identifier)
    sendHeaders = QtCore.pyqtSignal(dict)
    sendHeaderIndex = QtCore.pyqtSignal(str)

    def __init__(self, parent: QtWidgets.QWidget=None) -> None:
        super().__init__(parent)

        # Auto save parametres
        self.autosave_dir: str = None
        self.autosave_timeout: int = 120_000
        self.autosave_timer: QtCore.QTimer = QtCore.QTimer(self)
        self.autosave_timer.timeout.connect(self.autosave)

        # Window parameters
        self.setWindowTitle("Fluor - Spectra Viewer")
        self.setMinimumHeight(999)
        self.setMinimumWidth(1200)
        self.installEventFilter(self)

        # Shared data
        self.data_index: Identifier = None
        self.data_original: Dict[Identifier, Data] = None
        self.data_modified: Dict[Identifier, Data] = None
        self.header_index: str = None
        self.header_map: Dict[str, Header] = None

        # Widgets
        self.central_widget = QtWidgets.QWidget(self)
        self.central_layout = QtWidgets.QGridLayout(self.central_widget)
        self.central_widget.setLayout(self.central_layout)
        self.setCentralWidget(self.central_widget)

        self.central_layout.setColumnStretch(0, 0)
        self.central_layout.setColumnStretch(1, 1)
        self.central_layout.setColumnStretch(2, 0)

        self.central_layout.setColumnMinimumWidth(0, 350)
        self.central_layout.setColumnMinimumWidth(1, 300)
        self.central_layout.setColumnMinimumWidth(2, 800)

        # Add list tab
        self.list_tab = ListTab(self)
        self.central_layout.addWidget(self.list_tab, 0, 0)

        self.sendData.connect(self.list_tab.receiveData)
        self.sendHeaders.connect(self.list_tab.receiveHeaders)
        self.sendHeaderIndex.connect(self.list_tab.receiveHeaderIndex)
        self.list_tab.sendActivatedData.connect(self.receiveDataIndex)
        self.list_tab.sendActivatedHeader.connect(self.receiveHeaderIndex)
        self.list_tab.sendExportData.connect(self.receiveExportData)
        self.list_tab.sendExportMap.connect(self.receiveExportMap)

        # Add adjust tab
        self.adjust_tab = AdjustTab(self)
        self.central_layout.addWidget(self.adjust_tab, 0, 1, alignment=QtCore.Qt.AlignTop)
    
        self.sendData.connect(self.adjust_tab.receiveData)
        self.sendDataIndex.connect(self.adjust_tab.receiveDataIndex)
        
        # Add graph tab
        self.graph_tab = GraphTab(self)
        self.central_layout.addWidget(self.graph_tab, 0, 2)
        
        self.sendData.connect(self.graph_tab.receiveData)
        self.sendDataIndex.connect(self.graph_tab.receiveDataIndex)

        # Connects between layouts
        self.adjust_tab.sendDataModified.connect(self.graph_tab.receiveUpdate)

    def loadData(self, reader: MappedReader) -> None:
        """
        Loads the data into the viewer
            :param reader: the fully loaded mapped data
            :raises ValueError: if the map is invalid
        """
        if not reader.valid(print_invalid=True):
            raise ValueError("reader must be valid")

        # Populate interface with spectrum data
        self.data_original = reader.collection
        self.data_modified = copy.deepcopy(self.data_original)

        self.sendData.emit(self.data_original, self.data_modified)

        # Secondly! populate with header data
        self.header_map = reader.headers
        self.sendHeaders.emit(self.header_map)

        # Get first entree and have the interface select it
        if self.header_map:
            self.header_index = list(self.header_map.keys())[0]
            self.sendHeaderIndex.emit(self.header_index)
   
    @QtCore.pyqtSlot(Identifier)
    def receiveDataIndex(self, index: Identifier) -> None:
        """
        Slot: set the active index and activates the relevant pushbuttons
        """
        self.data_index = index
        self.sendDataIndex.emit(index)
    
    @QtCore.pyqtSlot(str)
    def receiveHeaderIndex(self, index: str) -> None:
        """
        Slot: set the active index and activates the relevant pushbuttons
        """
        self.header_index = index
        self.sendHeaderIndex.emit(index)

    @QtCore.pyqtSlot(str, Format)
    def receiveExportData(self, path: str, output_format: Format) -> None:
        """
        Slot: receives and export data request to the path using of the defined type
            :param path: absolute save path
            :param output_format: file format to save
        """
        if output_format == Format.ini:
            print(".ini format not yet implemented. Please export as json")
            return

        output = MappedReader()
        output.collection = self.data_modified
        output.headers = self.header_map

        output.export_data(path)
    
    @QtCore.pyqtSlot(str)
    def receiveExportMap(self, path: str) -> None:
        """
        Slot: receives and export data request to the path using of the defined type
            :param path: absolute save path
            :param output_format: file format to save
        """
        output = MappedReader()
        output.collection = self.data_modified
        output.headers = self.header_map

        output.export_map(path)
        
    def set_autosave_dir(self, path: str) -> None:
        """
        Sets the autosave directory and enables autosaving (every minute)
            :param path: the directory to place the autosave files into
        """
        if not os.path.isdir(path):
            self.autosave_dir = None
            self.autosave_timer.stop()
            raise ValueError("Autosave directory doesnt exist")

        self.autosave_dir = path
        self.autosave_timer.start(self.autosave_timeout)

    def autosave(self) -> None:
        """
        Autosaves the map and the data
        """
        output = MappedReader()
        output.collection = self.data_modified
        output.headers = self.header_map

        path = os.path.join(self.autosave_dir, "autosave_map.json")
        
        # Autosave map
        with open(path, "w", encoding="utf-8") as file:
            file.write(output.dumps_map())
        
        path = os.path.join(self.autosave_dir, "autosave_data.json")

        with open(path, "w", encoding="utf-8") as file:
            file.write(output.dumps_data(warnings=False))

        print("autosave")


class Application(QtWidgets.QApplication):
    globalClicked = QtCore.pyqtSignal(object, object)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.installEventFilter(self)

    def eventFilter(self, source, event):
        """
        EventFilter for KeyPress events: MouseButtonPress.
            :param source: memory path of the events origin
            :param event[QEvent]: QEvent
        """
        if event.type() == QtCore.QEvent.MouseButtonRelease:
            self.globalClicked.emit(source, event)
            return False
        #if event.type() == QtCore.QEvent.Close:
        #    #self.central_widget.graph.writeSettings()
        #    self.writeSettings()
        #    return False
        return super().eventFilter(source, event)
