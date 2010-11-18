#   This library is free software; you can redistribute it and/or
#   modify it under the terms of the GNU Lesser General Public
#   License as published by the Free Software Foundation; either
#   version 2.1 of the License, or (at your option) any later version.
#
#   This library is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   Lesser General Public License for more details.
#
#   You should have received a copy of the GNU Lesser General Public
#   License along with this library; if not, write to the 
#     Free Software Foundation, Inc., 
#     59 Temple Place, Suite 330, 
#     Boston, MA  02111-1307  USA

# This file is part of urlgrabber, a high-level cross-protocol url-grabber
# Copyright 2002-2004 Michael D. Stenner, Ryan Tomayko

# This file was modified (considerably) to be integrated with w3af. Some modifications are:
#   - Added the size limit for responses
#   - Raising w3afExceptions in some places
#   - Modified the HTTPResponse object in order to be able to perform multiple reads, and
#     added a hack for the HEAD method.

"""An HTTP handler for urllib2 that supports HTTP 1.1 and keepalive.

>>> import urllib2
>>> from keepalive import HTTPHandler
>>> keepalive_handler = HTTPHandler()
>>> opener = urllib2.build_opener(keepalive_handler)
>>> urllib2.install_opener(opener)
>>> 
>>> fo = urllib2.urlopen('http://www.python.org')

If a connection to a given host is requested, and all of the existing
connections are still in use, another connection will be opened.  If
the handler tries to use an existing connection but it fails in some
way, it will be closed and removed from the pool.

To remove the handler, simply re-run build_opener with no arguments, and
install that opener.

You can explicitly close connections by using the close_connection()
method of the returned file-like object (described below) or you can
use the handler methods:

  close_connection(host)
  close_all()
  open_connections()

NOTE: using the close_connection and close_all methods of the handler
should be done with care when using multiple threads.
  * there is nothing that prevents another thread from creating new
    connections immediately after connections are closed
  * no checks are done to prevent in-use connections from being closed

>>> keepalive_handler.close_all()

EXTRA ATTRIBUTES AND METHODS

  Upon a status of 200, the object returned has a few additional
  attributes and methods, which should not be used if you want to
  remain consistent with the normal urllib2-returned objects:

    close_connection()  -  close the connection to the host
    readlines()      -  you know, readlines()
    status            -  the return status (ie 404)
    reason            -  english translation of status (ie 'File not found')

  If you want the best of both worlds, use this inside an
  AttributeError-catching try:

  >>> try: status = fo.status
  >>> except AttributeError: status = None

  Unfortunately, these are ONLY there if status == 200, so it's not
  easy to distinguish between non-200 responses.  The reason is that
  urllib2 tries to do clever things with error codes 301, 302, 401,
  and 407, and it wraps the object upon return.

  For python versions earlier than 2.4, you can avoid this fancy error
  handling by setting the module-level global HANDLE_ERRORS to zero.
  You see, prior to 2.4, it's the HTTP Handler's job to determine what
  to handle specially, and what to just pass up.  HANDLE_ERRORS == 0
  means "pass everything up".  In python 2.4, however, this job no
  longer belongs to the HTTP Handler and is now done by a NEW handler,
  HTTPErrorProcessor.  Here's the bottom line:

    python version < 2.4
        HANDLE_ERRORS == 1  (default) pass up 200, treat the rest as
                            errors
        HANDLE_ERRORS == 0  pass everything up, error processing is
                            left to the calling code
    python version >= 2.4
        HANDLE_ERRORS == 1  pass up 200, treat the rest as errors
        HANDLE_ERRORS == 0  (default) pass everything up, let the
                            other handlers (specifically,
                            HTTPErrorProcessor) decide what to do

  In practice, setting the variable either way makes little difference
  in python 2.4, so for the most consistent behavior across versions,
  you probably just want to use the defaults, which will give you
  exceptions on errors.

"""

# $Id: keepalive.py,v 1.16 2006/09/22 00:58:05 mstenner Exp $

from __future__ import with_statement

import urllib2
import httplib
import socket
import threading
import traceback
import urllib
import sys

if __name__ != '__main__':
    import core.controllers.outputManager as om
    from core.controllers.w3afException import w3afException
    import core.data.kb.config as cf
    from core.data.constants.httpConstants import *

