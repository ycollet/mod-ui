"""Bridge the callback APIs still used by MOD to current Tornado."""

from functools import wraps
import inspect
import logging

import tornado
from tornado import gen, util, web
from tornado.concurrent import Future
from tornado.ioloop import IOLoop
from tornado.iostream import StreamClosedError


def task(func, *args, **kwargs):
    if gen.is_coroutine_function(func) or inspect.iscoroutinefunction(func):
        return gen.convert_yielded(func(*args, **kwargs))

    future = Future()

    def done(*values):
        if not future.done():
            future.set_result(None if not values else values[0] if len(values) == 1 else values)

    func(*args, callback=done, **kwargs)
    return future


def asynchronous(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        self._auto_finish = False
        return method(self, *args, **kwargs)

    return wrapper


def install():
    if not hasattr(util, "unicode_type"):
        util.unicode_type = str
    if not hasattr(gen, "Task"):
        gen.Task = task
    if not hasattr(gen, "engine"):
        gen.engine = gen.coroutine
    if not hasattr(web, "asynchronous"):
        web.asynchronous = asynchronous
    if not hasattr(IOLoop, "instance"):
        IOLoop.instance = staticmethod(IOLoop.current)


def _callback(future, callback, with_result):
    def done(completed):
        try:
            result = completed.result()
        except StreamClosedError as error:
            logging.warning("MOD stream closed during asynchronous I/O: %s", error)
            return
        if with_result:
            return callback(result)
        return callback()

    IOLoop.current().add_future(future, done)


def connect(stream, address, callback):
    if tornado.version_info < (6, 0):
        stream.connect(address, callback)
    else:
        _callback(stream.connect(address), callback, False)


def read_until(stream, delimiter, callback):
    if tornado.version_info < (6, 0):
        stream.read_until(delimiter, callback)
    else:
        _callback(stream.read_until(delimiter), callback, True)
