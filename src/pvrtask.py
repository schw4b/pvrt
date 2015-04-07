#!/usr/bin/python
"""pvrtask (Peripheral Visual Recognition Task) by Simon Schwab"""
# Copyright (C) 2010-2012 Simon Schwab
# Department of Psychiatric Neurophysiology, University of Bern.
#
# Distributed under the terms of the GNU General Public License (GPL).
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from psychopy import core, visual, event
from Tkinter import Tk, Frame, Button, Radiobutton, Menu, Label, Entry, \
                    E, W, StringVar, mainloop, OptionMenu, END, Spinbox

from tkFileDialog import asksaveasfile

import time, sys, os, random, portio, datetime, tkMessageBox, tkFont, \
        string, pdb # pdb for debugger

class Sword:
    """A sWord is not a sword but a scrambled word, or actually
    a random character string that may contain selected characters
    or not (logical parameter match)."""
    def __init__(self, match):
        alphabet = ['b', 'd', 'l', 'p', 'q', 'w']
        random.shuffle(alphabet)

        # create swords of size 5
        vector = [alphabet[1],
                  alphabet[2],
                  alphabet[3],
                  alphabet[4]]

        self.string = ''.join(vector)

        if len(match):
            vector[0] = match
            random.shuffle(vector)
            self.string = ''.join(vector)

class Trial:
    """A Trial shows a central and peripheral stimulus.
    In each Trial, user input and the notification of
    the eye tracker is handled using TTL I/O on the parallel
    port."""
    FIX_CROSS_DUR = 1.0 # 2.0
    STIM_DUR = 1.0 # 2.0
    TTL_ON = 0x2
    TTL_OFF = 0x0
    TTL_DURATION = 0.050 # 50 ms is fine for 50Hz and 200Hz Tracking
    KBOARD_ANSWER_YES = 'y'
    KBOARD_ANSWER_NO = 'n'
    KBOARD_ANSWER_QUIT = 'q'
    BBOX_ANSWER_LEFT = 0x38
    BBOX_ANSWER_RIGHT = 0x68

    def __init__(self, input_device, handedness, clock, trial_number,
                 block_number, fix_cross, central_stim, peri_stim, window):

        Trial.input_type = input_device
        Trial.handedness = handedness
        Trial.clock = clock

        self.trial_nr = trial_number
        self.block_nr = block_number
        self.fix_cross = fix_cross
        self.central_stim = central_stim
        self.peri_stim = peri_stim
        Trial.window = window

        self.timer = None
        self.__run()

    def __run(self):
        """ Runs the trial until subject responds."""
        # Start of the trial
        trial_start = Trial.clock.getTime()
        portio.outb(Trial.TTL_ON, 0x378)
        time.sleep(Trial.TTL_DURATION)
        portio.outb(Trial.TTL_OFF, 0x378)

        # Fixation Cross
        self.fix_cross.draw()
        Trial.window.flip(clearBuffer = True)
        fix_cross_on = self.clock.getTime()
        time.sleep(Trial.FIX_CROSS_DUR)

        # Center Stimulus
        self.central_stim.draw()
        Trial.window.flip(clearBuffer = True)
        center_stim_on = self.clock.getTime()
        time.sleep(Trial.STIM_DUR)

        # Peripheral Stimulus and Response
        self.peri_stim.draw()
        Trial.window.flip(clearBuffer = True)
        peri_stim_on = self.clock.getTime()
        is_stim_on = True

        # Get user response
        while True:
            response_box = portio.inb(0x379)
            response_keyb = event.getKeys(keyList =
                                          [Trial.KBOARD_ANSWER_YES,
                                           Trial.KBOARD_ANSWER_NO,
                                           Trial.KBOARD_ANSWER_QUIT])

            # Flip stimulus when stimulus duration is reached
            # before subject response.
            if (is_stim_on and
                self.clock.getTime() - peri_stim_on >= Trial.STIM_DUR):
                Trial.window.flip(clearBuffer = True)
                peri_stim_off = self.clock.getTime()
                is_stim_on = False

            # Get response time
            if (response_box == Trial.BBOX_ANSWER_RIGHT or
                response_box == Trial.BBOX_ANSWER_LEFT or
                len(response_keyb) > 0):
                reaction_time = self.clock.getTime() - peri_stim_on
                break

        # Flip stimulus when stimulus duration is reached
        # after subject response
        if is_stim_on:
            while True:
                if (self.clock.getTime() - peri_stim_on >= Trial.STIM_DUR):
                    Trial.window.flip(clearBuffer = True)
                    peri_stim_off = self.clock.getTime()
                    break

        if  Trial.input_type == "Keyboard":
            response = response_keyb[0] # We only take the first key pressed
        elif Trial.input_type == "Response Box":
            response = response_box

        # Assign response box response
        if response == Trial.BBOX_ANSWER_RIGHT:
            response = "button_right"
        elif response == Trial.BBOX_ANSWER_LEFT:
            response = "button_left"

        # Assert timing
        assert trial_start < fix_cross_on
        assert fix_cross_on < center_stim_on
        assert center_stim_on < peri_stim_on
        assert peri_stim_on < peri_stim_off

        # Assert Condition
        # assert self.central_stim.get_name() == self.peri_stim.get_name()
        assert self.central_stim.get_position() == "central"
        assert (self.peri_stim.get_position() == "left" or
                self.peri_stim.get_position() == "right")

        # We only use timer data when yes or no was responded.
        # We don't want timer data if quit was pressed
        if (response == 'button_left' or
            response == 'button_right'or
            response == Trial.KBOARD_ANSWER_YES  or
            response == Trial.KBOARD_ANSWER_NO):

            # the element order of the timer has to match the
            # legend of the output file, so be careful with changes,
            # and don't forget to change the data file legend also.
            self.timer = [self.trial_nr,
                          self.block_nr,
                          trial_start,
                          self.central_stim.get_name(),
                          self.central_stim.get_type(),
                          self.central_stim.get_position(),
                          self.peri_stim.get_name(),
                          self.peri_stim.get_type(),
                          self.peri_stim.get_position(),
                          fix_cross_on,
                          center_stim_on,
                          peri_stim_on,
                          peri_stim_off,
                          response,
                          reaction_time]
            print self.timer

    def get_timer(self):
        """Returns the timer data of the trial"""
        return self.timer

class SquareStim(visual.ShapeStim):
    """A square stimulus: has a color (yellow or red) and a position
    (left, central or right), and can be drawn on a window."""
    def __init__(self, color, position, window):
        self.myname = "square"
        self.color = color
        self.position = position

        # A square consists of 4 vertices from top left (1) to bottom left (2),
        # bottom right (3) and top right (4).
        square = [[0, position.get_square_height()],
                  [0, 0],
                  [position.get_square_width(), 0],
                  [position.get_square_width(), position.get_square_height()]]
        visual.ShapeStim.__init__(self,
                                  window,
                                  lineRGB=color.get_color(),
                                  fillRGB=color.get_color(),
                                  vertices=square,
                                  pos=position.get_square_position())

    def get_name(self):
        """Gets the name of the stimulus."""
        return self.myname

    def get_type(self):
        """Gets the color of the stimulus"""
        return self.color.get_name()

    def get_position(self):
        """Gets the position (left central, or right) of the stimulus."""
        return self.position.get_name()

class LandoltStim(visual.TextStim):
    """A Landolt stimulus: has an orientation (opened to the top or bottom) and
    a position (left, central or right), and can be drawn on a window."""

    FONT = 'Sloan'

    # The sloan font was downloaded from
    # http://www.psych.nyu.edu/pelli/software.html
    # and published here:
    # Pelli, D. G., Robson, J. G., & Wilkins, A. J. (1988) The design of a
    # new letter chart for measuring contrast sensitivity.  Clinical Vision
    # Sciences 2, 187-199.

    def __init__(self, orientation, position, window):
        self.myname = "landolt"
        self.orientation = orientation
        self.position = position
        visual.TextStim.__init__(self,
                                 window,
                                 text="C",
                                 ori=orientation.get_orientation(),
                                 height=position.get_landolt_size(),
                                 pos=position.get_landolt_position(),
                                 font=LandoltStim.FONT)

    def get_name(self):
        """Gets the name of the stimulus."""
        return self.myname

    def get_type(self):
        """Gets the orientation of the stimulus."""
        return self.orientation.get_name()

    def get_position(self):
        """Gets the position (left central, or right) of the stimulus."""
        return self.position.get_name()