DEBUG = None
MAXCONNECTIONS = 500

if sys.version_info < (2, 4): HANDLE_ERRORS = 1
else: HANDLE_ERRORS = 0


class HTTPResponse(httplib.HTTPResponse):
    # we need to subclass HTTPResponse in order to
    # 1) add readline() and readlines() methods
    # 2) add close_connection() methods
    # 3) add info() and geturl() methods

    # in order to add readline(), read must be modified to deal with a
    # buffer.  example: readline must read a buffer and then spit back
    # one line at a time.  The only real alternative is to read one
    # BYTE at a time (ick).  Once something has been read, it can't be
    # put back (ok, maybe it can, but that's even uglier than this),
    # so if you THEN do a normal read, you must first take stuff from
    # the buffer.

    # the read method wraps the original to accomodate buffering,
    # although read() never adds to the buffer.
    # Both readline and readlines have been stolen with almost no
    # modification from socket.py
    

    def __init__(self, sock, debuglevel=0, strict=0, method=None):
        if method: # the httplib in python 2.3 uses the method arg
            httplib.HTTPResponse.__init__(self, sock, debuglevel, method)
        else: # 2.2 doesn't
            httplib.HTTPResponse.__init__(self, sock, debuglevel)
        self.fileno = sock.fileno
        self.code = None
        self._rbuf = ''
        self._rbufsize = 8096
        self._handler = None # inserted by the handler later
        self._host = None   # (same)
        self._url = None     # (same)
        self._connection = None # (same)
        self._method = method
        
        self._multiread = None

    def _raw_read(self, amt=None):
        '''
        This is the original read function from httplib with a minor modification
        that allows me to check the size of the file being fetched, and throw an exception
        in case it is too big.
        '''
        if self.fp is None:
            return ''

        if __name__ != '__main__':
            if self.length > cf.cf.getData('maxFileSize'):
                self.status = NO_CONTENT
                self.reason = 'No Content'  # Reason-Phrase
                return ''

        if self.chunked:
            return self._read_chunked(amt)

        if amt is None:
            # unbounded read
            if self.length is None:
                s = self.fp.read()
            else:
                s = self._safe_read(self.length)
                self.length = 0
            self.close()        # we read everything
            return s

        if self.length is not None:
            if amt > self.length:
                # clip the read to the "end of response"
                amt = self.length

        # we do not use _safe_read() here because this may be a .will_close
        # connection, and the user is reading more bytes than will be provided
        # (for example, reading in 1k chunks)
        s = self.fp.read(amt)
        if self.length is not None:
            self.length -= len(s)

        return s

    def close(self):
        if self.fp:
            self.fp.close()
            self.fp = None
            if self._handler:
                self._handler._request_closed(self, self._host, self._connection)

    def close_connection(self):
        self._handler._remove_connection(self._host, self._connection, close=1)
        self.close()
        
    def info(self):
        return self.headers

    def geturl(self):
        return self._url

    def read(self, amt=None):
        # w3af does always read all the content of the response...
        # and I also need to do multiple reads to this response...
        # BUGBUG: Is this OK? What if a HEAD method actually returns something?!
        if self._method == 'HEAD':
            # This indicates that we have read all that we needed from the socket
            # and that the socket can be reused!
            #
            # This like fixes the bug with title "GET is much faster than HEAD".
            #https://sourceforge.net/tracker2/?func=detail&aid=2202532&group_id=170274&atid=853652
            self.close()
            return ''
            
        if self._multiread is None:
            #read all
            self._multiread = self._raw_read()  
            
        if not amt is None:
            L = len(self._rbuf)
            if amt > L:
                amt -= L
            else:
                s = self._rbuf[:amt]
                self._rbuf = self._rbuf[amt:]
                return s
        else:
            s = self._rbuf + self._multiread
            self._rbuf = ''
            return s

    def readline(self, limit=-1):
        data = ""
        i = self._rbuf.find('\n')
        while i < 0 and not (0 < limit <= len(self._rbuf)):
            new = self._raw_read(self._rbufsize)
            if not new: break
            i = new.find('\n')
            if i >= 0: i = i + len(self._rbuf)
            self._rbuf = self._rbuf + new
        if i < 0: i = len(self._rbuf)
        else: i = i+1
        if 0 <= limit < len(self._rbuf): i = limit
        data, self._rbuf = self._rbuf[:i], self._rbuf[i:]
        return data

    def readlines(self, sizehint = 0):
        total = 0
        list = []
        while 1:
            line = self.readline()
            if not line: break
            list.append(line)
            total += len(line)
            if sizehint and total >= sizehint:
                break
        return list

    def setBody( self, data ):
        '''
        This was added to make my life a lot simpler while implementing mangle plugins
        '''
        self._multiread = data

