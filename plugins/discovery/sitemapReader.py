'''
sitemapReader.py

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
from core.controllers.basePlugin.baseDiscoveryPlugin import baseDiscoveryPlugin
import core.data.kb.knowledgeBase as kb
import core.data.parsers.urlParser as urlParser
from core.controllers.w3afException import *

class sitemapReader(baseDiscoveryPlugin):
    '''
    Analyze the sitemap.xml file and find new URLs
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''

    def __init__(self):
        baseDiscoveryPlugin.__init__(self)
        self._exec = True

    def discover(self, fuzzableRequest ):
        '''
        Get the sitemap.xml file and parse it.
        
        @parameter fuzzableRequest: A fuzzableRequest instance that contains (among other things) the URL to test.
        '''
        if not self._exec:
            # This will remove the plugin from the discovery plugins to be runned.
            raise w3afRunOnce()
        else:
            # Only run once
            self._exec = False
            self._fuzzableRequests = []
            self.is404 = kb.kb.getData( 'error404page', '404' )
            
            baseUrl = urlParser.baseUrl( fuzzableRequest.getURL() )
            sitemapUrl = urlParser.urlJoin(  baseUrl , 'sitemap.xml' )
            response = self._urlOpener.GET( sitemapUrl, useCache=True )
            
            if not self.is404( response ) and '</urlset>' in response.getBody():
                om.out.debug('Analyzing sitemap.xml file.')
                
                self._fuzzableRequests.extend( self._createFuzzableRequests( response ) )
                
                import xml.dom.minidom
                om.out.debug('Parsing xml file with xml.dom.minidom.')
                try:
                    dom = xml.dom.minidom.parseString( response.getBody() )
                except:
                    raise w3afException('Error while parsing sitemap.xml')
                urlList = dom.getElementsByTagName("loc")
                for url in urlList:
                    url = url.childNodes[0].data 
                    om.out.information( 'sitemapReader found a new URL: ' + url )
                    response = self._urlOpener.GET( url, useCache=True )
                    self._fuzzableRequests.extend( self._createFuzzableRequests( response ) )

        return self._fuzzableRequests
        
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
        </OptionList>\
        '

    def setOptions( self, OptionList ):
        '''
        This method sets all the options that are configured using the user interface 
        generated by the framework using the result of getOptionsXML().
        
        @parameter OptionList: A dictionary with the options for the plugin.
        @return: No value is returned.
        ''' 
        pass

    def getPluginDeps( self ):
        '''
        @return: A list with the names of the plugins that should be runned before the
        current one.
        '''
        return ['discovery.error404page']
    
    def getLongDesc( self ):
        '''
        @return: A DETAILED description of the plugin functions and features.
        '''
        return '''
        This plugin searches for the sitemap.xml file, and parses it.
        
        The sitemap.xml file is used by the site administrator to give the google search engine more information
        about the site. By parsing this file, the plugin will find new URL's and other usefull information.
        '''
