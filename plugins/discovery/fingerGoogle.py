'''
fingerGoogle.py

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
from core.data.searchEngines.google import google as google
from core.controllers.basePlugin.baseDiscoveryPlugin import baseDiscoveryPlugin
import core.data.parsers.urlParser as urlParser
import core.data.parsers.dpCache as dpCache
from core.controllers.w3afException import w3afRunOnce

class fingerGoogle(baseDiscoveryPlugin):
    '''
    Search Google using the Google API to get a list of users for a domain.
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''
    
    '''
    Go here to get a API License : http://www.google.com/apis/
    
    Get pygoogle from : http://pygoogle.sourceforge.net/
    
    This plugin wont use proxy/proxy auth/auth/etc settings (for now). Original
    stand alone version that did not used pygoogle by Sergio Alvarez shadown@gmail.com .
    
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''

    def __init__(self):
        baseDiscoveryPlugin.__init__(self)
        
        # Internal variables
        self._run = True
        self._accounts = []
        
        # User configured 
        self._key = ''
        self._resultLimit = 300
        self._fastSearch = False
        
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
            
            self._google = google( self._urlOpener, self._key )
            self._domain = domain = urlParser.getDomain( fuzzableRequest.getURL() )
            self._domainRoot = urlParser.getRootDomain( domain )
            
            if self._fastSearch:
                self._doFastSearch( domain )
            else:
                self._doCompleteSearch( domain )
            
            self._tm.join( self )
            self.printUniq( kb.kb.getData( 'fingerGoogle', 'mails' ), None )
            return []

    def _doFastSearch( self, domain ):
        '''
        Only search for mail addresses in the google result page.
        '''
        resultPageObjects = self._google.getNResultPages( '@'+ self._domainRoot , self._resultLimit )
        
        for result in resultPageObjects:
            self._parseDocument( result )
        
    def _doCompleteSearch( self, domain ):
        '''
        Performs a complete search for email addresses.
        '''
        results = self._google.getNResults( '@'+ self._domainRoot , self._resultLimit )
        
        for result in results:
            targs = (result,)
            self._tm.startFunction( target=self._findAccounts, args=targs, ownerObj=self )
            
    def _findAccounts(self, googlePage ):
        '''
        Finds mails in google result.
        
        @return: A list of valid accounts
        '''
        try:
            om.out.debug('Searching for mails in: ' + googlePage.URL )
            if self._domain == urlParser.getDomain( googlePage.URL ):
                response = self._urlOpener.GET( googlePage.URL, useCache=True, grepResult=True )
            else:
                response = self._urlOpener.GET( googlePage.URL, useCache=True, grepResult=False )
        except KeyboardInterrupt, e:
            raise e
        except w3afException, w3:
            pass
        except Exception, e:
            om.out.debug('URL Error while fetching page in fingerGoogle, error: ' + str(e) )
        else:
            self._parseDocument( response )
            
    def _parseDocument( self, response ):
        '''
        Parses the HTML and adds the mail addresses to the kb.
        '''
        dp = dpCache.dpc.getDocumentParserFor( response.getBody(), 'http://'+self._domainRoot+'/' )
        for account in dp.getAccounts():
            if account not in self._accounts:
                self._accounts.append( account )
                
                i = info.info()
                mail = account + '@' + self._domainRoot
                i.setName(mail)
                i.setURL( response.getURI() )
                i.setDesc( 'The mail account: "'+ mail + '" was found in: "' + response.getURI() + '"' )
                i['mail'] = mail
                i['user'] = account
                kb.kb.append( 'mails', 'mails', i )
                kb.kb.append( self, 'mails', i )
    
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
            <Option name="key">\
                <default>'+self._key+'</default>\
                <desc>Google API License key</desc>\
                <type>string</type>\
                <help>To use this plugin you have to own your own google API license key OR you can directly use the search engine using clasic HTTP. If this parameter is left blank, the search engine will be used, otherwise the google webservice will be used.Go to http://www.google.com/apis/ to get more information.</help>\
            </Option>\
            <Option name="resultLimit">\
                <default>'+str(self._resultLimit)+'</default>\
                <desc>Fetch the first "resultLimit" results from the Google search</desc>\
                <type>integer</type>\
                <help></help>\
            </Option>\
            <Option name="fastSearch">\
                <default>'+str(self._fastSearch)+'</default>\
                <desc>Do a fast search, when this feature is enabled, not all mail addresses are found</desc>\
                <type>boolean</type>\
                <help>This method is faster, because it only searches for emails in the small page snippet that google shows\
                to the user after performing a common search.</help>\
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
        self._key = optionsMap['key']
        self._resultLimit = optionsMap['resultLimit']
        self._fastSearch = optionsMap['fastSearch']
            
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
        This plugin finds mail addresses in google.
        
        Two configurable parameters exist:
            - key
            - resultLimit
            - fastSearch
        
        If fastSearch is set to False, this plugin searches google for : "@domain.com", requests all search results and parses 
        them in order   to find new mail addresses. If the fastSearch configuration parameter is set to True, only mail addresses
        that appear on the google result page are parsed and added to the list, the result links are\'nt visited.
        '''
