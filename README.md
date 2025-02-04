Rigdio (& RigDJ)
================
**Rigdio** is an automated goalhorn/anthem player designed to ease the burden on streamers during cup events, and increase the options available to managers/caretakers for the team's music exports.<br>
**RigDJ** is the GUI editor for .4ccm files, released along with Rigdio. It allows for graphical editing of anthem and player songs as well as the various conditions you can set for them. If you intend to use more complex instructions for your music, it is recommended you use RigDJ to avoid needing to know the .4ccm formatting for every condition type.

If you're just looking for the program, you can find it [here](https://github.com/the4chancup/rigdio/releases). Information on how to use Rigdio/RigDJ themselves can also be found [here](https://implyingrigged.info/wiki/Rigdio).

## Build Guide
If you're interested in building Rigdio/RigDJ yourself, here's some info that'll help.

### Requirements
* [Python 3.8.10](https://www.python.org/downloads/release/python-3810/) (but any 3.8 version will do) - Programming language required to run and build the code. Do not use the later Python versions (3.9 or later) as they don't natively support Windows 7, which some streamers still use.
* [VLC (64-bit)](https://www.videolan.org/vlc/download-windows.html) - Contains the media libraries required to play the songs on Rigdio. It is important that you install the 64-bit version of VLC and not 32-bit which is the default download. Click on the arrow next to the `Download VLC` button and select `Installer for 64bit version` to download the correct version.
* [python-vlc](https://pypi.org/project/python-vlc/) - Python module used for utilising the VLC media library functions to play songs on Rigdio.
* [PyYAML](https://pypi.org/project/PyYAML/) - Python module used for parsing the default settings used in Rigdio.
* [pyinstaller](https://pypi.org/project/pyinstaller/) - Python module used for building the executable files.
* [pydub](https://pypi.org/project/pydub/) - Python module formerly used for levelling the audio of all song files in a music export to a uniform level. Currently not needed as the levelling feature has been removed (for now).

### Running the Python file
If you've made any changes to the code and wish to test them out without having to build the whole program, you can run it directly through Command Prompt. Open up Command Prompt in your project folder and enter `python (name of code file)`. This also allows you to see whatever messages/errors Rigdio/RigDJ spits out while it's running, making it easier to debug.

For example, the command line to run Rigdio is
```
python rigdio.py
```

Similarly, the command line to run RigDJ is
```
python rigdj.py
```

### Building Rigdio/RigDJ
Once you've fully made and tested out your code changes, you can start building the executables. Simply run the batch file for whichever executable you wish to build (**compile-rigdio.bat** for Rigdio, **compile-rigdj.bat** for RigDJ) and wait for the process to finish. Assuming the build process went smoothly and without error, you will see a couple new files and folders. The built executable will be stored in the `dist` folder for you to test out yourself.<br>
**TIP:** Replace the executable in the Rigdio release folder with your own built executable before testing it out to have a more accurate runtime environment (Rigdio/RigDJ will use the plugins inside the release folder instead of the ones installed in your system).

If you're on Mac/Linux then you will need to run the command line manually; Fortunately it's short and only a single line.<br>
The command line to build the Rigdio executable is
```
pyinstaller -F --noconsole --icon=rigdio.ico rigdio.py
```

And the command line to build the RigDJ executable is
```
pyinstaller -F --noconsole rigdj.py
```