class LandoltStimSmall(visual.TextStim):
    """A small Landolt stimulus: has an orientation (opened to the top or bottom) and
    a position (left, central or right), and can be drawn on a window."""

    FONT = 'Sloan'

    # The sloan font was downloaded from
    # http://www.psych.nyu.edu/pelli/software.html
    # and published here:
    # Pelli, D. G., Robson, J. G., & Wilkins, A. J. (1988) The design of a
    # new letter chart for measuring contrast sensitivity.  Clinical Vision
    # Sciences 2, 187-199.

    def __init__(self, orientation, position, window):
        self.myname = "landoltsmall"
        self.orientation = orientation
        self.position = position
        visual.TextStim.__init__(self,
                                 window,
                                 text="C",
                                 ori=orientation.get_orientation(),
                                 height=position.get_landoltsmall_size(),
                                 pos=position.get_landolt_position(),
                                 font=LandoltStim.FONT)

    def get_name(self):
        """Gets the name of the stimulus."""
        return self.myname

    def get_type(self):
        """Gets the orientation of the stimulus."""
        return self.orientation.get_name()

    def get_position(self):
        """Gets the position (left central, or right) of the stimulus."""
        return self.position.get_name()


class SwordStim(visual.TextStim):
    """A Char stimulus: has a position (left, central or right), a color,
    and can be drawn on a window."""

    FONT = 'FreeSans'

    # The sloan font was downloaded from
    # http://www.psych.nyu.edu/pelli/software.html
    # and published here:
    # Pelli, D. G., Robson, J. G., & Wilkins, A. J. (1988) The design of a
    # new letter chart for measuring contrast sensitivity.  Clinical Vision
    # Sciences 2, 187-199.

    def __init__(self, color, position, window, char):
        self.aName = char
        self.myColor = color # myColor because mother class occupies color property
        self.position = position
        visual.TextStim.__init__(self,
                                 window,
                                 text=char,
                                 height=position.get_sword_size(),
                                 pos=position.get_landolt_position(),
                                 font=SwordStim.FONT,
                                 color=color.get_color())
        self.selection = ['i', 'o', 'x', 'v']

    def get_name(self):
        """Gets the name of the stimulus."""
        return self.aName

    def get_type(self):
        """Gets the type of the stimulus, match or nomatch"""
        if self.myColor.get_name() != 'white' or len(self.aName) == 1:
            return self.myColor.get_name()
        else:
            if (string.find(self.aName, self.selection[0]) >= 0 or
                string.find(self.aName, self.selection[1]) >= 0 or
                string.find(self.aName, self.selection[2]) >= 0 or
                string.find(self.aName, self.selection[3]) >= 0 ):
                return 'match'
            else:
                return 'nomatch'

    def get_position(self):
        """Gets the position (left central, or right) of the stimulus."""
        return self.position.get_name()

class Position:
    """Spatial information about position and size of the stimuli."""
    # The origin (X_0, y_0) of the coordinate system is in the center of the
    # window.

    # Stimulus height and width corresponds to 8 x 8 cm on the screen.

    # Because peripheral stimuli are projected bigger on the screen (longer
    # distance of light) they need to be drawn smaller here.

    # A additional height correction is used to align the peripheral stimuli
    # perfectly in the vertical axis.

    # Landolts are anchored in the center of the object, while
    # Squares are anchored in the bottom left corner of the object.

    # Landolds only need a height value. Squares need a height and width value.

    # todo: new scaling factor for smaller landolt stimuli

    # Central and peripheral square
    R = 0.75 # Resize Factor
    R_SWORD = 0.5 # Resize factor swords

    C_SQUARE_WIDTH = 1.37 * R
    C_SQUARE_HEIGHT = 1.40 * R
    P_SQUARE_WIDTH = 1.25 * R
    P_SQUARE_HEIGHT = 1.21 * R


    # Landolt
    C_LANDOLT_SIZE = 1.46 * R
    P_LANDOLT_SIZE = 1.3 * R

    LANDOLTSMALL_FACTOR = 0.5

    C_SWORD_SIZE = 1.46 * R_SWORD
    P_SWORD_SIZE = 1.30 * R_SWORD

    ECCENTRICITY = 13.0
    X = 0.0 # horizontal axis

    def __init__(self, position, eyeheight):
        self.name = position

        # Convert eye height in cm to window coordinate units. This linear
        # function is used to exactly display the stimuli at eye height.
        y_cent = 0.1762 * float(eyeheight) - 15.8767
        y_peri = 0.1569 * float(eyeheight) - 12.3922

        # Calculate Landolt anchor positions
        landolt_anchor_central = [Position.X, y_cent]
        landolt_anchor_left = [Position.X - Position.ECCENTRICITY, y_peri]
        landolt_anchor_right = [Position.X + Position.ECCENTRICITY, y_peri]

        # Calculate Square anchor positions
        square_anchor_central = [Position.X - Position.C_SQUARE_WIDTH/2,
                                 y_cent - Position.C_SQUARE_HEIGHT/2]
        square_anchor_left = [Position.X - Position.ECCENTRICITY -
                              Position.P_SQUARE_WIDTH/2,
                              y_peri - Position.P_SQUARE_HEIGHT/2]

        square_anchor_right = [Position.X + Position.ECCENTRICITY -
                               Position.P_SQUARE_WIDTH/2,
                               y_peri - Position.P_SQUARE_HEIGHT/2]

        # Test that left stimulus is left of center and center left
        # of right stimulus (testing the x-axis)
        assert landolt_anchor_left[0] < landolt_anchor_central[0]
        assert landolt_anchor_central[0] < landolt_anchor_right[0]
        assert square_anchor_left[0] < square_anchor_central[0]
        assert square_anchor_central[0] < square_anchor_right[0]

        # This properties are used in get methods as interface for
        # e.g. drawing calibration screens.
        self.fixcross_position = landolt_anchor_central
        self.left_position = landolt_anchor_left
        self.right_position = landolt_anchor_right

        if position == "left":
            self.landolt_position = landolt_anchor_left
            self.square_position = square_anchor_left
            self.square_width = Position.P_SQUARE_WIDTH
            self.square_height = Position.P_SQUARE_HEIGHT
            self.landolt_size = Position.P_LANDOLT_SIZE
            self.sword_size = Position.P_SWORD_SIZE
        elif position == "central":
            self.landolt_position = landolt_anchor_central
            self.square_position = square_anchor_central
            self.square_width = Position.C_SQUARE_WIDTH
            self.square_height = Position.C_SQUARE_HEIGHT
            self.landolt_size = Position.C_LANDOLT_SIZE
            self.sword_size = Position.C_SWORD_SIZE
        elif position == "right":
            self.landolt_position = landolt_anchor_right
            self.square_position = square_anchor_right
            self.square_width = Position.P_SQUARE_WIDTH
            self.square_height = Position.P_SQUARE_HEIGHT
            self.landolt_size = Position.P_LANDOLT_SIZE
            self.sword_size = Position.P_SWORD_SIZE
        else:
            assert 0, "Stimulus position is wrong!"

    def get_name(self):
        """Gets the position name."""
        return self.name

    def get_square_position(self):
        """Gets the position vector of the Square."""
        return self.square_position

    def get_landolt_position(self):
        """Gets the position vector of the Landolt."""
        return self.landolt_position

    def get_square_height(self):
        """Gets the height of the square."""
        return self.square_height

    def get_square_width(self):
        """Gets the width of the square."""
        return self.square_width

    def get_landolt_size(self):
        """Gets the size of the Landolt."""
        return self.landolt_size

    def get_landoltsmall_size(self):
        """Gets the size of the Landolt."""
        return self.landolt_size * Position.LANDOLTSMALL_FACTOR

    def get_sword_size(self):
        """Gets the size of the Landolt."""
        return self.sword_size

    def get_fixcross_position(self):
        """Gets the position of the fixation cross."""
        return self.fixcross_position

    def get_left_position(self):
        """Gets left position, which is the
        central point on the left screen."""
        return self.left_position

    def get_right_position(self):
        """Gets right position, which is the
        central point on the right screen."""
        return self.right_position

class Color:
    """The color of the Square stimulus, either red or yellow"""
    RED = [1, -1, -1]
    YELLOW = [1, 1, -1]
    WHITE = [1, 1, 1]

    def __init__(self, color):
        self.name = color

        if color == "red":
            self.color = Color.RED
        elif color == "yellow":
            self.color = Color.YELLOW
        elif color == "white":
            self.color = Color.WHITE
        else:
            assert 0, "Stimulus color is wrong!"

    def get_name(self):
        """Gets the color name"""
        return self.name

    def get_color(self):
        """Gets the RGB vector"""
        return self.color

class Orientation:
    """The orientation of the Landolt stimulus."""
    UP = 90
    DOWN = 270

    def __init__(self, orientation):
        self.name = orientation

        if orientation == "up":
            self.orientation = Orientation.UP
        elif orientation == "down":
            self.orientation = Orientation.DOWN
        else:
            assert 0, "Stimulus orientation is wrong!"

    def get_name(self):
        """Gets the orientation name"""
        return self.name

    def get_orientation(self):
        """Gets the orientation in degrees"""
        return self.orientation

