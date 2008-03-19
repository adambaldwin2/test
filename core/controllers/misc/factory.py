'''
factory.py

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

'''
This module defines a factory function that is used around the project.

@author: Andres Riancho ( andres.riancho@gmail.com )
'''
import sys

def factory(ModuleName, *args):
    '''
    This function creates an instance of a class thats inside a module
    with the same name.
    
    Example :
    >> f00 = factory( ''plugins.discovery.googleSpider'' )
    >> print f00
    <googleSpider.googleSpider instance at 0xb7a1f28c>
    
    @parameter ModuleName: What do you want to instanciate ?
    @return: An instance.
    '''
    __import__(ModuleName)
    aModule = sys.modules[ModuleName]
    className = ModuleName.split('.')[len(ModuleName.split('.'))-1]
    aClass = getattr( aModule , className )
    return apply(aClass, args)
