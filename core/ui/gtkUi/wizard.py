'''
wizard.py

Copyright 2008 Andres Riancho

This file is part of w3af, w3af.sourceforge.net .

w3af is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation version 2 of the License.

w3af is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with w3af; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

'''

import gtk, os
from . import entries, confpanel, helpers
from core.controllers.w3afException import w3afException

class Quest(object):
    def __init__(self, quest):
        self.quest = quest
        self.ptype = self.pname = None

    def getOptions(self):
        opts = self.quest.getOptionObjects()
        return opts

class QuestOptions(gtk.VBox):
    def __init__(self, w3af, wizard):
        self.w3af = w3af
        self.wizard = wizard
        super(QuestOptions,self).__init__()

        self.widg = gtk.Label("")
        self.pack_start(self.widg)
        self.activeQuestion = None
        
        self.show_all()

    def saveOptions(self):
        '''Saves the changed options.'''

#        import pdb;pdb.set_trace()
        options = self.widg.options
        invalid = []
        for opt in options:
            if hasattr(opt.widg, "isValid"):
                if not opt.widg.isValid():
                    invalid.append(opt.getName())
        if invalid:
            msg = "The configuration can't be saved, there is a problem in the following parameter(s):\n\n"
            msg += "\n-".join(invalid)
            dlg = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_WARNING, gtk.BUTTONS_OK, msg)
            dlg.set_title('Configuration error')
            dlg.run()
            dlg.destroy()
            return

        print "Grabamos!!!"
        for opt in options:
            print opt
            opt.setValue( opt.widg.getValue() )

        try:
            helpers.coreWrap(self.wizard.setAnswer, options)
        except w3afException:
            return

    def configChanged(self, flag):
        # just to comply with API
        pass

    def setQuestOptions(self, quest):
        print "set quest!", quest
        self.activeQuestion = quest
        self.remove(self.widg)
        self.widg = confpanel.OnlyOptions(self, self.w3af, Quest(quest), gtk.Button(), gtk.Button())
        self.pack_start(self.widg)

    def clear(self):
        self.remove(self.widg)
        self.widg = gtk.Label("")
        self.pack_start(self.widg)

class Wizard(entries.RememberingWindow):
    '''The wizard to help the user to create a profile.

    @author: Facundo Batista <facundobatista =at= taniquetil.com.ar>
    '''
    def __init__(self, w3af, wizard):
        super(Wizard,self).__init__(w3af, "wizard", "w3af Wizard: " + wizard.getName())
        self.set_icon_from_file('core/ui/gtkUi/data/w3af_icon.png')
        self.w3af = w3af
        self.wizard = wizard

        # the image at the left
        mainhbox = gtk.HBox()
        self.vbox.pack_start(mainhbox)
        leftframe = gtk.image_new_from_file('core/ui/gtkUi/data/wizard_frame.png')
        mainhbox.pack_start(leftframe, False, False)
        mainvbox = gtk.VBox()
        mainhbox.pack_start(mainvbox)

        # the structure
        self.qtitle = gtk.Label()
        mainvbox.pack_start(self.qtitle, False, False, padding=10)
        self.quest = gtk.Label()
        self.quest.set_line_wrap(True)
        mainvbox.pack_start(self.quest, True, False, padding=10)
        self.panel = QuestOptions(w3af, wizard)
        mainvbox.pack_start(self.panel, True, False, padding=10)

        # fill it
        quest = self.wizard.next()
        self._firstQuestion = quest
        self._buildWindow(quest)

        # go button
        butbox = gtk.HBox()
        self.prevbtn = gtk.Button("  Back  ")
        self.prevbtn.set_sensitive(False)
        self.prevbtn.connect("clicked", self._goBack)
        butbox.pack_start(self.prevbtn, True, False)
        self.nextbtn = gtk.Button("  Next  ")
        self.nextbtn.connect("clicked", self._goNext)
        butbox.pack_start(self.nextbtn, True, False)
        mainvbox.pack_start(butbox, False, False)
        
        # Show all!
        self.show_all()

    def _goNext(self, widg):
        '''Shows the next question.'''
        self.panel.saveOptions()
        quest = self.wizard.next()
        self.prevbtn.set_sensitive(True)
        if quest is None:
            self._buildFinal()
            self.nextbtn.set_sensitive(False)
        else:
            self._buildWindow(quest)
            self.nextbtn.set_sensitive(True)

    def _goBack(self, widg):
        '''Shows the previous question.'''
        self.panel.saveOptions()
        quest = self.wizard.previous()
        self.nextbtn.set_sensitive(True)
        if quest is self._firstQuestion:
            self.prevbtn.set_sensitive(False)
        self._buildWindow(quest)

    def _buildWindow(self, question):
        '''Builds the useful pane for a question.

        @param question: the question with the info to build.
        '''
        self.qtitle.set_markup("<b>%s</b>" % question.getQuestionTitle())
        self.quest.set_text(question.getQuestionString())
        self.panel.setQuestOptions(question)

    def _buildFinal(self):
        '''End titles window.'''
        self.qtitle.set_markup("<b>Game Over</b>")
        self.quest.set_text("No more questions!! FIXME: here you'll be able to save")
        self.panel.clear()

