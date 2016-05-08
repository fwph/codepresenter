"""
CodePresenter plugin for Sublime Text

Loads a given file, and gradually reveals it as you bang on the keyboard.

Known issue: banging on the 'enter' key will frequently cause macros to run,
which this doesn't deal with nicely now. So skip enter.
"""
import os
import shutil
import sublime
import sublime_plugin


class CodePresenterView(object):
    PADDING = 25
    """ code presenter model for a particular view """
    def __init__(self, view, source, sink):
        self.view = view
        self.source = source
        self.sink = sink

        self.character_source = None
        self.index = 0
        self.last_region = sublime.Region(-1, 0)
        self.last_size = None

    @property
    def done(self):
        return self.index >= len(self.character_source) +\
                CodePresenterView.PADDING

    @property
    def view_id(self):
        """ access to the id of the view this is using """
        return self.view.id()

    def do_edit(self, edit):
        """ do the actual edit. first erase the text that was just added
            (last character, since this should be called for every character
            entry) then append the next character.

            if the cursor selection is *not* at the end of the file, though
            do nothing
        """
        if self.character_source is None:
            with open(self.source, 'r') as insource:
                self.character_source = list(insource.read())
                self.index = 0

        cursor = self.view.sel()[0]
        cursor.a = cursor.a - 1
        if cursor.b != self.view.size():
            pass
        elif self.index >= len(self.character_source):
            # this provides a little leeway to stop typing
            if not self.done:
                self.last_region = cursor
                self.view.erase(edit, cursor)
                self.index += 1
        else:
            self.last_region = cursor
            self.view.erase(edit, cursor)
            self.view.insert(edit, self.view.size(),
                             self.character_source[self.index])
            self.index += 1
            self.last_size = self.view.size()


class CodePresenterProject(object):
    """ handling for the code presenter project itself.

        this currently uses the project data file, but this might be shady;
        should figure out if it really ought to have its own project file.

        as it is, there may be some additional user configurable per-project
        options which would want an additional configuration file.
    """
    PROJECTS = {}

    def __init__(self, window):
        self.window = window
        self.project_file = None
        self.project_data = None

        self.code_presenter_config = None
        self.source = None
        self.sink = None

        self.views = {}

        CodePresenterProject.PROJECTS[self.project_id] = self
        self.load_config()

    @classmethod
    def get_project(cls, window):
        """ used to retrieve a particular project by window ID """

        if not window.id() in cls.PROJECTS:
            cls(window)

        return cls.PROJECTS[window.id()]

    @classmethod
    def find_view(cls, view):
        """ used to retrieve a particular project by window ID """
        project = cls.get_project(view.window())
        cp_view = None
        if project is not None:
            cp_view = project.get_view(view)

        return cp_view

    @property
    def project_id(self):
        """ id of the project object is the window id """
        return self.window.id()

    def load_config(self):
        """ load the codepresenter config for the project """
        self.project_file = self.window.project_file_name()
        self.project_data = self.window.project_data()

        if self.project_file is not None:
            self.code_presenter_config =\
                self.project_data.get('settings', {}).get('codepresenter',
                                                          None)
        if self.code_presenter_config is not None:
            self.source = self.code_presenter_config.get('source', None)
            self.sink = self.code_presenter_config.get('sink', None)

    def update_project_config(self):
        """ write changes to the project config """
        if self.project_data is None:
            print("CodePresenter: Requires a project to work!")
            return

        if self.code_presenter_config is None:
            self.code_presenter_config = {'active': True}
            if self.project_data.get('settings', None) is None:
                self.project_data['settings'] = {}
            self.project_data['settings']['codepresenter'] =\
                self.code_presenter_config

        self.code_presenter_config['source'] = self.source
        self.code_presenter_config['sink'] = self.sink

        self.window.set_project_data(self.project_data)

    def clear_sink(self):
        """
            clear out the sink, closing all views in the process.
            @todo: deal with directories
        """
        self.load_config()

        # close all the views
        for view in self.window.views():
            self.window.focus_view(view)
            self.window.run_command("close_file")

        shutil.rmtree(self.sink)
        os.mkdir(self.sink)

        self.views = {}

    @classmethod
    def find_files(cls, path):
        filelist = []
        dirlist = []
        for root, dirs, files in os.walk(path):
            dirs[:] = [adir for adir in dirs if not adir.startswith('.')]
            dirlist.extend(dirs)
            files = [os.path.join(root, afile) for afile in files
                     if not afile.startswith('.')]
            filelist.extend(files)
        return filelist, dirlist

    def activate(self):
        """
            start the code presentation
        """
        if self.source is None or self.sink is None:
            print(("CodePresenter: Refusing to activate without"
                   " a source and a sink"))
            return

        source_files, source_dirs = self.find_files(self.source)

        for sourcefile in source_files:
            sinkfile = sourcefile.replace(self.source, self.sink, 1)

            # make sure the containing directory exists
            newdir = os.path.dirname(sinkfile)
            os.makedirs(newdir, exist_ok=True)

            new_view = self.window.open_file(sinkfile)
            new_view.set_scratch(True)

            cp_view = CodePresenterView(new_view, sourcefile, sinkfile)

            self.add_view(cp_view)

    def add_view(self, view):
        """ put it in the view dict. """
        self.views[view.view_id] = view

    def get_view(self, view):
        """ retrieve a view from the local store """
        return self.views.get(view.id(), None)


