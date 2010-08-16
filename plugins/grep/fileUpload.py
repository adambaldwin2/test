'''
fileUpload.py

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
import core.data.kb.info as info

import re


class fileUpload(baseGrepPlugin):
    '''
    Find HTML forms with file upload capabilities.
      
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''

    def __init__(self):
        baseGrepPlugin.__init__(self)

    def grep(self, request, response):
        '''
        Plugin entry point, verify if the HTML has a form with file uploads.
        
        @parameter request: The HTTP request object.
        @parameter response: The HTTP response object
        @return: None
        '''
        if response.is_text_or_html():
            
            dom = response.getDOM()
            
            # In some strange cases, we fail to normalize the document
            if dom != None:
                
                # Find all input tags
                element_list = dom.findall( 'input' )
            
                for element in element_list:
                    
                    if 'type' in element.attrib and element.attrib['type'].lower() == 'file':
                        i = info.info()
                        i.setName('File upload form')
                        i.setURL( response.getURL() )
                        i.setId( response.id )
                        msg = 'The URL: "' + response.getURL() + '" has form '
                        msg += 'with file upload capabilities.'
                        i.setDesc( msg )
                        i.addToHighlight( tag.group(0) )
                        kb.kb.append( self , 'fileUpload' , i ) 
    
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
        self.printUniq( kb.kb.getData( 'fileUpload', 'fileUpload' ), 'URL' )

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
        This plugin greps every page for forms with file upload capabilities.
        '''
