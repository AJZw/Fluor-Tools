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

"""
Graphing layout and plotting classes

:class: GraphVerticalLabel
A rotated QLabel with adjusted alignment for use as Y-axis label

:class: GraphHorizontalLabel
A Qlabel with adjusted aligment for use as X-axis label

:class: GraphPlotLayout
A QGridLayout to combine GraphPlot, with its GraphVerticalLabel and GraphHorizontalLabel
Propagates attribute calls to its GraphPlot child

:class: GraphPlot
A FigureCanvasQTAgg plots the excitation/emission wavelengths
"""

from PyQt5 import QtCore, QtWidgets

from matplotlib import use as MplUse
MplUse("Qt5Agg")
from matplotlib import colorbar as MplColorbar
from matplotlib import figure as MplFigure
from matplotlib.colors import LinearSegmentedColormap as MplLinearSegmentedColormap
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from mpl_toolkits.axes_grid1 import make_axes_locatable

#########################################################################
## Graph classes
#########################################################################

class GraphVerticalLabel(QtWidgets.QLabel):
    """ QLabel for vertical text aligned to y-axis GraphPlot """
    def __init__(self, *args):
        super().__init__(*args)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setStyleSheet("font-weight: bold;")

    def paintEvent(self, event):
        """
        reimplementation of paintEvent; rotates self.text() 90 degrees counterclockwise
        and aligns text theoretically to GraphPlot
            :param  event[QEvent]: (unused) Qt returns event, not used for function
        """
        del event
        painter = QtWidgets.QStylePainter(self)
        painter.translate(0, self.height())
        painter.rotate(-90)

        # x, y are rotated together with the painter
        if self.alignment() == QtCore.Qt.AlignTop:
            label_x = self.height() - self.sizeHint().height() - 5
        elif self.alignment() == QtCore.Qt.AlignBottom:
            label_x = 30
        elif self.alignment() == QtCore.Qt.AlignCenter:
            label_x = (self.height() - self.sizeHint().height() -35) / 2 + 30
        else:
            painter.drawText(0, 0, self.height(), self.width(), self.alignment(), self.text())
            return

        label_y = round(self.width() * 0.75)
        painter.drawText(label_x, label_y, self.text())

    def minimumSizeHint(self):
        """ Wrapper of super().minimumSizeHint; swaps width and height"""
        size = super().minimumSizeHint()
        return QtCore.QSize(size.height(), size.width())

    def sizeHint(self):
        """ Wrapper of super().sizeHint; swaps width and height"""
        size = super().sizeHint()
        return QtCore.QSize(size.height(), size.width())

class GraphHorizontalLabel(QtWidgets.QLabel):
    """ QLabel for horizontal text aligned to x-axis Graphplot """
    def __init__(self, *args):
        super().__init__(*args)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setStyleSheet("font-weight: bold;")

    def paintEvent(self, event):
        """
        reimplementation of paintEvent; custom alignment
            :param  event[QEvent]: (unused) Qt returns event, not used for function
        """
        del event
        painter = QtWidgets.QStylePainter(self)
        # x, y are rotated together with the painter
        if self.alignment() == QtCore.Qt.AlignRight:
            label_x = self.width() - self.sizeHint().width() - 8
        elif self.alignment() == QtCore.Qt.AlignLeft:
            label_x = 28
        elif self.alignment() == QtCore.Qt.AlignCenter:
            label_x = (self.width() - self.sizeHint().width() -36) / 2 + 28
        else:
            painter.drawText(0, 0, self.height(), self.width(), self.alignment(), self.text())
            return

        label_y = round(self.height() * 0.75)
        painter.drawText(label_x, label_y, self.text())

