'''
preg_replace.py

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

from core.data.fuzzer.fuzzer import createMutants
import core.controllers.outputManager as om
# options
from core.data.options.option import option
from core.data.options.optionList import optionList

from core.controllers.basePlugin.baseAuditPlugin import baseAuditPlugin
import core.data.kb.knowledgeBase as kb
from core.controllers.w3afException import w3afException
import core.data.kb.vuln as vuln
import core.data.constants.severity as severity
import re

class preg_replace(baseAuditPlugin):
    '''
    Find unsafe usage of PHPs preg_replace.
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''

    def __init__(self):
        baseAuditPlugin.__init__(self)
        
    def _fuzzRequests(self, freq ):
        '''
        Tests an URL for unsafe usage of PHP's preg_replace.
        
        @param freq: A fuzzableRequest
        '''
        om.out.debug( 'preg_replace plugin is testing: ' + freq.getURL() )
        
        # First I check If I get the error message from php
        oResponse = self._sendMutant( freq , analyze=False ).getBody()
        mutants = createMutants( freq , ['a' + ')/' * 100 ,] , oResponse=oResponse )
        self._errorGeneration = True
        
        for mutant in mutants:
            if self._hasNoBug( 'preg_replace' , 'preg_replace' , mutant.getURL() , mutant.getVar() ):
                # Only spawn a thread if the mutant has a modified variable
                # that has no reported bugs in the kb
                targs = (mutant,)
                self._tm.startFunction( target=self._sendMutant, args=targs, ownerObj=self )
        
    def _analyzeResult( self, mutant, response ):
        '''
        Analyze results of the _sendMutant method.
        '''
        pregErrorList = self._findpregError( response )
        for pregError in pregErrorList:
            if not re.search( pregError, mutant.getOriginalResponseBody(), re.IGNORECASE ):
                v = vuln.vuln( mutant )
                v.setId( response.id )
                v.setSeverity(severity.HIGH)
                v.setName( 'Unsafe usage of preg_replace' )
                v.setDesc( 'Unsafe usage of preg_replace was found at: ' + mutant.foundAt() )
                kb.kb.append( self, 'preg_replace', v )
        
    def end(self):
        '''
        This method is called when the plugin wont be used anymore.
        '''
        self._tm.join( self )
        self.printUniq( kb.kb.getData( 'preg_replace', 'preg_replace' ), 'VAR' )
    
    def _findpregError( self, response ):
        '''
        This method searches for preg_replace errors in html's.
        
        @parameter response: The HTTP response object
        @return: A list of errors found on the page
        '''
        res = []
        for pregError in self._getPregError():
            match = re.search( pregError, response.getBody() , re.IGNORECASE )
            if  match:
                om.out.information('Found unsafe usage of preg_replace(). The error showed by the web application is (only a fragment is shown): "' + response.getBody()[match.start():match.end()] + '". The error was found on response with id ' + str(response.id) + '.')
                res.append(pregError)
        return res

    def _getPregError(self):
        errors = []
        errors.append( 'Compilation failed: unmatched parentheses at offset' )
        errors.append( '<b>Warning</b>:  preg_replace\\(\\) \\[<a' )
        return errors

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
        This plugin will find preg_replace vulnerabilities. This PHP function is vulnerable when the user
        can control the regular expression or the content of the string being analyzed and the regular expression
        has the 'e' modifier.
        
        Right now this plugin will only find preg_replace vulnerabilities when PHP is configured to show errors,
        but a new version will find "blind" preg_replace errors .
        '''
