import socket
import ssl
from urllib.parse import urlparse

class InvalidURLScheme(Exception):
    pass

class Request:
    def __init__(self, conn):
        self.url = urlparse( conn.recv(1024).rstrip(b'\r\n') )
        if self.url.scheme != b'gemini':
            raise InvalidURLScheme(f'URL scheme must be gemini://, got {self.url.scheme}')

class Response:
    def __init__(self, conn):
        self.conn = conn

    def send(self, text):
        header_and_body = '20 text/gemini\r\n' + text
        self.conn.send(bytes(header_and_body, encoding='utf-8'))

    def send_file(self, file_path):
        with open(file_path) as f:
            self.send(f.read())

class Server:
    def __init__(self):
        self.context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
        self.context.check_hostname = False
        self.context.set_ciphers('TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:TLS_AES_128_GCM_SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-SHA384:ECDHE-RSA-AES256-SHA384:DHE-RSA-AES256-SHA256:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA256:DHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES256-SHA:ECDHE-RSA-AES256-SHA:DHE-RSA-AES256-SHA:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES128-SHA:DHE-RSA-AES128-SHA:RSA-PSK-AES256-GCM-SHA384:DHE-PSK-AES256-GCM-SHA384:RSA-PSK-CHACHA20-POLY1305:DHE-PSK-CHACHA20-POLY1305:ECDHE-PSK-CHACHA20-POLY1305:AES256-GCM-SHA384:PSK-AES256-GCM-SHA384:PSK-CHACHA20-POLY1305:RSA-PSK-AES128-GCM-SHA256:DHE-PSK-AES128-GCM-SHA256:AES128-GCM-SHA256:PSK-AES128-GCM-SHA256:AES256-SHA256:AES128-SHA256:ECDHE-PSK-AES256-CBC-SHA384:ECDHE-PSK-AES256-CBC-SHA:SRP-RSA-AES-256-CBC-SHA:SRP-AES-256-CBC-SHA:RSA-PSK-AES256-CBC-SHA384:DHE-PSK-AES256-CBC-SHA384:RSA-PSK-AES256-CBC-SHA:DHE-PSK-AES256-CBC-SHA:AES256-SHA:PSK-AES256-CBC-SHA384:PSK-AES256-CBC-SHA:ECDHE-PSK-AES128-CBC-SHA256:ECDHE-PSK-AES128-CBC-SHA:SRP-RSA-AES-128-CBC-SHA:SRP-AES-128-CBC-SHA:RSA-PSK-AES128-CBC-SHA256:DHE-PSK-AES128-CBC-SHA256:RSA-PSK-AES128-CBC-SHA:DHE-PSK-AES128-CBC-SHA:AES128-SHA:PSK-AES128-CBC-SHA256:PSK-AES128-CBC-SHA')
        self.context.load_cert_chain('cert.pem', 'key.pem')
        self.context.verify_mode = ssl.CERT_OPTIONAL

        self.routes = {}

    def route(self, path):
        '''
        Decorator which associates a handler with a route.
        '''
        def save_route_handler(handler):
            self.routes[path] = handler
        return save_route_handler

    def _determine_route_handler(self, req):
        route = req.url.path.decode('utf-8')
        if route == '':
            return self.routes['/']
        return self.routes[route]

    def listen(self, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0) as sock:
            sock.bind(('127.0.0.1', port))
            sock.listen(5)
            with self.context.wrap_socket(sock, server_side=True) as ssock:
                conn, _ = ssock.accept()
                try:
                    req = Request(conn)
                    res = Response(conn)
                    self._determine_route_handler(req)(req, res)
                except InvalidURLScheme as e:
                    print(e)
                finally:
                    conn.close()
