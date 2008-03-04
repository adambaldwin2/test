'''
fingerprint404Page.py

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
import core.data.kb.knowledgeBase as kb
import core.data.kb.config as cf
import core.data.parsers.urlParser as urlParser
from core.data.fuzzer.fuzzer import *
import difflib

class fingerprint404Page:
    '''
    Read the 404 page returned by the server.
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''

    def __init__(self, uriOpener):
        self._urlOpener =  uriOpener
        
        self._404pageList = []
        
        # This is gooood! It will put the function in a place that's available for all.
        kb.kb.save( 'error404page', '404', self.is404 )

        # Only report once
        self._reported = False
        self._alreadyAnalyzed = False

    def  _add404Knowledge( self, httpResponse ):
        '''
        Creates the regular expression and saves it to the kb.
        '''
        domainPath = urlParser.getDomainPath( httpResponse.getURL() )
        try:
            response, randAlNumFile, extension = self._generate404( httpResponse.getURL() )
        except w3afException, w3:
            om.out.debug('w3af exception:' + str(w3) )
        except KeyboardInterrupt, k:
            raise k
        except Exception, e:
            om.out.debug('Something went wrong while getting a 404 page...')
            raise e
        else:
            if response.getCode() not in [404,401,403] and not self._reported:
                # Not using 404 in error pages
                om.out.information('Server uses ' + str(response.getCode()) + ' instead of HTTP 404 error code. ')
                self._reported = True
            
            #om.out.debug('The 404 page for "'+domainPath+'" is : "'+response.getBody()+'".')
            self._404pageList.append( (response, randAlNumFile, extension) )
    
    def _byDirectory( self, httpResponse ):
        '''
        @return: True if the httpResponse is a 404 based on the knowledge found by _add404Knowledge and the data
        in _404pageList regarding the directory.
        '''
        tmp = [ response.getBody() for (response, randAlNumFile, extension) in self._404pageList if \
        urlParser.getDomainPath(httpResponse.getURL()) == urlParser.getDomainPath(response.getURL())]
        
        if len( tmp ):
            # All items in this directory should be the same...
            responseBody = tmp[0]
            if difflib.SequenceMatcher( None, responseBody, httpResponse.getBody() ).ratio() < 0.10:
                return False
            else:
                om.out.debug(httpResponse.getURL() + ' is a 404 (_byDirectory).')
                return True
        else:
            self._add404Knowledge( httpResponse )
            return self._byDirectory( httpResponse )
    
    def _byDirectoryAndExtension( self, httpResponse ):
        '''
        @return: True if the httpResponse is a 404 based on the knowledge found by _add404Knowledge and the data
        in _404pageList regarding the directory AND the file extension.
        '''
        tmp = [ response.getBody() for (response, randAlNumFile, extension) in self._404pageList if \
        urlParser.getDomainPath(httpResponse.getURL()) == urlParser.getDomainPath(response.getURL()) and \
        (urlParser.getExtension(httpResponse.getURL()) == '' or urlParser.getExtension(httpResponse.getURL()) == extension)]
        
        if len( tmp ):
            # All items in this directory/extension combination should be the same...
            responseBody = tmp[0]
            if difflib.SequenceMatcher( None, responseBody, httpResponse.getBody() ).ratio() > 0.90:
                om.out.debug(httpResponse.getURL() + ' is a 404 (_byDirectoryAndExtension).')            
                return True
            else:
                return False
        else:
            self._add404Knowledge( httpResponse )
            return self._byDirectoryAndExtension( httpResponse )
            
    def is404( self, httpResponse ):
        if not self._alreadyAnalyzed:
            self._add404Knowledge( httpResponse )
        
        # Set a variable that is widely used
        domainPath = urlParser.getDomainPath( httpResponse.getURL() )
        
        # Check for the fixed responses
        if domainPath in cf.cf.getData('always404'):
            return True
        elif domainPath in cf.cf.getData('404exceptions'):
            return False
          
        # Start the fun.
        if cf.cf.getData('autodetect404'):
            return self._autodetect( httpResponse )
        elif cf.cf.getData('byDirectory404'):
            return self._byDirectory( httpResponse )
        # worse case
        elif cf.cf.getData('byDirectoryAndExtension404'):
            return self._byDirectoryAndExtension( httpResponse )
        
    def _autodetect( self, httpResponse ):
        '''
        Try to autodetect how I'm going to handle the 404 messages
        @parameter httpResponse: The URL
        '''
        if len( self._404pageList ) <= 25:
            om.out.debug('I can\'t perform autodetection yet (404pageList has '+str(len(self._404pageList))+' items). Keep on working with the worse case')
            return self._byDirectoryAndExtension( httpResponse )
        else:
            if not self._alreadyAnalyzed:
                om.out.debug('Starting analysis of responses.')
                self._analyzeData()
                self._alreadyAnalyzed = True
            
            # Now return a response
            if kb.kb.getData('error404page', 'trust404'):
                if httpResponse.getCode() == 404:
                    om.out.debug(httpResponse.getURL() + ' is a 404 (_autodetect trusting 404).')
                    return True
                else:
                    return False
            elif kb.kb.getData('error404page', 'trustBody'):
                if difflib.SequenceMatcher( None, httpResponse.getBody(), kb.kb.getData('error404page', 'trustBody') ).ratio() > 0.90:
                    om.out.debug(httpResponse.getURL() + ' is a 404 (_autodetect trusting body).')
                    return True
                else:
                    return False
            else:
                # worse case
                return self._byDirectoryAndExtension( httpResponse )
            
    def _analyzeData( self ):
        # Check if all are 404
        tmp = [ (response, randAlNumFile, extension) for (response, randAlNumFile, extension) in self._404pageList if response.getCode() == 404 ]
        if len(tmp) == len(self._404pageList):
            om.out.debug('The remote web site uses 404 as 404.')
            kb.kb.save('error404page', 'trust404', True)
            return
            
        # Check if the 404 error message body is the same for all directories
        def areEqual( tmp ):
            for respBody1 in tmp:
                for respBody2 in tmp:
                    if difflib.SequenceMatcher( None, respBody1, respBody2 ).ratio() > 0.90:
                        return True
            return False
        
        tmp = [ response.getBody() for (response, randAlNumFile, extension) in self._404pageList ]
        if areEqual( tmp ):
            om.out.debug('The remote web site uses always the same body for all 404 responses.')
            kb.kb.save('error404page', 'trustBody', tmp[0] )
            return
            
        # hmmm... I have nothing else to analyze... if I get here it means that the web application is wierd and
        # nothing will help me detect 404 pages...
        
    def getName( self ):
        return 'error404page'
    
    def _generate404( self, url ):
        # Get the filename extension and create a 404 for it
        extension = urlParser.getExtension( url )
        domainPath = urlParser.getDomainPath( url )
        if not extension:
            extension = 'html'
        
        randAlNumFile = createRandAlNum( 11 ) + '.' + extension
        url404 = urlParser.urlJoin(  domainPath , randAlNumFile )
        
        try:
            response = self._urlOpener.GET( url404, useCache=True, grepResult=False )
        except w3afException, w3:
            raise w3afException('Exception while fetching a 404 page, error: ' + str(w3) )
        except Exception, e:
            raise w3afException('Unhandled exception while fetching a 404 page, error: ' + str(e) )
            
        return response, randAlNumFile, extension