class SimpleRadioButton(gtk.VBox):
    '''Simple to use radiobutton.'''
    def __init__(self, callback):
        super(SimpleRadioButton,self).__init__()
        self.selected = None
        self._rb = None
        self.callback = callback
        self.active = None

    def add(self, text, obj):
        self._rb = gtk.RadioButton(self._rb, text)
        self._rb.connect("toggled", self._changed, obj)
        self.pack_start(self._rb, False, False)
        if self.active is None:
            self.active = obj
        
    def _changed(self, widget, obj):
        if widget.get_active():
            self.callback(obj)
            self.active = obj

class WizardChooser(entries.RememberingWindow):
    '''Window that let's the user to choose a Wizard.

    @author: Facundo Batista <facundobatista =at= taniquetil.com.ar>
    '''
    def __init__(self, w3af):
        super(WizardChooser,self).__init__(w3af, "wizardchooser", "w3af - Wizard Chooser")
        self.set_icon_from_file('core/ui/gtkUi/data/w3af_icon.png')
        self.w3af = w3af

        # the image at the left
        mainhbox = gtk.HBox()
        self.vbox.pack_start(mainhbox)
        leftframe = gtk.image_new_from_file('core/ui/gtkUi/data/wizard_frame.png')
        mainhbox.pack_start(leftframe, False, False)
        mainvbox = gtk.VBox()
        mainhbox.pack_start(mainvbox)

        # the message
        l = gtk.Label("Select the wizard to run:")
        mainvbox.pack_start(l, False, False, padding = 10)

        # radiobutton and descrip
        innerbox = gtk.HBox()
        self.rbuts = SimpleRadioButton(self._changedRB)
        initlabel = None
        for wiz in self._getWizards():
            if initlabel is None:
                initlabel = wiz.getWizardDescription()
            self.rbuts.add(wiz.getName(), wiz)
        innerbox.pack_start(self.rbuts, True, False)

        self.wizdesc = gtk.Label(initlabel)
        innerbox.pack_start(self.wizdesc)
        mainvbox.pack_start(innerbox, True, False)

        # go button
        buthbox = gtk.HBox()
        gobtn = gtk.Button("Run the wizard")
        gobtn.connect("clicked", self._goWizard)
        buthbox.pack_start(gobtn, True, False)
        mainvbox.pack_start(buthbox, False, False, padding = 10)
        
        # Show all!
        self.show_all()

    def _changedRB(self, widget):
        '''The radiobutton changed.'''
        self.wizdesc.set_label(widget.getWizardDescription())

    def _goWizard(self, widget):
        '''Runs the selected wizard.'''
        self.destroy()
        Wizard(self.w3af, self.rbuts.active)

    def _getWizards(self):
        '''Returns the existing wizards.'''
        wizs = []
        for arch in os.listdir("core/controllers/wizard/wizards"):
            if arch.endswith(".py") and not arch.startswith("__"):
                base = arch[:-3]
                modbase = __import__("core.controllers.wizard.wizards."+base, fromlist=[None])
                cls = getattr(modbase, base)
                wizs.append(cls())
        return wizs
