'''
confpanel.py

Copyright 2007 Andres Riancho

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

import pygtk
pygtk.require('2.0')
import gtk
import xml.dom
import core.ui.gtkUi.entries as entries
import core.ui.gtkUi.helpers as helpers
from core.controllers.w3afException import w3afException
from core.controllers.basePlugin.basePlugin import basePlugin

# decision of which widget implements the option to each type
wrapperWidgets = {
    "boolean": entries.BooleanOption,
    "integer": entries.IntegerOption,
    "string": entries.StringOption,
    "float": entries.FloatOption,
    "list": entries.ListOption,
}

class Option(object):
    '''Plugin configuration option.

    @param option: an XML node with the option information

    Received the semiparsed XML from the plugin, and store in self the 
    option attributes (default, desc, help and type).

    @author: Facundo Batista <facundobatista =at= taniquetil.com.ar>
    '''
    def __init__(self, option):
        self.name = option.getAttribute('name')
        for tag in "default desc help type".split():
            try:
                value = option.getElementsByTagName(tag)[0].childNodes[0].data
            except:
                value = ""
            setattr(self, tag, value)

    def __str__(self):
        return "Option %s <%s> [%s] (%s)" % (self.name, self.type, self.default, self.desc)

    def getFullConfig(self):
        '''Collects the configuration of the plugin in a dict.

        @return: A dict with the configuration.
        '''
        d = {}
        for tag in "desc help type".split():
            d[tag] = getattr(self, tag)
        d['default'] = self.widg.getValue()
        return d
        

class EasyTable(gtk.Table):
    '''Simplification of gtk.Table.

    @param arg: all it receives goes to gtk.Table
    @param kw: all it receives goes to gtk.Table

    This class is to have a simple way to add rows to the table.

    @author: Facundo Batista <facundobatista =at= taniquetil.com.ar>
    '''
    def __init__(self, *arg, **kw):
        super(EasyTable,self).__init__(*arg, **kw)
        self.auto_rowcounter = 0
        self.set_row_spacings(1)

    def autoAddRow(self, *widgets):
        '''Simple way to add rows to a table.

        @param widgets: all the widgets to the row

        This method creates a new row, adds the widgets and show() them.
        '''
        r = self.auto_rowcounter
        for i,widg in enumerate(widgets):
            if widg is not None:
                self.attach(widg, i, i+1, r, r+1, yoptions=gtk.EXPAND, xpadding=5)
                widg.show()
        self.auto_rowcounter += 1


class OnlyOptions(gtk.VBox):
    '''Only the options for configuration.

    @param parentwidg: The parentwidg, to propagate changes
    @param plugin: The selected plugin, for which the configuration is.
    @param options: The options to configure.
    @param save_btn: The save button.
    @param rvrt_btn: The revert button.

    @author: Facundo Batista <facundobatista =at= taniquetil.com.ar>
    '''
    def __init__(self, parentwidg, w3af, plugin, save_btn, rvrt_btn):
        super(OnlyOptions,self).__init__()
        self.set_spacing(5)
        self.w3af = w3af
        self.parentwidg = parentwidg

        # options
        self.options = []
        xmloptions = plugin.getOptionsXML()
        xmlDoc = xml.dom.minidom.parseString(xmloptions)
        for xmlOpt in xmlDoc.getElementsByTagName('Option'):
            option = Option(xmlOpt)
            self.options.append(option)

        # buttons
        save_btn.connect("clicked", self._savePanel, plugin)
        save_btn.set_sensitive(False)
        rvrt_btn.set_sensitive(False)
        rvrt_btn.connect("clicked", self._revertPanel)
        self.save_btn = save_btn
        self.rvrt_btn = rvrt_btn
        
        # middle table (the heart of the panel)
        if self.options:
            tabbox = gtk.HBox()
            table = self._makeTable()
            tabbox.pack_start(table, expand=False)
            tabbox.show()
            self.pack_start(tabbox, expand=True, fill=False)
        self.show()

    def _makeTable(self):
        '''Creates the table in which all the options are shown.

        @return: The created table

        For each row, it will put:

            - the option label
            - the configurable widget (textentry, checkbox, etc.)
            - an optional button to get more help (if the help is available)

        Also, the configurable widget gets a tooltip for a small description.
        '''
        table = EasyTable(len(self.options), 3)
        self.widgets_status = {}
        self.propagAnyWidgetChanged = helpers.PropagateBuffer(self._changedAnyWidget)
        tooltips = gtk.Tooltips()
        for i,opt in enumerate(self.options):
            titl = gtk.Label(opt.name)
            titl.set_alignment(0.0, 0.5)
#            propagWidgetChanged = helpers.PropagateBuffer(self._changedWidget)
            widg = wrapperWidgets[opt.type](self._changedWidget, opt.default)
            opt.widg = widg
            tooltips.set_tip(widg, opt.desc)
            if opt.help:
                helpbtn = entries.SemiStockButton("", gtk.STOCK_INFO)
                cleanhelp = helpers.cleanDescription(opt.help)
                helpbtn.connect("clicked", self._showHelp, cleanhelp)
            else:
                helpbtn = None
            table.autoAddRow(titl, widg, helpbtn)
            self.widgets_status[widg] = (titl, opt.name, "<b>%s</b>" % opt.name)
        table.show()
        return table

    def _changedAnyWidget(self, like_initial):
        '''Adjust the save/revert buttons and alert the tree of the change.

        @param like_initial: if the widgets are modified or not.

        It only will be called if any widget changed its state, through
        a propagation buffer.
        '''
        self.save_btn.set_sensitive(not like_initial)
        self.rvrt_btn.set_sensitive(not like_initial)
        self.parentwidg.configChanged(like_initial)

    def _changedWidget(self, widg, like_initial):
        '''Receives signal when a widget changed or not.

        @param widg: the widget who changed.
        @param like_initial: if it's modified or not

        Handles the boldness of the option label and then propagates
        the change.
        '''
        (labl, orig, chng) = self.widgets_status[widg]
        if like_initial:
            labl.set_text(orig)
        else:
            labl.set_markup(chng)
        self.propagAnyWidgetChanged.change(widg, like_initial)

    def _showHelp(self, widg, helpmsg):
        '''Shows a dialog with the help message of the config option.

        @param widg: the widget who generated the signal
        @param helpmsg: the message to show in the dialog
        '''
        dlg = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_OK, helpmsg)
        dlg.set_title('Plugin help')
        dlg.run()
        dlg.destroy()

    def _savePanel(self, widg, plugin):
        '''Saves the config changes to the plugins.

        @param widg: the widget who generated the signal
        @param plugin: the plugin to save the configuration

        First it checks if there's some invalid configuration, then gets the value of 
        each option and save them to the plugin.
        '''
        # check if all widgets are valid
        invalid = []
        for opt in self.options:
            if hasattr(opt.widg, "isValid"):
                if not opt.widg.isValid():
                    invalid.append(opt.name)
        if invalid:
            msg = "The configuration can't be saved, there is a problem in the following parameter(s):\n\n"
            msg += "\n".join(invalid)
            dlg = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_WARNING, gtk.BUTTONS_OK, msg)
            dlg.set_title('Configuration error')
            dlg.run()
            dlg.destroy()
            return

        # we get the values, save, and if the save is ok, we
        # fix the values in the widgets
        tosave = {}
        for opt in self.options:
            tosave[opt.name] = opt.getFullConfig()

        try:
            if isinstance(plugin, basePlugin):
                helpers.coreWrap(self.w3af.setPluginOptions, plugin.pname, plugin.ptype, tosave)
            else:
                helpers.coreWrap(plugin.setOptions, tosave)
        except w3afException:
            return
        for opt in self.options:
            opt.widg.save()

    def _revertPanel(self, *vals):
        '''Revert all widgets to their initial state.'''
        for widg in self.widgets_status:
            widg.revertValue()
