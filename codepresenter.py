""" 
Codesenter plugin for Sublime Text

Loads a given file, and gradually reveals it as you bang on the keyboard. 
"""
# pylint: disable=W0221

import os
import sublime
import sublime_plugin
from CodePresenter import codepresenter_util

FILE_SOURCE = '/Users/fwph/code/sublime/codepresenter/dummy.txt'


projects = {}
views = {}

class CodepresenterBaseCommand(sublime_plugin.WindowCommand):
    """ base class for the various commands that need info about the project """
    def __init__(self, *args, **kwargs):
        super(CodepresenterBaseCommand, self).__init__(*args, **kwargs)
        
        self.cp_project = codepresenter_util.CodePresenterProject.get_project(self.window)

    def load_config(self):
        """ load the codepresenter config for the project """
        self.cp_project.load_config()


class CodepresenterSetSourceCommand(CodepresenterBaseCommand):
    """ command for the sidebar to set the code presenter source directory """
    def __init__(self, *args, **kwargs):
        super(CodepresenterSetSourceCommand, self).__init__(*args, **kwargs)

    def run(self, dirs):
        """ run """
        self.cp_project.load_config()
        self.cp_project.source=dirs[0]
        self.cp_project.update_project_config()

class CodepresenterSetSinkCommand(CodepresenterBaseCommand):
    """ command for the sidebar to set the code presenter sink directory """
    def __init__(self, *args, **kwargs):
        super(CodepresenterSetSinkCommand, self).__init__(*args, **kwargs)

    def run(self, dirs):
        """ run """
        self.cp_project.load_config()
        self.cp_project.sink = dirs[0]
        self.cp_project.update_project_config()

class CodepresenterDebugCommand(CodepresenterBaseCommand):
    """ print some debug information to the console """
    def __init__(self, *args, **kwargs):
        super(CodepresenterDebugCommand, self).__init__(*args, **kwargs)

    def run(self):
        self.load_config()
        print(self.cp_project)
        print(os.listdir(self.cp_project.source))

class CodepresenterActivateCommand(CodepresenterBaseCommand):
    def __init__(self, *args, **kwargs):
        super(CodepresenterActivateCommand, self).__init__(*args, **kwargs)
        
    def run(self, *args, **kwargs):
        self.load_config()

        self.cp_project.clear_sink()
        self.cp_project.activate()

class CodepresenterinsertCommand(sublime_plugin.TextCommand):
    """
    Does the actual text insertion into the view.

    This will be in place of anything else typed.
    """
    def __init__(self, *args, **kwargs):
        super(CodepresenterinsertCommand, self).__init__(*args, **kwargs)
        self.index = 0
        self.last_region = sublime.Region(-1, 0)
        self.character_source = None

    def run(self, edit):
        cp_view = codepresenter_util.CodePresenterProject.find_view(self.view)
        if cp_view is not None:
            cp_view.do_edit(edit)


class CodepresenterEventListener(sublime_plugin.EventListener):
    """
    Listens for new views, and view modified events.

    When the target view is modified, issues an InsertcodeCommand
    """
    def __init__(self, *args, **kwargs):
        super(CodepresenterEventListener, self).__init__(*args, **kwargs)

    def on_modified(self, view):
        """ runs the insertion command when the target view is modified """
        if view.window() is None:
            return
        cp_view = codepresenter_util.CodePresenterProject.find_view(view)
        if cp_view is not None:
            if cp_view.last_size is None:
                cp_view.last_size = view.size()
            elif cp_view.last_size > view.size():
                cp_view.last_size = view.size()
                return
            elif cp_view.last_size == view.size():
                return
            view.run_command('codepresenterinsert')

