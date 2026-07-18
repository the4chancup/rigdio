from condition import *
from os.path import splitext, dirname, abspath
import os, sys
os.environ["PATH"] = dirname(abspath(sys.argv[0])) + os.pathsep + os.environ["PATH"]
import mpv
import random, time

# Cache of playback positions (in ms) keyed by absolute file path.
# Used by sync-enabled goalhorns to preserve playback position
# across different ConditionPlayer instances with the same filename,
# without sharing a single MediaPlayer object (which caused concurrency bugs).
_position_cache = {}

class ConditionList:
   def __init__(self, pname = "NOPLAYER", tname = "NOTEAM", data = [], songname = "New Song", home = True, runInstructions = True):
      self.pname = pname
      self.tname = tname
      self.home = home
      self.songname = songname
      self.conditions = []
      self.instructions = []
      self.disabled = False
      self.startTime = 0
      self.event = None
      self.endType = "loop"
      self.pauseType = "continue"
      for tokenStr in data:
         tokens = processTokens(tokenStr)
         condition = buildCondition(tokens, pname=self.pname, tname=self.tname, home=self.home)
         if condition.isInstruction():
            self.instructions.append(condition)
         else:
            self.conditions.append(condition)
      self.all = self.conditions + self.instructions
      if runInstructions:
         self.instruct()

   def __str__(self):
      output = "{}".format(basename(self.songname))
      for condition in self.conditions:
         output = output + ";" + str(condition)
      for instruction in self.instructions:
         output = output + ";" + str(instruction)
      return output

   def __repr__ (self):
      pname = self.pname
      tname = self.tname
      data = str(self).split(";")[1:]
      songname = self.songname
      home = self.home
      output = "ConditionList(pname={},tname={},data={},songname={},home={})"
      return output.format(pname,tname,data,songname,home)

   def __len__ (self):
      return len(self.all)

   def __iter__ (self):
      return self.all.__iter__()

   def __getitem__ (self, key):
      return self.all[key]

   def __setitem__ (self, key, value):
      temp = self.all[key]
      if temp.isInstruction():
         index = self.instructions.index(temp)
         self.instructions[index] = value
      else:
         index = self.conditions.index(temp)
         self.conditions[index] = value
      # insert new value where it was
      self.all[key] = value

   def instruct (self):
      for instruction in self.instructions:
         if instruction.allowUnloaded():
            print("Preparing {} instruction".format(instruction))
            instruction.prep(self)

   def append (self, item):
      self.all.append(item)
      if item.isInstruction():
         self.instructions.append(item)
      else:
         self.conditions.append(item)

   def disable (self):
      self.disabled = True

   def pop (self, index = 0):
      item = self.all.pop(index)
      if item.isInstruction():
         self.instructions.remove(item)
      else:
         self.conditions.remove(item)
      return item

   def check (self, gamestate):
      if self.disabled:
         raise UnloadSong
      for condition in self.conditions:
         print("Checking {}".format(condition))
         if not condition.check(gamestate):
            return False
      return True

   def toYML (self):
      # with no conditions, simply return song name
      if len(self.all) == 0:
         return basename(self.songname)
      # otherwise, store filename in dict
      output = {}
      output["filename"] = basename(self.songname)
      output["conditions"] = []
      for item in self.conditions:
         output["conditions"].append(item.toYML())
      output["instructions"] = []
      for item in self.instructions:
         output["instructions"].append(item.toYML())
      return output

