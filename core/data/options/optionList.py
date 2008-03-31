'''
optionList.py

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

import copy
from core.controllers.w3afException import w3afException

class optionList:
    '''
    This class represents a list of options.
    
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''
    def __init__(self):
        self._oList = []
        
    def add( self, option ):
        self._oList.append( option )
        
    def __str__( self ):
        res = '<?xml version="1.0" encoding="ISO-8859-1"?>\n<OptionList>\n'
        for o in self._oList:
            res += str(o)
        res += '</OptionList>'
        return res
        
    def __getitem__( self, itemName ):
        '''
        This method is used when on any configurable object the developer does something like:
        
        def setOptions( self, optionsList ):
            self._checkPersistent = optionsList['checkPersistent']
            
        @return: The value of the item that was selected
        '''
        for o in self._oList:
            if o.getName() == itemName:
                return o.getValue()
        raise w3afException('The optionList object doesn\'t contain an option with the name: ' + itemName )
