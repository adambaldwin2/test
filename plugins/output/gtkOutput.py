'''
gtkOutput.py

Copyright 2008 Andres Riancho

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


from core.controllers.basePlugin.baseOutputPlugin import baseOutputPlugin
import core.data.kb.knowledgeBase as kb
from core.controllers.w3afException import *

# The output plugin must know the session name that is saved in the config object,
# the session name is assigned in the target settings
import core.data.kb.config as cf

import Queue

# The database
from extlib.buzhug.buzhug import Base

# Only to be used with care.
import core.controllers.outputManager as om
import os

class gtkOutput(baseOutputPlugin):
    '''
    Saves messages to kb.kb.getData('gtkOutput', 'queue'), messages are saved in the form of objects.
    
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''
    
    def __init__(self):
        self.queue = Queue.Queue()
        kb.kb.save( 'gtkOutput', 'queue' , self.queue )
        baseOutputPlugin.__init__(self)
        
        sessionName = cf.cf.getData('sessionName')
        db_req_res_dirName = os.path.join('sessions', 'db_req_' + sessionName )
        
        try:
            self._del_dir(db_req_res_dirName)
        except Exception, e:
            # I get here when the session directory for this db wasn't created
            # and when the user has no permissions to remove the directory
            pass
            
        try:
            self._db_req_res = Base( db_req_res_dirName )
            # Create the database
            #CREATE TABLE request_response (id INTEGER PRIMARY KEY, method TEXT, uri TEXT, http_version TEXT, headers TEXT, data TEXT, http_version TEXT, code INTEGER, msg TEXT, headers TEXT, body TEXT)
            self._db_req_res.create( ('id',int), ('method', str), ('uri', str), ('http_version', str), ('request_headers', str), ('postdata', str), ('code', int), ('msg', str), ('response_headers', str), ('body', str) )
        except Exception, e:
            raise w3afException('An exception was raised while creating the gtkOutput database: ' + str(e) )
        else:
            kb.kb.save('gtkOutput', 'db', self._db_req_res )
    
    def _del_dir(self,path):
        for file in os.listdir(path):
            file_or_dir = os.path.join(path,file)
            if os.path.isdir(file_or_dir) and not os.path.islink(file_or_dir):
                del_dir(file_or_dir) #it's a directory reucursive call to function again
            else:
                try:
                    os.remove(file_or_dir) #it's a file, delete it
                except Exception, e:
                    #probably failed because it is not a normal file
                    raise w3afException('An exception was raised while removing the old database: ' + str(e) )
        os.rmdir(path) #delete the directory here

    def debug(self, msgString, newLine = True ):
        '''
        This method is called from the output object. The output object was called from a plugin
        or from the framework. This method should take an action for debug messages.
        '''
        m = message( 'debug', msgString , newLine )
        self._addToQueue( m )
    
    def information(self, msgString , newLine = True ):
        '''
        This method is called from the output object. The output object was called from a plugin
        or from the framework. This method should take an action for informational messages.
        ''' 
        m = message( 'information', msgString , newLine )
        self._addToQueue( m )

    def error(self, msgString , newLine = True ):
        '''
        This method is called from the output object. The output object was called from a plugin
        or from the framework. This method should take an action for error messages.
        '''     
        m = message( 'error', msgString , newLine )
        self._addToQueue( m )

    def vulnerability(self, msgString , newLine = True ):
        '''
        This method is called from the output object. The output object was called from a plugin
        or from the framework. This method should take an action when a vulnerability is found.
        '''     
        m = message( 'vulnerability', msgString , newLine )
        self._addToQueue( m )
        
    def console( self, msgString, newLine = True ):
        '''
        This method is used by the w3af console to print messages to the outside.
        '''
        m = message( 'console', msgString , newLine )
        self._addToQueue( m )
    
    def _addToQueue( self, m ):
        '''
        Adds a message object to the queue. If the queue isn't there, it creates one.
        '''
        self.queue.put( m )
    
    def logHttp( self, request, response):
        try:
            #CREATE TABLE request_response (id INTEGER PRIMARY KEY, method TEXT, uri TEXT, http_version TEXT, headers TEXT, data TEXT, http_version TEXT, code INTEGER, msg TEXT, headers TEXT, body TEXT)
            self._db_req_res.insert(response.id, request.getMethod(), request.getURI(), '1.1', request.dumpHeaders(), request.getData(), response.getCode(), response.getMsg(), response.dumpHeaders(), response.getBody() )
        except KeyboardInterrupt, k:
            raise k
        except Exception, e:
            om.out.error( 'Exception while inserting request/response to the database: ' + str(e) )
            raise e
        
    def getLongDesc( self ):
        '''
        @return: A DETAILED description of the plugin functions and features.
        '''
        return '''
        Saves messages to kb.kb.getData('gtkOutput', 'queue'), messages are saved in the form of objects. This plugin
        was created to be able to communicate with the gtkUi and should be enabled if you are using it.
        '''

    def getOptionsXML(self):
        '''
        This method returns a XML containing the Options that the plugin has.
        Using this XML the framework will build a window, a menu, or some other input method to retrieve
        the info from the user. The XML has to validate against the xml schema file located at :
        w3af/core/display.xsd
        
        This method MUST be implemented on every plugin. 
        
        @return: XML String
        @see: core/display.xsd
        '''
        return  '<?xml version="1.0" encoding="ISO-8859-1"?>\
        <OptionList>\
        </OptionList>\
        '

class message:
    def __init__( self, type, msg , newLine=True ):
        self._type = type
        self._msg = unicode(msg)
        self._newLine = newLine
        
    def getMsg( self ):
        return self._msg
    
    def getType( self ):
        return self._type
        
    def getNewLine( self ):
        return self._newLine
        
