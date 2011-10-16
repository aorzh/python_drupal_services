#!/usr/bin/env python
#
# (c) 2009 Kasper Souren
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the Affero GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the Affro GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
drupal_services is a module to call Drupal Services.

Check /admin/build/services/settings on your Drupal install.

DrupalServices can be passed a configuration dict.  Based on that it
will instantiate the proper class.  Using Drupal Services with keys
but without a session is currently not supported.
"""


import xmlrpclib, time, random, string, hmac, hashlib, pprint

class CookieTransport(xmlrpclib.Transport):
    def send_content(self, connection, request_body):
        if hasattr(self,'cookiename'):
            connection.putheader('Cookie', "%s=%s" % (self.cookiename, self.cookievalue))
        return xmlrpclib.Transport.send_content(self, connection, request_body)
                              
class BasicServices(xmlrpclib.Server):
    """Drupal Services without keys or sessions, not very secure."""
    def __init__(self, url):
        xmlrpclib.Server.__init__(self, url)
        self.connection = self.system.connect()
        self.sessid = self.connection['sessid']

    def call(self, method_name, *args):
        return getattr(self, method_name)(self._build_eval_list(method_name, args))
                           
    def _build_eval_list(self, method_name, args):
        # method_name is used in ServicesSessidKey
        return args

    def __eval(self, to_eval):
        print to_eval
        try:
            return eval(to_eval)
        except xmlrpclib.Fault, err:
            print "Oh oh. An xmlrpc fault occurred."
            print "Fault code: %d" % err.faultCode
            print "Fault string: %s" % err.faultString



class ServicesSessid(BasicServices):
    """Drupal Services with sessid."""
    def __init__(self, url, username, password):
        transport = CookieTransport()        
        xmlrpclib.Server.__init__(self, url, transport)
        sessioninfo = self.user.login(username, password)
        transport.cookiename = sessioninfo['session_name']
        transport.cookievalue = sessioninfo['sessid']

class ServicesSessidKey(ServicesSessid):
    """Drupal Services with sessid and keys."""
    def __init__(self, url, username, password, domain, key):
        BasicServices.__init__(self, url)
        self.domain = domain
        self.key = key
        self.session = self.call('user.login', username, password)
        self.sessid = self.session['sessid']

    def _build_eval_list(self, method_name, args):
        hash, timestamp, nonce = self._token(method_name)
        return ([hash,
                 self.domain, timestamp,
                 nonce, self.sessid] +
                map(None, args))

    def _token(self, api_function):
        timestamp = str(int(time.mktime(time.localtime())))
        nonce = "".join(random.sample(string.letters+string.digits, 10))
        return (hmac.new(self.key, "%s;%s;%s;%s" % 
                         (timestamp, self.domain, nonce, api_function), 
                         hashlib.sha256).hexdigest(),
                timestamp,
                nonce)


class ServicesKey(BasicServices):
    """Drupal Services with keys."""
    def __init__(self, url, domain, key):
        BasicServices.__init__(self, url)
        self.domain = domain
        self.key = key

    def _build_eval_list(self, method_name, args):
        hash, timestamp, nonce = self._token(method_name)
        return ([hash,
                 self.domain, 
                 timestamp,
                 nonce] +
                map(None, args))

    def _token(self, api_function):
        timestamp = str(int(time.mktime(time.localtime())))
        nonce = "".join(random.sample(string.letters+string.digits, 10))
        return (hmac.new(self.key, "%s;%s;%s;%s" % 
                         (timestamp, self.domain, nonce, api_function), 
                         hashlib.sha256).hexdigest(),
                timestamp,
                nonce)


class DrupalServices: 
    """Drupal services class.  

    config is a nice way to deal with configuration files."""
    def __init__(self, config):
        self.config = config
        if (config.has_key('username') and config.has_key('key')):
            self.server = ServicesSessidKey(config['url'], 
                                            config['username'], config['password'], 
                                            config['domain'], config['key'])
        elif (config.has_key('username')):
            self.server = ServicesSessid(config['url'], 
                                         config['username'], config['password'])
        elif (config.has_key('key')):
            self.server = ServicesKey(config['url'], 
                                      config['domain'], config['key'])
        else:
            self.server = BasicServices(config['url'])

    def call(self, method_name, *args):
        # It would be neat to add a smart __getattr__ but that would
        # only go one level deep, e.g. server.node, not
        # server.node.save.
        return self.server.call(method_name, *args)

    def listMethods(self):
        return self.server.system.listMethods()
    
    def getInfo(self, method_name):
        print method_name
        print self.server.system.methodHelp(method_name)
        print self.server.system.methodSignature(method_name)




if __name__ == "__main__":
    from config import config
    drupal = DrupalServices(config)

    new_node = { 'type': 'page',
                 'title': 'Just a little test',
                 'body': '''Ordenar bibliotecas es ejercer de un modo silencioso el arte de la critica.
-- Jorge Luis Borges. (1899-1986) Escritor argentino.''',
                 }
    new_node_id = drupal.call('node.save', new_node)
    print 'New node id: %s' % new_node_id 
    print drupal.call('node.get', int(new_node_id), ['body'])