class ConnectionManager:
    """
    The connection manager must be able to:
        * keep track of all existing HTTPConnections
        * kill the connections that we're not going to use anymore
    """
    def __init__(self):
        self._lock = threading.RLock()
        self._hostmap = {} # map hosts to a list of connections
        self._connmap = {} # map connections to host
        self._readymap = {} # map connection to ready state

    def add(self, host, connection, ready):
        '''
        Add a connection to the connmap.
        '''
        with self._lock:
            try:
                if not self._hostmap.has_key(host): self._hostmap[host] = []
                self._hostmap[host].append(connection)
                self._connmap[connection] = host
                self._readymap[connection] = ready
            finally:
                if __name__ != '__main__':
                    msg = 'keepalive: added one connection, len(self._hostmap["'+host+'"]): '
                    msg += str( self.get_connectionNumber(host) )
                    om.out.debug( msg )

    def remove(self, connection):
        '''
        Remove a connection, it was closed by the server.
        '''
        with self._lock:
            try:
                host = self._connmap[connection]
            except KeyError:
                pass
            else:
                del self._connmap[connection]
                del self._readymap[connection]
                self._hostmap[host].remove(connection)
                if __name__ != '__main__':
                    msg = 'keepalive: removed one connection,  len(self._hostmap["'+host+'"]): '
                    msg += str( self.get_connectionNumber(host) )
                    om.out.debug( msg )
                if not self._hostmap[host]: del self._hostmap[host]

    def set_ready(self, connection, ready):
        self._readymap[connection] = ready
        
    def get_ready_conn(self, host):
        conn = None
        
        with self._lock:
            if self._hostmap.has_key(host):
                for c in self._hostmap[host]:
                    if self._readymap[c]:
                        self._readymap[c] = 0
                        conn = c
                        break
        
        return conn

    def get_all(self, host=None):
        if host:
            return list(self._hostmap.get(host, []))
        else:
            return dict(self._hostmap)
    
    def get_connectionNumber( self, host=None ):
        res = 0
        if host is None:
            for i in self._hostmap.keys():
                res += len(self._hostmap[ i ])
        else:
            res = len(self._hostmap[ host ])
        return res
        
