#!/usr/bin/env python
import tornado.httpserver
import tornado.ioloop
import tornado.process
import tornado.web
import tornado.websocket
import os
import sys


clients = []
header = 'RIFF\x88\xd55\x00WAVEfmt \x10\x00\x00\x00\x03\x00\x01\x00D\xac\x00\x00\x10\xb1\x02\x00\x04\x00 \x00fact\x04\x00\x00\x00Pu\r\x00PEAK\x10\x00\x00\x00\x01\x00\x00\x00\xfe\xd2\x1dX\xa8\xe7i?\xd8C\x01\x00data@\xd55\x00'



class ServerWSHandler(tornado.websocket.WebSocketHandler):
    connections = []

    @tornado.gen.coroutine
    def open(self):
        print("VAPI Client Connected")
        # Start transcoder:
        self.sp = tornado.process.Subprocess(
            "ffmpeg  -f s16le -ar 16000 -ac 1  -i pipe: -f f32le -ar 44100 pipe:",
            stdin=tornado.process.Subprocess.STREAM,
            stdout=tornado.process.Subprocess.STREAM,
            shell=True,
        )

        self.connections.append(self)
        self.write_message('00000000', binary=True)
        yield self.reader()

    @tornado.gen.coroutine
    def reader(self):
        print 'reading'
        while True:
            b = yield self.sp.stdout.read_bytes(3528)
            sys.stdout.write('>')
            sys.stdout.flush()
            broadcast(b)

    @tornado.gen.coroutine
    def on_message(self, message):
        if type(message) == str:
            sys.stdout.write('.')
            sys.stdout.flush()
            self.write_message(message, binary=True)
            # Feed bytes to transcoder:
            yield self.sp.stdin.write(message)
        else:
            print(message)
            self.write_message('ok')

    def on_close(self):
        print("VAPI Client Disconnected")
        self.connections.remove(self)
        # We won't be needing this transcoder any more:
        self.sp.proc.terminate()


def broadcast(message):
    data = header + message
    for conn in clients:
        conn.write_message(data, binary=True)


class ClientWSHandler(tornado.websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True
    def open(self):
        print("Browser Client Connected")
        clients.append(self)

    def on_message(self, message):
        print("Browser Client Message Recieved")

    def on_close(self):
        print("Browser Client Disconnected")
        clients.remove(self)


static_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
application = tornado.web.Application([
    (r'/socket', ServerWSHandler),
    (r'/browser', ClientWSHandler),
    (r'/s/(.*)', tornado.web.StaticFileHandler, {'path': static_path}),
])

if __name__ == "__main__":
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8000)
    tornado.ioloop.IOLoop.instance().start()
