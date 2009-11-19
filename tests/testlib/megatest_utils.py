import BaseHTTPServer
import errno
import os
import mimetypes
import socket
import sys
import threading


class MinimalistHTTPServer(BaseHTTPServer.HTTPServer):
    'A HTTP server class to pass parameters to MinimalistHTTPRequestHandler'

    def set_file(self, allowed_file):
        'Prepare everything for serving our single available file.'
        # Avoid any funny business regarding the path, just in case.
        self.allowed_file = os.path.realpath(allowed_file)


class MinimalistHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    '''A minimalist request handler, to handle only GET requests
    for a single, specified file'''

    def do_GET(self):
        'Serve the specified file when requested, return errors otherwise'
        # The only request path to accept is '/self.server.allowed_file'.
        if self.path != '/' + os.path.basename(self.server.allowed_file):
            self.send_error(403)
            return

        try:
            fout = open(self.server.allowed_file)
        except IOError:
            self.send_error(404)
            return

        self.send_response(200)
        mimetypes.init()
        mime_guess = mimetypes.guess_type(self.server.allowed_file)
        if mime_guess[0] is not None:
            self.send_header('Content-Type', mime_guess[0])
        if mime_guess[1] is not None:
            self.send_header('Content-Encoding', mime_guess[1])
        statinfo = os.stat(self.server.allowed_file)
        self.send_header('Content-Length', statinfo.st_size)
        self.end_headers()
        try:
            self.wfile.write(fout.read())
        except socket.error, e:
            # EPIPE likely means the client's closed the connection,
            # it's nothing of concern so suppress the error message.
            if errno.errorcode[e[0]] == 'EPIPE':
                pass

        fout.close()
        return


class HTTPServerLauncher(object):
    'A launcher class for MinimalistHTTPServer.'

    def __init__(self, server_addr, file):
        self.server = MinimalistHTTPServer(server_addr,
                                           MinimalistHTTPRequestHandler)
        self.server.set_file(file)

    def request_shutdown(self):
        if sys.version_info >= (2, 6):
            self.server.shutdown()
        else:
            self.run_it = False

    def run(self):
        if sys.version_info >= (2, 6):
            # Safe to use here because 2.6 provides server.shutdown().
            self.server.serve_forever()
        else:
            self.run_it = True
            while self.run_it == True:
                # WARNING: if this blocks and no request arrives, the server
                # may remain up indefinitely! FIXME?
                self.server.handle_request()
