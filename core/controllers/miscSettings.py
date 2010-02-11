'''
miscSettings.py

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

from core.controllers.configurable import configurable
import core.data.kb.config as cf
from core.controllers.threads.threadManager import threadManagerObj as tm

# options
from core.data.options.option import option
from core.data.options.optionList import optionList

# Raise errors
from core.controllers.w3afException import w3afException

from core.controllers.misc.get_local_ip import get_local_ip
from core.controllers.misc.get_net_iface import get_net_iface


class miscSettings(configurable):
    '''
    A class that acts as an interface for the user interfaces, so they can configure w3af 
    settings using getOptions and SetOptions.
    '''
    
    def __init__( self ):
        '''
        Set the defaults and save them to the config dict.
        '''
        #
        # User configured variables
        #
        if cf.cf.getData('autoDependencies') == None:
            # It's the first time I'm runned
            cf.cf.save('fuzzableCookie', False )
            cf.cf.save('fuzzFileContent', True )
            cf.cf.save('fuzzFileName', False )
            cf.cf.save('fuzzFCExt', 'txt' )
            cf.cf.save('fuzzFormComboValues', 'tmb')
            cf.cf.save('autoDependencies', True )
            cf.cf.save('maxDepth', 25 )
            cf.cf.save('maxThreads', 15 )
            cf.cf.save('fuzzableHeaders', [] )
            cf.cf.save('maxDiscoveryLoops', 500 )
            
            #
            #
            #
            ifname = get_net_iface()
            cf.cf.save('interface', ifname )
            
            #
            #   This doesn't send any packets, and gives you a nice default setting.
            #   In most cases, it is the "public" IP address, which will work perfectly
            #   in all plugins that need a reverse connection (rfiProxy)
            #
            local_address = get_local_ip()
            if not local_address:
                local_address = '127.0.0.1' #do'h!                
        
            cf.cf.save('localAddress', local_address)
            cf.cf.save('demo', False )
            cf.cf.save('nonTargets', [] )
            cf.cf.save('exportFuzzableRequests', '')
    
    def getOptions( self ):
        '''
        @return: A list of option objects for this plugin.
        '''
        ######## Fuzzer parameters ########
        d1 = 'Indicates if w3af plugins will use cookies as a fuzzable parameter'
        o1 = option('fuzzCookie', cf.cf.getData('fuzzableCookie'), d1, 'boolean',
                            tabid='Fuzzer parameters')

        d2 = 'Indicates if w3af plugins will send the fuzzed payload to the file forms'
        o2 = option('fuzzFileContent', cf.cf.getData('fuzzFileContent'), d2, 'boolean',
                            tabid='Fuzzer parameters')
        
        d3 = 'Indicates if w3af plugins will send fuzzed filenames in order to find vulnerabilities'
        h3 = 'For example, if the discovered URL is http://test/filename.php, and fuzzFileName'
        h3 += ' is enabled, w3af will request among other things: http://test/file\'a\'a\'name.php'
        h3 += ' in order to find SQL injections. This type of vulns are getting more common every'
        h3 += ' day!'
        o3 = option('fuzzFileName', cf.cf.getData('fuzzFileName'), d3, 'boolean', help=h3, 
                            tabid='Fuzzer parameters')
        
        d4 = 'Indicates the extension to use when fuzzing file content'
        o4 = option('fuzzFCExt', cf.cf.getData('fuzzFCExt'), d4, 'string', tabid='Fuzzer parameters')

        d5 = 'A list with all fuzzable header names'
        o5 = option('fuzzableHeaders', cf.cf.getData('fuzzableHeaders'), d5, 'list',
                            tabid='Fuzzer parameters')

        d15 = 'Indicates what HTML form combo values w3af plugins will use: all, tb, tmb, t, b'
        h15 = 'Indicates what HTML form combo values, e.g. select options values,  w3af plugins will'
        h15 += ' use: all (All values), tb (only top and bottom values), tmb (top, middle and bottom'
        h15 += ' values), t (top values), b (bottom values)'
        o15 = option('fuzzFormComboValues', cf.cf.getData('fuzzFormComboValues'), d15, 'string',
                            help=h15, tabid='Fuzzer parameters')

        ######## Core parameters ########
        d6 = 'Automatic dependency enabling for plugins'
        h6 = 'If autoDependencies is enabled, and pluginA depends on pluginB that wasn\'t enabled,'
        h6 += ' then pluginB is automatically enabled.'
        o6 = option('autoDependencies', cf.cf.getData('autoDependencies'), d6, 'boolean',
                            help=h6, tabid='Core settings')

        d7 = 'Maximum depth of the discovery phase'
        h7 = 'For example, if set to 10, the webSpider plugin will only follow 10 link levels while'
        h7 += ' spidering the site. This applies to the whole discovery phase; not only to'
        h7 += ' the webSpider.'
        o7 = option('maxDepth', cf.cf.getData('maxDepth'), d7, 'integer', help=h7,
                            tabid='Core settings')
        
        d8 = 'Maximum number of threads that the w3af process will spawn.'
        d8 += ' Zero means no threads (recommended)'
        h8 = 'The maximum valid number of threads is 100.'
        o8 = option('maxThreads', cf.cf.getData('maxThreads'), d8, 'integer',
                            tabid='Core settings', help=h8)
        
        d9 = 'Maximum number of times the discovery function is called'
        o9 = option('maxDiscoveryLoops', cf.cf.getData('maxDiscoveryLoops'), d9, 'integer', 
                            tabid='Core settings')
        
        ######## Network parameters ########
        d10 = 'Local interface name to use when sniffing, doing reverse connections, etc.'
        o10 = option('interface', cf.cf.getData('interface'), d10, 'string', tabid='Network settings')

        d11 = 'Local IP address to use when doing reverse connections'
        o11 = option('localAddress', cf.cf.getData('localAddress'), d11, 'string',
                                tabid='Network settings')
        
        ######### Misc ###########
        d12 = 'Enable this when you are doing a demo in a conference'
        o12 = option('demo', cf.cf.getData('demo'), d12, 'boolean', tabid='Misc settings')
        
        d13 = 'A comma separated list of URLs that w3af should completely ignore'
        h13 = 'Sometimes it\'s a good idea to ignore some URLs and test them manually'
        o13 = option('nonTargets', cf.cf.getData('nonTargets'), d13, 'list', tabid='Misc settings')
        
        d14 = 'Export all discovered fuzzable requests to the given file (CSV)'
        o14 = option('exportFuzzableRequests', cf.cf.getData('exportFuzzableRequests'), d14,
                            'string', tabid='Export fuzzable Requests')
        
        ol = optionList()
        ol.add(o1)
        ol.add(o2)
        ol.add(o3)
        ol.add(o4)
        ol.add(o5)
        ol.add(o6)
        ol.add(o7)
        ol.add(o8)
        ol.add(o9)
        ol.add(o10)
        ol.add(o11)
        ol.add(o12)
        ol.add(o13)
        ol.add(o14)
        ol.add(o15)
        return ol
    
    def getDesc( self ):
        return 'This section is used to configure misc settings that affect the core and all plugins.'
    
    def setOptions( self, optionsMap ):
        '''
        This method sets all the options that are configured using the user interface 
        generated by the framework using the result of getOptions().
        
        @parameter optionsMap: A dictionary with the options for the plugin.
        @return: No value is returned.
        '''
        cf.cf.save('fuzzableCookie', optionsMap['fuzzCookie'].getValue() )
        cf.cf.save('fuzzFileContent', optionsMap['fuzzFileContent'].getValue() )
        cf.cf.save('fuzzFileName', optionsMap['fuzzFileName'].getValue() )
        cf.cf.save('fuzzFCExt', optionsMap['fuzzFCExt'].getValue() )
        cf.cf.save('fuzzFormComboValues', optionsMap['fuzzFormComboValues'].getValue() )
        cf.cf.save('autoDependencies', optionsMap['autoDependencies'].getValue() )
        cf.cf.save('maxDepth', optionsMap['maxDepth'].getValue() )
        
        if optionsMap['maxThreads'].getValue()  > 100:
            raise w3afException('The maximum valid number of threads is 100.')
        max_threads = optionsMap['maxThreads'].getValue()
        cf.cf.save('maxThreads', max_threads )
        tm.setMaxThreads( max_threads )
        
        cf.cf.save('fuzzableHeaders', optionsMap['fuzzableHeaders'].getValue() )
        cf.cf.save('maxDiscoveryLoops', optionsMap['maxDiscoveryLoops'].getValue() )
        cf.cf.save('interface', optionsMap['interface'].getValue() )
        cf.cf.save('localAddress', optionsMap['localAddress'].getValue() )
        cf.cf.save('demo', optionsMap['demo'].getValue()  )
        cf.cf.save('nonTargets', optionsMap['nonTargets'].getValue() )
        cf.cf.save('exportFuzzableRequests', optionsMap['exportFuzzableRequests'].getValue() )
        
# This is an undercover call to __init__ :) , so I can set all default parameters.
miscSettings()
