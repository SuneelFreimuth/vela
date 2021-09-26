"""
A simple framework for Gemini servers.
"""
import socket
import ssl
import sys
from urllib.parse import urlparse
from typing import Callable, Union
from dataclasses import dataclass
import asyncio

import mimetypes
mimetypes.add_type("text/gemini", ".gmi")


class RoutePatternDoesNotMatch(Exception):
    pass


def parse_route(route_pattern, route):
    """
    Return a dict of the named segments. None if the route fails
    to match the pattern.
    """
    params = dict()
    route_pattern_segments = route_pattern.strip("/").split("/")
    route_segments = route.strip("/").split("/")
    for i, (pattern_segment, route_segment) in enumerate(
        zip(route_pattern_segments, route_segments)
    ):
        if pattern_segment[0] == "{" and pattern_segment[-1] == "}":
            name = pattern_segment[1:-1]
            if name[0] == "*":
                params[name[1:]] = route_segments[i:]
                break
            else:
                params[name] = route_segment
        elif pattern_segment != route_segment:
            return None
    return params


class InvalidURLScheme(Exception):
    pass


class Request:
    """Request received from the client."""

    def __init__(self, url: str, route_segments: [str], route_params: {str: Union[str, list[str]]}):
        self.url = url
        self.route_segments = route_segments
        self.route_params = route_params


class Response:
    """Sends data to the client."""

    def __init__(self, conn: socket.socket):
        self.conn = conn

    def send(self, text: Union[str, bytes]):
        """Send a string as text/gemini to the client."""
        response_data = text.encode('utf-8') if type(text) == str else text
        self._send_header_and_body(b"20 text/gemini", response_data)

    def send_file(self, file_path: Union[str, bytes]):
        """Serve a file to the client."""
        with open(file_path, "rb") as f:
            mimetype, _ = mimetypes.guess_type(file_path)
            self._send_header_and_body(
                bytes("20 " + mimetype, encoding="utf-8"), f.read()
            )

    def _send_header_and_body(self, header: bytes, body: bytes):
        self.conn.send(header + b"\r\n" + body)


RouteHandler = Callable[[Request, Response], None]


class Server:
    def __init__(self, cert: str, key: str):
        self.context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        self.context.check_hostname = False
        self.context.set_ciphers(
            "TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:TLS_AES_128_GCM_SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384"
        )
        self.context.load_cert_chain(cert, key)
        self.context.verify_mode = ssl.CERT_OPTIONAL

        self.routes: {str: RouteHandler} = dict()
        self.default_route = '/'

    def route(self, route: str, default=False):
        """
        Binds a handler to a route.
        """
        if default:
            self.default_route = route

        def save_route_handler(handler: RouteHandler):
            self.routes[route] = handler

        return save_route_handler

    # def _determine_route_handler(self, req: Request):
    #     route = req.url.path.decode("utf-8")
    #     if route == "":
    #         return self.routes["/"]
    #     # TODO: Make this adapt to default routes
    #     return self.routes[route if route in self.routes else self.default_route]

    def _parse_route(self, route: str):
        for route_pattern in self.routes.keys():
            route_params = parse_route(route_pattern)
            if route_params != None:
                return route_params
        return None

    async def _on_connection(self, conn: socket.socket, addr):
        try:
            url = urlparse(conn.recv(1024).rstrip(b"\r\n"))
            if url.scheme != b"gemini":
                raise InvalidURLScheme(
                    f"URL scheme must be gemini://, got {url.scheme}"
                )
            route = url.path.decode('utf-8')
            route_params = self._parse_route(route)
            if route_params != None:
                req = Request(url, route_segments, route_params)
                res = Response(conn)
                self._determine_route_handler(req)(req, res)
            else:
                req = Request(url, route_segments, route_params)
                res = Response(conn)
                self._determine_route_handler(req)(req, res)
        except InvalidURLScheme as e:
            print(e, file=sys.stderr)
        finally:
            conn.close()

    def listen(self, port: int, address: str = "127.0.0.1"):
        exit_code = 0
        # TODO: Replace with interface which allows a testing component to be shimmed in
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0) as sock:
            sock.bind((address, port))
            sock.listen(5)
            with self.context.wrap_socket(sock, server_side=True) as ssock:
                while True:
                    try:
                        conn, addr = ssock.accept()
                        asyncio.run(self._on_connection(conn, addr))
                    except KeyboardInterrupt:
                        print("Keyboard interrupt, closing server...")
                        exit_code = 130
                        break
        if exit_code != 0:
            exit(exit_code)

