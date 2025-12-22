from version import riglevel_version as version
from tkinter import *
import tkinter.messagebox as messagebox
from config import settings, openConfig, applyDarkMode

import os
from threading import Thread
from glob import glob
from pydub import AudioSegment
from pydub.utils import mediainfo

from tkinter import ttk
import tkinter.filedialog as filedialog

from logger import startLog
if __name__ == '__main__':
   # allow/forbid riglevel to write to log depending on user's configs
   if settings.config["write_to_log"]:
      startLog("riglevel.log")
   print("riglevel {}".format(version))

class Riglevel (Frame):
   def __init__(self, master):
      super().__init__(master)
      colours = settings.darkColours if settings.config["dark_mode_enabled"] else settings.lightColours
      Label(self, text="Use this program to normalize music sound levels.").grid(columnspan=2)
      Label(self, text="").grid(row=1)

      # text box widget to change normalized export type (default is MP3)
      typeFrame = Frame(self)
      typeFrame.grid(row=2, columnspan=2)

      Label(typeFrame, text="Normalized export type: ").pack(side=LEFT)
      self.exportType = StringVar()
      self.exportType.set("mp3")
      Radiobutton(typeFrame, text = "MP3", variable = self.exportType, value = "mp3", selectcolor=colours["bg"]).pack(side=LEFT)
      Radiobutton(typeFrame, text = "OPUS", variable = self.exportType, value = "opus", selectcolor=colours["bg"]).pack(side=LEFT)

      # text box widget to change desired normalized sound levels
      targetFrame = Frame(self)
      targetFrame.grid(row=3, columnspan=2)

      Label(targetFrame, text="Target sound level: ").pack(side=LEFT)
      self.targetLevelVar = StringVar()
      self.targetLevelVar.set(settings.level["target"])
      Entry(targetFrame, textvariable=self.targetLevelVar, width=10).pack(side=LEFT)
      # note: dBFS (decibel full scale) is not the same as dB
      Label(targetFrame, text="dBFS").pack(side=LEFT)

      importFolderBtn = Button(self, text="Import music folder", command=self.loadMusic, bg=colours["load"])
      importFolderBtn.grid(row=4, column=0, pady=5)
      importFileBtn = Button(self, text="Import music file", command=lambda: self.loadMusic(False), bg=colours["load"])
      importFileBtn.grid(row=4, column=1, pady=5)

      self.countLbl = Label(self, text="0 out of 0 songs to normalize")
      self.countLbl.grid(row=5, columnspan=2, pady=2)

      normalizeBtn = Button(self, text="Normalize music", command=self.startNormalizeThread, bg=colours["normalize"])
      normalizeBtn.grid(row=6, columnspan=2, pady=2)

      # tip text
      Label(self, text="Tip: This normalizes music by its average loudness, not its peak.\n" \
      "It's highly recommended to keep the target level between -20 and -10.").grid(row=7, columnspan=2)

      # to show progress of normalization process
      self.progress = IntVar()
      self.progressbar = ttk.Progressbar(self, variable=self.progress, length=250)
      self.progressbar.grid(row=8, columnspan=2, pady=5)

      self.audioFileTypes = [".mp3", ".ogg", ".opus", ".flac", ".m4a", ".wav"]
      self.validArr = []
      self.thread = None

   # load music and identify which song(s) need to be normalized
   # folder argument to differentiate between importing folder or file
   def loadMusic(self, folder = True):
      songArr = []
      if (folder):
         f = filedialog.askdirectory()
         # leave function if user cancels dialog
         if f == "": return

         # go through files in directory, only count non-normalized songs
         for path, _, files in os.walk(f):
            for file in files:
               file = os.path.join(path, file)
               name, ext = os.path.splitext(file)
               if ext.lower() in self.audioFileTypes and not name.endswith("_normalized"):
                  songArr.append(file)
      else:
         f = filedialog.askopenfilename(filetypes = (("Music files", "*.mp3 *.ogg *.opus *.flac *.m4a *.wav"),("All files","*")))
         # leave function if user cancels dialog
         if f == "": return

         name, ext = os.path.splitext(f)
         if ext in self.audioFileTypes and not name.endswith("_normalized"):
            songArr.append(f)
      
      # copy list of song names to filter out already normalized songs
      self.validArr = songArr.copy()
      for song in songArr:
         # if song already has a normalized equivalent, remove it from the valid list
         if glob(os.path.splitext(song)[0] + "_normalized.*"):
            self.validArr.remove(song)
      # display number of songs that need to be normalized out of how many were scanned
      self.countLbl['text'] = "{} out of {} songs to normalize".format(len(self.validArr), len(songArr))

   def startNormalizeThread(self):
      if self.thread is not None:
         message = "Unable to start normalization due to currently ongoing process. Please wait for it to finish first."
         print(message)
         messagebox.showwarning("Process Error", message)
         return
      self.thread = Thread(target=self.normalizeMusic)
      self.thread.start()

   def normalizeMusic(self):
      # if there's zero valid songs to normalize, do nothing
      if len(self.validArr) == 0:
         print("Normalize button pressed but no songs to normalize.")
         self.countLbl['text'] = "No songs to normalize"
         self.thread = None
         return
      
      # create a copy of the valid songs array before clearing it for future use
      copyArr = self.validArr.copy()
      self.validArr.clear()

      self.progress.set(0)
      failedArr = []
      count, max = 0, len(copyArr)
      for song in copyArr:
         # if the user exits the program in the middle of the process, kill the thread
         if killThread:
            print("Normalization process ended early.")
            self.thread = None
            return

         print("Processing file " + song)
         name, ext = os.path.splitext(song)
         ext = ext[1:]
         try:
            # pydub can't seem to open opus files despite ffmpeg supporting it
            # tricking it into reading it as an ogg file works
            sound = AudioSegment.from_file(song, format="ogg" if ext == "opus" else ext)
            metadata = mediainfo(song).get("TAG", {})
         except Exception as e:
            # if song file could not be read, skip it while noting down the name
            print("Pydub failed to read {}. This is highly likely due to the " \
            "song file using an audio codec that isn't supported.".format(song))
            failedArr.append(song)
            count += 1
            self.updateProgress(count, max)
            continue

         # get target audio level, return error if invalid input
         try:
            target = float(self.targetLevelVar.get())
            if (target > 0):
               message = "Audio level cannot be more than 0 dBFS."
               print(message)
               messagebox.showwarning("Input Error", message)
               self.thread = None
               return
         except ValueError:
            message = "Invalid audio level input, enter only numbers for the audio level."
            print(message)
            messagebox.showwarning("Input Error", message)
            self.thread = None
            return
         
         # normalize song to specified dBFS level
         change = target - sound.dBFS
         # take into account the music's peak to avoid it clipping
         change = min(change, 0.0 - sound.max_dBFS)
         print(f"   File has average loudness of {sound.dBFS:.3f} dBFS and peak of {sound.max_dBFS:.3f} " \
         f"dBFS, target is {target} dBFS; applying {change:.3f} dBFS gain while avoiding peak clipping.")
         output = sound.apply_gain(change)

         # export normalized song
         outfile = name + f"_normalized.{self.exportType.get()}"
         print(f"   Writing normalised file to {outfile}")
         # if there's title and artist metadata in original song, embed it into normalized version
         title = ""
         artist = ""
         if (metadata):
            title = metadata.get("title", "")
            artist = metadata.get("artist", "")

         # export normalized song according to user selection
         if (self.exportType.get() == "opus"):
            output.export(outfile, format="opus", parameters=["-c:a", "libopus", "-b:a", "160k"],
                          tags={"title": title, "artist": artist})
         else:
            output.export(outfile, format="mp3", parameters=["-c:a", "libmp3lame", "-q:a", "0"],
                          tags={"title": title, "artist": artist})

         # tick up the counter and update progress bar accordingly
         count += 1
         self.updateProgress(count, max)
      
      # change text to show process complete
      message = "Normalization complete"
      # if there are songs that failed to be normalized, display warning window
      # listing the affected songs
      if failedArr:
         message += " with {} failed songs".format(len(failedArr))
         failed = "One or more songs could not be normalized, this is likely " \
         "due to the file using an audio codec that isn't supported. " \
         "It's recommended that you normalize the affected songs yourself " \
         "or reencode them and try again.\n" \
         "List of songs that could not be normalized:\n\n"
         for song in failedArr:
            failed += song + "\n"
         print(failed)
         messagebox.showwarning("Incomplete Normalization", failed)
      print(message)
      self.countLbl['text'] = message
      self.thread = None

   def updateProgress(self, count, max):
      if count == max:
         self.progress.set(99.9)
      else:
         self.progressbar.step(round((1 / max) * 100, 1))

def main():
   master = Tk()
   # exit protocol to ensure normalization thread is killed
   def close():
      global killThread
      killThread = True
      master.destroy()

   # change window palette to dark mode if enabled in config
   if settings.config["dark_mode_enabled"]:
      applyDarkMode(master)
   master.title("riglevel {}".format(version))
   riglevel = Riglevel(master)
   riglevel.pack()
   master.protocol("WM_DELETE_WINDOW", close)
   # if config file was generated, show config prompt window before letting Riglevel run
   if settings.fileGen:
      openConfig()
   mainloop()

killThread = False
if __name__ == '__main__':
   main()
