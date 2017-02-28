#!/usr/bin/env python

import sys
import matplotlib
matplotlib.use('Qt4Agg')
matplotlib.rcParams['backend.qt4'] = 'PySide'
import pylab
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib import pyplot as plt
from matplotlib.figure import Figure
from PySide.QtCore import *
from PySide.QtGui import *


class SignalViewer(QObject):
    """

    Class for viewing, filtering, and recording signals

    """

    def __init__(self, signal_source=None):
        # Constructor. If called with no arguments, user must assign signal source and initialize.

        # Initialize as QObject
        QObject.__init__(self)

        # Properties controlling signal source viewed
        self._signal_source = None
        self._selected_channels = range(4)
        self._show_filtered_data = True
        self._mode_select = 'Time Domain'

        # Timer
        self._timer = None

        # GUI components
        self._qt_app = None
        self._qt_main_widget = None

        # Signal figure that will be rendered on GUI
        self._signal_figure = None
        self._signal_ax = None
        self._signal_lines = []
        self._tableau20 = None

        # Set signal source
        self.set_signal_source(signal_source)

        # Initialize
        self.initialize()

    def set_signal_source(self, signal_source):
        # Set method for signal source. Returns false if empty input.
        # TODO: Add some checking that signal source has required properties/methods

        if signal_source:
            self._signal_source = signal_source
            return True
        else:
            return False

    def initialize(self):
        # Starts gui, assuming signal source has been set

        if not self._signal_source:
            print('No Signal Source Assigned. Use signal_viewer.set_signal_source().\n')
            return

        print('Initializing Signal Viewer.\n')

        self._setup_gui()

        # TODO: Update mode select property

        # TODO: Make channel select method

        # Timer
        self._timer = QTimer(self)
        self.connect(self._timer, SIGNAL("timeout()"), self._update)

        # TODO: Make _update_figure() method which syncs properties with UI objects
        #self._update_figure()

        self._update()

        # Start timer
        self._timer.start(10)

        # Execute App (no code after this wil run)
        self.run()

    def _setup_gui(self):
        # Sets up main display
        self._qt_app = QApplication(sys.argv)
        self._qt_main_widget = QTWindow()

        # Set up the matplotlib figure
        self._signal_figure = plt.figure(figsize=(10, 7.5))
        self._signal_ax = self._signal_figure.add_subplot(111)

        # Add widget to gui
        self._signal_canvas = FigureCanvas(self._signal_figure)
        self._qt_main_widget.layout.insertWidget(0, self._signal_canvas)

        # Format figure
        # Set axis labels
        plt.xlabel('Sample Number', fontsize=16)
        plt.ylabel('Source Units', fontsize=16)
        plt.xlim(0, self._signal_source.num_samples)

        # Remove the plot frame lines. They are unnecessary chartjunk.
        self._signal_ax.spines["top"].set_visible(False)
        self._signal_ax.spines["bottom"].set_visible(False)
        self._signal_ax.spines["right"].set_visible(False)
        self._signal_ax.spines["left"].set_visible(False)

        # Ensure that the axis ticks only show up on the bottom and left of the plot.
        # Ticks on the right and top of the plot are generally unnecessary chartjunk.
        self._signal_ax.get_xaxis().tick_bottom()
        self._signal_ax.get_yaxis().tick_left()

        # These are the "Tableau 20" colors as RGB.
        tableau20 = [(31, 119, 180), (174, 199, 232), (255, 127, 14), (255, 187, 120),
                     (44, 160, 44), (152, 223, 138), (214, 39, 40), (255, 152, 150),
                     (148, 103, 189), (197, 176, 213), (140, 86, 75), (196, 156, 148),
                     (227, 119, 194), (247, 182, 210), (127, 127, 127), (199, 199, 199),
                     (188, 189, 34), (219, 219, 141), (23, 190, 207), (158, 218, 229)]

        # Scale the RGB values to the [0, 1] range, which is the format matplotlib accepts.
        for i in range(len(tableau20)):
            r, g, b = tableau20[i]
            tableau20[i] = (r / 255., g / 255., b / 255.)

        # Will setup 16 lines which can be plotted
        for i_channel in range(16):
            self._signal_lines.append(self._signal_ax.plot(0, 0, color=tableau20[i_channel]))
            self._signal_lines[-1][0].set_visible(True)

    def _update(self):
        # Called by timer object to update GUI
        if self._mode_select == 'Time Domain':
            # Need to update based on signal emit, once gui has started
            self._qt_main_widget.custom_signal.connect(self._update_time_domain)
            self._qt_main_widget.custom_signal.emit()

    def _update_time_domain(self):

        # Get Data
        # TODO: Add getFilteredData method to signal source
        channel_data = self._signal_source.get_data()

        # Plot data
        for i_channel in range(16):
            if i_channel in self._selected_channels:
                signal = channel_data[:, i_channel]
                sample_num = [x+1 for x in range(len(signal))]
                self._signal_lines[i_channel][0].set_xdata(sample_num)
                self._signal_lines[i_channel][0].set_ydata(signal)
                self._signal_lines[i_channel][0].set_visible(True)
            else:
                self._signal_lines[i_channel][0].set_visible(False)

        # TODO: This is taking a while, especially the draw() method
        # Setup range
        #self._signal_ax.relim()
        #self._signal_ax.autoscale_view()
        # Redraw
        self._signal_canvas.draw()

        # Return if empty
        if not channel_data.any():
            return

    def run(self):
        self._qt_main_widget.show()
        self._qt_app.exec_()


class QTWindow(QWidget):
    """

    Class for the main qt display

    """

    # This signal can be used on the fly, just needs to be instantiated up front
    custom_signal = Signal()

    def __init__(self):
        # Initialize as QWidget
        QWidget.__init__(self)

        # Initialize the QWidget and
        # set its title and minimum width
        self.setWindowTitle('Signal Viewer')
        self.setMinimumWidth(400)
        # TODO: Set minimum height
        # TODO: Set position

        # Create the QVBoxLayout that lays out the whole window
        self.layout = QVBoxLayout()

        # # Create the QHBoxLayout that will lay out the lower portion of the window
        # self.lowerHBoxLayout = QHBoxLayout()
        #
        # # Placeholder items for now
        # self.lowerHBoxLayout.addWidget(QLabel('Plot Domain', self))
        # self.lowerHBoxLayout.addWidget(QLabel('Plot Properties', self))
        # self.lowerHBoxLayout.addWidget(QLabel('Channel Select', self))
        #
        # self.layout.addLayout(self.lowerHBoxLayout)

        self.setLayout(self.layout)

if __name__ == "__main__":
    s = SignalViewer()
