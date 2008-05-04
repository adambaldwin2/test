'''
rootMenu.py

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

from core.ui.consoleUi.menu import *
from core.ui.consoleUi.plugins import *
from core.ui.consoleUi.profiles import *
from core.ui.consoleUi.exploit import *
import core.controllers.miscSettings as ms
#from core.ui.consoleUi.session import *
from core.ui.consoleUi.util import *


class rootMenu(menu):
    '''
    Main menu
    @author Alexander Berezhnoy (alexander.berezhnoy |at| gmail.com)
    '''

    def __init__(self, name, console, core, parent=None):
        menu.__init__(self, name, console, core, parent)
        self._loadHelp( 'root' )

        mapDict(self.addChild, {
            'plugins': pluginsMenu,
            'target' : (configMenu, self._w3af.target),
            'misc-settings' : (configMenu, ms.miscSettings()),
            'http-settings' : (configMenu, self._w3af.uriOpener.settings),
            'profiles' : profilesMenu,
            'exploit' : exploit,
       })
    
    def _cmd_start(self, params):
        try:
            self._w3af.initPlugins()
            self._w3af.verifyEnvironment()
            self._w3af.start()
        except Exception, e:
            om.out.console(str(e))
 
    def _cmd_version(self, params):
        '''
        Show the w3af version and exit
        '''
        om.out.console( self._w3af.getVersion() )