class ConditionPlayer (ConditionList):
   def __init__ (self, pname, tname, data, songname, home, type = "goalhorn", sync = False):
      ConditionList.__init__(self,pname,tname,data,songname,home,False)
      self.type = type
      self.isGoalhorn = type=="goalhorn"
      self.sync = sync
      self.song = self.loadsong(songname)
      self.fade = None
      self.startTime = 0
      self.customSpeed = False
      self.firstPlay = True
      self.randomise = False
      self.warcry = False
      self.pauseType = "continue"
      self.instructionsStart = []
      self.instructionsPause = []
      self.instructionsEnd = []
      self.maxVolume = 80
      # repetition settings; may be changed by instructions
      norepeat = set(["victory","chant"])
      self.repeat = (pname not in norepeat)
      # append and prepare the instructions to this object
      self.appendInstructions()
      self.instruct()
      # songs with a set start time require manual looping so that it loops back to the set time
      setStartTime = any(isinstance(instruction, StartInstruction) for instruction in self.instructionsStart)
      self.manualLoop = setStartTime
      self._configureLooping()

   def _configureLooping (self):
      # configure native looping for repeat-enabled songs;
      # called both at init and after reloadSong since each player is separate
      if self.repeat and self.event is None and isinstance(self.song, mpv.MPV) and not self.manualLoop:
         self.song.loop_file = "inf"

   def appendInstructions (self):
      for instruction in self.instructions:
         print("Appending {} instruction".format(instruction))
         instruction.append(self)

   def instruct (self):
      for instruction in self.instructions:
         print("Preparing {} instruction".format(instruction))
         instruction.prep(self)

   def loadsong(self, filename):
      print("Attempting to load "+filename)
      fullpath = abspath(filename)

      # if song cannot be found, return error message instead of MediaPlayer
      # reason is to have rigdio check for all missing files before raising exception
      if not isfile(fullpath):
         return basename(fullpath) + " not found."
      # vid=False prevents video tracks; pause=True keeps file paused until play()
      # keep_open=True prevents idle mode after EOF (matches ended state behavior)
      player = mpv.MPV(vid=False, pause=True, keep_open=True)
      player.loadfile(fullpath)
      return player

   def reloadSong (self):
      self.firstPlay = True
      # clear saved position since we're resetting to the beginning
      _position_cache.pop(abspath(self.songname), None)
      self.song = self.loadsong(self.songname)
      self._configureLooping()
      self.instruct()

   def play (self):
      if self.fade is not None:
         print("Song played quickly after pause, cancelling fade.")
         thread = self.fade
         self.fade = None
         thread.join()
      self.song.pause = False
      self.song.volume = self.maxVolume
      # restore saved playback position for sync-enabled goalhorns
      if self.sync and self.isGoalhorn and not self.warcry and isinstance(self.song, mpv.MPV):
         fullpath = abspath(self.songname)
         if fullpath in _position_cache:
            self.song.time_pos = _position_cache[fullpath] / 1000.0
      if self.firstPlay:
         for instruction in self.instructionsStart:
            instruction.run(self)
         self.firstPlay = False

   def adjustVolume (self, value):
      self.maxVolume = int(value)
      self.song.volume = self.maxVolume

   def pause (self, fade=None):
      # save playback position for sync-enabled goalhorns before pausing
      if self.sync and self.isGoalhorn and not self.warcry and isinstance(self.song, mpv.MPV):
         pos = self.song.time_pos
         if pos is not None:
            _position_cache[abspath(self.songname)] = int(pos * 1000)
      if fade is None:
         fade = self.type in settings.fade and settings.fade[self.type]
      # don't fade out if the song has already ended (e.g. advance/warcry)
      if fade and not self.song.eof_reached:
         print("Fading out {}.".format(self.songname))
         self.fade = threading.Thread(target=self.fadeOut)
         self.fade.start()
      else:
         for instruction in self.instructionsPause:
            instruction.run(self)
         self.song.pause = True
         if self.song.eof_reached:
            self.reloadSong()

   def onEnd (self, callback):
      @self.song.event_callback('end-file')
      def _handler(event):
         callback()

   def fadeOut (self):
      # save playback position for sync-enabled goalhorns before fading out
      if self.sync and self.isGoalhorn and not self.warcry and isinstance(self.song, mpv.MPV):
         pos = self.song.time_pos
         if pos is not None:
            _position_cache[abspath(self.songname)] = int(pos * 1000)
      i = 100
      while i > 0:
         if self.fade == None:
            break
         volume = int(self.maxVolume * i/100)
         self.song.volume = volume
         sleep(settings.fade["time"]/100)
         i -= 1
      for instruction in self.instructionsPause:
         instruction.run(self)
      self.song.pause = True
      if self.song.eof_reached:
         self.reloadSong()
      self.song.volume = self.maxVolume
      self.fade = None

   def disable (self):
      self.song.command("stop")
      super().disable()

