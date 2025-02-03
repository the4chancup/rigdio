from tkinter import *
from config import settings

import os.path, vlc, threading, time, random

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
      # When the window is destroyed, end the chant thread early
      self.bind("<Destroy>", self.chantsFrame.endThread)

# UI frame for the window
class ChantsFrame(Frame):
   def __init__(self, parent, chantsManager):
      Frame.__init__(self, parent)
      self.chantsManager = chantsManager
      
      # volume slider
      Label(self, text="Chants Volume").grid(columnspan=2)
      self.chantVolume = Scale(self, from_=0, to=100, orient=HORIZONTAL, command=self.adjustVolume, showvalue=0, length = 150)
      self.chantVolume.set(80)
      self.chantVolume.grid(columnspan=2)
      # blank space between the sliders and chant buttons to separate them, make it look nicer
      Label(self, text=None).grid(columnspan=2)

      # chant timer checkbox, for if the user
      self.timerCheckbox = IntVar(value=1)
      self.enableTimerCheckbox = Checkbutton(self, text="Enable Timer", variable = self.timerCheckbox, command=self.enableTimer)
      self.enableTimerCheckbox.grid(columnspan=2)

      self.chantTimerText = Label(self, text="Chants Timer")
      self.chantTimerText.grid(columnspan=2)

      # chant timer slider
      self.chantTimer = Scale(self, from_=20, to=60, orient=HORIZONTAL, command=self.adjustTimer, resolution=5, showvalue=1, length = 150)
      self.chantTimer.set(30)
      self.chantTimer.grid(columnspan=2)
      # blank space between the sliders and chant buttons to separate them, make it look nicer
      Label(self, text=None).grid(columnspan=2)

      # chants lists to replace buttons when new chants are loaded
      self.homeChantsList = list()
      self.awayChantsList = list()
      self.createChants(self.chantsManager.homeChants is not None, self.chantsManager.awayChants is not None)

      # chant that is currently being played
      self.activeChant = None

      # used to end the checkChantDone thread early
      self.endThreadEarly = False

      # used to check if program is using the timer
      self.usingTimer = True

   def endThread (self, event):
      self.endThreadEarly = True

   # creates the chant buttons
   def createChants (self, home = False, away = False):
      if home:
         self.clearChantList(self.homeChantsList)
         
         if self.chantsManager.homeChants is not None:
            chants = self.chantsManager.homeChants
            # a chant button that plays a random chant when it's pressed
            self.randomChant = ChantsButton(self, chants, "Random", True, True)
            self.randomChant.insert(8)

            for i in range(len(chants)):
               chantName = os.path.basename(chants[i].songname)
               self.chantsButton = ChantsButton(self, chants[i], chantName, chants[i].home)
               self.homeChantsList.append(self.chantsButton)
               self.chantsButton.insert(i+9)
      if away:
         self.clearChantList(self.awayChantsList)

         if self.chantsManager.awayChants is not None:
            chants = self.chantsManager.awayChants
            # a chant button that plays a random chant when it's pressed
            self.randomChant = ChantsButton(self, chants, "Random", False, True)
            self.randomChant.insert(8)

            for i in range(len(chants)):
               chantName = os.path.basename(chants[i].songname)
               self.chantsButton = ChantsButton(self, chants[i], chantName, chants[i].home)
               self.awayChantsList.append(self.chantsButton)
               self.chantsButton.insert(i+9)

   # clears out chants in the window
   def clearChantList (self, chantList):
      if chantList:
         for chant in chantList:
            chant.playButton.destroy()
         chantList.clear()

   def adjustVolume (self, value):
      # shoves all of the chants into a single list
      self.allChants = self.homeChantsList + self.awayChantsList

      # adjusts the volume of all the chants at the same time
      if self.allChants:
         for chantButton in self.allChants:
            chantButton.chant.adjustVolume(value)

   def adjustTimer (self, value):
      # shoves all of the chants into a single list
      self.allChants = self.homeChantsList + self.awayChantsList

      # adjusts the fade out timer of all the chants at the same time
      if self.allChants:
         for chantButton in self.allChants:
            chantButton.fadeOutTime = float(value)

   # used to enable/disable the use of the timer for chants, greys out and disables the text and slider to show it better
   def enableTimer (self):
      value = self.timerCheckbox.get()
      self.usingTimer = False if value == 0 else True

      self.chantTimerText["fg"] = 'grey' if value == 0 else 'black'

      self.chantTimer["state"] = DISABLED if value == 0 else NORMAL
      self.chantTimer["fg"] = 'grey' if value == 0 else 'black'

   # used to disable the use of the timer stuff when a chant is playing, to prevent the user from messing with it during a chant and causing problems
   def disableChantTimer(self, disable):
      self.enableTimerCheckbox["state"] = DISABLED if disable else NORMAL
      self.enableTimerCheckbox["fg"] = 'grey' if disable else 'black'

      # if user is not using the timer in the first place, don't touch the text and slider
      if self.usingTimer:
         self.chantTimerText["fg"] = 'grey' if disable else 'black'
         
         self.chantTimer["state"] = DISABLED if disable else NORMAL
         self.chantTimer["fg"] = 'grey' if disable else 'black'