class Stimuli:
    """Creates a container for the fixation cross,
    and the central an peripheral stimuli."""

    def __init__(self, win, eyeheight):

        # Square colors
        red = Color("red")
        yellow = Color("yellow")

        # Landolt orientations
        up = Orientation("up")
        down = Orientation("down")

        # Positions
        left = Position("left", eyeheight)
        central = Position("central", eyeheight)
        right = Position("right", eyeheight)

        # Fixation Cross
        self.fix_cross = Point(win, central.get_fixcross_position())

        # Central Stimuli (No. 0, 1, 2, 3)
        sq_red_c = SquareStim(red, central, win)
        sq_yel_c = SquareStim(yellow, central, win)
        lt_dn_c = LandoltStim(down, central, win)
        lt_up_c = LandoltStim(up, central, win)

        # Peripheral Squares (No. 0, 1, 2, 3)
        sq_red_l = SquareStim(red, left, win)
        sq_red_r = SquareStim(red, right, win)
        sq_yel_l = SquareStim(yellow, left, win)
        sq_yel_r = SquareStim(yellow, right, win)

        # Peripheral Landolts (No. 4, 5, 6, 7)
        lt_dn_l = LandoltStim(down, left, win)
        lt_dn_r = LandoltStim(down, right, win)
        lt_up_l = LandoltStim(up, left, win)
        lt_up_r = LandoltStim(up, right, win)

        self.central_stimuli = [sq_red_c, sq_yel_c, lt_dn_c, lt_up_c]
        self.peripheral_stimuli = [sq_red_l, sq_red_r, sq_yel_l, sq_yel_r,
                                   lt_dn_l, lt_dn_r, lt_up_l, lt_up_r]

    def get_central_stimuli(self):
        "Returns a list of the 4 possible central stimuli"
        return self.central_stimuli

    def get_peripheral_stimuli(self):
        "Returns a list of the 8 possible peripheral stimuli"
        return self.peripheral_stimuli

    def get_fixation_cross(self):
        "Gets the fixation cross"
        return self.fix_cross

class StimuliLandoltSmall:
    """Creates a container for the fixation cross,
    and the central an peripheral stimuli."""

    def __init__(self, win, eyeheight):

        # Square colors
        red = Color("red")
        yellow = Color("yellow")

        # Landolt orientations
        up = Orientation("up")
        down = Orientation("down")

        # Positions
        left = Position("left", eyeheight)
        central = Position("central", eyeheight)
        right = Position("right", eyeheight)

        # Fixation Cross
        self.fix_cross = Point(win, central.get_fixcross_position())

        # Central Stimuli (No. 0, 1, 2, 3, 4, 5)
        sq_red_c = SquareStim(red, central, win)
        sq_yel_c = SquareStim(yellow, central, win)
        lt_dn_c = LandoltStim(down, central, win)
        lt_up_c = LandoltStim(up, central, win)
        ltsmall_dn_c = LandoltStimSmall(down, central, win) # extending with new type
        ltsmall_up_c = LandoltStimSmall(up, central, win)

        # Peripheral Squares (No. 0, 1, 2, 3)
        sq_red_l = SquareStim(red, left, win)
        sq_red_r = SquareStim(red, right, win)
        sq_yel_l = SquareStim(yellow, left, win)
        sq_yel_r = SquareStim(yellow, right, win)

        # Peripheral Landolts (No. 4, 5, 6, 7)
        lt_dn_l = LandoltStim(down, left, win)
        lt_dn_r = LandoltStim(down, right, win)
        lt_up_l = LandoltStim(up, left, win)
        lt_up_r = LandoltStim(up, right, win)
        ltsmall_up_l = LandoltStimSmall(up, left, win)
        ltsmall_up_r = LandoltStimSmall(up, right, win)
        ltsmall_dn_l = LandoltStimSmall(down, left, win)
        ltsmall_dn_r = LandoltStimSmall(down, right, win)

        self.central_stimuli = [sq_red_c, sq_yel_c, lt_dn_c, lt_up_c, ltsmall_dn_c, ltsmall_up_c]
        self.peripheral_stimuli = [sq_red_l, sq_red_r, sq_yel_l, sq_yel_r,
                                   lt_dn_l, lt_dn_r, lt_up_l, lt_up_r,
                                   ltsmall_dn_l, ltsmall_dn_r, ltsmall_up_l, ltsmall_up_r]

    def get_central_stimuli(self):
        "Returns a list of the 6 possible central stimuli"
        return self.central_stimuli

    def get_peripheral_stimuli(self):
        "Returns a list of the 10 possible peripheral stimuli"
        return self.peripheral_stimuli

    def get_fixation_cross(self):
        "Gets the fixation cross"
        return self.fix_cross

class StimuliSword:
    """Creates a container for the fixation cross,
    and the central an peripheral stimuli."""

    def __init__(self, win, eyeheight):

        # Square colors
        red = Color("red")
        yellow = Color("yellow")
        white = Color("white")

        # Positions
        left = Position("left", eyeheight)
        central = Position("central", eyeheight)
        right = Position("right", eyeheight)

        # Fixation Cross
        self.fix_cross = Point(win, central.get_fixcross_position())

        # Central Stimuli
        self.central_stimuli = [
                                SwordStim(red   , central, win, "i"),    # color task
                                SwordStim(red   , central, win, "i"),
                                SwordStim(yellow, central, win, "i"),
                                SwordStim(yellow, central, win, "i"),
                                SwordStim(red   , central, win, "o"),
                                SwordStim(red   , central, win, "o"),
                                SwordStim(yellow, central, win, "o"),
                                SwordStim(yellow, central, win, "o"),
                                SwordStim(red   , central, win, "x"),
                                SwordStim(red   , central, win, "x"),
                                SwordStim(yellow, central, win, "x"),
                                SwordStim(yellow, central, win, "x"),
                                SwordStim(red   , central, win, "v"),
                                SwordStim(red   , central, win, "v"),
                                SwordStim(yellow, central, win, "v"),
                                SwordStim(yellow, central, win, "v"),
                                SwordStim(white, central, win, "i"),    # search task
                                SwordStim(white, central, win, "i"),
                                SwordStim(white, central, win, "i"),
                                SwordStim(white, central, win, "i"),
                                SwordStim(white, central, win, "o"),
                                SwordStim(white, central, win, "o"),
                                SwordStim(white, central, win, "o"),
                                SwordStim(white, central, win, "o"),
                                SwordStim(white, central, win, "x"),
                                SwordStim(white, central, win, "x"),
                                SwordStim(white, central, win, "x"),
                                SwordStim(white, central, win, "x"),
                                SwordStim(white, central, win, "v"),
                                SwordStim(white, central, win, "v"),
                                SwordStim(white, central, win, "v"),
                                SwordStim(white, central, win, "v")
                                ]

        # initialize 32 random strings, 16 of them contain {a, c, o, u}
        self.peripheral_stimuli = [SwordStim(red,    left , win, Sword("").string),      # color task
                                   SwordStim(yellow, left , win, Sword("").string),      # no char matches because of
                                   SwordStim(yellow, right , win, Sword("").string),     # subject confusion
                                   SwordStim(red,    right , win, Sword("").string),
                                   SwordStim(red,    left , win, Sword("").string),
                                   SwordStim(yellow, left , win, Sword("").string),
                                   SwordStim(yellow, right , win, Sword("").string),
                                   SwordStim(red,    right , win, Sword("").string),
                                   SwordStim(red,    left , win, Sword("").string),
                                   SwordStim(yellow, left , win, Sword("").string),
                                   SwordStim(yellow, right , win, Sword("").string),
                                   SwordStim(red,    right , win, Sword("").string),
                                   SwordStim(red,    left , win, Sword("").string),
                                   SwordStim(yellow, left , win, Sword("").string),
                                   SwordStim(yellow, right , win, Sword("").string),
                                   SwordStim(red,    right , win, Sword("").string),
                                   SwordStim(white, left , win, Sword("i").string),    # search task
                                   SwordStim(white, right, win, Sword("i").string),
                                   SwordStim(white, left , win, Sword("").string),
                                   SwordStim(white, right, win, Sword("").string),
                                   SwordStim(white, left , win, Sword("o").string),
                                   SwordStim(white, right, win, Sword("o").string),
                                   SwordStim(white, left , win, Sword("").string),
                                   SwordStim(white, right, win, Sword("").string),
                                   SwordStim(white, left , win, Sword("x").string),
                                   SwordStim(white, right, win, Sword("x").string),
                                   SwordStim(white, left , win, Sword("").string),
                                   SwordStim(white, right, win, Sword("").string),
                                   SwordStim(white, left , win, Sword("v").string),
                                   SwordStim(white, right, win, Sword("v").string),
                                   SwordStim(white, left , win, Sword("").string),
                                   SwordStim(white, right, win, Sword("").string)
                                   ]

    def get_central_stimuli(self):
        "Returns a list of the 4 possible central stimuli"
        return self.central_stimuli

    def get_peripheral_stimuli(self):
        "Returns a list of the 8 possible peripheral stimuli"
        return self.peripheral_stimuli

    def get_fixation_cross(self):
        "Gets the fixation cross"
        return self.fix_cross

