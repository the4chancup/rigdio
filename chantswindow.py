from tkinter import *
from config import settings

import os.path, vlc, threading, time

# chants window class
class chantswindow(Toplevel):
   def __init__(self, parent, chantsManager):
      super().__init__(parent)
      self.chantsManager = chantsManager

      # inserts the UI frame into the window
      self.chantsFrame = ChantsFrame(self, self.chantsManager)
      self.chantsFrame.pack()

      self.title("Manual Chants")
      # Change what happens when you click the X button
      # This is done so changes also reflect in the main window class
      self.protocol('WM_DELETE_WINDOW', parent.close)

# UI frame for the window
class ChantsFrame(Frame):
   def __init__(self, parent, chantsManager):
      Frame.__init__(self, parent)
      self.chantsManager = chantsManager

      Label(self, text="Chants Volume").grid(columnspan=2)
      # volume slider
      self.chantVolume = Scale(self, from_=0, to=100, orient=HORIZONTAL, command=self.adjustVolume, showvalue=0, length = 150)
      self.chantVolume.set(80)
      self.chantVolume.grid(row=1, columnspan=2)
      # blank space between volume slider and chant buttons to separate them, make it look nicer
      Label(self, text=None).grid(columnspan=2)

      # chants lists to replace buttons when new chants are loaded
      self.homeChantsList = list()
      self.awayChantsList = list()
      self.createChants(self.chantsManager.homeChants is not None, self.chantsManager.awayChants is not None)

      # chant that is currently being played
      self.activeChant = None

      # used to end the checkChantDone thread early
      self.endThreadEarly = False

   def createChants (self, home = False, away = False):
      if home:
         # if there are already chants in the window, delete them
         if self.homeChantsList:
            for chant in self.homeChantsList:
               chant.playButton.destroy()
            self.homeChantsList.clear()

         chants = self.chantsManager.homeChants
         for i in range(len(chants)):
            chantName = os.path.basename(chants[i].songname)
            self.chantsButton = ChantsButton(self, chants[i], chantName, chants[i].home)
            self.homeChantsList.append(self.chantsButton)
            self.chantsButton.insert(i+3)
      if away:
         # if there are already chants in the window, delete them
         if self.awayChantsList:
            for chant in self.awayChantsList:
               chant.playButton.destroy()
            self.awayChantsList.clear()

         chants = self.chantsManager.awayChants
         for i in range(len(chants)):
            chantName = os.path.basename(chants[i].songname)
            self.chantsButton = ChantsButton(self, chants[i], chantName, chants[i].home)
            self.awayChantsList.append(self.chantsButton)
            self.chantsButton.insert(i+3)

   def adjustVolume (self, value):
      # shoves all of the chants into a single list
      self.allChants = self.homeChantsList + self.awayChantsList

      # adjusts the volume of all the chants at the same time
      if self.allChants:
         for chantButton in self.allChants:
            chantButton.chant.adjustVolume(value)

# creates and manages the chant buttons
class ChantsButton:
   def __init__ (self, frame, chant, text, home):
      self.chant = chant
      self.frame = frame
      self.text = text
      self.home = home

      # how long a chant can be played for until it begins to fade out
      self.fadeOutTime = 25
      self.playButton = Button(frame, text=self.text, command=self.playChant, bg=settings.colours["home" if self.home else "away"])

   def playChant (self):
      # if there is already a chant going on, ignore command
      if self.frame.activeChant is not None:
         print("Denied, chant currently playing")
      else:
         # otherwise, set this chant as the active chant and begin playing
         self.playButton.configure(relief=SUNKEN)
         self.frame.activeChant = self.chant
         self.chantEndCheck = threading.Thread(target=self.checkChantDone)
         self.chant.reloadSong()
         self.chant.play()
         print("Chant now playing")
         self.chantEndCheck.start()

   # checks when the chant is done or playing too long
   def checkChantDone (self):
      self.chantStart = time.time()
      while self.chantEndCheck is not None:
         if self.frame.endThreadEarly:
            self.chantEndCheck = None
            break
         
         if self.chant.song.get_media().get_state() == vlc.State.Ended:
            self.chantDone()
            self.chantEndCheck = None
         elif (time.time() - self.chantStart) > self.fadeOutTime:
            print("Chant timed out, fade starting")
            self.chant.fade = True
            self.chant.fadeOut()
            self.chantDone()
            self.chantEndCheck = None

   # clears out the activeChant variable once the chant is over
   def chantDone (self):
      if self.frame.activeChant is not None:
         print("Chant {} concluded.".format(self.text))
         self.playButton.configure(relief=RAISED)
         self.frame.activeChant = None

   def insert (self, row):
      self.playButton.grid(row=row, column=0 if self.home else 1)

class ChantsManager:
   def __init__ (self, window):
      self.window = window

      # stores chant information
      self.homeChants = None
      self.awayChants = None

   def setHome (self, filename=None, parsed=None):
      if parsed is not None:
         self.homeChants = parsed
         if (self.window is not None):
            self.window.chantsFrame.createChants(home = True)
      else:
         print("No chants received for home team.")
         self.homeChants = None

   def setAway (self, filename=None, parsed=None):
      if parsed is not None:
         self.awayChants = parsed
         if (self.window is not None):
            self.window.chantsFrame.createChants(away = True)
      else:
         print("No chants received for away team.")
         self.awayChants = None