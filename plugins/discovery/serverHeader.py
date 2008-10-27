'''
serverHeader.py

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
import core.data.kb.info as info
from core.controllers.w3afException import w3afRunOnce

class serverHeader(baseDiscoveryPlugin):
    '''
    Identify the server type based on the server header.
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''
    
    '''
    Nothing strange, just do a GET request to the url and save the server headers
    to the kb. A smarter way to check the server type is with the hmap plugin.
    
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''

    def __init__(self):
        baseDiscoveryPlugin.__init__(self)
        self._execOneTime = True
        self._exec = True
        self._xpowered = True

    def discover(self, fuzzableRequest ):
        '''
        Nothing strange, just do a GET request to the url and save the server headers
        to the kb. A smarter way to check the server type is with the hmap plugin.
        
        @parameter fuzzableRequest: A fuzzableRequest instance that contains (among other things) the URL to test.
        '''
        if not self._exec:
            # This will remove the plugin from the discovery plugins to be runned.
            raise w3afRunOnce()
        else:
            try:
                response = self._urlOpener.GET( fuzzableRequest.getURL(), useCache=True )       
            except KeyboardInterrupt,e:
                raise e
            else:
                server = ''
                for h in response.getHeaders().keys():
                    if h.lower() == 'server':
                        server = response.getHeaders()[h]
                
                if server != '':
                    i = info.info()
                    i.setName('Server header')
                    i.setId( response.getId() )
                    i.setDesc('The server header for the remote web server is: "' + server + '".' )
                    i['server'] = server
                    om.out.information( i.getDesc() )
                    
                    # Save the results in the KB so the user can look at it
                    kb.kb.append( self, 'server', i )
                    
                    # Also save this for easy internal use
                    # other plugins can use this information
                    kb.kb.save( self , 'serverString' , server )
                    
                else:
                    # strange !
                    i = info.info()
                    i.setName('Omited server header')
                    i.setId( response.getId() )
                    i.setDesc('The remote HTTP Server ommited the "server" header in it\'s response.' )
                    om.out.information( i.getDesc() )
                    
                    # Save the results in the KB so that other plugins can use this information
                    kb.kb.append( self, 'omitedHeader', i )
                    
                if self._execOneTime:
                    self._exec = False
                
        if self._xpowered:
            self._checkXPower( fuzzableRequest )
        
        return []
        
    def _checkXPower( self, fuzzableRequest ):
        try:
            response = self._urlOpener.GET( fuzzableRequest.getURL(), useCache=True )
        except:
            pass
        else:
            poweredBy = ''
            for h in response.getHeaders().keys():
                for d in [ 'ASPNET','POWERED']:
                    if d in h.upper() or h.upper() in d :
                        poweredBy = response.getHeaders()[h]
                        
                        i = info.info()
                        i.setName('Powered by header')
                        i.setId( response.getId() )
                        i.setDesc('"' + h + '" header for this HTTP server is: "' + poweredBy + '".' )
                        i['poweredBy'] = poweredBy
                        om.out.information( i.getDesc() )
                        
                        # Save the results in the KB so that other plugins can use this information
                        
                        # Before knowing that some servers may return more than one poweredby header I had:
                        #kb.kb.save( self , 'poweredBy' , poweredBy )
                        # But I have seen an IIS server with PHP that returns both the ASP.NET and the PHP headers
                        poweredByInKb = [ i['poweredBy'] for i in kb.kb.getData( 'serverHeader', 'poweredBy' ) ]
                        if poweredBy not in poweredByInKb:
                            kb.kb.append( self , 'poweredBy' , i )
                        
                        # Also save this for easy internal use
                        kb.kb.append( self , 'poweredByString' , poweredBy )
                        
                        if self._execOneTime:
                            self._xpowered = False          
            
            if poweredBy == '':
                # not as strange as the one above, this is because of a config or simply
                # cause I requested a static "html" file.
                # I will save the server header as the poweredBy, its the best choice I have right now
                if kb.kb.getData( 'serverHeader' , 'serverString' ) not in kb.kb.getData( 'serverHeader', 'poweredByString' ):
                    kb.kb.append( self , 'poweredByString' , kb.kb.getData( 'serverHeader' , 'serverString' ) )
    
    def getOptions( self ):
        '''
        @return: A list of option objects for this plugin.
        '''
        d1 = 'Execute plugin only one time'
        h1 = 'Generally the server header wont change during a scan to \
    a same site, so executing this plugin only one time is a safe choice.'
        o1 = option('execOneTime', self._execOneTime, d1, 'boolean', help=h1)
        
        ol = optionList()
        ol.add(o1)
        return ol

    def setOptions( self, optionsMap ):
        '''
        This method sets all the options that are configured using the user interface 
        generated by the framework using the result of getOptions().
        
        @parameter optionsMap: A dictionary with the options for the plugin.
        @return: No value is returned.
        ''' 
        self._execOneTime = optionsMap['execOneTime'].getValue()

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
        This plugin gets the server header and saves the result to the knowledgeBase.
        '''
