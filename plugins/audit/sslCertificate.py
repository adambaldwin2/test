'''
sslCertificate.py

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

from core.controllers.basePlugin.baseAuditPlugin import baseAuditPlugin
import core.data.kb.knowledgeBase as kb
from core.controllers.w3afException import w3afException
import socket
import re
from core.data.parsers.urlParser import getProtocol, getDomain
import core.data.constants.severity as severity

class sslCertificate(baseAuditPlugin):
    '''
    Check the SSL certificate validity( if https is being used ).
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''

    def __init__(self):
        baseAuditPlugin.__init__(self)

    def _fuzzRequests(self, freq ):
        '''
        Get the cert and do some checks against it.
        
        @param freq: A fuzzableRequest
        '''
        url = freq.getURL()
        if 'HTTPS' == getProtocol( url ).upper():
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            splited = getDomain(url).split(':')
            if len( splited ) == 1:
                port = 443
                host = splited[0]
            else:
                port = splited[1]
                host = splited[0]
            s.connect( ( host , port ) )
            s = socket.ssl( s )
            
            def printCert( certStr ):
                # All of this could be replaced with a smarter re, but i had no time
                pparsecertstringre = re.compile(    r"""(?:/)(\w(?:\w|))(?:=)""")
                varNames = pparsecertstringre.findall( certStr )
                pos = 0
                for i in xrange( len(varNames) ):
                    start = certStr.find( varNames[ i ], pos )
                    if ( i +1 ) != len(varNames):
                        end = certStr.find( varNames[ i + 1], start )
                    else:
                        end = len( certStr ) +1
                    value = certStr[ start+ len(varNames[ i ]) +1 : end -1 ]
                    om.out.information('- '+ varNames[ i ] + '=' + value)
            
            om.out.information('Issuer of SSL Certificate:')
            printCert( s.issuer() )
            om.out.information('Server SSL Certificate:')
            printCert( s.server() )

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
        This plugin audits SSL certificate parameters.
        
        Note: It's only usefull when testing HTTPS sites.
        '''
