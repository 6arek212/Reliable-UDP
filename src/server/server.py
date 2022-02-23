import socket
import threading
import json
from os import listdir
from os.path import isfile, join
import os

from file_download import FileDownload
from file_download2 import FileDownload2
from file_download3 import FileDownload3
from file_download4 import FileDownload4

PORT = 5000
IP = "192.168.1.21"
dirname = os.path.dirname(__file__)
filename = os.path.join(dirname, 'data')

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind((IP, PORT))
sock.listen(10)

clients_names = {}
clients_download = {}


def get_files(client_socket):
    onlyfiles = [f for f in listdir(filename) if isfile(join(filename, f))]
    names = 'Available files: '
    for name in onlyfiles:
        names += name + ', '
    names = names[:len(names) - 2]
    names.capitalize()
    client_socket.send(f'{names}'.encode())


def get_users(client_socket):
    names = 'Online users: '
    for name in clients_names.keys():
        names += name + ', '
    names = names[:len(names) - 2]
    names.capitalize()
    client_socket.send(f'{names}'.encode())


def send_to_all(client_socket, msg):
    for sck in clients_names.values():
        try:
            # if sck is not client_socket:
            sck.send(f'{msg}'.encode())
        except Exception as e:
            print(e)


def send_to(to, msg):
    try:
        clients_names[to].send(f'{msg}'.encode())
    except Exception as e:
        print(e)


def delete_file_downloader(client_sock):
    try:
        if client_sock in clients_download:
            print('remove file downloader for this client')
            clients_download.pop(client_sock)
    except Exception as e:
        print('remove file downloader failed', e)


def handle_data(client_socket, data):
    try:
        dj = json.loads(data)
        if dj['type'] == 'disconnect':
            clients_names.pop(dj['name'])
            send_to_all(client_socket, f' {dj["name"]} disconnected')
            client_socket.close()
            return False

        if dj['type'] == 'connect':
            clients_names[dj['name']] = client_socket
            send_to_all(client_socket, f' {dj["name"]} connected')

        if dj['type'] == 'message-all':
            send_to_all(client_socket, dj['message'])

        if dj['type'] == 'message-to':
            send_to(dj['to'], dj['message'])

        if dj['type'] == 'get_users':
            get_users(client_socket)

        if dj['type'] == 'get_files_list':
            get_files(client_socket)

        if dj['type'] == 'pause_download':
            if clients_download.get(client_socket) is None:
                client_socket.send('you must request to download first !'.encode())
            else:
                if dj['val']:
                    clients_download.get(client_socket).set_is_paused(True)
                else:
                    clients_download.get(client_socket).set_is_paused(False)

        if dj['type'] == 'get_file':
            if dj['filename'] is None or not dj['filename']:
                client_socket.send('you must attach a file name to the message !'.encode())
            else:
                print(clients_download.get(client_socket) is None)
                if clients_download.get(client_socket) is None:
                    print('got file download req', (client_socket.getsockname()[0], int(dj['port'])))
                    fd = FileDownload2(dj['filename'], IP, (client_socket.getsockname()[0], int(dj['port'])),
                                      lambda: delete_file_downloader(client_socket))
                    fd.start()
                    clients_download[client_socket] = fd
                else:
                    if clients_download.get(client_socket).is_paused:
                        clients_download.get(client_socket).set_is_paused(False)

        return True
    except Exception as e:
        print('handle_data', e)
        return False


def listen_to_client(client_socket):
    try:
        while True:
            data = client_socket.recv(1024).decode('UTF-8')
            if not data:
                break
            else:
                print('---', data, '---')
                if not handle_data(client_socket, data):
                    break

    except Exception as e:
        print('listen_to_client', e)
        for (key, value) in clients_names.items():
            if value is client_sock:
                clients_names.pop(key)
        client_socket.close()


print('server is up')
while 1:
    client_sock, address = sock.accept()
    threading.Thread(target=listen_to_client, args=(client_sock,)).start()
