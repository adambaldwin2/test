'''
LDAPi.py

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
from core.data.fuzzer.fuzzer import createMutants
import core.controllers.outputManager as om
# options
from core.data.options.option import option
from core.data.options.optionList import optionList

from core.controllers.basePlugin.baseAuditPlugin import baseAuditPlugin
import core.data.kb.knowledgeBase as kb
from core.controllers.w3afException import w3afException
import core.data.parsers.urlParser as urlParser
import core.data.constants.severity as severity
import re

class LDAPi(baseAuditPlugin):
    '''
    Find LDAP injection bugs.
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''

    def __init__(self):
        baseAuditPlugin.__init__(self)
        
    def _fuzzRequests(self, freq ):
        '''
        Tests an URL for LDAP injection vulnerabilities.
        
        @param freq: A fuzzableRequest
        '''
        om.out.debug( 'LDAPi plugin is testing: ' + freq.getURL() )
        
        oResponse = self._sendMutant( freq , analyze=False ).getBody()
        ldapiStrings = self._getLDAPiStrings()
        mutants = createMutants( freq , ldapiStrings, oResponse=oResponse )
            
        for mutant in mutants:
            if self._hasNoBug( 'LDAPi','LDAPi',mutant.getURL() , mutant.getVar() ):
                # Only spawn a thread if the mutant has a modified variable
                # that has no reported bugs in the kb
                targs = (mutant,)
                self._tm.startFunction( target=self._sendMutant, args=targs , ownerObj=self )
            
    def _getLDAPiStrings( self ):
        '''
        Gets a list of strings to test against the web app.
        
        @return: A list with all LDAPi strings to test.
        '''
        LDAPstr = []
        LDAPstr.append("^(#$!@#$)(()))******")
        return LDAPstr

    def _analyzeResult( self, mutant, response ):
        '''
        Analyze results of the _sendMutant method.
        '''
        LDAPErrorList = self._findLDAPError( response )
        for ldapError in LDAPErrorList:
            if not re.search( ldapError, mutant.getOriginalResponseBody(), re.IGNORECASE ):
                v = vuln.vuln( mutant )
                v.setId( response.id )
                v.setSeverity(severity.HIGH)
                v.setName( 'LDAP injection vulnerability' )
                v.setDesc( 'LDAP injection was found at: ' + response.getURL() + ' . Using method: ' + v.getMethod() + '. The data sent was: ' + str(mutant.getDc()) )
                kb.kb.append( self, 'LDAPi', v )
    
    def end(self):
        '''
        This method is called when the plugin wont be used anymore.
        '''
        self._tm.join( self )
        self.printUniq( kb.kb.getData( 'LDAPi', 'LDAPi' ), 'VAR' )
        
    def _findLDAPError( self, response ):
        '''
        This method searches for LDAP errors in html's.
        
        @parameter response: The HTTP response object
        @return: A list of errors found on the page
        '''
        res = []
        for ldapError in self._getLDAPErrors():
            match = re.search( ldapError, response.getBody() , re.IGNORECASE )
            if  match:
                om.out.information('Found LDAP injection. The error returned by the web application is (only a fragment is shown): "' + response.getBody()[match.start():match.end()] + '". The error was found on response with id ' + str(response.id) + '.')
                res.append( ldapError )
        return res
        
    def _getLDAPErrors( self ):
        errorStr = []
        errorStr.append('supplied argument is not a valid ldap')
        errorStr.append('javax.naming.NameNotFoundException'.lower())
        return errorStr
        
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
        This plugin will find LDAP injections.
        '''
