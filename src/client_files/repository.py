import json
import socket
import threading

from client_files.file_transfer_repo import FileRepository
from client_files.ui_events import UIEvents

SERVER_DEFAULT_IP = "10.113.4.200"
PORT = 5000


class Repository:

    def __init__(self, callback) -> None:
        self.sock = None
        self.name = None
        self.is_connected = False
        self.fr = None
        self.callback = callback

    def connect_to_server(self, ip, name):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.name = name
        mip = SERVER_DEFAULT_IP if (ip is None or not ip) else ip
        print('server ip is ', mip, name)
        try:
            self.sock.connect((mip, PORT))
            self.sock.send(f'{{"name": "{name}","type":"connect"}}'.encode())
            self.callback(UIEvents.Connect(True))
            self.is_connected = True
            threading.Thread(target=self.listen).start()
        except Exception as e:
            self.is_connected = False
            print('connect_to_server', e)

    def handle_incoming_data(self, data):
        try:
            print('in data ',data)
            json_data = json.loads(data)
            if 'type' not in json_data:
                raise Exception('something wrong with incoming json')

            ui_data = None
            if json_data['type'] == 'get_files':
                ui_data = UIEvents.Message(json_data['data'])

            if json_data['type'] == 'get_users':
                ui_data = UIEvents.OnlineUsers(json_data['data'])

            if json_data['type'] == 'sent_to_all' or json_data['type'] == 'private_message':
                ui_data = UIEvents.Message(json_data['data'])

            if json_data['type'] == 'user_disconnected':
                self.callback(UIEvents.Message(f'{json_data["data"]}, left the chat'))
                ui_data = UIEvents.UserDisconnected(json_data['data'])

            if json_data['type'] == 'new_user':
                self.callback(UIEvents.Message(f'{json_data["data"]}, has joined the chat say hi'))
                ui_data = UIEvents.NewUser(json_data['data'])

            self.callback(ui_data)
        except Exception as e:
            print('handle_incoming_data', e)

    def listen(self):
        while self.is_connected:
            try:
                data = self.sock.recv(1024).decode('UTF-8')
                if not data:
                    break
                else:
                    self.handle_incoming_data(data)
            except Exception as e:
                print(e)
                self.is_connected = False
        self.sock.close()
        self.callback(UIEvents.Message(f'{self.name} disconnected'))

    def send_msg_to_all(self, msg):
        if not self.is_connected:
            raise Exception('you need to connect to the server_files first !')
        self.sock.send(f'{{"message": "{msg}","type":"message-all"}}'.encode())

    def send_msg_to(self, to, msg):
        if not self.is_connected:
            raise Exception('you need to connect to the server_files first !')

        self.sock.send(
            f'{{"message": "{msg}","to":"{to}","type":"message-to"}}'.encode())
        self.callback(UIEvents.Message(f'(Me) {msg}'))

    def get_users(self):
        if not self.is_connected:
            raise Exception('you need to connect to the server_files first !')

        self.sock.send(
            f'{{"type":"get_users"}}'.encode())

    def get_files_list(self):
        if not self.is_connected:
            raise Exception('you need to connect to the server_files first !')

        self.sock.send(
            f'{{"type":"get_files_list"}}'.encode())

    def get_file(self, filename):
        if not self.is_connected or not filename:
            raise Exception('you need to connect to the server_files first ! or check filename')
        if self.fr is not None and self.fr.state != FileRepository.DONE:
            return
        self.fr = FileRepository(self.sock, self.callback)
        self.fr.get_file(filename)

    def pause_download(self):
        if not self.is_connected or self.fr is None:
            raise Exception('you need to connect to the server_files first !')
        self.fr.pause()
        print('pausing !', self.fr.is_paused)
        val = 'true' if self.fr.is_paused else 'false'
        self.sock.send(
            f'{{"type":"pause_download","val":{val}}}'.encode())

    def disconnect(self):
        if not self.is_connected:
            raise Exception('you need to connect to the server_files first !')
        self.sock.send(f'{{"name": "{self.name}","type":"disconnect"}}'.encode())
        self.is_connected = False
        self.callback(UIEvents.Connect(False))