class Session:
    """The Session shows the instructions and
    presents the blocks and trials."""

    BBOX_ANSWER_MIDDLE = 0x58
    KBOARD_SPACE = 'space'

    PAUSE_DURATION = 20 # Pause durations in seconds

    def __init__(self, input_device, handedness, screen, eyeheight,
                 win_size, win_color, monitor, blocks, trials, clock):

        self.input_device = input_device
        self.handedness = handedness

        Session.win_size = win_size
        Session.win_color = win_color
        Session.monitor = monitor

        self.blocks = blocks
        self.trials = trials
        self.clock = clock

        self.has_quit = False

        # create window
        self.win = visual.Window(size=Session.win_size,
                                 monitor=Session.monitor,
                                 units="deg",
                                 color=Session.win_color,
                                 screen=screen)
        self.win.flip(clearBuffer = True)
        # create stimuli
        stimuli = Stimuli(self.win, eyeheight)
        self.fix_cross = stimuli.get_fixation_cross()
        self.c_stimuli = stimuli.get_central_stimuli()
        self.p_stimuli = stimuli.get_peripheral_stimuli()
        self.data = list()

        # Randomization
        # We have two stimuli matrices (central and peripheral).
        # A random sequence is used to present the stimuli combinations.
        # Number of trials should be a multiple of 16. The combination
        # matrices are extended, e.g. by factor 2 if using 32 trials
        self.cent_seq = [0, 0, 0, 0,
                         1, 1, 1, 1,
                         2, 2, 2, 2,
                         3, 3, 3, 3] * (self.trials/16)
        self.peri_seq = [0, 1, 2, 3,
                         0, 1, 2, 3,
                         4, 5, 6, 7,
                         4, 5, 6, 7] * (self.trials/16)

        self.rand_seq = range(0, self.trials)
        random.shuffle(self.rand_seq) # block randomization
        self.__show_instructions()
        self.__run()

    def __pause(self):
        """Pause among the experimental blocks for relaxing times."""

        pause_string = "Kurze Pause (20 Sekunden)"
        ready_string = """
                       Das Experiment geht nun weiter. Bitte druecken Sie
                       die rote Taste, wenn Sie bereit sind.
                       """

        pause = visual.TextStim(self.win, text=pause_string,
                                height=0.5, font='FreeSans')
        ready = visual.TextStim(self.win, text=ready_string,
                                height=0.5, font='FreeSans')

        pause.draw()
        self.win.flip(clearBuffer = True)
        time.sleep(Session.PAUSE_DURATION)
        ready.draw()
        self.win.flip(clearBuffer = True)

        event.clearEvents(eventType = None)
        while True:
            key = event.getKeys(keyList = Session.KBOARD_SPACE)
            button = portio.inb(0x379)
            if len(key) > 0 or button == Session.BBOX_ANSWER_MIDDLE:
                self.win.flip(clearBuffer = True)
                break

    def __show_instructions(self):

        text = """
        Wenn die beiden Figuren gleich sind, druecken Sie mit dem
        Zeigefinger. Wenn die beiden Figuren eine verschiedene
        Farbe haben, oder eine unterschiedliche Orientierung, dann
        druecken sie mit dem Mittelfinger.

        Versuchen Sie, so schnell wie moeglich zu druecken, aber
        wichtiger ist, dass Sie korrekte Antworten geben.

        Wenn Sie bereit sind, druecken Sie dir rote Taste, um das
        Experiment zu beginnen. Ansonsten fragen sie den
        Versuchsleiter.

        """

        text = """
        Wenn die beiden Figuren gleich sind, druecken Sie mit dem linken Daumen.

        """

        instructions = visual.TextStim(self.win, text=text,
                                       height=0.5, font='FreeSans')
        instructions.draw()
        self.win.flip(clearBuffer = True)

        event.clearEvents(eventType = None)
        while True:
            key = event.getKeys(keyList = Session.KBOARD_SPACE)
            button = portio.inb(0x379)
            if len(key) > 0 or button == Session.BBOX_ANSWER_MIDDLE:
                self.win.flip(clearBuffer = True)
                break

    def __run(self):
        """Presents instructions, and all the trials in blocks"""

        trial_nr = 0 # we need this to count throughout the blocks
        # block j, trial i
        for j in range(0, self.blocks):
            for i in range(0, self.trials):
                if self.has_quit:
                    break
                trial = Trial(self.input_device,
                              self.handedness,
                              self.clock,
                              trial_nr + 1,
                              j + 1,
                              self.fix_cross,
                              self.c_stimuli[self.cent_seq[self.rand_seq[i]]],
                              self.p_stimuli[self.peri_seq[self.rand_seq[i]]],
                              self.win)
                trial_nr = trial_nr + 1

                # if quit key was pressed timer is 'None'
                # and not written to data
                if trial.get_timer() == None:
                    self.has_quit = True
                else:
                    self.data.append(trial.get_timer())

            # we don't make a pause in experiments with 1 block only,
            # neither at the end of the last block.
            if self.blocks > 1 and j < 2 and not self.has_quit:
                self.__pause()

        # Exit experiment
        self.win.close()

    def get_var_names(self):
        """Gets the variable names."""
        # This has to match the timer of the Trial object
        return [['trial_nr',
                 'block_nr',
                 'trial_start',
                 'central_stim_name',
                 'central_stim_type',
                 'central_stim_position',
                 'peri_stim_name',
                 'peri_stim_type',
                 'peri_stim_position',
                 'fixation_point_on',
                 'center_stim_on',
                 'peri_stim_on',
                 'peri_stim_off',
                 'response',
                 'response_time']]

    def get_data(self):
        """Returns the data"""
        return self.data

class SessionLandoltSmall:
    """The Session shows the instructions and
    presents the blocks and trials. Adapded for Miriam"""

    BBOX_ANSWER_MIDDLE = 0x5f
    KBOARD_SPACE = 'space'

    PAUSE_DURATION = 20 # Pause durations in seconds

    def __init__(self, input_device, handedness, screen, eyeheight,
                 win_size, win_color, monitor, blocks, trials, clock):

        self.input_device = input_device
        self.handedness = handedness

        Session.win_size = win_size
        Session.win_color = win_color
        Session.monitor = monitor

        self.blocks = blocks
        self.trials = trials
        self.clock = clock

        self.has_quit = False

        # create window
        self.win = visual.Window(size=Session.win_size,
                                 monitor=Session.monitor,
                                 units="deg",
                                 color=Session.win_color,
                                 screen=screen)
        self.win.flip(clearBuffer = True)
        # create stimuli
        stimuli = StimuliLandoltSmall(self.win, eyeheight)
        self.fix_cross = stimuli.get_fixation_cross()
        self.c_stimuli = stimuli.get_central_stimuli()
        self.p_stimuli = stimuli.get_peripheral_stimuli()
        self.data = list()

        # Randomization
        # We have two stimuli matrices (central and peripheral).
        # A random sequence is used to present the stimuli combinations.
        # Number of trials should be a multiple of 24. The combination
        # matrices are extended, e.g. by factor 2 if using 32 trials
        self.cent_seq = [0, 0, 0, 0,  # sq
                         1, 1, 1, 1,
                         2, 2, 2, 2,  # lt
                         3, 3, 3, 3,
                         4, 4, 4, 4,  # lt small
                         5, 5, 5, 5 ] * (self.trials/24)
        self.peri_seq = [0, 1, 2, 3, # sq
                         0, 1, 2, 3,
                         4, 5, 6, 7,
                         4, 5, 6, 7,
                         8, 9,10,11,
                         8, 9,10,11 ] * (self.trials/24)

        self.rand_seq = range(0, self.trials)
        random.shuffle(self.rand_seq) # block randomization
        self.__show_instructions()
        self.__run()

    def __pause(self):
        """Pause among the experimental blocks for relaxing times."""

        pause_string = "Kurze Pause (20 Sekunden)"
        ready_string = """
                       Das Experiment geht nun weiter. Bitte druecken Sie
                       die rote Taste, wenn Sie bereit sind.
                       """

        pause = visual.TextStim(self.win, text=pause_string,
                                height=0.5, font='FreeSans')
        ready = visual.TextStim(self.win, text=ready_string,
                                height=0.5, font='FreeSans')

        pause.draw()
        self.win.flip(clearBuffer = True)
        time.sleep(Session.PAUSE_DURATION)
        ready.draw()
        self.win.flip(clearBuffer = True)

        event.clearEvents(eventType = None)
        while True:
            key = event.getKeys(keyList = Session.KBOARD_SPACE)
            button = portio.inb(0x379)
            if len(key) > 0 or button == Session.BBOX_ANSWER_MIDDLE:
                self.win.flip(clearBuffer = True)
                break

    def __show_instructions(self):

        text = """
        Wenn die beiden Figuren gleich sind, druecken Sie mit dem
        rechten Daumen, wenn Sie Rechtshaender sind und umgekehrt.
        Wenn die beiden Figuren eine verschiedene Farbe haben,
        oder eine unterschiedliche Orientierung, dann druecken
        sie mit dem linken Daumen und umgekehrt.
        Versuchen Sie, so schnell wie moeglich zu druecken, aber
        wichtiger ist, dass Sie korrekte Antworten geben.

        Wenn Sie bereit sind, druecken Sie dir rote Taste, um das
        Experiment zu beginnen. Ansonsten fragen sie den
        Versuchsleiter.

        """
        instructions = visual.TextStim(self.win, text=text,
                                       height=0.5, font='FreeSans')
        instructions.draw()
        self.win.flip(clearBuffer = True)

        event.clearEvents(eventType = None)
        while True:
            key = event.getKeys(keyList = Session.KBOARD_SPACE)
            button = portio.inb(0x379)
            if len(key) > 0 or button == Session.BBOX_ANSWER_MIDDLE:
                self.win.flip(clearBuffer = True)
                break

    def __run(self):
        """Presents instructions, and all the trials in blocks"""

        trial_nr = 0 # we need this to count throughout the blocks
        # block j, trial i
        for j in range(0, self.blocks):
            for i in range(0, self.trials):
                if self.has_quit:
                    break
                trial = Trial(self.input_device,
                              self.handedness,
                              self.clock,
                              trial_nr + 1,
                              j + 1,
                              self.fix_cross,
                              self.c_stimuli[self.cent_seq[self.rand_seq[i]]],
                              self.p_stimuli[self.peri_seq[self.rand_seq[i]]],
                              self.win)
                trial_nr = trial_nr + 1

                # if quit key was pressed timer is 'None'
                # and not written to data
                if trial.get_timer() == None:
                    self.has_quit = True
                else:
                    self.data.append(trial.get_timer())

            # we don't make a pause in experiments with 1 block only,
            # neither at the end of the last block.
            if self.blocks > 1 and j < 2 and not self.has_quit:
                self.__pause()

        # Exit experiment
        self.win.close()

    def get_var_names(self):
        """Gets the variable names."""
        # This has to match the timer of the Trial object
        return [['trial_nr',
                 'block_nr',
                 'trial_start',
                 'central_stim_name',
                 'central_stim_type',
                 'central_stim_position',
                 'peri_stim_name',
                 'peri_stim_type',
                 'peri_stim_position',
                 'fixation_point_on',
                 'center_stim_on',
                 'peri_stim_on',
                 'peri_stim_off',
                 'response',
                 'response_time']]

    def get_data(self):
        """Returns the data"""
        return self.data

