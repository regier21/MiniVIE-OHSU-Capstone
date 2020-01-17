# -*- coding: utf-8 -*-
"""
Created on Tue Jan 26 18:03:38 2016

This class is designed to web services for the mobile app

@author: R. Armiger
"""
from typing import Optional, Awaitable
import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.template
from interface.app_interface import AppInterface
import logging
from utilities.user_config import get_user_config_var


# https://stackoverflow.com/questions/12479054/how-to-run-functions-outside-websocket-loop-in-python-tornado
wss = []  # list of websockets send commands
func_handle = []  # list of callbacks for message recv

# store the last messages so we don't re-transmit a lot of repeated data
message_history = {'sys_status': '', 'output_class': '', 'training_class': '',
                   'motion_test_status': '', 'motion_test_setup': '', 'motion_test_update': '',
                   'TAC_status': '', 'TAC_setup': '', 'TAC_update': '',
                   'joint_cmd': '', 'joint_pos': '', 'joint_torque': '', 'joint_temp': '',
                   'strNormalizeMyoPosition': '', 'strNormalizeMyoPositionImage': ''}


class WSHandler(tornado.websocket.WebSocketHandler):
    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        pass

    def open(self):
        logging.debug('Connection opened...')
        if self not in wss:
            wss.append(self)

    def on_message(self, message):
        logging.debug('Received:' + message)
        for func in func_handle:
            func(message)

    def on_close(self):
        logging.debug('Connection closed...')
        if self in wss:
            wss.remove(self)


class TestHandler(tornado.web.RequestHandler):
    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        pass

    def get(self):
        # self.render('../../www/mplTemplates/test_template.html', title='Testlist', items=('one', 'two', 'three'))
        self.render('../../www/mplTemplates/index.html', title='Testlist', items=('one', 'two', 'three'),
                    enableNfu=True, enableUnity=True)
        pass


class MainHandler(tornado.web.RequestHandler):
    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        pass

    def get(self):
        from os import path
        homepath = get_user_config_var('MobileApp.path', "../www/mplHome")
        homepage = get_user_config_var('MobileApp.homepage', "index.html")
        homepage_path = path.join(homepath, homepage)
        loader = tornado.template.Loader(".")
        self.write(loader.load(homepage_path).generate())


class TrainingManagerWebsocket(AppInterface):
    """
    This Training manager uses websockets provided through tornado

    """

    def __init__(self):
        import threading

        # Initialize superclass
        super(AppInterface, self).__init__()

        homepath = get_user_config_var('MobileApp.path', "../www/mplHome")

        # handle to websocket interface
        self.application = tornado.web.Application([
            (r'/ws', WSHandler),
            (r'/', MainHandler),
            (r'/test_area', TestHandler),
            (r"/(.*)", tornado.web.StaticFileHandler, {"path": homepath}),
        ])

        self.last_msg = message_history

        # keep count of skipped messages so we can send at some nominal rate
        self.msg_skip_count = 0

        self.thread = threading.Thread(target=tornado.ioloop.IOLoop.instance().start, name='WebThread')

    def setup(self, port=9090):
        self.application.listen(port)
        self.thread.start()

    def get_websocket_count(self):
        return len(wss)

    def get_websockets(self):
        return wss

    def add_message_handler(self, func):
        # attach a function to receive commands from websocket

        if func not in func_handle:
            func_handle.append(func)

    def send_message(self, msg_id, msg):
        # send message but only when the string changes (or timeout occurs)

        if not self.last_msg[msg_id] == msg:
            self.last_msg[msg_id] = msg
            try:
                logging.debug(msg_id + ':' + msg)
                for ws in wss:
                    ws.write_message(msg_id + ':' + msg)

            except Exception as e:
                logging.error(e)

            return
        else:
            self.msg_skip_count += 1

        # add a timeout so that we get 'some' messages as a nominal rate
        if self.msg_skip_count > 500:

            # re-send all messages
            for key, val in self.last_msg.items():
                try:
                    logging.debug(key + ':' + val)
                    for ws in wss:
                        ws.write_message(key + ':' + val)
                except Exception as e:
                    logging.error(e)

            # reset counter
            self.msg_skip_count = 0

    def close(self):
        pass
