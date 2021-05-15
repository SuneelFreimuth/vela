import socket
import ssl
import sys
from urllib.parse import urlparse
import mimetypes

mimetypes.add_type("text/gemini", ".gmi")


class InvalidURLScheme(Exception):
    pass


class Request:
    def __init__(self, conn: socket.socket):
        self.url = urlparse(conn.recv(1024).rstrip(b"\r\n"))
        if self.url.scheme != b"gemini":
            raise InvalidURLScheme(
                f"URL scheme must be gemini://, got {self.url.scheme}"
            )


class Response:
    def __init__(self, conn: socket.socket):
        self.conn = conn

    def send(self, text: str):
        self._send_header_and_body(b"20 text/gemini", text.encode("utf-8"))

    def send_file(self, file_path: str):
        with open(file_path, "rb") as f:
            mimetype, _ = mimetypes.guess_type(file_path)
            self._send_header_and_body(
                bytes("20 " + mimetype, encoding="utf-8"), f.read()
            )

    def _send_header_and_body(self, header: bytes, body: bytes):
        self.conn.send(header + b"\r\n" + body)


class Server:
    def __init__(self, cert: str, key: str):
        self.context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        self.context.check_hostname = False
        self.context.set_ciphers(
            "TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:TLS_AES_128_GCM_SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384"
        )
        self.context.load_cert_chain(cert, key)
        self.context.verify_mode = ssl.CERT_OPTIONAL

        self.routes = dict()
        self.default_route = "/"

    def route(self, path: str, default=False):
        """
        Binds a handler to a route.
        """
        if default:
            self.default_route = path

        def save_route_handler(handler):
            self.routes[path] = handler

        return save_route_handler

    def _determine_route_handler(self, req: Request):
        route = req.url.path.decode("utf-8")
        if route == "":
            return self.routes["/"]
        return self.routes[route if route in self.routes else self.default_route]

    def _on_connection(self, conn: socket.socket, addr):
        try:
            req = Request(conn)
            res = Response(conn)
            self._determine_route_handler(req)(req, res)
        except InvalidURLScheme as e:
            print(e, file=sys.stderr)
        finally:
            conn.close()

    def listen(self, port: int):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0) as sock:
            sock.bind(("127.0.0.1", port))
            sock.listen(5)
            with self.context.wrap_socket(sock, server_side=True) as ssock:
                while True:
                    try:
                        conn, addr = ssock.accept()
                        self._on_connection(conn, addr)
                    except KeyboardInterrupt:
                        ssock.close()
                        print("Keyboard interrupt, closing server...")
                        exit(130)
                    except:
                        ssock.close()
                        raise
