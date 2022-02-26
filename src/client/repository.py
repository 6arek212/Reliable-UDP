import socket
import threading

from client.file_transfer_repo import FileRepository

IP = "192.168.1.21"
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
        mip = IP if ip is None else ip
        print('ip is ', mip)
        self.sock.connect((IP, PORT))
        self.sock.send(f'{{"name": "{name}","type":"connect"}}'.encode())
        self.is_connected = True
        threading.Thread(target=self.listen).start()

    def listen(self):
        while self.is_connected:
            try:
                data = self.sock.recv(1024).decode('UTF-8')
                if not data:
                    break
                else:
                    self.callback(data)
            except Exception as e:
                print(e)
        self.sock.close()
        self.callback(f'{self.name} disconnected')

    def send_msg_to_all(self, msg):
        if not self.is_connected:
            raise Exception('you need to connect to the server_files first !')

        self.sock.send(f'{{"message": "{msg}","type":"message-all"}}'.encode())

    def send_msg_to(self, to, msg):
        if not self.is_connected:
            raise Exception('you need to connect to the server_files first !')

        self.sock.send(
            f'{{"message": "{msg}","to":"{to}","type":"message-to"}}'.encode())
        self.callback(msg)

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

    def get_file(self, filename, callback):
        if not self.is_connected or not filename:
            raise Exception('you need to connect to the server_files first ! or check filename')
        if self.fr is not None and self.fr.state != FileRepository.DONE:
            return
        self.fr = FileRepository(self.sock)
        self.fr.get_file(filename, callback)

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