class SessionSword:
    """The Session shows the instructions and
    presents the blocks and trials."""

    BBOX_ANSWER_MIDDLE = 0x5f
    KBOARD_SPACE = 'space'

    PAUSE_DURATION = 20 # Pause durations in seconds

    def __init__(self, input_device, handedness, screen, eyeheight,
                 win_size, win_color, monitor, blocks, trials, clock):

        self.input_device = input_device
        self.handedness = handedness

        Session.win_size = win_size
        Session.win_color = win_color
        Session.monitor = monitor

        self.blocks = blocks
        self.trials = trials
        self.clock = clock

        self.has_quit = False

        # create window
        self.win = visual.Window(size=Session.win_size,
                                 monitor=Session.monitor,
                                 units="deg",
                                 color=Session.win_color,
                                 screen=screen)
        self.win.flip(clearBuffer = True)
        # create stimuli
        stimuli = StimuliSword(self.win, eyeheight)
        self.fix_cross = stimuli.get_fixation_cross()
        self.c_stimuli = stimuli.get_central_stimuli()
        self.p_stimuli = stimuli.get_peripheral_stimuli()
        self.data = list()

        # Randomization
        # We have two stimuli matrices (central and peripheral).
        # A random sequence is used to present the stimuli combinations.
        # Number of trials should be a multiple of 16. The combination
        # matrices are extended, e.g. by factor 2 if using 32 trials
        #self.cent_seq = [0, 1, 2, 3,   # color
        #                 4, 5, 6, 7,   # color
        #                 8, 9, 10, 11, # white
        #                 12, 13, 14, 15] * (self.trials/16) # white
        #self.peri_seq = [0, 1, 2, 3,
        #                 0, 1, 2, 3,
        #                 4, 5, 6, 7,
        #                 4, 5, 6, 7] * (self.trials/16)

        self.rand_seq = range(0, self.trials)
        random.shuffle(self.rand_seq) # block randomization
        self.__show_instructions()
        self.__run()

    def __pause(self):
        """Pause among the experimental blocks for relaxing times."""

        pause_string = "Kurze Pause (20 Sekunden)"
        ready_string = """
                       Das Experiment geht nun weiter. Bitte druecken Sie
                       die rote Taste, wenn Sie bereit sind.
                       """

        pause = visual.TextStim(self.win, text=pause_string,
                                height=0.5, font='FreeSans')
        ready = visual.TextStim(self.win, text=ready_string,
                                height=0.5, font='FreeSans')

        pause.draw()
        self.win.flip(clearBuffer = True)
        time.sleep(Session.PAUSE_DURATION)
        ready.draw()
        self.win.flip(clearBuffer = True)

        event.clearEvents(eventType = None)
        while True:
            key = event.getKeys(keyList = Session.KBOARD_SPACE)
            button = portio.inb(0x379)
            if len(key) > 0 or button == Session.BBOX_ANSWER_MIDDLE:
                self.win.flip(clearBuffer = True)
                break

    def __show_instructions(self):

        text = """
        Schauen sie immer zuerst auf den Punkt, danach auf die Figuren.
        Sie muessen folgende 2 Aufgaben zu loesen:

        1. Wenn die erste und zweite Figure uebereinstimmen, druecken
        Sie "Ja" mit dem  Zeigefinger. Das ist der Fall, wenn die
        erste und die zweite Figur die selbe Farbe aufweisen.
        2. Bei weissen Figuren kommt es darauf an, ob die erste Figur
        (ein Buchstabe) in der zweiten Figur (mehrere Buchstaben)
        enthalten ist.
        Versuchen Sie, so schnell wie moeglich zu druecken, aber
        wichtiger ist, dass Sie korrekte Antworten geben. Wenn Sie
        bereit sind, druecken Sie dir rote Taste, um das Experiment
        zu beginnen. Ansonsten fragen sie den Versuchsleiter.
        """
        instructions = visual.TextStim(self.win, text=text,
                                       height=0.5, font='FreeSans')
        instructions.draw()
        self.win.flip(clearBuffer = True)

        event.clearEvents(eventType = None)
        while True:
            key = event.getKeys(keyList = Session.KBOARD_SPACE)
            button = portio.inb(0x379)
            if len(key) > 0 or button == Session.BBOX_ANSWER_MIDDLE:
                self.win.flip(clearBuffer = True)
                break

    def __run(self):
        """Presents instructions, and all the trials in blocks"""

        trial_nr = 0 # we need this to count throughout the blocks
        # block j, trial i
        for j in range(0, self.blocks):
            for i in range(0, self.trials):
                if self.has_quit:
                    break
                trial = Trial(self.input_device,
                              self.handedness,
                              self.clock,
                              trial_nr + 1,
                              j + 1,
                              self.fix_cross,
                              self.c_stimuli[self.rand_seq[i]],
                              self.p_stimuli[self.rand_seq[i]],
                              self.win)
                trial_nr = trial_nr + 1

                # if quit key was pressed timer is 'None'
                # and not written to data
                if trial.get_timer() == None:
                    self.has_quit = True
                else:
                    self.data.append(trial.get_timer())

            # we don't make a pause in experiments with 1 block only,
            # neither at the end of the last block.
            if self.blocks > 1 and j < 2 and not self.has_quit:
                self.__pause()

        # Exit experiment
        self.win.close()

    def get_var_names(self):
        """Gets the variable names."""
        # This has to match the timer of the Trial object
        return [['trial_nr',
                 'block_nr',
                 'trial_start',
                 'central_stim_name',
                 'central_stim_type',
                 'central_stim_position',
                 'peri_stim_name',
                 'peri_stim_type',
                 'peri_stim_position',
                 'fixation_point_on',
                 'center_stim_on',
                 'peri_stim_on',
                 'peri_stim_off',
                 'response',
                 'response_time']]

    def get_data(self):
        """Returns the data"""
        return self.data

class IDGenerator:
    """The ID Generator creates a random
    string to identify the subjects."""

    LENGTH = 6

    def get_id(self):
        """Returns a new the ID"""
        self.subjectid = ""
        alphabet = string.letters
        selection = random.sample(alphabet, random.randint(IDGenerator.LENGTH,
                                                           IDGenerator.LENGTH))

        # Assemble character list into a sting
        # ['a', 'b'] -> 'ab'
        for i in range(0, IDGenerator.LENGTH):
            self.subjectid = self.subjectid + selection[i]

        return self.subjectid

