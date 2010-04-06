import re
from plugins.attack.payloads.base_payload import base_payload

class hostname(base_payload):
    '''
    This payload shows the server hostname
    '''
    def api_read(self):
        result = []
        values = []
        values.append(self.shell.read('/etc/hostname')[:-1])
        values.append(self.shell.read('/proc/sys/kernel/hostname')[:-1])

        for v in values:
            if not v in result:
               result.append(v)
        
        result = list(set(result))
        result = [p for p in result if p != '']
        return result
        
    def run_read(self):
        result = self.api_read()
        if result == [ ]:
            result.append('Hostname not found.')
        return result
        
