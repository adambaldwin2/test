'''
metaTags.py

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

import core.data.parsers.dpCache as dpCache
import core.controllers.outputManager as om
from core.controllers.basePlugin.baseGrepPlugin import baseGrepPlugin
import core.data.kb.knowledgeBase as kb
import core.data.kb.vuln as vuln
from core.data.getResponseType import *

class metaTags(baseGrepPlugin):
    '''
    Grep every page for interesting meta tags.
      
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''

    def __init__(self):
        baseGrepPlugin.__init__(self)
        
        self.is404 = None
        self._comments = {}
        self._search404 = False
        
        self._interestingWords = ['user', 'pass', 'microsoft', 'visual', 'linux', 'source', 
        'author', 'release', 'version', 'verify-v1' ]
        
        '''
        Can someone explain what this meta tag does?
        <meta name="verify-v1" content="/JBoXnwT1d7TbbWCwL8tXe+Ts2I2LXYrdnnK50g7kdY=" /> 
        
        Answer:
        That's one of the verification elements used by Google Sitemaps. When you sign up for Sitemaps you 
        have to add that element to a root page to demonstrate to Google that you're the site owner. So there is 
        probably a Sitemaps account for the site, if you haven't found it already. 
        '''
        
        self._alreadyReportedInteresting = {}
        
    def _testResponse(self, request, response):
        
        if isTextOrHtml(response.getHeaders()):
            self.is404 = kb.kb.getData( 'error404page', '404' )
            
            if not self.is404( response ):
                dp = dpCache.dpc.getDocumentParserFor( response.getBody(), response.getURL() )
                metaTagList = dp.getMetaTags()
                
                for tag in metaTagList:
                    name = self._findName( tag )
                    for attr in tag:
                        for word in self._interestingWords:
                            if ( word in attr[0].lower() ) or ( word in attr[1].lower() ):
                                # The atribute is interesting!
                                
                                # Init the map if necesary
                                if response.getURL() not in self._alreadyReportedInteresting:
                                    self._alreadyReportedInteresting[ response.getURL() ] = []
                                    
                                self._alreadyReportedInteresting[ response.getURL() ].append( (name,attr[1]) )
                            else:
                                # The attribute ain't interesting
                                pass
    
    def _findName( self, tag ):
        '''
        @return: the tag name.
        '''
        for attr in tag:
            if attr[0].lower() == 'name':
                return attr[1]
        return ''
        
    def setOptions( self, optionsMap ):
        self._search404 = optionsMap['search404']
    
    def getOptionsXML(self):
        '''
        This method returns a XML containing the Options that the plugin has.
        Using this XML the framework will build a window, a menu, or some other input method to retrieve
        the info from the user. The XML has to validate against the xml schema file located at :
        w3af/core/output.xsd
        '''
        return  '<?xml version="1.0" encoding="ISO-8859-1"?>\
        <OptionList>\
            <Option name="search404">\
                <default>'+str(self._search404)+'</default>\
                <desc>Search comments on 404 pages.</desc>\
                <type>boolean</type>\
            </Option>\
        </OptionList>\
        '

    def end(self):
        '''
        This method is called when the plugin wont be used anymore.
        '''
        for url in self._alreadyReportedInteresting:
            om.out.information('The page at: ' + url + ' sent the following interesting meta tags:' )
            for reported in self._alreadyReportedInteresting[ url ]:
                name = reported[0]
                content = reported[1]
                om.out.information('- ' + name + ' = ' + content )

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
        This plugin greps every page for interesting meta tags. Some interesting meta tags are the ones
        that contain : 'microsoft', 'visual', 'linux' .
        '''
