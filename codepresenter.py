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
import re


class CodePresenterView(object):
    PADDING = 25
    """ code presenter model for a particular view """
    def __init__(self, view, source, sink, offset=0):
        self.view = view
        self.source = source
        self.sink = sink

        self.character_source = None
        self.index = offset
        self.last_region = sublime.Region(offset-1, offset)
        self.last_size = None

    @property
    def done(self):
        return self.index >= len(self.character_source) +\
                CodePresenterView.PADDING

    @property
    def view_id(self):
        """ access to the id of the view this is using """
        return self.view.id()

    def set_initial_cursor(self):
        self.view.sel().clear()
        extent = self.view.layout_extent()
        pt = self.view.layout_to_text(extent)
        endreg = sublime.Region(pt, pt)
        self.view.sel().add(endreg)
        self.last_region = endreg

    def do_edit(self, edit):
        """ do the actual edit. first erase the text that was just added
            (last character, since this should be called for every character
            entry) then append the next character.

            if the cursor selection is *not* at the end of the file, though
            do nothing
        """

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

        self.dir_fixtures = []
        self.file_fixtures = []

        self.views = {}

        # for substage presentations -- run folder by folder
        self.last_stage = None
        self.did_fixtures = False

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

    def set_fixtures(self, dirs, files):
        self.load_config()
        for adir in dirs:
            if adir not in self.dir_fixtures:
                self.dir_fixtures.append(adir)
        for afile in files:
            if afile not in self.file_fixtures:
                self.file_fixtures.append(afile)
        self.update_project_config()

    def clear_fixtures(self, dirs, files):
        self.load_config()
        for adir in dirs:
            if adir in self.dir_fixtures:
                self.dir_fixtures.remove(adir)
        for afile in files:
            if afile in self.file_fixtures:
                self.file_fixtures.remove(afile)
        self.update_project_config()

    def set_ffwd_point(self, filename, offset):
        self.load_config()
        if not filename.startswith(self.source):
            print("CodePresenter: file %s not in source %s" % (filename,
                                                               self.source))
            return

        if 'offsets' not in self.code_presenter_config:
            self.code_presenter_config['offsets'] = {}
        self.code_presenter_config['offsets'][filename] = offset
        self.update_project_config()

    def clear_ffwd_point(self, filename):
        self.load_config()

        if not filename.startswith(self.source):
            print("CodePresenter: file %s not in source %s" % (filename,
                                                               self.source))
            return

        if 'offsets' in self.code_presenter_config and filename in \
                self.code_presenter_config['offsets']:
            del self.code_presenter_config['offsets'][filename]

        self.update_project_config()

    def file_ffwd_offset(self, filename):
        offset = 0
        if 'offsets' in self.code_presenter_config:
            offset = self.code_presenter_config['offsets'].get(filename, 0)
        return offset

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
            if 'fixtures' in self.code_presenter_config:
                self.dir_fixtures =\
                    self.code_presenter_config['fixtures'].get('dirs', [])
                self.file_fixtures =\
                    self.code_presenter_config['fixtures'].get('files', [])

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
        self.code_presenter_config['fixtures'] = {
            'dirs': self.dir_fixtures,
            'files': self.file_fixtures,
        }

        self.window.set_project_data(self.project_data)

    def clear_sink(self, hard=False):
        """
            clear out the sink, closing all views in the process.
            @todo: deal with directories
        """
        self.last_stage = None
        self.did_fixtures = False

        self.load_config()
        cp_settings = sublime.load_settings('CodePresenter.sublime-settings')
        # close all the views
        for view in self.window.views():
            self.window.focus_view(view)
            self.window.run_command("close_file")

        if cp_settings.get('delete_directories', False) or hard:
            # this seems to be unreliable, at best, on windows
            shutil.rmtree(self.sink)
            os.mkdir(self.sink)
        else:
            toremove, _ = self.find_files(self.sink)
            for file in toremove:
                try:
                    os.remove(file)
                except TypeError:
                    print(file)

        self.views = {}

    def find_files(self, path):
        cp_settings = sublime.load_settings('CodePresenter.sublime-settings')
        # neither of the following can handle file patterns, unfortunately
        ignore_dirs = cp_settings.get('ignore_directories', [])
        ignore_files = cp_settings.get('ignore_files', [])
        ignore_patterns = cp_settings.get('ignore_patterns', [])

        ignore_re = [re.compile(pattern) for pattern in ignore_patterns]

        filelist = []
        dirlist = []
        for root, dirs, files in os.walk(path):
            dirs[:] = [adir for adir in dirs if not (adir.startswith('.') or
                                                     adir in ignore_dirs)]
            dirlist.extend(dirs)
            files = [os.path.join(root, afile) for afile in files
                     if not (afile.startswith('.') or
                             afile in ignore_files or
                             any([pat.match(afile) for pat in ignore_re]))]
            filelist.extend(files)
        return filelist, dirlist

    def activate(self):
        self.activate_from(self.source)

    def next_stage(self):
        substages = [os.path.join(self.source, adir)
                     for adir in os.listdir(self.source)]
        substages = [adir for adir in substages
                     if os.path.isdir(adir)]
        substages = [stage for stage in substages
                     if stage not in self.dir_fixtures]
        substages.sort()

        if self.last_stage is None:
            self.activate_from(substages[0])
        else:
            nextindex = substages.index(self.last_stage) + 1
            if nextindex < len(substages):
                self.activate_from(substages[nextindex])

    def load_fixtures(self):
        source_files, source_dirs = self.find_files(self.source)
        for sourcefile in source_files:
            if sourcefile in self.file_fixtures or\
                any([sourcefile.startswith(adir)
                     for adir in self.dir_fixtures]):

                sinkfile = sourcefile.replace(self.source, self.sink, 1)

                # make sure the containing directory exists
                newdir = os.path.dirname(sinkfile)
                os.makedirs(newdir, exist_ok=True)
                shutil.copyfile(sourcefile, sinkfile)
        self.did_fixtures = True

    def activate_from(self, location):
        """
            start the code presentation
        """
        if self.source is None or self.sink is None:
            print(("CodePresenter: Refusing to activate without"
                   " a source and a sink"))
            return
        if not location.startswith(self.source):
            print(("CodePresenter: Cannot activate presentation"
                   " from %s (not in %s)") % (location, self.source))

        self.last_stage = location
        if not self.did_fixtures:
            self.load_fixtures()

        cp_settings = sublime.load_settings('CodePresenter.sublime-settings')
        touch_files = cp_settings.get('touch_sink_files', False)
        # handle fixtures

        source_files, source_dirs = self.find_files(location)

        # order the source file tabs in a nice way
        source_files.sort(reverse=True)

        for sourcefile in source_files:

            if sourcefile in self.file_fixtures or\
                any([sourcefile.startswith(adir)
                     for adir in self.dir_fixtures]):
                continue

            sinkfile = sourcefile.replace(self.source, self.sink, 1)
            try:
                # make sure the containing directory exists
                newdir = os.path.dirname(sinkfile)
                os.makedirs(newdir, exist_ok=True)
                offset = self.file_ffwd_offset(sourcefile)
                if touch_files or offset > 0:
                    sfile = open(sinkfile, "w", encoding='utf-8')
                    if offset is not None:
                        with open(sourcefile, 'r', encoding='utf-8') as ifile:
                            contents = ifile.read()
                            sfile.write(contents[:offset])
                    sfile.close()

                new_view = self.window.open_file(sinkfile)
                new_view.set_scratch(True)

                cp_view = CodePresenterView(new_view, sourcefile,
                                            sinkfile, offset)
                with open(sourcefile, 'r', encoding='utf-8') as insource:
                    cp_view.character_source = list(insource.read())
                self.add_view(cp_view)

            except UnicodeDecodeError:
                print(("CodePresenter: Error decoding source file. This likely"
                       " means the file is not encoded as utf-8, which is "
                       "currently a requirement of CodePresenter. The "
                       "problem file was: %s") % sourcefile)
                print(("Please report an issue at "
                       "https://github.com/fwph/codepresenter/issue with the "
                       "correct encoding of your file if you know it."))
        # this helps presentations using the sftp plugin operate smoothly
        if cp_settings.get('sftp_upload_folder', False):
            self.window.run_command('sftp_upload_folder')

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


