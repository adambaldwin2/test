'''
basicAuthBrute.py

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

from core.controllers.basePlugin.baseBruteforcePlugin import baseBruteforcePlugin
import core.data.kb.knowledgeBase as kb
from core.controllers.w3afException import w3afException
import core.data.kb.vuln as vuln
from core.data.url.xUrllib import xUrllib
import os.path
from core.controllers.bruteforce.bruteforcer import bruteforcer
import core.data.parsers.urlParser as urlParser
import core.data.constants.severity as severity

class basicAuthBrute(baseBruteforcePlugin):
    '''
    Bruteforce HTTP basic authentication.
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''

    def __init__(self):
        baseBruteforcePlugin.__init__(self)

    def _fuzzRequests(self, freq ):
        '''
        Tries to bruteforce a basic HTTP auth. This aint fast!
        
        @param freq: A fuzzableRequest
        '''
        authUrlList = [ urlParser.getDomainPath( i.getURL() ) for i in kb.kb.getData( 'httpAuthDetect', 'auth' )]
        
        domPath = urlParser.getDomainPath( freq.getURL() )
        
        if domPath in authUrlList:
            if domPath not in self._alreadyTested:
                om.out.information('Starting basic authentication bruteforce on URL: ' + domPath )
                self._initBruteforcer( domPath )

                while not self._found or not self._stopOnFirst:
                    combinations = []
                    
                    for i in xrange( 30 ):
                        try:
                            combinations.append( self._bruteforcer.getNext() )
                        except:
                            om.out.information('No more user/password combinations available.')
                            self._alreadyTested.append( domPath )
                            return
                    
                    self._bruteforce( domPath, combinations )
    
    def _bruteWorker( self, url, combinations ):
        '''
        @parameter url: A string representation of an URL
        @parameter combinations: A list of tuples with (user,pass)
        '''
        # get instance outside loop...
        uriOpener = xUrllib()
        uriOpener.setGrepPlugins( [] )
        # So uriOpener._init aint called
        uriOpener._cacheOpener = ''
    
        for combination in combinations:
            user = combination[0]
            passwd = combination[1]
            
            uriOpener.settings.setBasicAuth( url, user, passwd  )
            # The next line replaces the uriOpener opener with a new one that has
            # the basic auth settings configured
            
            #IMPORTANT: This line also calls __init__ on all urllib2 handlers, to have in mind:
            # the localCache clears the cache when you call init...
            # this creates problem with multithreading
            uriOpener.settings.buildOpeners()
            uriOpener._opener = uriOpener.settings.getCustomUrlopen()
            
            # This "if" is for multithreading
            if not self._found or not self._stopOnFirst:

                try:
                    response = uriOpener.GET( url, useCache=False, analyze=False )
                except w3afException, w3:
                    om.out.debug('Exception while bruteforcing basic authentication, error message: ' + str(w3) )
                except Exception, e:
                    om.out.debug('Unhandled exception while bruteforcing basic authentication, error message: ' + str(e) )
                else:
                    # GET was OK
                    if response.getCode() == 200:
                        self._found = True
                        v = vuln.vuln()
                        v.setURL( url )
                        v.setDesc( 'Found authentication credentials to: '+ url +
                        ' . A correct user and password combination is: ' + user + '/' + passwd)
                        v['user'] = user
                        v['pass'] = passwd
                        v['response'] = response
                        v.setSeverity(severity.HIGH)
                        v.setName( 'Guessable credentials' )
                
                        kb.kb.append( self , 'auth' , v )
                        om.out.vulnerability( v.getDesc(), severity=v.getSeverity() )
                        break
                
    def getLongDesc( self ):
        '''
        @return: A DETAILED description of the plugin functions and features.
        '''
        return '''
        This plugin bruteforces basic authentication logins.
        
        Nine configurable parameters exist:
            - usersFile
            - stopOnFirst
            - passwdFile
            - passEqUser
            - useMailUsers
            - useSvnUsers
            - useMails
            - useProfiling
            - profilingNumber
        
        This plugin will take users from the file pointed by "usersFile", mail users found on the site ( if "useMailUsers" is
        set to True ), mails found on the site ( if "useMails" is set to True ), and svn users found on the site ( if "useSvnUsers"
        is set to True ).
        
        This plugin will take passwords from the file pointed by "passwdFile" and the result of the password profiling plugin 
        ( if "useProfiling" is set to True). The profilingNumber sets the number of results from the password profiling plugin
        to use in the password field.
        
        The "stopOnFirst" parameter indicates if the bruteforce will stop when finding the first valid credentials or not.
        '''
