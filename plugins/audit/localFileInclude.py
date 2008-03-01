'''
localFileInclude.py

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

import core.data.kb.vuln as vuln
from core.data.fuzzer.fuzzer import *
import core.controllers.outputManager as om
from core.controllers.basePlugin.baseAuditPlugin import baseAuditPlugin
import core.data.kb.knowledgeBase as kb
import core.data.parsers.urlParser as urlParser
import core.data.constants.severity as severity
import re

class localFileInclude(baseAuditPlugin):
    '''
    Find local file inclusion vulnerabilities.
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''

    def __init__(self):
        baseAuditPlugin.__init__(self)

    def _fuzzRequests(self, freq ):
        '''
        Tests an URL for local file inclusion vulnerabilities.
        
        @param freq: A fuzzableRequest
        '''
        om.out.debug( 'localFileInclude plugin is testing: ' + freq.getURL() )
        
        oResponse = self._sendMutant( freq , analyze=False ).getBody()
        localFiles = self._getLocalFileList()
        
        mutants = createMutants( freq , localFiles, oResponse=oResponse )
            
        for mutant in mutants:
            if self._hasNoBug( 'localFileInclude','localFileInclude',mutant.getURL() , mutant.getVar() ):
                # Only spawn a thread if the mutant has a modified variable
                # that has no reported bugs in the kb
                targs = (mutant,)
                # I don't grep the result, because if I really find a local file inclusion, I will be requesting
                # /etc/passwd and that would generate A LOT of false positives in the grep.pathDisclosure plugin
                kwds = {'grepResult':False}
                self._tm.startFunction( target=self._sendMutant, args=targs , kwds=kwds, ownerObj=self )
        
            
    def _getLocalFileList( self ):
        '''
        This method returns a list of local files to try to include.
        
        @return: A string, see above.
        '''
        localFiles = []
        # I will only try to open this files, they are easy to identify of they echoed by a vulnerable
        # web app and they are on all unix or windows default installs. Feel free to mail me ( Andres Riancho )
        # if you know about other default files that could be installed on AIX ? Solaris ? and are not /etc/passwd
        if cf.cf.getData('targetOS') in ['unix', 'unknown']:
            localFiles.append("../../../../../../../../etc/passwd") 
            localFiles.append("/etc/passwd")    
            localFiles.append("/etc/passwd\0")  
        if cf.cf.getData('targetOS') in ['windows', 'unknown']:
            localFiles.append("../../../../../../../../../../boot.ini\0")           
            localFiles.append("C:\\boot.ini")
            localFiles.append("C:\\boot.ini\0")
            localFiles.append("%SYSTEMROOT%\\win.ini")
            localFiles.append("%SYSTEMROOT%\\win.ini\0")
        return localFiles
        
    def _analyzeResult( self, mutant, response ):
        '''
        Analyze results of the _sendMutant method.
        '''
        fileContentList = self._findFile( response )
        for fileContent in fileContentList:
            if not re.search( fileContent, mutant.getOriginalResponseBody(), re.IGNORECASE ):
                v = vuln.vuln( mutant )
                v.setId( response.id )
                v.setName( 'Local file inclusion vulnerability' )
                v.setSeverity(severity.MEDIUM)
                v.setDesc( 'Local File Inclusion was found at: ' + response.getURL() + ' . Using method: ' + v.getMethod() + '. The data sent was: ' + str(mutant.getDc()) )
                v['filePattern'] = fileContent
                kb.kb.append( 'localFileInclude', 'localFileInclude', v )
    
    def end(self):
        '''
        This method is called when the plugin wont be used anymore.
        '''
        self._tm.join( self )
        self.printUniq( kb.kb.getData( 'localFileInclude', 'localFileInclude' ), 'VAR' )

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
        This method finds out if the local file has been successfully included in 
        the resulting HTML.
        
        @parameter response: The HTTP response object
        @return: A list of errors found on the page
        '''
        res = []
        for filePattern in self._getFilePatterns():
            match = re.search( filePattern, response.getBody() , re.IGNORECASE )
            if  match:
                om.out.information('Found file fragment. The section where the file is included is (only a fragment is shown): "' + response.getBody()[match.start():match.end()]  + '". The error was found on response with id ' + str(response.id) + '.')
                res.append( filePattern ) 
        return res
    
    def _getFilePatterns(self):
        '''
        @return: A list of strings to find in the resulting HTML in order to check for local file includes.
        '''
        filePatterns = []
        
        # /etc/passwd
        filePatterns.append("root:x:0:0:")  
        filePatterns.append("daemon:x:1:1:")
        filePatterns.append(":/bin/bash")
        filePatterns.append(":/bin/sh")
        
        # boot.ini
        filePatterns.append("\\[boot loader\\]")
        filePatterns.append("default=multi\\(")
        filePatterns.append("\\[operating systems\\]")
        
        # win.ini
        filePatterns.append("\\[fonts\\]")
        
        # Inclusion errors
        filePatterns.append("java.io.FileNotFoundException:")
        filePatterns.append("fread\\(\\):")
        filePatterns.append("for inclusion '\\(include_path=")
        filePatterns.append("Failed opening required")
        
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
        This plugin will find local file include vulnerabilities. This is done by sending to all injectable parameters
        file paths like "../../../../../etc/passwd" and searching in the response for strings like "root:x:0:0:".
        '''
