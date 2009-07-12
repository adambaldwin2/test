'''
dir_bruter.py

Copyright 2009 Jon Rose

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
from core.controllers.w3afException import w3afRunOnce
import core.data.parsers.urlParser as urlParser
import os

import core.data.kb.knowledgeBase as kb
from core.controllers.misc.levenshtein import relative_distance
from core.data.fuzzer.fuzzer import createRandAlNum


class dir_bruter(baseDiscoveryPlugin):
    '''
    Finds Web server directories by bruteforcing.

    @author: Jon Rose ( jrose@owasp.org )
    @author: Andres Riancho ( andres@bonsai-sec.com )
    '''
    def __init__(self):
        baseDiscoveryPlugin.__init__(self)
        self._exec = True
        
        # User configured parameters
        self._dir_list = 'plugins' + os.path.sep + 'discovery' + os.path.sep + 'dir_bruter'
        self._dir_list += os.path.sep + 'common_dirs_small.db'
        self._be_recursive = True

        # Internal variables
        self._fuzzable_requests = []
        self.is_404 = None
        self._200_as_404 = False
        self._404_as_404 = False
        self._failed_to_fingerprint = False
        self._404_content = None
        self._tested_base_url = False

    def discover(self, fuzzableRequest ):
        '''
        Get the file and parse it.
        @parameter fuzzableRequest: A fuzzableRequest instance that contains
                                                      (among other things) the URL to test.
        '''
        if not self._exec:
            raise w3afRunOnce()
        else:
            
            if not self._be_recursive:
                # Only run once
                self._exec = False
                
            if self.is_404 == None:
                self.is_404 = kb.kb.getData( 'error404page', '404' )

            self._fuzzable_requests = []
            
            domain_path = urlParser.getDomainPath( fuzzableRequest.getURL() )
            base_url = urlParser.baseUrl( fuzzableRequest.getURL() )
            
            to_test = []
            if not self._tested_base_url:
                to_test.append( base_url )
                self._tested_base_url = True
                
            if domain_path != base_url:
                to_test.append( domain_path )
            
            for base_path in to_test:
                # Perform some requests to see how the server responds to "404"
                self._fingerprint_404( base_path )
                self._bruteforce_directories( base_path )

        return self._fuzzable_requests
    
    def _bruteforce_directories(self, base_path):
        '''
        @parameter base_path: The base path to use in the bruteforcing process, can be something
        like http://host.tld/ or http://host.tld/images/ .
        '''
        for directory_name in file(self._dir_list):
            directory_name = directory_name.strip()
            
            # ignore comments and empty lines
            if directory_name and not directory_name.startswith('#'):
                dir_url = urlParser.urlJoin(  base_path , directory_name)
                dir_url +=  '/'

                http_response = self._urlOpener.GET( dir_url, useCache=False )
                
                if not self._internal_is_404( http_response ):
                    fuzzable_reqs = self._createFuzzableRequests( http_response )
                    self._fuzzable_requests.extend( fuzzable_reqs )
                    
                    msg = 'Directory bruteforcer plugin found directory "'
                    msg += http_response.getURL()  + '"'
                    
                    if self._404_as_404:
                        msg += ' with HTTP response code ' + str(http_response.getCode())
                        msg += ' and Content-Length: ' + str(len(http_response.getBody()))
                    
                    if self._200_as_404:
                        msg +=  ' with Content-Length: ' + str(len(http_response.getBody()))
                        
                    msg += '.'
                    
                    om.out.information( msg )

    def _fingerprint_404(self, base_path):
        '''
        Perform some requests to see what kind of 404 the server has.
        
        @return: None
        '''
        #
        # Generate a list of 404's
        #
        response_list = []
        for i in xrange(5):
            rnd_str = createRandAlNum( i + 6)
            
            dir_url = urlParser.urlJoin( base_path, rnd_str + '/')
            http_response = self._urlOpener.GET( dir_url, useCache=False )
            response_list.append(http_response)
            
        #
        # Analyze it
        #
        count_200 = 0
        count_404 = 0
        for response in response_list:
            # TODO: create a dict here, and work with that, this simplistic approach fails when errors 403, 401, 500 are returned!!
            if response.getCode() == 200:
                count_200 += 1
            if response.getCode() == 404:
                count_404 += 1
        
        if len(response_list) == count_200:
            # Server uses 200 as 404
            self._200_as_404 = True
            self._404_as_404 = False
            self._404_content = response_list[0].getBody()
            
        elif len(response_list) == count_404:
            # Server uses 200 as 404
            self._404_as_404 = True
            self._200_as_404 = False
            
        else:
            self._failed_to_fingerprint = True
        
    def _internal_is_404(self, http_response):
        '''
        @parameter http_response: The http_response that we want to know if it's a 404 or not
        @return: True if it's a 404
        '''
        if self._404_as_404:
            if http_response.getCode() == 404:
                return True
            else:
                return False
                
        elif self._200_as_404:
            # relative_distance() == 1 , they are equal
            # relative_distance() == 0 , they are completely different
            if relative_distance( self._404_content, http_response.getBody() ) < 0.75:
                return False
            else:
                return True
                
        elif self._failed_to_fingerprint:
            return self.is_404( http_response )
            
    def getOptions( self ):
        '''
        @return: A list of option objects for this plugin.
        '''    
        d1 = 'Wordlist to use in directory bruteforcing process.'
        o1 = option('wordlist', self._dir_list , d1, 'string')
        
        d2 = 'If set to True, this plugin will bruteforce all directories, not only the root'
        d2 += ' directory.'
        o2 = option('be_recursive', self._be_recursive , d2, 'boolean')

        ol = optionList()
        ol.add(o1)
        ol.add(o2)

        return ol
        

    def setOptions( self, OptionList ):
        '''
        This method sets all the options that are configured using the user interface 
        generated by the framework using the result of getOptions().
        
        @parameter OptionList: A dictionary with the options for the plugin.
        @return: No value is returned.
        ''' 
        dir_list = OptionList['wordlist'].getValue()
        if os.path.exists( dir_list ):
            self._dir_list = dir_list
            
        self._be_recursive = OptionList['be_recursive'].getValue()

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
        This plugin finds directories on a web server by bruteforcing the names using a list.

        Two configurable parameters exist:
            - wordlist: The wordlist to be used in the directory bruteforce process.
            - be_recursive: If set to True, this plugin will bruteforce all directories, not only
            the root directory.
        '''
