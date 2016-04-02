""" 
Codesenter plugin for Sublime Text

Loads a given file, and gradually reveals it as you bang on the keyboard. 
"""

import sublime, sublime_plugin

FILE_SOURCE = '/Users/fwph/code/sublime/codepresenter/dummy.txt'


class CodepresenterinsertCommand(sublime_plugin.TextCommand):
    """
    Does the actual text insertion into the view.

    This will be in place of anything else typed.
    """
    def __init__(self, *args, **kwargs):
        super(CodepresenterinsertCommand, self).__init__(*args, **kwargs)
        self.myview = None
        self.character_source = []
        self.index = 0
        self.last_region = sublime.Region(-1, 0)
        with open(FILE_SOURCE, 'r') as infile:
            self.character_source = list(infile.read())

    def run(self, edit):
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

class CodepresenterEventListener(sublime_plugin.EventListener):
    """
    Listens for new views, and view modified events.

    When the target view is modified, issues an InsertcodeCommand
    """
    def __init__(self, *args, **kwargs):
        super(CodepresenterEventListener, self).__init__(*args, **kwargs)
        self.myview = None
        self.last_size = None

    def on_modified(self, view):
        """ runs the insertion command when the target view is modified """
        if self.myview is not None and view == self.myview:
            if self.last_size == None:
                self.last_size = self.myview.size()
            elif self.last_size > self.myview.size():
                pass
            self.myview.run_command('codepresenterinsert')

    def on_new(self, view):
        """ listens for new views and grabs the first new one it sees.

            this will be replaced by having a special open command which
            will select the 
        """
        if self.myview == None:
            self.myview = view