# creates and manages the chant buttons
class ChantsButton:
   def __init__ (self, frame, chant, text, home, random = False):
      # used to randomize the chant by having the argument take in the list of chants instead
      if random and isinstance(chant, list):
         self.chantList = chant
      self.chant = chant
      self.frame = frame
      self.text = text
      self.home = home
      self.random = random

      self.playButton = Button(frame, text=self.text, command=self.playChant, bg=settings.colours["home" if self.home else "away"])

   def playChant (self):
      # if there is already a chant going on, ignore command
      if self.frame.activeChant is not None:
         print("Denied, chant currently playing")
      else:
         # randomly pick a chant from the list and set as this button's chant
         if (self.random):
            self.chant = random.choice(self.chantList)
         # otherwise, set this chant as the active chant and begin playing
         self.playButton.configure(relief=SUNKEN)
         self.frame.activeChant = self.chant
         self.chantEndCheck = threading.Thread(target=self.checkChantDone)
         self.chant.reloadSong()
         self.chant.play()
         print("Chant now playing")
         print("Chant Timer: {} seconds ".format(str(self.frame.chantTimer.get())))
         # while greying out the timer stuff and starting the chant end checker thread
         self.frame.disableChantTimer(True)
         self.chantEndCheck.start()

   # checks when the chant is done or playing too long
   def checkChantDone (self):
      self.chantStart = time.time()
      while self.chantEndCheck is not None:
         # stops and resets the active chant
         if self.frame.endThreadEarly:
            print("Window closed")
            self.chant.song.stop()
            self.chant.fade = None
            self.frame.activeChant = None
            self.chantEndCheck = None
         
         if self.chant.song.get_media().get_state() == vlc.State.Ended:
            self.chantDone()
            self.chantEndCheck = None
         # checks if the user is even using the timer in the first place as well
         elif self.frame.usingTimer and (time.time() - self.chantStart) > self.frame.chantTimer.get():
            print("Chant timed out, fade starting")
            self.chant.fade = True
            self.chant.fadeOut()
            self.chantDone()
            self.chantEndCheck = None

   # clears out the active chant variable once the chant is over
   def chantDone (self):
      if self.frame.activeChant is not None:
         self.playButton.configure(relief=RAISED)
         self.frame.activeChant = None
         print("Chant {} concluded.".format(self.text))
         self.frame.disableChantTimer(False)

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
      else:
         print("No chants received for home team.")
         self.homeChants = None
         
      if (self.window is not None):
         self.window.chantsFrame.createChants(home = True)


   def setAway (self, filename=None, parsed=None):
      if parsed is not None:
         self.awayChants = parsed
      else:
         print("No chants received for away team.")
         self.awayChants = None
         
      if (self.window is not None):
         self.window.chantsFrame.createChants(away = True)