class GraphPlotLayout(QtWidgets.QGridLayout):
    sendIndex = QtCore.pyqtSignal(str, int)

    """
    The QGridLayout for the Y and X Qlabels and GraphPlot instance.
    Propagates unspecified attributes to the GraphPlot instance
        :param args: args for GraphPlot instance
        :param kwargs: kwargs for GraphPlot instance
    """
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.setColumnMinimumWidth(0, 1)
        self.setColumnMinimumWidth(1, 1)
        self.setColumnStretch(1, 1)
        self.setRowStretch(0, 1)
        self.setHorizontalSpacing(0)
        self.setVerticalSpacing(0)

        # Order of addWidget is order of Qt's painting events
        self.graph = GraphPlot(*args, **kwargs)
        self.addWidget(self.graph, 0, 1)

        self.label_y = GraphVerticalLabel("Relative Intensity (%)")
        self.addWidget(self.label_y, 0, 0)

        self.label_x = GraphHorizontalLabel("Wavelength (nm)")
        self.addWidget(self.label_x, 1, 1)

    def deleteLater(self):
        """
        Runs clearLayout() before continueing to super().deleteLater()
        """
        self.clearLayout()
        super().deleteLater()

    def clearLayout(self):
        """
        Applies deleteLater() on all subwidgets and finally on self
        """
        while self.count():
            child = self.takeAt(0)
            if child.widget() is not None:
                child.widget().deleteLater()

    def __getattr__(self, name):
        """
        Forwards __getattr__ to the graphs __getattribute__
        """
        attribute = self.graph.__getattribute__(name)
        return attribute