class Experiment:
    """The Experiment starts the experimental or practice Session, contains
    the Graphical User Interface, can save the data, can show calibration
    screens, etc."""

    APP_NAME = "pvrtask 0.1"
    WIN_SIZE = (1024, 768) # Window size
    WIN_COLOR = -1 # Window background color
    MONITOR = "testMonitor"
    PRACTICE_BLOCKS = 1
    PRACTICE_TRIALS = 24
    BLOCKS = 3
    TRIALS = 48
    KBOARD_SPACE = 'space'
    KBOARD_TOGGLE = 't'
    KBOARD_QUIT = 'q'
    CALIBRATION_HEIGHT = 5.27 #120cm, if this is changed, resurvey calib. plane!

    def __init__(self):

        # Start global clock
        self.clock = core.Clock()

        self.id_generator = IDGenerator()
        self.motor_trials = None
        self.experimental_session = None
        self.practice_trials = None
        self.timer_head_calibration = None

        self.__init_gui()

    def __init_gui(self):
        """Initialize all GUI components"""
        root = Tk()
        root.resizable(width=0, height=0)
        root.title(Experiment.APP_NAME)
        root.option_add('*font', 'Helvetica -12')

        # create a menu
        menu = Menu(root)
        root.config(menu=menu)

        # # # Menu Display # # #
        filemenu = Menu(menu)
        menu.add_cascade(label="File", menu=filemenu)

        filemenu.add_command(label="Save As...", command=self.__save)
        filemenu.add_command(label="New Subject ID",
                             command=self.__new_id)
        filemenu.add_command(label="Exit", command=exit_program)

        # # # Menu Display # # #
        displaymenu = Menu(menu)
        menu.add_cascade(label="Display", menu=displaymenu)

        displaymenu.add_command(label="Stimuli Test Screen",
                                command=self.__show_stimuli_screen)
        displaymenu.add_command(label="Eye Calibration",
                                command=self.__start_eye_calibration)

        # # # Menu Run # # #
        runmenu = Menu(menu)
        menu.add_cascade(label="Run", menu=runmenu)

        runmenu.add_command(label="Head Calibration",
                                command=self.__start_head_calibration)
        #runmenu.add_command(label="Motor Trials",
        #                    command=self.__start_motor_trials)
        runmenu.add_command(label="Practice Trials",
                            command=self.__start_practice_trials)
        #runmenu.add_command(label="Experiment Landolt", command=self.__start_experiment)

        runmenu.add_command(label="Experiment Small Landolt", command=self.__start_experiment_smallLandolt)

        #runmenu.add_separator()

        #runmenu.add_command(label="Practice Trials sWords",
        #                    command=self.__start_practice_trials_sword)
        #runmenu.add_command(label="Experiment sWords", command=self.__start_experiment_sword)

        # # # Menu Help # # #
        helpmenu = Menu(menu)
        menu.add_cascade(label="Help", menu=helpmenu)
        helpmenu.add_command(label="About...", command=self.__show_about)

        # # # Window # # #

        # Subject ID field
        label_subjectid = Label(root, text="Subject ID: ")
        label_subjectid.grid(row=0, column=0, sticky=E)

        self.idvar = StringVar()
        entry_subjectid = Entry(root, textvariable=self.idvar)
        entry_subjectid.focus_set()
        entry_subjectid.grid(row=0, column=1, sticky=W)
        # Set the ID
        self.idvar.set(self.id_generator.get_id())

        # Date field
        label_date = Label(root, text="Date: ")
        label_date.grid(row=1, column=0, sticky=E)

        today = datetime.date.today()
        self.today_string = today.isoformat()
        label_today = Label(root, text=self.today_string)
        label_today.grid(row=1, column=1, sticky=W)

        # Year of birth field
        label_birthyear = Label(root, text="Year of Birth: ")
        label_birthyear.grid(row=2, column=0, sticky=E)

        self.birthyear = StringVar()
        entry_birthyear = Entry(root, textvariable = self.birthyear)
        entry_birthyear.focus_set()
        entry_birthyear.grid(row=2, column=1, sticky=W)
        self.birthyear.set("Enter Year")

        # Sex
        label_sex = Label(root, text="Sex: ")
        label_sex.grid(row=3, column=0, sticky=E)

        self.sex = StringVar()
        rbutton_male = Radiobutton(root, text="Male", variable=self.sex,
                                   value="Male")
        rbutton_male.grid(row=3, column=1, sticky=W)
        rbutton_female = Radiobutton(root, text="Female", variable=self.sex,
                                     value="Female")
        rbutton_female.grid(row=4, column=1, sticky=W)

        # Handedness
        label_hand = Label(root, text="Handedness: ")
        label_hand.grid(row=5, column=0, sticky=E)

        self.hand = StringVar()
        # Set right as default
        #self.hand.set("right")
        rbutton_right = Radiobutton(root, text="Right", variable=self.hand,
                                    value="right")
        rbutton_right.grid(row=5, column=1, sticky=W)
        rbutton_left = Radiobutton(root, text="Left", variable=self.hand,
                                   value="left")
        rbutton_left.grid(row=6, column=1, sticky=W)

        # Group
        label_group = Label(root, text="Group: ")
        label_group.grid(row=7, column=0, sticky=E)

        self.group = StringVar()
        rbutton_control = Radiobutton(root, text="Control", variable=self.group,
                                      value="Control")
        rbutton_control.grid(row=7, column=1, sticky=W)
        rbutton_schizophrenia = Radiobutton(root, text="Patient",
                                            variable=self.group,
                                            value="Patient")
        rbutton_schizophrenia.grid(row=8, column=1, sticky=W)

        # Eye height
        label_eyeheight = Label(root, text="Eye Height: ")
        label_eyeheight.grid(row=9, column=0, sticky=E)

        self.spinbox_eyeheight = Spinbox(root, from_=100, to=200)
        self.spinbox_eyeheight.grid(row=9, column=1, sticky=W)

        # Input Device
        label_input = Label(root, text="Input Device: ")
        label_input.grid(row=10, column=0, sticky=E)

        self.inputdev = StringVar()
        #self.inputdev.set("Response Box")
        self.inputdev.set("Keyboard")
        optionmenu_input = OptionMenu(root, self.inputdev,
                                      "Response Box", "Keyboard")
        optionmenu_input.grid(row=10, column=1, sticky=W)

        # Screen
        label_screen = Label(root, text="Experiment Screen: ")
        label_screen.grid(row=11, column=0, sticky=E)

        self.screen = StringVar()
        self.screen.set("Default")
        optionmenu_screen = OptionMenu(root, self.screen,
                                       "Default", "Beamer")
        optionmenu_screen.grid(row=11, column=1, sticky=W)

        # Start and Save Button
