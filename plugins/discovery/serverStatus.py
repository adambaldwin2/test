'''
serverStatus.py

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
import core.data.kb.knowledgeBase as kb
import core.data.kb.vuln as vuln
import core.data.parsers.urlParser as urlParser
from core.controllers.w3afException import w3afRunOnce
import re
import core.data.constants.severity as severity

class serverStatus(baseDiscoveryPlugin):
    '''
    Find new URL's from the Apache server-status cgi.
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''

    def __init__(self):
        baseDiscoveryPlugin.__init__(self)
        self._exec = True
        self._sharedHostingHosts = []

    def discover(self, fuzzableRequest ):
        '''
        Get the server-status and parse it.
        
        @parameter fuzzableRequest: A fuzzableRequest instance that contains (among other things) the URL to test.
        '''
        res = []
        if not self._exec :
            # This will remove the plugin from the discovery plugins to be runned.
            raise w3afRunOnce()
            
        else:
            # Only run once
            self._exec = False
            
            self.is404 = kb.kb.getData( 'error404page', '404' )
            
            baseUrl = urlParser.baseUrl( fuzzableRequest.getURL() )
            serverStatusUrl = urlParser.urlJoin(  baseUrl , 'server-status' )
            response = self._urlOpener.GET( serverStatusUrl, useCache=True )
            
            if not self.is404( response ) and response.getCode() not in range(400,404):
                om.out.information( 'Apache server-status cgi exists. The URL is: ' + response.getURL() )
                
                # Create some simple fuzzable requests
                res.extend( self._createFuzzableRequests( response ) )
                
                # Now really parse the file and create custom made fuzzable requests
                for domain, path in re.findall('<td>.*?<td nowrap>(.*?)<td nowrap>.*? (.*?) HTTP/1', response.getBody() ):
                    if 'unavailable' in domain:
                        domain = urlParser.getDomain( response.getURL() )
                        
                    foundURL = urlParser.getProtocol( response.getURL() ) + '://' + domain + path
                    # Check if the requested domain and the found one are equal.
                    if urlParser.getDomain( foundURL ) == urlParser.getDomain( response.getURL() ):
                        # They are equal, request the URL and create the fuzzable requests
                        tmpRes = self._urlOpener.GET( foundURL, useCache=True )
                        if not self.is404( tmpRes ):
                            res.extend( self._createFuzzableRequests( tmpRes ) )
                    else:
                        # This is a shared hosting server
                        self._sharedHostingHosts.append( domain )
                
                # Now that we are outsite the for loop, we can report the possible vulns
                if len( self._sharedHostingHosts ):
                    v = vuln.vuln()
                    v.setURL( fuzzableRequest.getURL() )
                    v.setId( 0 )
                    self._sharedHostingHosts = list( set( self._sharedHostingHosts ) )
                    v['alsoInHosting'] = self._sharedHostingHosts
                    v.setDesc( 'The web application under test seems to be in a shared hosting.' )
                    v.setName( 'Shared hosting' )
                    v.setSeverity(severity.MEDIUM)
                    
                    kb.kb.append( self, 'sharedHosting', v )
                    om.out.vulnerability( v.getDesc() )
                
                    om.out.vulnerability('This list of domains, and the domain of the web application under test, all point to the same server:' )
                    for url in self._sharedHostingHosts:
                        om.out.vulnerability('- ' + url )
                # Check if well parsed
                elif 'apache' in response.getBody().lower():
                    om.out.information('Couldn\'t find any URLs in the apache server status page. Two things can trigger this: \
                    The Apache web server sent a server-status page that the serverStatus plugin failed to parse OR the remote \
                    web server has no traffic. If you are sure about the first one, please report a bug.')
                    om.out.debug('The server-status body is: "'+response.getBody()+'"')
        
        return res
        
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
        This plugin fetches the server-status file used by Apache, and parses it. After parsing, new URL's are
        found, and in some cases, the plugin can deduce the existance of other domains hosted on the same
        server.
        '''
