import socket
import threading
import json
from os import listdir
from os.path import isfile, join
import os
from time import sleep

from server_files.file_download import FileDownload

PORT = 5000
IP = socket.gethostbyname(socket.gethostname())
dirname = os.path.dirname(__file__)
filename = os.path.join(dirname, 'server_files/data')

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind((IP, PORT))
sock.listen(10)

clients_names = {}
clients_download = {}


def json_response(type, data):
    if isinstance(data, list):
        return f'{{"type":"{type}" , "data": {json.dumps(data)}}}'
    return f'{{"type":"{type}" , "data": "{data}"}}'


def get_files(client_socket):
    onlyfiles = [f for f in listdir(filename) if isfile(join(filename, f))]
    names = []
    for name in onlyfiles:
        names.append(name)
    client_socket.send(json_response('get_files', names).encode())


def get_users(client_socket=None):
    users = []
    for user in clients_names.keys():
        users.append(user)
    if client_socket is not None:
        client_socket.send(json_response('get_users', users).encode())
    return users


def send_to_all(client_socket, msg, type=None):
    for sck in clients_names.values():
        try:
            # if sck is not client_socket:
            if type is None:
                sck.send(json_response('sent_to_all', f'(Public) {msg}').encode())
            else:
                sck.send(json_response(type, msg).encode())
        except Exception as e:
            print(e)


def send_to(to, msg):
    try:
        clients_names[to].send(json_response('private_message', msg).encode())
    except Exception as e:
        print(e)


def delete_file_downloader(client_sock):
    try:
        if client_sock in clients_download:
            print('remove file downloader for this client_files')
            clients_download.pop(client_sock)
    except Exception as e:
        print('remove file downloader failed', e)


def handle_data(client_socket, data):
    try:
        dj = json.loads(data)
        if dj['type'] == 'disconnect':
            clients_names.pop(dj['name'])
            send_to_all(client_socket, f'{dj["name"]}', 'user_disconnected')
            client_socket.close()
            return False

        if dj['type'] == 'connect':
            clients_names[dj['name']] = client_socket
            send_to_all(client_socket, f'{dj["name"]}', 'new_user')
            sleep(.005)
            client_socket.send(json_response('get_users', get_users()).encode())

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
                client_socket.send(json_response('message', 'you must request to download first !').encode())
            else:
                if dj['val']:
                    clients_download.get(client_socket).set_is_paused(True)
                else:
                    clients_download.get(client_socket).set_is_paused(False)

        if dj['type'] == 'get_file':
            if dj['filename'] is None or not dj['filename']:
                client_socket.send(json_response('message', 'you must attach a file name to the message !').encode())
            else:
                print(clients_download.get(client_socket) is None)
                if clients_download.get(client_socket) is None:
                    print('got file download req', (client_socket.getsockname()[0], int(dj['port'])))
                    fd = FileDownload(dj['filename'], IP, (client_socket.getsockname()[0], int(dj['port'])),
                                      lambda: delete_file_downloader(client_socket))
                    fd.start()
                    clients_download[client_socket] = fd
                else:
                    if clients_download.get(client_socket).state == FileDownload.PAUSE:
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
                break
        client_socket.close()


print(f'Server is up on ip {IP} , port {PORT}')
while 1:
    client_sock, address = sock.accept()
    threading.Thread(target=listen_to_client, args=(client_sock,)).start()
