'''
httpAuthDetect.py

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

import core.data.parsers.htmlParser as htmlParser
import core.controllers.outputManager as om
from core.controllers.basePlugin.baseGrepPlugin import baseGrepPlugin
import core.data.kb.knowledgeBase as kb
import core.data.kb.info as info
import core.data.kb.vuln as vuln
import re
from core.data.getResponseType import *
import core.data.constants.severity as severity

class httpAuthDetect(baseGrepPlugin):
    '''
    Find responses that indicate that the resource requires auth.
      
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''

    def __init__(self):
        baseGrepPlugin.__init__(self)

    def _testResponse(self, request, response):
        
        if response.getCode() == 401:
            wwwAuth = ''
            for key in response.getHeaders():
                if key.lower() == 'www-authenticate':
                    wwwAuth = response.getHeaders()[ key ]
            
            i = info.info()
            i.setName('HTTP Basic authentication')
            i.setURL( response.getURL() )
            i.setId( response.id )
            i.setDesc( 'The resource: '+ response.getURL() + ' requires authentication.' +
            ' The message is: ' + wwwAuth + ' .')
            i['message'] = wwwAuth
            
            kb.kb.append( self , 'auth' , i )
            om.out.vulnerability( i.getDesc() )
            
        elif re.match( '.*://(.*?):(.*?)@.*' , response.getURL() ):
            # An authentication URI was found!
            
            v = vuln.vuln()
            v.setURL( response.getURL() )
            v.setId( response.id )
            v.setDesc( 'The resource: '+ response.getURL() + ' has a user and password in the URI .')
            v.setSeverity(severity.HIGH)
            v.setName( 'Basic HTTP credentials' )
            
            kb.kb.append( self , 'userPassUri' , v )
            om.out.vulnerability( v.getDesc() )
            
        # I also search for authentication URI's in the body
        # I know that by doing this I loose the chance of finding hashes in PDF files, but...
        # This is much faster
        if isTextOrHtml( response.getHeaders() ):
            for authURI in re.findall( '\w{2,10}://(.*?):(.*?)@' , response.getBody() ):
                v = vuln.vuln()
                v.setURL( response.getURL() )
                v.setId( response.id )
                v.setDesc( 'The resource: '+ response.getURL() + ' has a user and password in the body .')
                
                v.setSeverity(severity.HIGH)
                v.setName( 'Basic HTTP credentials' )
                
                kb.kb.append( self , 'userPassUri' , v )
                om.out.vulnerability( v.getDesc() )
            
    def setOptions( self, OptionList ):
        pass
    
    def getOptionsXML(self):
        '''
        This method returns a XML containing the Options that the plugin has.
        Using this XML the framework will build a window, a menu, or some other input method to retrieve
        the info from the user. The XML has to validate against the xml schema file located at :
        w3af/core/output.xsd
        '''
        return  '<?xml version="1.0" encoding="ISO-8859-1"?>\
        <OptionList>\
        </OptionList>\
        '

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
        This plugin greps every page and finds responses that indicate that the resource requires
        authentication.
        '''