class KeepAliveHandler:
    def __init__(self):
        self._cm = ConnectionManager()
        self._lock = threading.RLock()
        
    #### Connection Management
    def open_connections(self):
        """return a list of connected hosts and the number of connections
        to each.  [('foo.com:80', 2), ('bar.org', 1)]"""
        return [(host, len(li)) for (host, li) in self._cm.get_all().items()]

    def close_connection(self, host):
        """close connection(s) to <host>
        host is the host:port spec, as in 'www.cnn.com:8080' as passed in.
        no error occurs if there is no connection to that host."""
        for h in self._cm.get_all(host):
            self._cm.remove(h)
            h.close()
        
    def close_all(self):
        """close all open connections"""
        for host, conns in self._cm.get_all().items():
            for h in conns:
                self._cm.remove(h)
                h.close()
        
    def _request_closed(self, request, host, connection):
        """tells us that this request is now closed and that the
        connection is ready for another request"""
        self._cm.set_ready(connection, 1)

    def _remove_connection(self, host, connection, close=0):
        if close: connection.close()
        self._cm.remove(connection)
        
    #### Transaction Execution
    def do_open(self, req):
        host = req.get_host()
        if not host:
            raise urllib2.URLError('no host given')
        
        if self._cm.get_connectionNumber() >= MAXCONNECTIONS:
            # This will fix the 'Too many open files' exception
            if __name__ != '__main__':
                msg = 'keepalive: Closing all connections. The connection number exceeded'
                msg += ' MAXCONNECTIONS (' + str(MAXCONNECTIONS) + ') .'
                om.out.debug( msg )
            
            with self._lock:
                self.close_all()

        else:
            if __name__ != '__main__':
                msg = 'keepalive: The connection manager has '
                msg += str(self._cm.get_connectionNumber()) + ' active connections.'
                om.out.debug( msg )
            
        try:
            h = self._cm.get_ready_conn(host)
            while h:
                r = self._reuse_connection(h, req, host)

                # if this response is non-None, then it worked and we're
                # done.  Break out, skipping the else block.
                if r: break

                # connection is bad - possibly closed by server
                # discard it and ask for the next free connection
                h.close()
                self._cm.remove(h)
                h = self._cm.get_ready_conn(host)
            else:
                # no (working) free connections were found.  Create a new one.
                h = self._get_connection(host)
                
                # First of all, call the request method. This is needed for HTTPS Proxy
                if isinstance(h, ProxyHTTPConnection):
                    h.proxy_setup( req.get_full_url() )
                
                if DEBUG: DEBUG.info("creating new connection to %s (%d)", host, id(h))
                self._cm.add(host, h, 0)
                self._start_transaction(h, req)
                r = h.getresponse()
        except (socket.error, httplib.HTTPException), err:
            raise urllib2.URLError(err)
            
        # if not a persistent connection, don't try to reuse it
        if r.will_close: self._cm.remove(h)

        if DEBUG: DEBUG.info("STATUS: %s, %s", r.status, r.reason)
        r._handler = self
        r._host = host
        r._url = req.get_full_url()
        r._connection = h
        r.code = r.status
        r.headers = r.msg
        r.msg = r.reason
        
        if r.status == 200 or not HANDLE_ERRORS:
            return r
        else:
            return self.parent.error('http', req, r, r.status, r.msg, r.headers)

    def _reuse_connection(self, h, req, host):
        """start the transaction with a re-used connection
        return a response object (r) upon success or None on failure.
        This DOES not close or remove bad connections in cases where
        it returns.  However, if an unexpected exception occurs, it
        will close and remove the connection before re-raising.
        """
        try:
            self._start_transaction(h, req)
            r = h.getresponse()
            # note: just because we got something back doesn't mean it
            # worked.  We'll check the version below, too.
        except (socket.error, httplib.HTTPException):
            r = None
        except:
            # adding this block just in case we've missed
            # something we will still raise the exception, but
            # lets try and close the connection and remove it
            # first.  We previously got into a nasty loop
            # where an exception was uncaught, and so the
            # connection stayed open.  On the next try, the
            # same exception was raised, etc.  The tradeoff is
            # that it's now possible this call will raise
            # a DIFFERENT exception
            if DEBUG: DEBUG.error("unexpected exception - closing connection to %s (%d)", host, id(h))
            self._cm.remove(h)
            h.close()
            raise
                    
        if r is None or r.version == 9:
            # httplib falls back to assuming HTTP 0.9 if it gets a
            # bad header back.  This is most likely to happen if
            # the socket has been closed by the server since we
            # last used the connection.
            if DEBUG: DEBUG.info("failed to re-use connection to %s (%d)", host, id(h))
            r = None
        else:
            if DEBUG: DEBUG.info("re-using connection to %s (%d)", host, id(h))
            r._multiread = None

        return r

    def _start_transaction(self, h, req):
        try:
            if req.has_data():
                data = req.get_data()
                h.putrequest( req.get_method() , req.get_selector(), skip_host=1, skip_accept_encoding=1)
                if not req.has_header('Content-type'):
                    h.putheader('Content-type' , 'application/x-www-form-urlencoded')
                if not req.has_header('Content-length'):
                    h.putheader('Content-length', '%d' % len(data))
            else:
                h.putrequest( req.get_method() , req.get_selector(), skip_host=1, skip_accept_encoding=1)
        except (socket.error, httplib.HTTPException), err:
            raise urllib2.URLError(err)
        
        headerDict = {}
        
        for k, v in self.parent.addheaders:
            headerDict[ k ] = v
            
        for k, v in req.headers.items():
            headerDict[ k ] = v     
            
        for k, v in req.unredirected_hdrs.items():
            headerDict[ k ] = v
        
        for k in headerDict:
            h.putheader(k, headerDict[k] )

        h.endheaders()
        if req.has_data():
            h.send(data)

    def _get_connection(self, host):
        return NotImplementedError