class PlayerManager:
   def __init__ (self, clists, home, game, master):
      # song information
      self.clists = clists
      self.home = home
      self.game = game
      # playerbutton information
      self.master = master
      # derived information
      self.song = None
      self.lastSong = None
      self.endChecker = None
      self.pname = clists[0].pname
      self.futureVolume = None
      self.warcry = True

   def __iter__ (self):
      for x in self.clists:
         yield x

   def adjustVolume (self, value):
      if self.song is not None:
         self.song.adjustVolume(value)
      self.futureVolume = value

   def getSong (self, song = None, skip = None):
      if song is not None:
         for clist in self.clists:
            if song == clist:
               return clist
      # iterate over songs with while loop
      i = 0
      while i < len(self.clists):
         # skip the song that just ended (advance instruction)
         if self.clists[i] is skip:
            i += 1
            continue
         # try to check the condition list
         try:
            checked = self.clists[i].check(self.game)
         # if a song will no longer be played, check will raise UnloadSong
         except UnloadSong:
            # disable the ConditionListPlayer, closing the song file
            self.clists[i].disable()
            # deleted
            del self.clists[i]
            # do not increment i, self.clists[i] is now the next song; continue
            continue
         # if randomise is true, check if all other songs have randomise true as well
         # do not count warcry songs
         if self.clists[i].randomise and not self.clists[i].warcry:
            f, randomSong = 0, True
            while f < len(self.clists):
               # if one of them is false and they're not a warcry, do not play a random song
               if not self.clists[f].randomise and not self.clists[f].warcry and self.clists[i].pname == self.clists[f].pname:
                  randomSong = False
                  break
               f += 1
            if randomSong:
               # copy the entire song list of that team
               x, randomList = 0, self.clists.copy()
               while x < len(randomList):
                  # traverse through and remove all songs that are not associated with the player clicked
                  # remove all warcry songs from the list as well
                  if self.clists[i].pname != randomList[x].pname or randomList[x].warcry:
                     randomList.pop(x)
                  else:
                     x += 1
               # reset the warcry variable so that warcry will play again when button is pressed
               self.warcry = True
               # return a randomly chosen song from the modified copied list
               return random.choice(randomList)
         # if conditions were met
         if checked:
            # if warcry is enabled, play the first song found, warcry included
            if self.warcry:
               return self.clists[i]
            # if a warcry has been played, play the first non-warcry song found
            else:
               if not self.clists[i].warcry:
                  # reset the warcry variable so that warcry will play again when button is pressed
                  self.warcry = True
                  return self.clists[i]
         # if the song didn't succeed, move to the next
         i += 1
      # fallback: if no valid song was found, play the first non-warcry song
      # that isn't the skipped one (advance instruction)
      if skip is not None:
         i = 0
         while i < len(self.clists):
            if self.clists[i] is skip:
               i += 1
               continue
            if not self.clists[i].warcry:
               self.warcry = True
               return self.clists[i]
            i += 1
         # final fallback: play the skipped song itself
         self.warcry = True
         return skip
      # if no song was found, return nothing
      return None

   def playSong (self, song = None, skip = None):
      # don't play multiple songs at once
      self.pauseSong()
      # get the song to play
      self.song = self.getSong(song, skip)
      # if volume was stored, update it
      if self.futureVolume is not None:
         self.song.adjustVolume(self.futureVolume)
      # check if no song was found
      if self.song is None:
         raise SongNotFound(self.pname)
      # log song
      print("Playing",self.song.songname)
      # a returnable value for whether this is the first time this song is played
      self.firstTime = self.song.firstPlay
      # play the song
      self.song.play()
      # start the end checker instruction thread
      if len(self.song.instructionsEnd) > 0 or (self.song.repeat and self.song.manualLoop):
         self.endChecker = threading.Thread(target=self.checkEnd)
         self.endChecker.start()
      # remove any data specific to this goal
      self.game.clearButtonFlags()
      # if the song is the victory anthem and not a warcry, start victory song duration timer
      if self.clists[0].pname == "victory" and not self.song.warcry:
         self.master.timer.retrieveSongInfo()

      # check if user has enabled write to title.log function
      if not self.song.warcry and settings.config["write_song_title_log"] > 0:
         global titleThread
         global titleCheck
         # if title timer thread already exists,
         # kill it and wait for it to die before creating a new one
         if titleCheck:
            titleCheck = False
            titleThread.join()
         titleThread = threading.Thread(target=self.writeTitleLog)
         titleThread.start()

      return self.firstTime

   def pauseSong (self):
      if self.song is not None:
         # clear end checker thread to prevent continuous running while paused
         self.endChecker = None
         # log pause
         print("Pausing",self.song.songname)
         # pause the song
         self.song.pause()
         # clear self.song
         self.lastSong = self.song
         self.song = None

   def checkEnd (self):
      while self.endChecker is not None:
         if self.song.song.eof_reached:
            if len(self.song.instructionsEnd) > 0:
               for instruction in self.song.instructionsEnd:
                  instruction.run(self)
               break

            if self.song.repeat and self.song.manualLoop:
               self.song.song.time_pos = 0
               sleep(0.05)
               self.song.song.pause = False
               self.song.song.volume = self.song.maxVolume
               for instruction in self.song.instructionsStart:
                  instruction.run(self.song)
               continue
         time.sleep(0.01)

   # if the song is currently playing or has been played, reset it
   def resetLastPlayed (self):
      if self.lastSong is not None or self.song is not None:
         self.pauseSong()
         self.lastSong.song.command("stop")
         self.lastSong.reloadSong()

   # writes currently playing song's details to title.log, clearing it after a set amount of time
   def writeTitleLog (self):
      print("Write title timer thread started.")
      global titleThread
      global titleCheck
      titleCheck = True
      # sleep delay needed for mpv to properly retrieve metadata
      sleep(1)
      # exit thread if it has been interrupted early
      if titleThread is None or not titleCheck:
         print("Write title timer thread ended early.")
         titleThread = None
         titleThread = False
         return

      # get metadata title and artist
      metadata = self.song.song.metadata or {}
      title = metadata.get("title")
      artist = metadata.get("artist")
      # music note to signify it's music or something (idk, it was requested)
      text = "♪ "
      # add artist details first if it's available
      if (artist is not None):
         text += artist + " — "
      try:
         # if a song doesn't have a metadata title, it returns the full filename including its path
         # hence it needs to be stripped before adding it to text
         if isfile(title):
            text += splitext(basename(title))[0]
         else:
            text += title
         # utf-8 encoding for weeb characters
         with open("title.log", 'w', encoding='utf8') as file:
            file.write(text)
      # if title could not be written in for some reason, use the filename instead
      except:
         path = self.song.song.path or ""
         text += splitext(basename(path))[0]
         with open("title.log", 'w', encoding='utf8') as file:
            file.write(text)

      timerStart = time.time()
      while titleThread is not None:
         # exit loop if thread has been interrupted, song has ended, or timer has run out
         if (not titleCheck or self.song is None or
               self.song.song.eof_reached or
               (time.time() - timerStart) > settings.config["write_song_title_log"]):
            break
         time.sleep(0.01)

      # clear title.log and exit thread
      print("Write title timer thread ended.")
      with open("title.log", 'w') as file:
         file.write("")
      titleThread = None
      titleCheck = False

# global variables for the title timer thread
# required as they need to be accessed across different PlayerManager instances
titleThread = None
titleCheck = False