#        button_start = Button(root, text="Start",
#                              command=self.__start_experiment)
#        button_start.grid(row=12, column=0)
#        button_save = Button(root, text="Save", command=self.__save)
#        button_save.grid(row=12, column=1)

        root.mainloop()

    def __show_about(self):
        """Shows About Dialogue"""
        tkFont.Font(family="Times", size=6, weight=tkFont.BOLD)
        string = Experiment.APP_NAME +\
        """Copyright (C) 2010 Simon Schwab"""
        tkMessageBox.showinfo("About", string)

    def __start_experiment(self):
        """Starts the experimental session"""
        self.experimental_session = Session(self.inputdev.get(),
                                     self.hand.get(),
                                     self.__get_screen_no(),
                                     self.spinbox_eyeheight.get(),
                                     Experiment.WIN_SIZE,
                                     Experiment.WIN_COLOR,
                                     Experiment.MONITOR,
                                     Experiment.BLOCKS,
                                     Experiment.TRIALS,
                                     self.clock)

    def __start_experiment_sword(self):
        """Starts the experimental session"""
        self.experimental_session = SessionSword(self.inputdev.get(),
                                     self.hand.get(),
                                     self.__get_screen_no(),
                                     self.spinbox_eyeheight.get(),
                                     Experiment.WIN_SIZE,
                                     Experiment.WIN_COLOR,
                                     Experiment.MONITOR,
                                     Experiment.BLOCKS,
                                     Experiment.TRIALS,
                                     self.clock)

    def __start_experiment_smallLandolt(self):
        """Starts the experimental for Miriam"""
        self.experimental_session = SessionLandoltSmall(self.inputdev.get(), # make custom session
                                     self.hand.get(),
                                     self.__get_screen_no(),
                                     self.spinbox_eyeheight.get(),
                                     Experiment.WIN_SIZE,
                                     Experiment.WIN_COLOR,
                                     Experiment.MONITOR,
                                     Experiment.BLOCKS,
                                     Experiment.TRIALS,
                                     self.clock)

    def __start_practice_trials(self):
        """An experimental session with fewer trials and blocks"""
        self.practice_trials = SessionLandoltSmall(self.inputdev.get(),
                                          self.hand.get(),
                                          self.__get_screen_no(),
                                          self.spinbox_eyeheight.get(),
                                          Experiment.WIN_SIZE,
                                          Experiment.WIN_COLOR,
                                          Experiment.MONITOR,
                                          Experiment.PRACTICE_BLOCKS,
                                          Experiment.PRACTICE_TRIALS,
                                          self.clock)

    def __start_practice_trials_sword(self):
        """An experimental session with fewer trials and blocks"""
        self.practice_trials = SessionSword(self.inputdev.get(),
                                          self.hand.get(),
                                          self.__get_screen_no(),
                                          self.spinbox_eyeheight.get(),
                                          Experiment.WIN_SIZE,
                                          Experiment.WIN_COLOR,
                                          Experiment.MONITOR,
                                          Experiment.PRACTICE_BLOCKS,
                                          Experiment.PRACTICE_TRIALS,
                                          self.clock)

    def __get_screen_no(self):
        """Returns 0 Default Screen, 1 Secondary Screen (Beamer)"""
        return (self.screen.get() == "Beamer")

    def __save(self):
        """Opens a Save As Dialogue and saves all data to a file"""
        if self.__has_experiment() or self.__has_practice_trials():

            file = asksaveasfile(mode='w', defaultextension=".txt")

            # Header
            header = self.__create_header()
            file.writelines('\t'.join(str(j) for j in i) + '\n' for i in header)

            # Head calibration timer
            if self.__has_head_calibration():
                file.writelines('Head Calibration: ' +
                                str(self.timer_head_calibration[0]) + ' ' +
                                str(self.timer_head_calibration[1]) + '\n')

            # Motor trials
            if self.__has_motor_trials():
                file.writelines('# motor trials\n')
                file.writelines('\t'.join(str(j) for j in i) +
                                '\n' for i in self.motor_trials.get_var_names())
                file.writelines('\t'.join(str(j) for j in i) +
                                '\n' for i in self.motor_trials.get_data())

            # Write practice trials if practice data available
            if self.__has_practice_trials():
                file.writelines('# practice trials\n')
                legend = self.practice_trials.get_var_names()
                file.writelines('\t'.join(str(j) for j in i) +
                                '\n' for i in legend)
                practice_data = self.practice_trials.get_data()
                file.writelines('\t'.join(str(j) for j in i) +
                                '\n' for i in practice_data)

            # Write experimental trials if practice data available
            if self.__has_experiment():
                file.writelines('# experimental trials\n')
                legend = self.experimental_session.get_var_names()
                file.writelines('\t'.join(str(j) for j in i) +
                                '\n' for i in legend)
                data = self.experimental_session.get_data()
                file.writelines('\t'.join(str(j) for j in i) +
                                '\n' for i in data)
            file.close()
        else:
            string = "Experiment has not started, no data to save!"
            tkMessageBox.showinfo("Save As...", string)

    def __create_header(self):
        """Help method to prepare the header of the data file."""
        title = ["# pvrtask data file"]
        # Adjust number of header lines if you change this method
        header_lines = ["# header_lines: 8"]
        id = ["Subject ID:", self.idvar.get()] # 1
        date = ["Date:", self.today_string] # 2
        year = ["Year of Birth:", self.birthyear.get()] # 3
        sex = ["Sex:", self.sex.get()] # 4
        hand = ["Handedness:", self.hand.get()] # 5
        group = ["Group:", self.group.get()] # 6
        eyeheight = ["Eye Height:", self.spinbox_eyeheight.get()] # 7

        return [title, header_lines, id, date,
                year, sex, hand, group, eyeheight]

    def __new_id(self):
        """Creates a new random Subject ID."""
        self.idvar.set(self.id_generator.get_id())

    def __has_experiment(self):
        """Checks if the experimental session was run."""
        return (self.experimental_session != None)

    def __has_head_calibration(self):
        """Checks if head calibration was run."""
        return (self.timer_head_calibration != None)

    def __has_practice_trials(self):
        """Checks if the practice tials were run."""
        return (self.practice_trials != None)

    def __has_motor_trials(self):
        """Checks if the motor tials were run."""
        return (self.motor_trials != None)

    def __start_motor_trials(self):
        """Runs motor trials..."""
        self.motor_trials = MotorTrials(self.inputdev.get(),
                                        self.hand.get(),
                                        self.__get_screen_no(),
                                        self.spinbox_eyeheight.get(),
                                        Experiment.WIN_SIZE,
                                        Experiment.WIN_COLOR,
                                        Experiment.MONITOR,
                                        self.clock)

    def __start_head_calibration(self):
        """Shows head calibration screen. Uses a TTL Signal to mark head
        calibration in data file."""
        TTL_ON = 0x1
        TTL_OFF = 0x0
        win = visual.Window(size=Experiment.WIN_SIZE,
                            monitor=Experiment.MONITOR,
                            units="deg",
                            color=Experiment.WIN_COLOR,
                            screen=self.__get_screen_no())
        win.flip(clearBuffer = True)

        pos = Position("central", self.spinbox_eyeheight.get())
        point_central = Point(win, pos.get_fixcross_position())

        # Wait until space is pressed
        while True:
            key = event.getKeys(keyList = Experiment.KBOARD_SPACE)
            if len(key) > 0:
                break

        point_central.draw()
        point_central.clearTextures()
        win.flip(clearBuffer = True)
        portio.outb(TTL_ON, 0x378)
        time_head_calibration_start = self.clock.getTime()
        time.sleep(2)
        portio.outb(TTL_OFF, 0x378)
        time_head_calibration_end = self.clock.getTime()
        self.timer_head_calibration = [time_head_calibration_start,
                                       time_head_calibration_end]
        win.close()

    def __show_stimuli_screen(self):
        """Shows stimuli test screen."""
        win = visual.Window(size=Experiment.WIN_SIZE,
                            monitor=Experiment.MONITOR,
                            units="deg",
                            color=Experiment.WIN_COLOR,
                            screen=self.__get_screen_no())
        win.flip(clearBuffer = True)

        pos = Position("central", self.spinbox_eyeheight.get())
        point_central = Point(win, pos.get_fixcross_position())
        point_left = Point(win, pos.get_left_position())
        point_right = Point(win, pos.get_right_position())

        stimuli = StimuliLandoltSmall(win, self.spinbox_eyeheight.get())
        cent = stimuli.get_central_stimuli()
        peri = stimuli.get_peripheral_stimuli()

        # Squares
        cent[0].draw()
        peri[0].draw()
        peri[1].draw()

        #Landolts
        cent[2].draw()
        peri[4].draw()
        peri[5].draw()

        #Small Landolt
        cent[4].draw()
        peri[8].draw()
        peri[9].draw()

        # draw horizontal and vertical line for adjustment of
        # the beamer to the screen.
        vertical_vertices = [[0, -12], [0, 12]]
        vertical_vertices_left = [[pos.get_left_position()[0], -12],
                                  [pos.get_left_position()[0], 12]]
        vertical_vertices_right = [[pos.get_right_position()[0], -12],
                                   [pos.get_right_position()[0], 12]]

        horizontal_vertices = [[-9, 0], [9, 0]]
        vertical_line = visual.ShapeStim(win,
                                         vertices=vertical_vertices,
                                         pos=[0, 0])
        vertical_line_left = visual.ShapeStim(win,
                                              vertices=vertical_vertices_left,
                                              pos=[0, 0])
        vertical_line_right = visual.ShapeStim(win,
                                               vertices=vertical_vertices_right,
                                               pos=[0, 0])
        horizontal_line = visual.ShapeStim(win,
                                           vertices=horizontal_vertices,
                                           pos=[0, 0])
        vertical_line.draw()
        vertical_line_left.draw()
        vertical_line_right.draw()
        horizontal_line.draw()

        point_central.draw()
        point_central.clearTextures()
        point_left.draw()
        point_left.clearTextures()
        point_right.draw()
        point_right.clearTextures()

        win.flip(clearBuffer = True)

        # Press any key to close testscreen
        while True:
            key = event.getKeys(keyList = Experiment.KBOARD_SPACE)
            if len(key) > 0:
                win.close()
                break

    def __start_eye_calibration(self):
        """Shows eye calibration screen."""

        # width = 5.0 # Width of calibration area 2x10 deg.
        width = 13.15 # Width of calibration area 2x25 deg.

        height = 3.75 # Height of calibration area 15 deg.
        win = visual.Window(size=Experiment.WIN_SIZE,
                            monitor=Experiment.MONITOR,
                            units="deg",
                            color=Experiment.WIN_COLOR,
                            screen=self.__get_screen_no())
        win.flip(clearBuffer = True)
        # likewise to the fixationt cross, the calibration points
        # are displayed at the subject's eye height
        pos = Position("central", self.spinbox_eyeheight.get())
        p_0 = [0, Experiment.CALIBRATION_HEIGHT] # point 1
        assert p_0[0] == 0 # check x of p0 is in the center of x-axis

        # Position p of points 1-13 indexed 0-12
        points = []
        points.append(p_0) # Point 1
        points.append([p_0[0] - width/2, p_0[1] + height/2]) # Point 2
        points.append([p_0[0] + width/2, p_0[1] + height/2]) # Point 3
        points.append([p_0[0] - width/2, p_0[1] - height/2]) # Point 4
        points.append([p_0[0] + width/2, p_0[1] - height/2]) # Point 5
        points.append([p_0[0] - width/2, p_0[1]]) # Point 6
        points.append([p_0[0], p_0[1] + height/2]) # Point 7
        points.append([p_0[0] + width/2, p_0[1]]) # Point 8
        points.append([p_0[0], p_0[1] - height/2]) # Point 9
        points.append([p_0[0] - width/4, p_0[1] + height/4]) # Point 10
        points.append([p_0[0] + width/4, p_0[1] + height/4]) # Point 11
        points.append([p_0[0] - width/4, p_0[1] - height/4]) # Point 12
        points.append([p_0[0] + width/4, p_0[1] - height/4]) # Point 13

        # create fixation points f of points 1-13
        fixation_points = []
        for point in points:
            fixation_points.append(Point(win, point))

        for fixation_point in fixation_points:
            fixation_point.draw()

        win.flip(clearBuffer = True)

        # Draw 13-point calibration screen, one after the other
        cancel = False
        for fixation_point in fixation_points:
            if cancel:
                break

            while True:
                key = event.getKeys(keyList = [Experiment.KBOARD_TOGGLE,
                                               Experiment.KBOARD_QUIT])
                if len(key) > 0:
                    if key[0] == Experiment.KBOARD_QUIT:
                        cancel = True
                        break
                    fixation_point.draw()
                    win.flip(clearBuffer = True)
                    break

        for fixation_point in fixation_points:
            fixation_point.clearTextures()

        # Close window
        while True:
            key = event.getKeys(keyList = [Experiment.KBOARD_TOGGLE,
                                           Experiment.KBOARD_QUIT])
            if cancel or len(key) > 0:
                win.close()
                break

