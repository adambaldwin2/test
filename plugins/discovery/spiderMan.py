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
from core.controllers.basePlugin.baseDiscoveryPlugin import baseDiscoveryPlugin
import core.data.url.httpResponse as httpResponse

import cStringIO
import signal

from core.data.request.frFactory import createFuzzableRequestRaw

import core.data.parsers.urlParser as urlParser

from core.data.getResponseType import *
from core.controllers.daemons.proxy import *
from core.controllers.w3afException import *
import core.data.constants.w3afPorts as w3afPorts

class sigCallback:
    '''
    The class object, when created, replaces current signal handler by itself.
    When the signal appears, the callback function is called and the handler is restored back.
    @author: Alexander Berezhnoy < alexander.berezhnoy |at| gmail.com >
    '''
    def __init__(self, fun, sigCode):
        self._fun = fun
        self._code = sigCode
        self._sigHandler = signal.getsignal(sigCode)
        signal.signal(sigCode, self)

    def __call__(self, *ignore):
        self._fun.__call__()
        signal.signal(self._code, self._sigHandler)



class spiderMan(baseDiscoveryPlugin):
    '''
    SpiderMan is a local proxy that will collect new URLs.
    
    @author: Andres Riancho ( andres.riancho@gmail.com )
    @author: Alexander Berezhnoy < alexander.berezhnoy |at| gmail.com >
    '''
    def __init__(self):
        self._run = True
        self._fuzzableRequests = []
        self.createFuzzableRequests = self._createFuzzableRequests
        self.extendFuzzableRequests = self._fuzzableRequests.extend

        # User configured parameters
        self._listenAddress = '127.0.0.1'
        self._listenPort = w3afPorts.SPIDERMAN

    def appendFuzzableRequest(self, command, path, postData, headers):
        freq = createFuzzableRequestRaw( command, path, postData, headers )
        self._fuzzableRequests.append(freq)

    def extFuzzableRequests(self, response):                 
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
            self._proxy = proxy(self._listenAddress, self._listenPort, self._urlOpener, self.createPH())
            
            # Inform the user
            om.out.information('spiderMan proxy is running on ' + self._listenAddress + ':' + str(self._listenPort) + ' .' )
            om.out.information('Please configure your browser to use these proxy settings and navigate the target site.')
            om.out.information('To exit spiderMan plugin please navigate to http://w3af/spiderMan?terminate or press ctrl+c .')
            
            # Set the signal handler
            sigCallback(self._proxy.stop, signal.SIGINT)

            # Run the server
            self._proxy.run()
            
        
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
            <Option name="listenAddress">\
                <default>'+str(self._listenAddress)+'</default>\
                <desc>IP address that the spiderMan proxy will use to receive requests</desc>\
                <type>string</type>\
                <help></help>\
            </Option>\
            <Option name="listenPort">\
                <default>'+str(self._listenPort)+'</default>\
                <desc>Port that the spiderMan HTTP proxy server will use to receive requests</desc>\
                <type>integer</type>\
                <help></help>\
            </Option>\
        </OptionList>\
        '

    def setOptions( self, optionsMap ):
        '''
        This method sets all the options that are configured using the user interface 
        generated by the framework using the result of getOptionsXML().
        
        @parameter OptionList: A dictionary with the options for the plugin.
        @return: No value is returned.
        '''

        self._listenAddress = optionsMap['listenAddress']
        self._listenPort  = optionsMap['listenPort']
        
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
        you should enable this plugin, do the login through the bworser and then let the other plugins spider the rest 
        of the application for you. Important note: If you enable webSpider, you should ignore the "logout" link.
        
        Two configurable parameters exist:
            - listenAddress
            - listenPort
        '''
        
class proxyHandler(w3afProxyHandler):

    def __init__(self, request, client_address, server, spiderMan):
        self._version = 'spiderMan-w3af/1.0'
        self._spiderMan = spiderMan
        self._urlOpener = spiderMan._urlOpener
        w3afProxyHandler.__init__(self, request, client_address, server)
    
    def doAll(self):
        if self.path == 'http://w3af/spiderMan?terminate':
            self._sendEnd()
            self._spiderMan.stopProxy()
        else:

            postData = self._getPostData()
            headers = self._getHeadersDict()
            om.out.debug("[spiderMan] Handling request: " + self.command + ' ' + self.path)
            self._spiderMan.appendFuzzableRequest( self.command, self.path, postData, headers )

            try:
                response = self._sendToServer()
            except Exception, e:
                self._sendError( e )
            else:
                if isTextOrHtml( response.getHeaders() ):
                    self._spiderMan.extFuzzableRequests( response )
                
                for h in response.getHeaders():
                    if 'cookie' in h.lower():
                        om.out.information('The remote web application sent the following cookie: "' + str(response.getHeaders()[h]) + '".\nw3af will use it during the rest of the process in order to maintain the session.')
                        
                self._sendToBrowser(response)
                
            return self._spiderMan._fuzzableRequests

    do_GET = do_POST = do_HEAD = doAll


    def _getHeadersDict(self):
        '''
        @return: Request headers as dictionary
        '''
        headers = {}
        for header in self.headers.keys():
            headers[header] = self.headers.getheader(header)

        return headers

    def _getPostData(self):
        '''
        @return: Post data preserving rfile
        '''
        postData = ''
        try:
            length = int(self.headers.getheader('content-length'))
        except:
            pass
        else:
            # rfile is not seekable, so a little trick
            postData = self.rfile.read(length)
            rfile = cStringIO.StringIO(postData)
            self.rfile = rfile
        
        return postData

    def _sendEnd( self ):
        '''
        Sends an HTML indicating that w3af spiderMan plugin has finished its execution.
        '''
        html = '<html>spiderMan plugin finished its execution.</html>'
        headers = {'Content-Length': str(len(html))}
        r = httpResponse.httpResponse( 200, html, headers, 
            'http://w3af/spiderMan?terminate', 'http://w3af/spiderMan?terminate',)
        self._sendToBrowser(r)
