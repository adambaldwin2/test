'''
spiderMan.py

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
import core.data.url.httpResponse as httpResponse
from core.data.parsers.urlParser import url_object

import cStringIO

from core.controllers.daemons.proxy import proxy, w3afProxyHandler
from core.controllers.w3afException import w3afException, w3afRunOnce
import core.data.constants.w3afPorts as w3afPorts

# Cohny changed the original http://w3af/spiderMan?terminate
# to http://127.7.7.7/spiderMan?terminate because in Opera we got
# an error if we used the original one! Thanks Cohny!
TERMINATE_URL = url_object('http://127.7.7.7/spiderMan?terminate')


class spiderMan(baseDiscoveryPlugin):
    '''
    SpiderMan is a local proxy that will collect new URLs.
    
    @author: Andres Riancho ( andres.riancho@gmail.com )
    @author: Alexander Berezhnoy < alexander.berezhnoy |at| gmail.com >
    '''
    def __init__(self):
        # Internal variables
        self._run = True
        self._fuzzableRequests = []

        # User configured parameters
        self._listenAddress = '127.0.0.1'
        self._listenPort = w3afPorts.SPIDERMAN

    def append_fuzzable_request(self, freq):
        '''
        Get a fuzzable request. Save it. Log it.
        
        This method is called from the proxyHandler.
        
        @return: None.
        '''
        self._fuzzableRequests.append(freq)

        if len(self._fuzzableRequests) == 1:
            om.out.information('Trapped fuzzable requests:')
        
        om.out.information( str(freq) )

    def ext_fuzzable_requests(self, response):
        self._fuzzableRequests.extend(self._createFuzzableRequests(response))

    def stopProxy(self):
        self._proxy.stop()
        
    def createPH(self):
        '''
        This method returns closure which is dressed up as a proxyHandler.
        It's a trick to get rid of global variables. 
        @return: proxyHandler constructor
        '''
        def constructor(request, client_addr, server):
            return proxyHandler(request, client_addr, server, self)

        return constructor
        
    def discover(self, freq ):

        
        if not self._run:
            # This will remove the plugin from the discovery plugins to be runned.
            raise w3afRunOnce()
        else:
            self._run = False
            
            # Create the proxy server
            self._proxy = proxy( self._listenAddress, self._listenPort, self._urlOpener, \
                                            self.createPH())
            self._proxy.targetDomain = freq.getURL().getDomain()
            
            # Inform the user
            msg = ('spiderMan proxy is running on %s:%s.\nPlease configure '
               'your browser to use these proxy settings and navigate the '
               'target site.\nTo exit spiderMan plugin please navigate to %s .'
               % (self._listenAddress, self._listenPort, TERMINATE_URL))
            om.out.information( msg )
            
            # Run the server
            self._proxy.run()
            
        return self._fuzzableRequests
    
    def getOptions( self ):
        '''
        @return: A list of option objects for this plugin.
        '''
        d1 = 'IP address that the spiderMan proxy will use to receive requests'
        o1 = option('listenAddress', self._listenAddress, d1, 'string')
        
        d2 = 'Port that the spiderMan HTTP proxy server will use to receive requests'
        o2 = option('listenPort', self._listenPort, d2, 'integer')
        
        ol = optionList()
        ol.add(o1)
        ol.add(o2)
        return ol
        
    def setOptions( self, optionsMap ):
        '''
        This method sets all the options that are configured using the user interface 
        generated by the framework using the result of getOptions().
        
        @parameter OptionList: A dictionary with the options for the plugin.
        @return: No value is returned.
        '''

        self._listenAddress = optionsMap['listenAddress'].getValue()
        self._listenPort  = optionsMap['listenPort'].getValue()
        
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
        This plugin is a local proxy that can be used to give the framework knowledge about the web
        application when it has a lot of client side code like Flash or Java applets. Whenever a w3af needs to
        test an application with flash or javascript, the user should enable this plugin and use a web browser
        to navigate the site using spiderMan proxy.
        
        The proxy will extract information from the user navigation and generate the necesary injection points for the 
        audit plugins.
        
        Another feature of this plugin is to save the cookies that are sent by the web application, in order to be able to
        use them in other plugins. So if you have a web application that has a login with cookie session management
        you should enable this plugin, do the login through the browser and then let the other plugins spider the rest 
        of the application for you. Important note: If you enable webSpider, you should ignore the "logout" link.
        
        Two configurable parameters exist:
            - listenAddress
            - listenPort
        '''

global_firstRequest = True
class proxyHandler(w3afProxyHandler):

    def __init__(self, request, client_address, server, spiderMan=None):
        self._version = 'spiderMan-w3af/1.0'
        if spiderMan is None:
            if hasattr(server, 'chainedHandler'):
                # see core.controllers.daemons.proxy.HTTPServerWrapper
                self._spiderMan = server.chainedHandler._spiderMan
        else:
            self._spiderMan = spiderMan
        self._urlOpener = self._spiderMan._urlOpener
        w3afProxyHandler.__init__(self, request, client_address, server)
    
    def doAll(self):
        global global_firstRequest
        if global_firstRequest:
            global_firstRequest = False
            om.out.information('The user is navigating through the spiderMan proxy.')
        
        # Convert to url_object
        path = url_object(self.path)
            
        if path == TERMINATE_URL:
            om.out.information('The user terminated the spiderMan session.')
            self._sendEnd()
            self._spiderMan.stopProxy()
        else:
            om.out.debug("[spiderMan] Handling request: %s %s" %
                                                    (self.command, path))
            #   Send this information to the plugin so it can send it to the core
            freq = self._createFuzzableRequest()
            self._spiderMan.append_fuzzable_request( freq )
            
            grep = True if path.getDomain() == self.server.w3afLayer.targetDomain else False
                
            try:
                response = self._sendToServer(grep=grep)
            except Exception, e:
                self._sendError( e )
            else:
                if response.is_text_or_html():
                    self._spiderMan.ext_fuzzable_requests( response )
                
                for h in response.getHeaders():
                    if 'cookie' in h.lower():
                        msg = ('The remote web application sent the following'
                           ' cookie: "%s".\nw3af will use it during the rest '
                           'of the process in order to maintain the session.'
                           % response.getHeaders()[h])
                        om.out.information( msg )
                self._sendToBrowser(response)
            return self._spiderMan._fuzzableRequests

    do_GET = do_POST = do_HEAD = doAll

    def _sendEnd( self ):
        '''
        Sends an HTML indicating that w3af spiderMan plugin has finished its execution.
        '''
        html = '<html>spiderMan plugin finished its execution.</html>'
        headers = {'Content-Length': str(len(html))}
        
        r = httpResponse.httpResponse( 200, html, headers, 
            TERMINATE_URL, TERMINATE_URL,)
        self._sendToBrowser(r)
