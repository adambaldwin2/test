import sys
sys.path.append('..')

import extlib.socksipy.socks as socks

if len(sys.argv) != 3:
  print 'Usage:'
  print 'python socksClient.py <host> <port>'
else:
  s = socks.socksocket()
  try:
    s.setproxy(socks.PROXY_TYPE_SOCKS4,"localhost")
    s.connect((sys.argv[1],int(sys.argv[2])))

    s.send('\n')
    print s.recv(1024)
  except:
    print 'Connection failed, is the socks client listening?'

  
