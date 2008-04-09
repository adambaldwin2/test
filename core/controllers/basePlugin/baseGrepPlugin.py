'''
baseGrepPlugin.py

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

import core.data.parsers.urlParser
from core.controllers.basePlugin.basePlugin import basePlugin
import core.controllers.outputManager as om
import core.data.kb.config as cf
import urllib
import core.data.parsers.urlParser as urlParser

class baseGrepPlugin(basePlugin):
    '''
    This is the base class for grep plugins, all grep plugins should inherit from it 
    and implement the following methods :
        1. testResponse(...)
        2. setOptions( OptionList )
        3. getOptionsXML()

    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''

    def __init__(self):
        basePlugin.__init__( self )
        self._urlOpener = None
        self._alreadyTested = []

    def testResponse(self, fuzzableRequest, response):
        '''
        This method tries to find patterns on responses.
        
        This method CAN be implemented on a plugin, but its better to do your searches in _testResponse().
        
        @param response: This is the httpResponse object to test.
        @param fuzzableRequest: This is the fuzzable request object that generated the current response being analyzed.
        @return: If something is found it must be reported to the Output Manager and the KB.
        '''
        if fuzzableRequest in self._alreadyTested:
            # The __eq__ includes, url, method and dc !
            #om.out.debug('Grep plugins not testing: ' + fuzzableRequest.getURL() + ' cause it was already tested.' )
            pass
        elif urlParser.getDomain( fuzzableRequest.getURL() ) in cf.cf.getData('targetDomains'):
            self._alreadyTested.append( fuzzableRequest )
            self._testResponse( fuzzableRequest, response )
        else:
            #om.out.debug('Grep plugins not testing: ' + fuzzableRequest.getURL() + ' cause it aint a target domain.' )
            pass
    
    def _wasSent( self, request, theWord ):
        '''
        Checks if the theWord was sent in the request, this is mainly used to avoid false positives.
        '''
        
        if request.getMethod().upper() == 'POST':
            sentData = request.getData()
            if sentData == None:
                sentData = ''
            else:
                sentData = urllib.unquote( sentData )
        else:
            url = urllib.unquote( request.getURL() )
            dp = urlParser.getDomainPath( url )
            sentData = url.replace( dp, '' )
        
        if sentData.count( theWord ):
            return True
        else:
            return False
            
    def _testResponse( self, request, response ):
        '''
        This method tries to find patterns on responses.
        
        This method MUST be implemented on every plugin.
        
        @param response: This is the htmlString response to test
        @param request: This is the request object that generated the current response being analyzed.
        @return: If something is found it must be reported to the Output Manager and the KB.
        '''
        raise w3afException('Plugin is not implementing required method _testResponse' )
        
    def setUrlOpener(self, foo):
        pass
        
    def getType( self ):
        return 'grep'
