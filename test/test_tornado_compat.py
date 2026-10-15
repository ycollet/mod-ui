import asyncio
import socket
import unittest

from tornado import gen, iostream, web
from tornado.netutil import bind_sockets
from tornado.tcpserver import TCPServer
from tornado.testing import AsyncHTTPTestCase, AsyncTestCase, gen_test

from mod.tornado_compat import connect, read_until, task


class TaskTests(AsyncTestCase):
    @gen_test
    async def test_callback_values(self):
        for values, expected in [((), None), ((42,), 42), ((1, 2), (1, 2))]:
            def work(callback):
                self.io_loop.add_callback(callback, *values)
            self.assertEqual(await task(work), expected)

    @gen_test
    async def test_generator_coroutine(self):
        @gen.coroutine
        def work(value):
            yield gen.sleep(0)
            return value

        self.assertEqual(await asyncio.wait_for(gen.Task(work, 42), 1), 42)

    @gen_test
    async def test_native_coroutine(self):
        async def work():
            await asyncio.sleep(0)
            return 42

        self.assertEqual(await task(work), 42)

    @gen_test
    async def test_coroutine_exception(self):
        @gen.coroutine
        def work():
            yield gen.sleep(0)
            raise ValueError("failed")

        with self.assertRaisesRegex(ValueError, "failed"):
            await task(work)

    @gen_test
    async def test_callback_stream_connect_and_read(self):
        class EchoServer(TCPServer):
            async def handle_stream(self, stream, address):
                try:
                    data = await stream.read_until(b"\0")
                    await stream.write(data)
                finally:
                    stream.close()

        sockets = bind_sockets(0, "127.0.0.1")
        address = sockets[0].getsockname()
        server = EchoServer()
        server.add_sockets(sockets)
        stream = iostream.IOStream(socket.socket())
        try:
            connected = asyncio.get_running_loop().create_future()
            connect(stream, address, lambda: connected.set_result(True))
            self.assertTrue(await asyncio.wait_for(connected, 1))
            response = asyncio.get_running_loop().create_future()
            read_until(stream, b"\0", response.set_result)
            await stream.write(b"resp 0\0")
            self.assertEqual(await asyncio.wait_for(response, 1), b"resp 0\0")
        finally:
            stream.close()
            server.stop()

    @gen_test
    async def test_stream_close_is_reported(self):
        left, right = socket.socketpair()
        stream = iostream.IOStream(left)
        called = []
        with self.assertLogs(level="WARNING") as messages:
            read_until(stream, b"\0", called.append)
            right.close()
            await gen.sleep(0.05)
        self.assertFalse(called)
        self.assertIn("stream closed", messages.output[0])
        stream.close()


class AsyncHandlerTests(AsyncHTTPTestCase):
    def get_app(self):
        class DelayedHandler(web.RequestHandler):
            @web.asynchronous
            def get(self):
                self.application.settings["io_loop"].call_later(0.01, self.finish, "ready")

        class CoroutineHandler(web.RequestHandler):
            @web.asynchronous
            @gen.engine
            def get(self):
                yield gen.sleep(0.01)
                self.finish("coroutine")

        return web.Application([
            ("/callback", DelayedHandler),
            ("/coroutine", CoroutineHandler),
        ], io_loop=self.io_loop)

    def test_delayed_response_is_not_finished_early(self):
        response = self.fetch("/callback")
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, b"ready")

    def test_generator_handler(self):
        response = self.fetch("/coroutine")
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, b"coroutine")


if __name__ == "__main__":
    unittest.main()