class HTTPHandler(KeepAliveHandler, urllib2.HTTPHandler):
    def __init__(self):
        KeepAliveHandler.__init__(self)

    def http_open(self, req):
        return self.do_open(req)

    def _get_connection(self, host):
        return HTTPConnection(host)

class HTTPSHandler(KeepAliveHandler, urllib2.HTTPSHandler):
    def __init__(self, proxy):
        KeepAliveHandler.__init__(self)
        self._proxy = proxy
        host = port = ''
        try:
            host, port = self._proxy.split(':')
        except:
            msg = 'The proxy you are specifying is invalid! (' 
            msg += self._proxy + '), IP:Port is expected.'
            raise w3afException( msg )

        if not host or not port:
            self._proxy = None
            
    def https_open(self, req):
        return self.do_open(req)

    def _get_connection(self, host):
        if self._proxy:
            proxyHost, port = self._proxy.split(':')
            return ProxyHTTPSConnection(proxyHost, port)
        else:
            return HTTPSConnection(host)

class ProxyHTTPConnection(httplib.HTTPConnection):
    '''
    this class is used to provide HTTPS CONNECT support.
    '''
    _ports = {'http' : 80, 'https' : 443}
    
    def __init__(self, host, port=None, strict=None):
        httplib.HTTPConnection.__init__(self, host, port, strict)
        
    def proxy_setup(self, url):
        #request is called before connect, so can interpret url and get
        #real host/port to be used to make CONNECT request to proxy
        proto, rest = urllib.splittype(url)
        if proto is None:
            raise ValueError, "unknown URL type: %s" % url
        #get host
        host, rest = urllib.splithost(rest)
        self._real_host = host
        
        #try to get port
        host, port = urllib.splitport(host)
        #if port is not defined try to get from proto
        if port is None:
            try:
                self._real_port = self._ports[proto]
            except KeyError:
                raise ValueError, "unknown protocol for: %s" % url
        else:
            self._real_port = port           
       
    def connect(self):
        httplib.HTTPConnection.connect(self)
        #send proxy CONNECT request
        self.send("CONNECT %s:%d HTTP/1.0\r\n\r\n" % (self._real_host, self._real_port))
        #expect a HTTP/1.0 200 Connection established
        response = self.response_class(self.sock, strict=self.strict, method=self._method)
        (version, code, message) = response._read_status()
        #probably here we can handle auth requests...
        if code != 200:
            #proxy returned and error, abort connection, and raise exception
            self.close()
            raise socket.error, "Proxy connection failed: %d %s" % (code, message.strip())
        #eat up header block from proxy....
        while True:
            #should not use directly fp probablu
            line = response.fp.readline()
            if line == '\r\n': break

class ProxyHTTPSConnection(ProxyHTTPConnection):
    '''
    this class is used to provide HTTPS CONNECT support.
    '''
    default_port = 443
    
    # Customized response class
    response_class = HTTPResponse
    
    def __init__(self, host, port = None, key_file = None, cert_file = None, strict = None):
        ProxyHTTPConnection.__init__(self, host, port)
        self.key_file = key_file
        self.cert_file = cert_file
    
    def connect(self):
        ProxyHTTPConnection.connect(self)
        #make the sock ssl-aware
        ssl = socket.ssl(self.sock, self.key_file, self.cert_file)
        self.sock = httplib.FakeSocket(self.sock, ssl)    

class HTTPConnection(httplib.HTTPConnection):
    # use the modified response class
    response_class = HTTPResponse

class HTTPSConnection(httplib.HTTPSConnection):
    response_class = HTTPResponse
    
#########################################################################
#####   TEST FUNCTIONS
#########################################################################

