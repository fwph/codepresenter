### CodePresenter

Sublime Text plugin to help with live coding demonstrations. Select a folder 
containing code you want to present as a 'live' demo, select a target folder to
save your demo code out to, start the code presentation, and impress everyone
with your wizardry.

## Install

### Package Control

The easiest way to install this is with [Package Control](http://wbond.net/sublime\_packages/package\_control).

 * If you just went and installed Package Control, you probably need to restart Sublime Text before doing this next bit.
 * Bring up the Command Palette (Command+Shift+p on OS X, Control+Shift+p on Linux/Windows).
 * Select "Package Control: Install Package" (it'll take a few seconds)
 * Select CodePresenter when the list appears.

Package Control will automatically keep CodePresenter up to date with the latest version.

### Manually
 * Clone the repo
 * Link the checkout to your Packages directory


## Usage:

### Basic Usage
  * Open or create a project
  * Add a folder or select one that exists and has files in it
  * Add a new empty folder
  * Right click on the first folder (in the side bar), and select
        *CodePresenter Actions -> Configure -> Set Source Folder*
  * Right click on the empty folder (in the side bar), and select
        *CodePresenter Actions -> Configure -> Set Sink Folder*
  * Right click on any file or folder in the side bar, and select
        *CodePresenter Actions -> Start Code Presentation*
  * Mash that keyboard!
  
### Advanced Usage
 * _Fixtures_ : Right click on a folder or file and select *CodePresenter Actions -> Configure -> Set Fixture*.
   + The file or folder will be copied directly to your Sink without modification or opening a view
   + Fixtures can also be cleared using *Clear Fixture*
 * _Multi-Stage_ : If your source contains multiple folders, you can start the presentation from one of the top level folders. 
   + Right click on a folder in the Side Bar and select *CodePresenter Actions -> Run Presentation Stage*
   + Following stages can be run with *Next Stage*
   + The presentation can be *Reset Presentation* or *Hard Reset Presentation*
   + Running *Next Stage* without first using *Run Presentation Stage* on a particular folder will start from the first stage
 * _Fast Forward_ : Files can start partially written
   + Open a file from your source folder
   + Locate the place where you want to start this file in the presentation
   + Right click and select *Code Presenter-> Set Fast Forward Point*
   + To clear, right click and select *Code Presenter-> Clear Fast Forward Point*
+  _Keyboard Shortcuts_:
    *  Commands for binding are *code_presenter_activate*, *code_presenter_reset*, and *code_presenter_next_stage*
  
### IMPORTANT:

  * All files in the sink folder will be destroyed when the presentation is started
  * All views in the active window will be closed. Views opened by CodePresenter will be closed without saving changes
  * I do not recommend mashing on the enter key; there are currently some issues with that (notably, tab insertion and various macros that occur when the enter key is pressed.)
  * This is my first Sublime Text plugin, if you have any feedback about the way it's written, please contact me!
