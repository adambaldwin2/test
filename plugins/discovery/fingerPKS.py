'''
fingerPKS.py

Copyright 2006 Andres Riancho

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

import core.controllers.outputManager as om

# options
from core.data.options.option import option
from core.data.options.optionList import optionList

from core.controllers.basePlugin.baseDiscoveryPlugin import baseDiscoveryPlugin
from core.controllers.w3afException import w3afException
from core.controllers.w3afException import w3afRunOnce

import core.data.kb.knowledgeBase as kb
import core.data.kb.info as info

from core.data.searchEngines.pks import pks as pks
import core.data.parsers.urlParser as urlParser


class fingerPKS(baseDiscoveryPlugin):
    '''
    Search MIT PKS to get a list of users for a domain.
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''

    def __init__(self):
        baseDiscoveryPlugin.__init__(self)
        
        # Internal variables
        self._run = True
        
    def discover(self, fuzzableRequest ):
        '''
        @parameter fuzzableRequest: A fuzzableRequest instance that contains (among other things) the URL to test.
        '''
        if not self._run:
            # This will remove the plugin from the discovery plugins to be runned.
            raise w3afRunOnce()
        else:
            # This plugin will only run one time. 
            self._run = False
            
            pks_se = pks( self._urlOpener)
            
            url = fuzzableRequest.getURL()
            domain_root = urlParser.getRootDomain( url )
            
            results = pks_se.search( domain_root )
            for result in results:
                i = info.info()
                i.setURL( 'http://pgp.mit.edu:11371/' )
                i.setId( [] )
                mail = result.username +'@' + domain_root
                i.setName( mail )
                i.setDesc( 'The mail account: "'+ mail + '" was found in the MIT PKS server. ' )
                i['mail'] = mail
                i['user'] = result.username
                i['name'] = result.name
                kb.kb.append( 'mails', 'mails', i )
                #   Don't save duplicated information in the KB. It's useless.
                #kb.kb.append( self, 'mails', i )
                om.out.information( i.getDesc() )

        return []
    
    def getOptions( self ):
        '''
        @return: A list of option objects for this plugin.
        '''    
        ol = optionList()
        return ol

    def setOptions( self, OptionList ):
        '''
        This method sets all the options that are configured using the user interface 
        generated by the framework using the result of getOptions().
        
        @parameter OptionList: A dictionary with the options for the plugin.
        @return: No value is returned.
        ''' 
        pass


    def getPluginDeps( self ):
        '''
        @return: A list with the names of the plugins that should be runned before the
        current one.
        '''
        return []

    def getLongDesc( self ):
        '''
        @return: A DETAILED description of the plugin functions and features.
        '''
        return '''
        This plugin finds mail addresses in PGP PKS servers.
        '''
