""" 
    classes to manage the data and operations of CodePresenter.

    used by the sublime plugin handlers
"""
import os
import sublime

class CodePresenterView(object):
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

        cursor = self.view.sel()[0]
        cursor.a = cursor.a - 1
        if cursor.a == self.last_region.a or\
            cursor.b != self.view.size() or self.index >= len(self.character_source):
            pass
        else:
            self.last_region = cursor
            self.view.erase(edit, cursor)
            self.view.insert(edit, self.view.size(), self.character_source[self.index])
            self.index += 1

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
            self.code_presenter_config = self.project_data.get('codepresenter', None)
        if self.code_presenter_config is not None:
            self.source = self.code_presenter_config.get('source', None)
            self.sink = self.code_presenter_config.get('sink', None)

    def update_project_config(self):
        """ write changes to the project config """
        if self.project_data is None:
            print("CodePresenter: Requires a project to work!")
            return

        if self.code_presenter_config is None:
            self.code_presenter_config = {'active' : True}
            self.project_data['codepresenter'] = self.code_presenter_config

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
            view.set_scratch(True)
            self.window.run_command("close_file")

        # remove all sink files 
        if self.sink is not None:
            for sinkfile in os.listdir(self.sink):
                sinkpath = os.path.join(self.sink, sinkfile)
                if os.path.exists(sinkpath):
                    os.remove(sinkpath)
        self.views = {}

    def activate(self):
        """
            start the code presentation
        """
        if self.source is None or self.sink is None:
            print("CodePresenter: Refusing to activate without a source and a sink")
            return

        source_files = os.listdir(self.source)

        for filep in source_files:
            sourcefile = os.path.join(self.source, filep)
            sinkfile = os.path.join(self.sink, filep)
            new_view = self.window.open_file(sinkfile)

            cp_view = CodePresenterView(new_view, sourcefile, sinkfile)

            self.add_view(cp_view)

    def add_view(self, view):
        """ put it in the view dict. """
        self.views[view.view_id] = view

    def get_view(self, view):
        return self.views.get(view.id(), None)