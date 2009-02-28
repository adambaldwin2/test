'''
documentParser.py

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
from core.controllers.w3afException import w3afException

import core.data.parsers.htmlParser as htmlParser
import core.data.parsers.pdfParser as pdfParser
import core.data.parsers.swfParser as swfParser
import core.data.parsers.wmlParser as wmlParser

try:
    from extlib.pyPdf import pyPdf as pyPdf
except ImportError:
    import pyPdf
    
import StringIO
import re

class documentParser:
    '''
    This class is a document parser.
    
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''
    def __init__(self, httpResponse, normalizeMarkup=True):
        if self._isWML( httpResponse ):
            self._parser = wmlParser.wmlParser( httpResponse )
        elif self._isPDF( httpResponse ):
            self._parser = pdfParser.pdfParser( httpResponse )
        elif self._isSWF( httpResponse ):
            self._parser = swfParser.swfParser( httpResponse )
        elif self._isHTMLorText( httpResponse ):
            self._parser = htmlParser.htmlParser( httpResponse, normalizeMarkup)
        else:
            raise w3afException('There is no parser for "' + httpResponse.getURL() + '".')
    
    def _isPDF( self, httpResponse ):
        '''
        @httpResponse: A http response object that contains a document of type HTML / PDF / WML / etc.
        @return: True if the document parameter is a string that contains a PDF document.
        '''
        document = httpResponse.getBody()
        
        header_match = self._getContentType(httpResponse) == 'application/pdf'
        contentMatch = document.startswith('%PDF-') and document.endswith('%%EOF')
        
        if header_match or contentMatch:
            try:
                pyPdf.PdfFileReader( StringIO.StringIO(document) )
            except Exception:
                return False
            else:
                return True
        else:
            return False
    
    def _isSWF(self, httpResponse):
        '''
        @return: True if the httpResponse contains a SWF file.
        '''
        body = httpResponse.getBody()
        
        if len(body) > 5:
            magic = body[:3]
            
            # TODO: Add more checks here?
            if magic in ['FWS', 'CWS']:
                return True
        
        return False
    
    def _isWML( self, httpResponse ):
        '''
        @httpResponse: A http response object that contains a document of type HTML / PDF / WML / etc.
        @return: True if the document parameter is a string that contains a WML document.
        '''
        document = httpResponse.getBody()
        
        header_match = self._getContentType(httpResponse) == 'text/vnd.wap.wml'
        contentMatch = re.search('<!DOCTYPE wml PUBLIC',  document,  re.IGNORECASE)
        
        if header_match or contentMatch:
            return True
        else:
            return False
    
    def _isHTMLorText( self, httpResponse ):
        '''
        @httpResponse: A http response object that contains a document of type HTML / PDF / WML / etc.
        @return: True if the document parameter is a string that contains a HTML or Text document.
        '''
        header_match = 'text' in self._getContentType(httpResponse)
        header_match |= 'html' in self._getContentType(httpResponse)
        
        if header_match:
            return True
        else:
            return False
    
    def _getContentType(self, httpResponse):
        '''
        @return: The value of the content-type header; '' if not found.
        '''
        for i in httpResponse.getHeaders():
            if i.lower() == 'content-type':
                return httpResponse.getHeaders()[i]
        return ''
    
    def getForms( self ):
        '''
        @return: A list of forms.
        '''
        return self._parser.getForms()
        
    def getReferences( self ):
        '''
        @return: A list of URL strings.
        '''
        return self._parser.getReferences()
    
    def getReferencesOfTag( self, tag ):
        '''
        @parameter tag: A tag object.
        @return: A list of references related to the tag that is passed as parameter.
        '''
        return self._parser.getReferencesOfTag( tag )
        
    def getEmails( self, domain=None ):
        '''
        @parameter domain: Indicates what email addresses I want to retrieve:   "*@domain".
        @return: A list of email accounts that are inside the document.
        '''
        return self._parser.getEmails( domain )
    
    def getComments( self ):
        '''
        @return: A list of comments.
        '''
        return self._parser.getComments()
    
    def getScripts( self ):
        '''
        @return: A list of scripts (like javascript).
        '''
        return self._parser.getScripts()
        
    def getMetaRedir( self ):
        '''
        @return: A list of the meta redirection tags.
        '''
        return self._parser.getMetaRedir()
        
    def getMetaTags( self ):
        '''
        @return: A list of all meta tags.
        '''
        return self._parser.getMetaTags()
    
    
