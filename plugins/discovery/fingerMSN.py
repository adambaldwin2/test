'''
fingerMSN.py

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
from core.controllers.w3afException import w3afException
import core.data.kb.knowledgeBase as kb
import core.data.kb.info as info
from core.data.searchEngines.msn import msn as msn
from core.controllers.basePlugin.baseDiscoveryPlugin import baseDiscoveryPlugin
import core.data.parsers.urlParser as urlParser
import core.data.parsers.dpCache as dpCache
from core.controllers.w3afException import w3afRunOnce

class fingerMSN(baseDiscoveryPlugin):
    '''
    Search MSN to get a list of users for a domain.
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''
    
    def __init__(self):
        baseDiscoveryPlugin.__init__(self)
        
        # Internal variables
        self._run = True
        self._accounts = []
        
        # User configured 
        self._resultLimit = 300
        
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
            newUsers = []
            self._msn = msn( self._urlOpener )
            
            self._domain = domain = urlParser.getDomain( fuzzableRequest.getURL() )
            
            try:
                self._domainRoot = urlParser.getRootDomain( domain )
            except Exception, e:
                om.out.debug( str(e) )
            else:
                results = self._msn.getNResults('@'+ self._domainRoot, self._resultLimit)
                    
                for result in results:
                    targs = (result,)
                    self._tm.startFunction( target=self._findAccounts, args=targs , ownerObj=self )

                self._tm.join( self )
                self.printUniq( kb.kb.getData( 'fingerMSN', 'mails' ), None )
                
        return []
    
    def _findAccounts(self, msnPage ):
        '''
        Finds mails in msn result.
        
        @return: A list of valid accounts
        '''
        try:
            om.out.debug('Searching for mails in: ' + msnPage.URL )
            if self._domain == urlParser.getDomain( msnPage.URL ):
                response = self._urlOpener.GET( msnPage.URL, useCache=True, grepResult=True )
            else:
                response = self._urlOpener.GET( msnPage.URL, useCache=True, grepResult=False )
        except KeyboardInterrupt, e:
            raise e
        except w3afException, w3:
            pass
        except Exception, e:
            om.out.debug('URL Error while fetching page in googleSpider, error: ' + str(ue) )
            self._newAccounts = []
        else:
            dp = dpCache.dpc.getDocumentParserFor( response.getBody(), 'http://'+self._domainRoot+'/' )
            for account in dp.getAccounts():
                if account not in self._accounts:
                    self._accounts.append( account )

                    i = info.info()
                    i.setURL( msnPage.URL )
                    mail = account +'@' + self._domainRoot
                    i.setName( mail )
                    i.setDesc( 'The mail account: "'+ mail + '" was found in: "' + msnPage.URL + '"' )
                    i['mail'] = mail
                    i['user'] = account
                    kb.kb.append( 'mails', 'mails', i )
                    kb.kb.append( 'fingerMSN', 'mails', i )
    
    def getOptionsXML(self):
        '''
        This method returns a XML containing the Options that the plugin has.
        Using this XML the framework will build a window, a menu, or some other input method to retrieve
        the info from the user. The XML has to validate against the xml schema file located at :
        w3af/core/ui/userInterface.dtd
        
        @return: XML with the plugin options.
        ''' 
        return  '<?xml version="1.0" encoding="ISO-8859-1"?>\
        <OptionList>\
            <Option name="resultLimit">\
                <default>'+str(self._resultLimit)+'</default>\
                <desc>Fetch the first "resultLimit" results from the MSN search</desc>\
                <type>integer</type>\
                <help></help>\
            </Option>\
        </OptionList>\
        '

    def setOptions( self, optionsMap ):
        '''
        This method sets all the options that are configured using the user interface 
        generated by the framework using the result of getOptionsXML().
        
        @parameter OptionList: A dictionary with the options for the plugin.
        @return: No value is returned.
        ''' 
        self._resultLimit = optionsMap['resultLimit']
            
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
        This plugin finds mail addresses in MSN search engine.
        
        One configurable parameter exist:
            - resultLimit
        
        This plugin searches MSN for : "@domain.com", requests all search results and parses them in order
        to find new mail addresses.
        '''
