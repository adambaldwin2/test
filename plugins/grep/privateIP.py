'''
privateIP.py

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
from core.controllers.basePlugin.baseGrepPlugin import baseGrepPlugin
import core.data.kb.knowledgeBase as kb
import core.data.kb.vuln as vuln
import core.data.parsers.urlParser as uparser
import re
from core.data.getResponseType import *
import core.data.constants.severity as severity

class privateIP(baseGrepPlugin):
    '''
    Find private IP addresses on the response body and headers.
      
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''

    def __init__(self):
        baseGrepPlugin.__init__(self)
        self._classA = re.compile('(10\.\d?\d?\d?\.\d?\d?\d?\.\d?\d?\d?)')
        self._classB = re.compile('(172\.[1-3]\d?\d?\.\d?\d?\d?\.\d?\d?\d?)')
        self._classC = re.compile('(192\.168\.\d?\d?\d?\.\d?\d?\d?)')
        self._regexList = [self._classA, self._classB, self._classC ]
        
    def _testResponse(self, request, response):
        
        headers = response.getHeaders()
        
        for regex in self._regexList:
            for h in headers.keys():
                val = headers[ h ]
                header = "%s: %s" % (h,val)
                res = regex.search( header )
                if res:                 
                    v = vuln.vuln()
                    v.setURL( response.getURL() )
                    v.setId( response.id )
                    v.setSeverity(severity.LOW)
                    v.setName( 'Private IP disclosure vulnerability' )
                    
                    v.setDesc( "The URL : " + v.getURL() + " returned an HTTP header with an IP address :" +  header )
                    v['header'] = header
                    kb.kb.append( self, 'header', v )       
        
        # Search for IP addresses on HTML
        if isTextOrHtml(response.getHeaders()):
            for regex in self._regexList:
                res = regex.search(response.getBody())
                if res:                 
                    for match in res.groups():
                        v = vuln.vuln()
                        v.setURL( response.getURL() )
                        v.setId( response.id )
                        v.setSeverity(severity.LOW)
                        v.setName( 'Private IP disclosure vulnerability' )
                        
                        v.setDesc( "The URL : " + v.getURL() + " returned an HTML document with an IP address : " + match )
                        v['html'] = match
                        kb.kb.append( self, 'html', v )     

    def setOptions( self, OptionList ):
        pass
    
    def getOptions( self ):
        '''
        @return: A list of option objects for this plugin.
        '''    
        ol = optionList()
        return ol

    def end(self):
        '''
        This method is called when the plugin wont be used anymore.
        '''
        self.printUniq( kb.kb.getData( 'privateIP', 'header' ), None )
        self.printUniq( kb.kb.getData( 'privateIP', 'html' ), None )
            
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
        This plugin greps every page body and headers for private IP addresses.
        '''