class CodePresenterSetFixtureCommand(CodePresenterBaseCommand):
    """ command for the sidebar to set a fixture

        fixtures will be copied as is, without opening the file(s). can be
        either a file or a directory.
    """
    def __init__(self, *args, **kwargs):
        super(CodePresenterSetFixtureCommand, self).__init__(*args, **kwargs)

    def run(self, **kwargs):
        """ run """
        dirs = kwargs['dirs']
        files = kwargs['files']
        self.cp_project.set_fixtures(dirs, files)


class CodePresenterClearFixtureCommand(CodePresenterBaseCommand):
    """ command for the sidebar to clear a fixture

        fixtures will be copied as is, without opening the file(s). can be
        either a file or a directory.
    """
    def __init__(self, *args, **kwargs):
        super(CodePresenterClearFixtureCommand, self).__init__(*args, **kwargs)

    def run(self, **kwargs):
        """ run """
        dirs = kwargs['dirs']
        files = kwargs['files']
        self.cp_project.clear_fixtures(dirs, files)


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

    def run(self, *args, **kwargs):
        self.load_config()

        if 'dirs' in kwargs:
            self.cp_project.activate_from(kwargs['dirs'][0])
        else:
            self.cp_project.clear_sink()
            self.cp_project.activate()


class CodePresenterNextStageCommand(CodePresenterBaseCommand):
    def __init__(self, *args, **kwargs):
        super(CodePresenterNextStageCommand, self).__init__(*args, **kwargs)

    def run(self, *args, **kwargs):
        self.load_config()
        self.cp_project.next_stage()