class CodePresenterBaseCommand(sublime_plugin.WindowCommand):
    """ base class for the various commands that need info about
        the project """
    def __init__(self, *args, **kwargs):
        super(CodePresenterBaseCommand, self).__init__(*args, **kwargs)
        self.cp_project = CodePresenterProject.get_project(self.window)

    def load_config(self):
        """ load the codepresenter config for the project """
        self.cp_project.load_config()


class CodePresenterSetSourceCommand(CodePresenterBaseCommand):
    """ command for the sidebar to set the code presenter source directory """
    def __init__(self, *args, **kwargs):
        super(CodePresenterSetSourceCommand, self).__init__(*args, **kwargs)

    def run(self, **kwargs):
        """ run """
        dirs = kwargs['dirs']
        self.cp_project.load_config()
        self.cp_project.source = dirs[0]
        if self.cp_project.source == self.cp_project.sink:
            self.cp_project.sink = None
        self.cp_project.update_project_config()


class CodePresenterSetSinkCommand(CodePresenterBaseCommand):
    """ command for the sidebar to set the code presenter sink directory """
    def __init__(self, *args, **kwargs):
        super(CodePresenterSetSinkCommand, self).__init__(*args, **kwargs)

    def run(self, **kwargs):
        """ run """
        dirs = kwargs['dirs']
        self.cp_project.load_config()
        if dirs[0] == self.cp_project.source:
            print("CodePresenter: refusing to set the source dir as sink")
        self.cp_project.sink = dirs[0]
        self.cp_project.update_project_config()


class CodePresenterDebugCommand(CodePresenterBaseCommand):
    """ print some debug information to the console """
    def __init__(self, *args, **kwargs):
        super(CodePresenterDebugCommand, self).__init__(*args, **kwargs)

    def run(self):
        self.load_config()
        print(self.cp_project)
        print(os.listdir(self.cp_project.source))


class CodePresenterActivateCommand(CodePresenterBaseCommand):
    def __init__(self, *args, **kwargs):
        super(CodePresenterActivateCommand, self).__init__(*args, **kwargs)

    def run(self):
        self.load_config()

        self.cp_project.clear_sink()
        self.cp_project.activate()


class CodePresenterInsertCommand(sublime_plugin.TextCommand):
    """
    Does the actual text insertion into the view.

    This will be in place of anything else typed.
    """
    def __init__(self, *args, **kwargs):
        super(CodePresenterInsertCommand, self).__init__(*args, **kwargs)
        self.index = 0
        self.last_region = sublime.Region(-1, 0)
        self.character_source = None

    def run(self, edit):
        cp_view = CodePresenterProject.find_view(self.view)
        if cp_view is not None:
            cp_view.do_edit(edit)


class CodePresenterEventListener(sublime_plugin.EventListener):
    """
    Listens for new views, and view modified events.

    When the target view is modified, issues an InsertcodeCommand
    """
    def __init__(self, *args, **kwargs):
        super(CodePresenterEventListener, self).__init__(*args, **kwargs)

    def on_modified(self, view):
        """ runs the insertion command when the target view is modified """
        if view.window() is None:
            return
        cp_view = CodePresenterProject.find_view(view)
        if cp_view is not None:
            if cp_view.last_size is None:
                cp_view.last_size = view.size()
            elif cp_view.last_size > view.size():
                cp_view.last_size = view.size()
                return
            elif cp_view.last_size == view.size():
                return
            view.run_command('code_presenter_insert')
