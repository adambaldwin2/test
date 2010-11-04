'''
findCaptchas.py

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

from core.controllers.basePlugin.baseDiscoveryPlugin import baseDiscoveryPlugin
import core.data.parsers.urlParser as urlParser
from core.controllers.w3afException import w3afException

import core.data.kb.knowledgeBase as kb
import core.data.kb.info as info

import sha
import mimetypes
import core.data.parsers.documentParser as documentParser


class findCaptchas(baseDiscoveryPlugin):
    '''
    Identify captcha images on web pages.
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''

    def __init__(self):
        baseDiscoveryPlugin.__init__(self)
        
    def discover(self, fuzzableRequest ):
        '''
        Find captcha images.
        
        @parameter fuzzableRequest: A fuzzableRequest instance that contains (among other things) the URL to test.
        '''
        # GET the document, and fetch the images
        image_map_1 = self._get_images( fuzzableRequest )
        
        # Re-GET the document, and fetch the images
        image_map_2 = self._get_images( fuzzableRequest )
        
        # Compare the images (different images may be captchas)
        changed_images_list = []
        if image_map_1.keys() != image_map_2.keys():
            for img_src in image_map_1:
                if img_src not in image_map_2:
                    changed_images_list.append( img_src )
        else:
            # Compare content
            for img_src in image_map_1:
                if image_map_1[ img_src ] != image_map_2[ img_src ]:
                    changed_images_list.append( img_src )
                
        for img_src in changed_images_list:
            i = info.info()
            i.setName('Captcha image detected')
            i.setURL( img_src )
            i.setMethod( 'GET' )
            i.setDesc( 'Found a CAPTCHA image at: "' + img_src + '".')
            kb.kb.append( self, 'findCaptchas', i )
            om.out.information( i.getDesc() )
            
        return []
    
    def _get_images( self, fuzzable_request ):
        '''
        Get all img tags and retrieve the src.
        
        @parameter fuzzable_request: The request to modify
        @return: A map with the img src as a key, and a hash of the image contents as the value
        '''
        res = {}
        
        try:
            response = self._urlOpener.GET( fuzzable_request.getURI(), useCache=False )
        except:
            om.out.debug('Failed to retrieve the page for finding captchas.')
        else:
            # Do not use dpCache here, it's no good.
            #dp = dpCache.dpc.getDocumentParserFor( response )
            try:
                document_parser = documentParser.documentParser( response )
            except w3afException:
                pass
            else:
                image_list = document_parser.getReferencesOfTag('img')
                image_list = [ urlParser.uri2url(i) for i in image_list]
                for img_src in image_list:
                    # TODO: Use self._tm.startFunction
                    try:
                        image_response = self._urlOpener.GET( img_src, useCache=False )
                    except:
                        om.out.debug('Failed to retrieve the image for finding captchas.')
                    else:
                        if image_response.is_image():
                            res[ img_src ] = sha.new(image_response.getBody()).hexdigest()
        
        return res

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
        This plugin finds any CAPTCHA images that appear on a HTML document. The
        discovery is performed by requesting the document two times, and comparing the
        hashes of the images, if they differ, then they may be a CAPTCHA.
        '''