class GraphPlot(FigureCanvasQTAgg):
    """
    The canvas and figure the fluorophore data is drawn in. Subclass of matplotlib FigureCanvasQTAgg.
        :param parent[QObject]: parent object.
    """
    def __init__(self, parent=None):
        self.parent = parent

        self.axis_min = 295
        self.axis_max = 905

        # Plot style
        self.figure_color = "#F0F0F0"
        self.background_color = "#FFFFFF"
        self.background_color_focus = "#FFFFFF"
        self.axis_color = "#000000"
        self.grid_color = "#000000"
        self.font_color = "#000000"
        self.font_family = "DejaVu Sans"
        self.font_size = 8
        self.font_weight = "semibold"

        # Builds main figure and canvas
        self.figure = MplFigure.Figure()
        self.figure.set_facecolor(self.figure_color)

        # Initializes Canvas widget
        FigureCanvasQTAgg.__init__(self, figure=self.figure)
        self.setMinimumSize(250, 250)

        # Ads subplot to axes
        self.axes = self.figure.add_subplot(1, 1, 1, facecolor=self.background_color)

        # Builds and sets look colorbar
        divider = make_axes_locatable(self.axes)
        self.colorbar = divider.append_axes("bottom", size=0.15, pad=0)
        self.colorbar.xaxis.set_visible(False)
        self.colorbar.yaxis.set_visible(False)
        for i, label in enumerate([200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200]):
            self.colorbar.text(0.008 + ((1/10*i)*0.984), -0.4, label, color=self.font_color, ha="center", va="top",
                          fontname=self.font_family, fontsize=self.font_size, weight=self.font_weight)

        #Plots Colorbar
        cmap_spectrum = MplLinearSegmentedColormap("spectrum", self.scaledColorDict(self.axis_min, self.axis_max, margin=0))
        self.colorbar_output = MplColorbar.ColorbarBase(self.colorbar, cmap=cmap_spectrum, orientation="horizontal")
        self.colorbar_output.outline.set_edgecolor(self.axis_color)

        # Specifies X, Y axis range and color
        self.axes.axis([self.axis_min, self.axis_max, -5, 105], set_facecolor=self.axis_color)
        self.axes.spines["bottom"].set_color(self.axis_color)
        self.axes.spines["top"].set_color(self.axis_color)
        self.axes.spines["left"].set_color(self.axis_color)
        self.axes.spines["right"].set_color(self.axis_color)

        # Sets tick and labels
        self.axes.set_yticks([0, 20, 40, 60, 80, 100])
        for tick in self.axes.get_yticklabels():
            tick.set_fontname(self.font_family)
            tick.set_fontsize(self.font_size)
            tick.set_weight(self.font_weight)
        self.axes.set_xticks([200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 750, 800, 850, 900, 950, 1000, 1050, 1100, 1150, 1200])
        self.axes.set_xticklabels([])
        self.axes.tick_params(axis="both", length=0, colors=self.font_color)

        # Specifies X and Y axis grid locations and color
        self.axes.grid(which="major", axis="y", linewidth=1, color=self.grid_color, alpha=0.1)
        self.axes.grid(which="major", axis="x", linewidth=1, color=self.grid_color, alpha=0.1)

        # Draws canvas
        self.draw()

    # Rescaling of the plot
    def scaleAxisX(self, min_value, max_value, margin=15):
        """
        Scales the X axis based on the min and max value
            :param min_value[int]: minimum value of the dataset
            :param max_value[int]: maximum value of the dataset
            :param margin[int]: margin on both sides of the min_value and max_value
        """
        tick_list = [0, 50, 100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 750, 800, 850, 900, 950, 1000, 1050, 1100, 1150, 1200, 1250, 1300, 1350, 1400, 1450, 1500]

        start_index = 0
        for i, tick in enumerate(tick_list):
            if i == 0:
                continue
            if min_value - margin <= tick:
                start_index = i
                break
        
        end_index = len(tick_list) - 1
        for i, tick in reversed(list(enumerate(tick_list))):
            if i == len(tick_list) - 1:
                continue

            if max_value + margin >= tick:
                end_index = i + 1
                break

        self.axes.set_xlim(left=min_value - margin, right=max_value + margin)
        self.axes.set_xticks(tick_list[start_index:end_index])
    
    def scaleColorBar(self, min_value, max_value, margin=15):
        """
        Scales the Colorbar and the tick labels on the min and max value
            :param min_value[int]: minimum value of the dataset 
            :param max_value[int]: maximum value of the dataset
            :param margin[int]: margin on both sides of the min_value and max_value
        """
        # Adjust tick labels
        tick_list = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500]

        # Remove previous labels
        for label in reversed(self.colorbar.texts):
            label.remove()

        # Calculate tick label fraction
        start_index = 0
        for i, tick in enumerate(tick_list):
            if i == 0:
                continue
            if min_value - margin <= tick:
                start_index = i
                break
        
        end_index = len(tick_list) - 1
        for i, tick in reversed(list(enumerate(tick_list))):
            if i == len(tick_list) - 1:
                continue

            if max_value + margin >= tick:
                end_index = i + 1
                break

        tick_new = tick_list[start_index:end_index]

        # Add new ticks
        for i, label in enumerate(tick_new):
            self.colorbar.text(
                ((label - min_value + margin) / (max_value - min_value + margin + margin)),
                -0.4,
                label,
                color=self.font_color,
                ha="center",
                va="top",
                fontname=self.font_family,
                fontsize=self.font_size,
                weight=self.font_weight
            )

        # Adjust colorbar
        # memory leak?????
        for collection in reversed(self.colorbar.collections):
            collection.remove()

        self.colorbar_output = MplColorbar.ColorbarBase(
            self.colorbar,
            cmap=MplLinearSegmentedColormap("spectrum", self.scaledColorDict(min_value, max_value, margin)),
            orientation="horizontal",
            drawedges=False
        )
        self.colorbar_output.outline.set_linewidth(0)

    # Base Plotting functions
    def plotLine(self, line_id, wavelength, intensity, zorder=2, color="#000000", line_style="-", fill=True, rescale=True, draw=False):
        """
        Plots a line of a certain ID.
            :param line_id[str]: the ID of the line, if the ID already exists, the line will be replaced
            :param wavelength[list[float]]: the x-axis
            :param intensity[list[float]]: the y-axis
            :param zorder[int]: order of the lines in z-stack
            :param color[str]: the color of the line
            :param line_style[str]: the line style of the line
            :param fill[bool]: whether the line is filled or not
            :param rescale[bool]: whether to rescale the x-axis
            :param draw[bool]: whether to draw after plot
        """
        self.axes.plot(
            wavelength,
            intensity,
            gid=line_id,
            visible=True,
            zorder=zorder,
            color=color,
            linewidth=1,
            linestyle=line_style,
            alpha=0.7
        )

        if fill is True:
            self.axes.fill_between(
                wavelength,
                0,
                intensity,
                visible=True,
                zorder=zorder -1,
                gid=line_id,
                facecolor=color,
                alpha=0.3
            )

        if rescale is True:
            self.scaleAxisX(min(wavelength), max(wavelength))
            self.scaleColorBar(min(wavelength), max(wavelength))

        if draw is True:
            self.draw()

    def plotLineHorizontal(self, line_id, intensity, zorder=5, color="#0000FF", line_style="-", draw=False):
        """
        Plots a horizontal line of a certain ID.
            :param line_id[str]: the ID of the line, if the ID already exists, the line will be replaced
            :param intensity[float]: the y-axis value
            :param zorder[int]: order of the lines in z-stack
            :param color[str]: the color of the line
            :param line_style[str]: the line style of the line
            :param draw[bool]: whether to draw after plot
        """
        wavelength = [0.0, 1500.0]
        intensity = [intensity, intensity]

        self.plotLine(line_id, wavelength, intensity, zorder=zorder, color=color, line_style=line_style, fill=False, rescale=False, draw=draw)

    def plotLineVertical(self, line_id, wavelength, zorder=5, color="#0000FF", line_style="-", draw=False):
        """
        Plots a vertical line of a certain ID.
            :param line_id[str]: the ID of the line, if the ID already exists, the line will be replaced
            :param intensity[float]: the x-axis value
            :param zorder[int]: order of the lines in z-stack
            :param color[str]: the color of the line
            :param line_style[str]: the line style of the line
            :param draw[bool]: whether to draw after plot
        """
        wavelength = [wavelength, wavelength]
        intensity = [-10, 110]

        self.plotLine(line_id, wavelength, intensity, zorder=zorder, color=color, line_style=line_style, fill=False, rescale=False, draw=draw)

    def eraseLines(self, line_id):
        """
        Removes the all lines with the specific line_id from the axes
            :param line_id[str]: the ID of the line to remove
        """     
        for line in reversed(self.axes.lines):
            if line.get_gid() == line_id:
                line.remove()

        for collection in reversed(self.axes.collections):
            if collection.get_gid() == line_id:
                collection.remove()

        self.draw()

    def eraseAll(self):
        """
        Removes all lines from the axes
        """
        for line in reversed(self.axes.lines):
            line.remove()

        for collection in reversed(self.axes.collections):
            collection.remove()

        self.draw()

    # Plotting functions: reset
    def resetPlot(self):
        """
        Resets GraphPlot instance to 'fresh' state:
        """
        self.eraseAll()
        self.scaleAxisX(self.axis_min, self.axis_max, margin=0)
        self.scaleColorBar(self.axis_min, self.axis_max, margin=0)
        self.draw()

    def resizeEvent(self, event):
        """
        Reimplementation of FigureCanvasQT.resizeEvent(). Additional spacing adjustment before replotting
            :param event: Qt's event parameter
        """
        # Reimplement first section of FigureCanvasQt.resizeEvent()
        if self._dpi_ratio_prev is None:
            return
        object_w = event.size().width() * self._dpi_ratio
        object_h = event.size().height() * self._dpi_ratio

        # Recalculate spacing
        left = round(27.8 / object_w, ndigits=3)
        right = round(1 - (9 / object_w), ndigits=3)
        top = round(1 - (6 / object_h), ndigits=3)
        bottom = round(15.8 / object_h, ndigits=3)
        self.figure.subplots_adjust(left=left, right=right, top=top, bottom=bottom)

        super().resizeEvent(event)

    @staticmethod
    def scaledColorDict(min_value, max_value, margin=15):
        """
        Calculates and correct the colorbar based on the value ranges
            :param min_value[int]: minimum value of the dataset
            :param max_value[int]: maximum value of the dataset
            :param margin[int]: margin on both sides of the min_value and max_value
            :returns [dict]: cmap for matplotlib colorbar
        """
        color_dict = {
            "red":[[380.0, 0.0, 0.3], [420.0, 0.333, 0.333], [440.0, 0.0, 0.0], [490.0, 0.0, 0.0], [510.0, 0.0, 0.0], [580.0, 1.0, 1.0], [645.0, 1.0, 1.0], [700.0, 1.0, 1.0], [780, 0.3, 0.0]],
            "green":[[380.0, 0.0, 0.0], [420.0, 0.0, 0.0], [440.0, 0.0, 0.0], [490.0, 1.0, 1.0], [510.0, 1.0, 1.0], [580.0, 1.0, 1.0], [645.0, 0.0, 0.0], [700, 0.0, 0.0], [780, 0.0, 0.0]],
            "blue":[[380.0, 0.0, 0.3], [420.0, 1.0, 1.0], [440.0, 1.0, 1.0], [490.0, 1.0, 1.0], [510.0, 0.0, 0.0], [580.0, 0.0, 0.0], [645.0, 0.0, 0.0], [700, 0.0, 0.0], [780, 0.0, 0.0]]
        }

        # Adjust fractions
        value_range = max_value - min_value + margin + margin
        for color in color_dict:
            for data in color_dict[color]:
                data[0] = (data[0] - min_value + margin)/value_range

        # Cutoff <0 sections we dont need
        for color in color_dict:
            for i, value in reversed(list(enumerate(color_dict[color]))):
                if value[0] == 0:
                    # Cutoff lower values
                    color_dict[color] = color_dict[color][i:]
                    break
                elif value[0] < 0:
                    if i == len(color_dict[color]) -1:
                        # Last entree is already smaller, so remove all and replace with empty
                        color_dict[color] = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]
                        break
                    else:
                        # Other cases interpolate value
                        x1 = color_dict[color][i][0]
                        x2 = color_dict[color][i+1][0]
                        dx = (0 - x1) / (x2 - x1)
                        y1 = color_dict[color][i][2]
                        y2 = color_dict[color][i+1][1]
                        dy = ((y2 - y1) * dx) + y1
                        color_dict[color][i] = [0.0, color_dict[color][i][1], dy]
                        color_dict[color] = color_dict[color][i:]
                        break

        # Cutoff >1 sections we dont need
        for color in color_dict:
            for i, value in enumerate(color_dict[color]):
                if value[0] == 1:
                    # Cutoff higher entrees
                    color_dict[color] = color_dict[color][:i+1]
                    break
                elif value[0] > 1:
                    if i == 0:
                        # First entree is already bigger, so remove all and replace with empty
                        color_dict[color] = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]
                        break
                    else:
                        # Other cases interpolate value
                        x1 = color_dict[color][i-1][0]
                        x2 = color_dict[color][i][0]
                        dx = (1 - x1) / (x2 - x1)
                        y1 = color_dict[color][i-1][2]
                        y2 = color_dict[color][i][1]
                        dy = ((y2 - y1) * dx) + y1
                        color_dict[color][i] = [1.0, dy, color_dict[color][i][2]]
                        color_dict[color] = color_dict[color][:i+1]
                        break

        # Final check and append
        for color in color_dict:
            if color_dict[color][0][0] != 0:
                color_dict[color].insert(0, [0.0, 0.0, 0.0])
            if color_dict[color][-1][0] != 1:
                color_dict[color].append([1.0, 0.0, 0.0])

        return color_dict

    @staticmethod
    def waveToRGB(wavelength):
        """
        Returns the red, green, blue channel (0-255 scale) of a specific wavelength based on the visible light spectrum.
        Thanks to R.L. from Blogger
            :param wavelength[int]: wavelength to transform into RGB value
        """
        wavelength = int(wavelength)
        # colour
        if wavelength >= 380 and wavelength < 440:
            red = -(wavelength - 440.) / (440. - 350.)
            green = 0.0
            blue = 1.0
        elif wavelength >= 440 and wavelength < 490:
            red = 0.0
            green = (wavelength - 440.) / (490. - 440.)
            blue = 1.0
        elif wavelength >= 490 and wavelength < 510:
            red = 0.0
            green = 1.0
            blue = -(wavelength - 510.) / (510. - 490.)
        elif wavelength >= 510 and wavelength < 580:
            red = (wavelength - 510.) / (580. - 510.)
            green = 1.0
            blue = 0.0
        elif wavelength >= 580 and wavelength < 645:
            red = 1.0
            green = -(wavelength - 645.) / (645. - 580.)
            blue = 0.0
        elif wavelength >= 645 and wavelength <= 780:
            red = 1.0
            green = 0.0
            blue = 0.0
        else:
            red = 0.0
            green = 0.0
            blue = 0.0

        # intensity correction
        if wavelength >= 380 and wavelength < 420:
            intensity = 0.3 + 0.7*(wavelength - 350) / (420 - 350)
        elif wavelength >= 420 and wavelength <= 700:
            intensity = 1.0
        elif wavelength > 700 and wavelength <= 780:
            intensity = 0.3 + 0.7*(780 - wavelength) / (780 - 700)
        else:
            intensity = 0.0
        intensity *= 255

        return [int(intensity*red)/255, int(intensity*green)/255, int(intensity*blue)/255]
