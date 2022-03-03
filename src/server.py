import socket
import threading
import json
from os import listdir
from os.path import isfile, join
import os
from server_files.file_download import FileDownload

PORT = 5000
IP = socket.gethostbyname(socket.gethostname())
dirname = os.path.dirname(__file__)
filename = os.path.join(dirname, 'server_files/data')
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind((IP, PORT))
sock.listen(10)

clients_names = {}
clients_address = {}
clients_download = {}


def json_response(type, data):
    if isinstance(data, list):
        return f'{{"type":"{type}" , "data": {json.dumps(data)}}}\0'
    return f'{{"type":"{type}" , "data": "{data}"}}\0'


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


def send_to_all(client_socket, msg, address, type=None):
    for sck in clients_names.values():
        try:
            # if sck is not client_socket:
            if type is None:
                sck.send(
                    json_response('public_message', f'(Public from {clients_address.get(address)}) {msg}').encode())
            else:
                sck.send(json_response(type, msg).encode())
        except Exception as e:
            print(e)


def send_to(to, msg, address):
    try:
        clients_names[to].send(
            json_response('private_message', f'(Private from {clients_address.get(address)}) {msg}').encode())
    except Exception as e:
        print(e)


def delete_file_downloader(address):
    try:
        if address in clients_download:
            print('remove file downloader for this client_files')
            clients_download.pop(address)
    except Exception as e:
        print('remove file downloader failed', e)


def handle_data(client_socket, data, address):
    try:
        print('---', data, '---')
        dj = json.loads(data)
        if dj['type'] == 'disconnect':
            if address in clients_address:
                delete_file_downloader(address)
                clients_address.pop(address)
                clients_names.pop(dj['name'])
                send_to_all(client_socket, f'{dj["name"]}', address, 'user_disconnected')
                client_socket.close()
            return False

        if dj['type'] == 'connect':
            if dj['name'] not in clients_names:
                clients_address[address] = dj['name']
                clients_names[dj['name']] = client_socket
                send_to_all(client_socket, f'{dj["name"]}', address, 'new_user')
                client_socket.send(json_response('get_users', get_users()).encode())

        if dj['type'] == 'message-all':
            send_to_all(client_socket, dj['message'], address)

        if dj['type'] == 'message-to':
            send_to(dj['to'], dj['message'], address)

        if dj['type'] == 'get_users':
            get_users(client_socket)

        if dj['type'] == 'get_files_list':
            get_files(client_socket)

        if dj['type'] == 'pause_download':
            if clients_download.get(address) is None:
                client_socket.send(json_response('message', 'you must request to download first !').encode())
            else:
                if dj['val']:
                    clients_download.get(address).set_is_paused(True)
                else:
                    clients_download.get(address).set_is_paused(False)

        if dj['type'] == 'get_file':
            if dj['filename'] is None or not dj['filename']:
                client_socket.send(json_response('message', 'you must attach a file name to the message !').encode())
            else:
                if clients_download.get(address) is None:
                    print('got file download req', (address[0], int(dj['port'])))
                    fd = FileDownload(dj['filename'], IP, (address[0], int(dj['port'])),
                                      lambda: delete_file_downloader(address))
                    fd.start()
                    clients_download[address] = fd
                else:
                    if clients_download.get(address).state == FileDownload.PAUSE:
                        clients_download.get(address).set_is_paused(False)

        return True
    except Exception as e:
        print('handle_data error', e)
        return False


def listen_to_client(client_socket, address):
    try:
        print(f'server listening for client {address}')
        flag = True
        while flag:
            data = client_socket.recv(1024).decode('UTF-8')
            if not data:
                break
            else:
                strings = data.split('\0')
                for s in strings:
                    if s.strip() and not handle_data(client_socket, s, address):
                        flag = False

    except Exception as e:
        print('listen_to_client', e)
        if address in clients_address:
            print('removed client stuff')
            clients_names.pop(clients_address.get(address))
            clients_address.pop(address)
        client_socket.close()


print(f'Server is up on ip {IP} , port {PORT}')
while 1:
    client_sock, address = sock.accept()
    threading.Thread(target=listen_to_client, args=(client_sock, address)).start()

"""
    Duplicate names error , must send a connected message letting him know he is connected !! 
"""
