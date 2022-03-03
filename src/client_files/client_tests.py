import socket
import unittest
from client_files.chat_events import ChatEvents
from client_files.controller import Controller
from client_files.ui_events import UIEvents

SERVER_DEFAULT_IP = socket.gethostbyname(socket.gethostname())
PORT = 5000


class ClientTests(unittest.TestCase):

    def test_get_files(self):
        def callback(data):
            print(data)
            if isinstance(data, UIEvents.Connect):
                if data.is_connected:
                    controller.trigger_event(ChatEvents.GetFiles())

            if isinstance(data, UIEvents.FilesList):
                self.assertIsNotNone(data)
                controller.trigger_event(ChatEvents.Disconnect())
                self.assertTrue(True)

        controller = Controller(callback)
        controller.trigger_event(ChatEvents.Connect(SERVER_DEFAULT_IP, PORT, 'wissam'))

    def test_connect(self):
        def callback(data):
            if isinstance(data, UIEvents.Connect):
                if data.is_connected:
                    controller.trigger_event(ChatEvents.Disconnect())
                    self.assertTrue(True)

        controller = Controller(callback)
        controller.trigger_event(ChatEvents.Connect(SERVER_DEFAULT_IP, PORT, 'wissam'))

    def test_get_users(self):
        def callback(data):
            if isinstance(data, UIEvents.OnlineUsers):
                print(f'{data.users}')
                if data.users:
                    controller.trigger_event(ChatEvents.Disconnect())
                    self.assertTrue(True)

            if isinstance(data, UIEvents.Connect):
                if data.is_connected:
                    controller.trigger_event(ChatEvents.GetUsers())

        controller = Controller(callback)
        controller.trigger_event(ChatEvents.Connect(SERVER_DEFAULT_IP, PORT, 'wissam'))

    def test_download_file(self):
        def callback(data):
            if isinstance(data, UIEvents.UpdateDownloadPercentage):
                print(f'{data.download_percentage}')
                if data.download_percentage >= 100:
                    controller.trigger_event(ChatEvents.Disconnect())
                    self.assertTrue(True)

            if isinstance(data, UIEvents.Connect):
                if data.is_connected:
                    controller.trigger_event(ChatEvents.DownloadFile('a1.pdf'))

        controller = Controller(callback)
        controller.trigger_event(ChatEvents.Connect(SERVER_DEFAULT_IP, PORT, 'wissam'))