class Point(visual.PatchStim):
    "Fixational point"

    SIZE = 0.15

    def __init__(self, window, position, rgb = [1, 1, 1]):

        visual.PatchStim.__init__(self, window, color=rgb, tex=None,
                                  mask='circle', size=Point.SIZE, pos=position)

class MotorTrials:
    """Motor Trials to test Subject's motoric skills"""

    TTL_ON = 0x2
    TTL_OFF = 0x0
    TTL_DURATION = 0.050 # 50 ms is fine for 50Hz and 200Hz Tracking
    FIX_CROSS_DUR = 2.0
    STIM_DUR = 2.0
    KBOARD_ANSWER_LEFT = 'n'
    KBOARD_ANSWER_RIGHT = 'm'
    KBOARD_ANSWER_QUIT = 'q'
    BBOX_ANSWER_LEFT = 0x3f
    # BBOX_ANSWER_MIDDLE = 0x5f
    BBOX_ANSWER_RIGHT = 0x6f

    def __init__(self, input_device, handedness, screen, eyeheight,
                 win_size, win_color, monitor, clock):

        self.input_device = input_device
        self.handedness = handedness
        self.clock = clock
        self.win = visual.Window(size=win_size,
                                 monitor=monitor,
                                 units="deg",
                                 color=win_color,
                                 screen=screen)
        self.win.flip(clearBuffer = True)
        # create stimuli
        stimuli = Stimuli(self.win, eyeheight)
        self.central_stimuli = stimuli.get_central_stimuli()
        self.fix_point = stimuli.get_fixation_cross()

        # Each of the 4 cental stimulus is presented 4 times
        self.sequence = [0, 0, 0, 0,
                         1, 1, 1, 1,
                         2, 2, 2, 2,
                         3, 3, 3, 3,]
        random.shuffle(self.sequence)

        self.data = list()
        self.__show_instructions()
        self.__run()

    def __show_instructions(self):

        text = """
        Sie werden einen Punkt sehen. Jedesmal wenn ein farbiges
        Quadrat oder ein C erscheint, muessen sie sofort mit dem
        Zeigefinger druecken.

        Versuchen Sie, so schnell wie moeglich zu druecken!

        Wenn Sie bereit sind, druecken Sie dir rote Taste, um das
        Experiment zu beginnen. Ansonsten fragen sie den
        Versuchsleiter.

        """
        instructions = visual.TextStim(self.win, text=text,
                                       height=0.5, font='FreeSans')
        instructions.draw()
        self.win.flip(clearBuffer = True)

        event.clearEvents(eventType = None)
        while True:
            key = event.getKeys(keyList = Session.KBOARD_SPACE)
            button = portio.inb(0x379)
            if len(key) > 0 or button == Session.BBOX_ANSWER_MIDDLE:
                self.win.flip(clearBuffer = True)
                break

    def __run(self):

        trial_nr = 1

        for i in self.sequence:

            # Start of the trial
            trial_start = self.clock.getTime()
            portio.outb(Trial.TTL_ON, 0x378)
            time.sleep(Trial.TTL_DURATION)
            portio.outb(Trial.TTL_OFF, 0x378)

            # Fixation point
            self.fix_point.draw()
            self.win.flip(clearBuffer = True)
            fix_cross_on = self.clock.getTime()
            time.sleep(MotorTrials.FIX_CROSS_DUR)

            # Stimulus
            self.central_stimuli[i].draw()
            self.win.flip(clearBuffer = True)
            stimulus_on = self.clock.getTime()
            is_stim_on = True

            # Get user response
            event.clearEvents(eventType = None)
            while True:

                response_box = portio.inb(0x379)
                response_keyb = event.getKeys(keyList =
                                              [MotorTrials.KBOARD_ANSWER_LEFT,
                                               MotorTrials.KBOARD_ANSWER_RIGHT,
                                               MotorTrials.KBOARD_ANSWER_QUIT])

                # Flip stimulus when stimulus duration is reached before
                # subject response. This is perfomed only once using the
                # boolean is_stim_on.
                if (is_stim_on and
                    self.clock.getTime() - stimulus_on >= MotorTrials.STIM_DUR):
                    self.win.flip(clearBuffer = True)
                    stimulus_off = self.clock.getTime()
                    is_stim_on = False

                # Get reaction time
                if (response_box == MotorTrials.BBOX_ANSWER_LEFT or
                    response_box == MotorTrials.BBOX_ANSWER_RIGHT or
                    len(response_keyb) > 0):
                    response_time = self.clock.getTime() - stimulus_on
                    break

            # Flip stimulus when stimulus duration is reached
            # after subject response
            if is_stim_on:
                while True:
                    if (self.clock.getTime() -
                        stimulus_on >= MotorTrials.STIM_DUR):
                        self.win.flip(clearBuffer = True)
                        stimulus_off = self.clock.getTime()
                        break

            # Check if the quit key was pressed
            if (response_keyb != [] and
                response_keyb[0] == MotorTrials.KBOARD_ANSWER_QUIT):
                break

            if self.input_device == "Keyboard":
                response = response_keyb[0] # We only take the first key pressed
            elif  self.input_device == "Response Box":
                response = response_box

            # Assign response box response
            if response == MotorTrials.BBOX_ANSWER_RIGHT:
                response = "button_right"
            elif response == MotorTrials.BBOX_ANSWER_LEFT:
                response = "button_left"

            timer = [trial_nr,
                     trial_start,
                     self.central_stimuli[i].get_name(),
                     self.central_stimuli[i].get_type(),
                     self.central_stimuli[i].get_position(),
                     fix_cross_on,
                     stimulus_on,
                     stimulus_off,
                     response,
                     response_time]

            print timer
            self.data.append(timer)

            trial_nr = trial_nr + 1

        self.fix_point.clearTextures()
        self.win.close()

    def get_data(self):
        return self.data

    def get_var_names(self):
        """Gets the variable names."""
        # This has to match the timer of the MotorTrials object
        return [['trial_nr',
                 'trial_start',
                 'stimulus_name',
                 'stimulus_type',
                 'stimulus_position',
                 'fixation_point_on',
                 'stimulus_on',
                 'stimulus_off',
                 'response',
                 'response_time']]

def check_root():
    """Check for root privileges"""
    if os.getuid():
        print 'You need to be root! Exiting.'
        time.sleep(2)
        sys.exit()

def init_parport():
    """Acquire permission for I/O on lp0"""
    status_a = portio.ioperm(0x378, 1, 1)
    status_b = portio.ioperm(0x379, 1, 1)
    if status_a and status_b:
        print 'ioperm 0x378:', os.strerror(status_a)
        print 'ioperm 0x379:', os.strerror(status_b)
        sys.exit()

    portio.outb(0x0, 0x378)

def exit_program():
    """Program exit"""
    core.quit()

# Run application
check_root()
init_parport()
Experiment()
