""" 
Codesenter plugin for Sublime Text

Loads a given file, and gradually reveals it as you bang on the keyboard. 
"""
# pylint: disable=W0221,C0325

import sublime
import sublime_plugin
import os

FILE_SOURCE = '/Users/fwph/code/sublime/codepresenter/dummy.txt'

projects = {}
views = {}

class CodepresenterBaseCommand(sublime_plugin.WindowCommand):
    """ base class for the various commands that need info about the project """
    def __init__(self, *args, **kwargs):
        super(CodepresenterBaseCommand, self).__init__(*args, **kwargs)
        
        self.project_data = None
        self.code_presenter_config = None
        self.source = None
        self.sink = None

        self.load_config()

    def load_config(self):
        """ load the codepresenter config for the project """
        project_data_file = self.window.project_file_name()
        if project_data_file is None:
            return

        project_data = self.window.project_data()
        projects[project_data_file] = project_data

        self.project_data = projects[project_data_file]
        
        if project_data_file is not None:
            self.code_presenter_config = self.project_data.get('codepresenter', None)
        if self.code_presenter_config is not None:
            self.source = self.code_presenter_config.get('source', None)
            self.sink = self.code_presenter_config.get('sink', None)


class CodepresenterSetSourceCommand(CodepresenterBaseCommand):
    """ command for the sidebar to set the code presenter source directory """
    def __init__(self, *args, **kwargs):
        super(CodepresenterSetSourceCommand, self).__init__(*args, **kwargs)

    def run(self, dirs):
        """ run """
        if self.project_data is None:
            print("CodePresenter: Requires a project to work!")
            return
        if self.code_presenter_config is None:
            self.code_presenter_config = {'active' : True}
            self.project_data['codepresenter'] = self.code_presenter_config
        self.code_presenter_config['source'] = dirs[0]
        self.window.set_project_data(self.project_data)

class CodepresenterSetSinkCommand(CodepresenterBaseCommand):
    """ command for the sidebar to set the code presenter sink directory """
    def __init__(self, *args, **kwargs):
        super(CodepresenterSetSinkCommand, self).__init__(*args, **kwargs)

    def run(self, dirs):
        """ run """
        if self.project_data is None:
            return
        if self.code_presenter_config is None:
            self.code_presenter_config = {'active' : True}
            self.project_data['codepresenter'] = self.code_presenter_config
        self.sink = dirs[0]
        self.code_presenter_config['sink'] = self.sink
        self.window.set_project_data(self.project_data)

class CodepresenterDebugCommand(CodepresenterBaseCommand):
    """ print some debug information to the console """
    def __init__(self, *args, **kwargs):
        super(CodepresenterDebugCommand, self).__init__(*args, **kwargs)

    def run(self):
        self.load_config()

        print(self.window.project_file_name())
        print(os.listdir(self.source))
        print(self.source)
        print(self.sink)


class CodepresenterActivateCommand(CodepresenterBaseCommand):
    def __init__(self, *args, **kwargs):
        super(CodepresenterActivateCommand, self).__init__(*args, **kwargs)
        
    def run(self, *args, **kwargs):
        self.load_config()

        if self.source is None or self.sink is None:
            print("CodePresenter: Refusing to activate without a source and a sink")
            return

        source_files = os.listdir(self.source)
        global views
        for view_data in views.values():
            try:
                view = view_data['view']
                self.window.focus_view(view)
                view.set_scratch(True)
                self.window.run_command("close_file")
            except Exception:
                pass
        views = {}

        for filep in source_files:
            base = os.path.basename(filep)
            some_view = self.window.open_file(os.path.join(self.sink, base))
            character_source = []
            sinkfile = os.path.join(self.sink, filep)

            if os.path.exists(sinkfile):
                os.remove(sinkfile)
            with open(os.path.join(self.source, filep), 'r') as infile:
                character_source = list(infile.read())
            views[some_view.id()] = {'source_file' : os.path.join(self.source, filep), 
                                     'character_source' : character_source,
                                     'last_size' : None,
                                     'view' : some_view}

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
        if self.character_source is None:
            self.character_source = views[self.view.id()]['character_source']

        cursor = self.view.sel()[0]
        cursor.a = cursor.a - 1
        if cursor.a == self.last_region.a or\
            cursor.b != self.view.size() or self.index >= len(self.character_source):
            pass
        else:
            self.last_region = cursor
            self.view.erase(edit, cursor)
            self.view.insert(edit, self.view.size(), self.character_source[self.index])
            #print(self.character_source)
            self.index += 1

class CodepresenterEventListener(sublime_plugin.EventListener):
    """
    Listens for new views, and view modified events.

    When the target view is modified, issues an InsertcodeCommand
    """
    def __init__(self, *args, **kwargs):
        super(CodepresenterEventListener, self).__init__(*args, **kwargs)

    def on_modified(self, view):
        """ runs the insertion command when the target view is modified """
        if view.id() in views:
            if views[view.id()]['last_size'] == None:
                views[view.id()]['last_size'] = view.size()
            elif views[view.id()]['last_size'] > view.size():
                pass
            view.run_command('codepresenterinsert')

