Sublime Text plugin to help with live coding demonstrations.

Usage:

    - Install the plugin (by, say, linking the checkout to your Packages directory )
    - open or create a project
    - add a folder or select one that exists and has files in it
    - add a new empty folder
    - right click on the first folder (in the side bar), and select
        CodePresenter Actions -> Set Source Folder
    - right click on the empty folder (in the side bar), and select
        CodePresenter Actions -> Set Sink Folder
    - right click on any file or folder in the side bar, and select
        CodePresenter Actions -> Start Code Presentation
    - mash that keyboard!

Notes:

    - All files in the sink folder will be destroyed when the presentation is started
    - All views in the active window will be closed, even if changes have been made, when the presentation is started
    - It won't handle subdirectories nicely, yet.