class CodePresenterResetCommand(CodePresenterBaseCommand):
    def __init__(self, *args, **kwargs):
        super(CodePresenterResetCommand, self).__init__(*args, **kwargs)

    def run(self, *args, **kwargs):
        self.load_config()
        self.cp_project.clear_sink(kwargs.get('hard', False))


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


class CodePresenterSetFforward(sublime_plugin.TextCommand):
    """
    Set a fast forward point for this file.

    If set, the file up to the given point will be loaded, and cursor placed
    at this point to continue the presentation from there.
    """
    def __init__(self, *args, **kwargs):
        super(CodePresenterSetFforward, self).__init__(*args, **kwargs)

    def run(self, *args, **kwargs):
        """ translating the event coords to a text offset seems
            over-complicated, but it seems to work.
        """
        coords = list(kwargs['event'].values())
        textcoords = self.view.window_to_text(coords)
        row, col = self.view.rowcol(textcoords)
        text_offset = self.view.text_point(row, col)
        project = CodePresenterProject.get_project(self.view.window())
        project.set_ffwd_point(self.view.file_name(), text_offset)

    def want_event(self):
        return True


class CodePresenterClearFforward(sublime_plugin.TextCommand):
    """
    Clears the fastforward point, if it exists.
    """
    def __init__(self, *args, **kwargs):
        super(CodePresenterClearFforward, self).__init__(*args, **kwargs)

    def run(self, *args, **kwargs):
        project = CodePresenterProject.get_project(self.view.window())
        project.clear_ffwd_point(self.view.file_name())


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

    def on_load(self, view):
        """ set up the proper cursor point once the file loads """
        cp_view = CodePresenterProject.find_view(view)

        if cp_view is not None:
            cp_view.set_initial_cursor()
