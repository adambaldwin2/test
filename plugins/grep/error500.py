'''
error500.py

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
from core.data.getResponseType import *
import re
import core.data.constants.severity as severity

class error500(baseGrepPlugin):
    '''
    Grep every page for error 500 pages that haven't been identified as bugs by other plugins.
      
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''

    def __init__(self):
        baseGrepPlugin.__init__(self)
        
        self._error500responses = []
        
    def _testResponse(self, request, response):
        
        if isTextOrHtml(response.getHeaders()) and response.getCode() in range( 400,600 )\
        and response.getCode() not in ( 404 , 403 ) and not self._falsePositive( response ):
            self._error500responses.append( (request,response) )
    
    def _falsePositive( self, response ):
        '''
        Filters out some false positives like this one:
        This false positive is generated by IIS when I send an URL that's "odd"
        Some examples of URLs that trigger this false positive:
            - http://127.0.0.2/ext.ini.%00.txt
            - http://127.0.0.2/%00/
            - http://127.0.0.2/%0a%0a<script>alert(\Vulnerable\)</script>.jsp
        
        @return: True if the response is a false positive.
        '''
        falsePositiveStrings = []
        falsePositiveStrings.append( '<h1>Bad Request (Invalid URL)</h1>' )
        for fps in falsePositiveStrings:
            if response.getBody() == fps:
                return True
        return False
    
    def getOptions( self ):
        '''
        @return: A list of option objects for this plugin.
        '''    
        ol = optionList()
        return ol
        
    def setOptions( self , o ):
        pass
        
    def end(self):
        '''
        This method is called when the plugin wont be used anymore.
        
        The real job of this plugin is done here, where I will try to see if one
        of the error500 responses were not identified as a vuln by some of my audit plugins
        '''
        allVulns = kb.kb.getAllVulns()
        #allInfos = kb.kb.getAllInfos()
        all = []
        all.extend( allVulns )
        #all.extend( allInfos )
        all = [ (v.getURI(), v.getDc()) for v in all ]
        for request, error500 in self._error500responses:
            if ( error500.getURI() , request.getDc() ) not in all:
                # Found a err 500 that wasnt identified !!!
                v = vuln.vuln()
                v.setURI( error500.getURI() )
                v.setURL( error500.getURL() )
                v.setId( error500.id )
                v.setSeverity(severity.MEDIUM)
                v.setName( 'Unhandled error in web application' )
                v.setDesc( 'An unidentified error was found at URL ' + v.getURL() +' . Enable all plugins and try again, if this is error still is not identified, please verify mannually.' )
                kb.kb.append( self, 'error500', v )
                
        self.printUniq( kb.kb.getData( 'error500', 'error500' ), 'VAR' )

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
        This plugin greps every page for error 500 pages that havent been catched by other plugins. By enabling this,
        you are enabling a "safety net" that will catch all bugs that havent been catched by other plugins.
        '''