def error_handler(url):
    global HANDLE_ERRORS
    orig = HANDLE_ERRORS
    keepalive_handler = HTTPHandler()
    opener = urllib2.build_opener(keepalive_handler)
    urllib2.install_opener(opener)
    pos = {0: 'off', 1: 'on'}
    for i in (0, 1):
        print "  fancy error handling %s (HANDLE_ERRORS = %i)" % (pos[i], i)
        HANDLE_ERRORS = i
        try:
            fo = urllib2.urlopen(url)
            foo = fo.read()
            fo.close()
            try: status, reason = fo.status, fo.reason
            except AttributeError: status, reason = None, None
        except IOError, e:
            print "  EXCEPTION: %s" % e
            raise
        else:
            print "  status = %s, reason = %s" % (status, reason)
    HANDLE_ERRORS = orig
    hosts = keepalive_handler.open_connections()
    print "open connections:", hosts
    keepalive_handler.close_all()

def continuity(url):
    import md5
    format = '%25s: %s'
    
    # first fetch the file with the normal http handler
    opener = urllib2.build_opener()
    urllib2.install_opener(opener)
    fo = urllib2.urlopen(url)
    foo = fo.read()
    fo.close()
    m = md5.new(foo)
    print format % ('normal urllib', m.hexdigest())

    # now install the keepalive handler and try again
    opener = urllib2.build_opener(HTTPHandler())
    urllib2.install_opener(opener)

    fo = urllib2.urlopen(url)
    foo = fo.read()
    fo.close()
    m = md5.new(foo)
    print format % ('keepalive read', m.hexdigest())

    fo = urllib2.urlopen(url)
    foo = ''
    while 1:
        f = fo.readline()
        if f: foo = foo + f
        else: break
    fo.close()
    m = md5.new(foo)
    print format % ('keepalive readline', m.hexdigest())

def comp(N, url):
    print '  making %i connections to:\n  %s' % (N, url)

    sys.stdout.write('  first using the normal urllib handlers')
    # first use normal opener
    opener = urllib2.build_opener()
    urllib2.install_opener(opener)
    t1 = fetch(N, url)
    print '  TIME: %.3f s' % t1

    sys.stdout.write('  now using the keepalive handler    ')
    # now install the keepalive handler and try again
    opener = urllib2.build_opener(HTTPHandler())
    urllib2.install_opener(opener)
    t2 = fetch(N, url)
    print '  TIME: %.3f s' % t2
    print '  improvement factor: %.2f' % (t1/t2, )
    
def fetch(N, url, delay=0):
    import time
    lens = []
    starttime = time.time()
    for i in range(N):
        if delay and i > 0: time.sleep(delay)
        fo = urllib2.urlopen(url)
        foo = fo.read()
        fo.close()
        lens.append(len(foo))
    diff = time.time() - starttime

    j = 0
    for i in lens[1:]:
        j = j + 1
        if not i == lens[0]:
            print "WARNING: inconsistent length on read %i: %i" % (j, i)

    return diff

def test_timeout(url):
    global DEBUG
    dbbackup = DEBUG
    class FakeLogger:
        def debug(self, msg, *args): print msg % args
        info = warning = error = debug
    DEBUG = FakeLogger()
    print "  fetching the file to establish a connection"
    fo = urllib2.urlopen(url)
    data1 = fo.read()
    fo.close()

    i = 60
    print "  waiting %i seconds for the server to close the connection" % i
    while i > 0:
        sys.stdout.write('\r  %2i' % i)
        sys.stdout.flush()
        time.sleep(1)
        i -= 1
    sys.stderr.write('\r')

    print "  fetching the file a second time"
    fo = urllib2.urlopen(url)
    data2 = fo.read()
    fo.close()

    if data1 == data2:
        print '  data are identical'
    else:
        print '  ERROR: DATA DIFFER'

    DEBUG = dbbackup

    
def test(url, N=10):
    print "checking error hander (do this on a non-200)"
    try: error_handler(url)
    except IOError, e:
        print "exiting - exception will prevent further tests"
        sys.exit()
    print
    print "performing continuity test (making sure stuff isn't corrupted)"
    continuity(url)
    print
    print "performing speed comparison"
    comp(N, url)
    print
    print "performing dropped-connection check"
    test_timeout(url)
    
if __name__ == '__main__':
    import time
    import sys
    try:
        N = int(sys.argv[1])
        url = sys.argv[2]
    except:
        print "%s <integer> <url>" % sys.argv[0]
    else:
        test(url, N)
