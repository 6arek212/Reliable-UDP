import random
import socket
import threading
from time import sleep

from rudp import RudpPacket

IP = "192.168.1.21"
PORT = 5000
BUFFER_SIZE = 10000
lock = threading.Lock()


class FileRepository3:

    def __init__(self, sock):
        self.sock = sock
        self.is_working = False
        self.udp_sock = None
        self.is_done = False
        self.is_paused = False
        self.callback = None
        self.file_name = None
        self.rev_buffer = []
        self.recv_wnd = {}
        self.send_buffer = []
        self.recv_buffer_size = 0
        self.seq = 0
        self.mutex = threading.Lock()
        self.cnt = 0

    def get_file(self, filename, callback):
        self.file_name = filename
        lock.acquire()
        self.callback = callback
        if self.is_working:
            return
        self.is_working = True
        lock.release()
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_sock.bind((IP, 0))
        self.sock.send(
            f'{{"type":"get_file" , "filename":"{filename}" , "port":"{self.udp_sock.getsockname()[1]}"}}'.encode())
        threading.Thread(target=self.listen_for_udp).start()
        threading.Thread(target=self.buffer_handler()).start()

    def listen_for_udp(self):
        while not self.is_done:
            try:
                data, address = self.udp_sock.recvfrom(BUFFER_SIZE)
                self.mutex.acquire()
                # if self.recv_buffer_size + len(data) <= BUFFER_SIZE:
                self.recv_buffer_size += len(data)
                self.rev_buffer.append((data, address))
                # else:
                #     packet = RudpPacket().unpack(data)
                #     print('packet was thrown because buffer is full ', packet)

                self.mutex.release()
            except Exception as e:
                print('listen_for_udp', e)
        self.is_working = False

    def buffer_handler(self):
        while not self.is_done:
            # try:
            self.mutex.acquire()
            if self.rev_buffer:
                data, address = self.rev_buffer.pop(0)
                self.recv_buffer_size -= len(data)
                packet = RudpPacket().unpack(data)

                if packet.type == RudpPacket.TYPE_DATA:
                    try:
                        self.handle_data(packet, address)
                    except Exception as e:
                        print('aaaaaaaaaaaa', e)

                if packet.type == RudpPacket.TYPE_FIN:
                    print('FIN REQUEST')
                    p = RudpPacket()
                    p.type = RudpPacket.TYPE_FINACK
                    p.ack_num = 0
                    p.seqnum = 0
                    self.udp_sock.sendto(p.pack(), address)
                    self.shut_down()
            self.mutex.release()
            # except Exception as e:
            #     print('buffer_handler' ,e)

    # def handle_data(self, packet, address):
    #     recv_wnd = packet.recv_wnd
    #     if packet.seqnum == self.seq:
    #         self.cnt = 0
    #         ra = random.uniform(0, 1)
    #         # if ra <= .8:
    #         self.seq = packet.ack_num
    #         with open(self.file_name, 'ab') as f:
    #             f.write(packet.data)
    #
    #         print(self.seq, packet.seqnum, packet.ack_num, 'ACKED' , f'rec wind {recv_wnd}')
    #         percentage = self.seq / packet.content_len * 100
    #         self.callback(percentage)
    #
    #
    #     else:
    #         self.cnt += 1
    #         print(f'out of order current seq {self.seq} got seq {packet.seqnum} ack num {packet.ack_num}')
    #         packet.ack_num = self.seq
    #
    #
    #
    #     packet.recv_wnd = BUFFER_SIZE - self.recv_buffer_size
    #     packet.type = RudpPacket.TYPE_ACK
    #     packet.data = None
    #     packet.datalength = 0
    #     data_bytes = packet.pack()
    #
    #     if recv_wnd < len(data_bytes):
    #         sleep(0.2)
    #     self.udp_sock.sendto(data_bytes, address)

    # if self.seq == packet.ack_num and self.cnt <= 3:
    #     packet.type = RudpPacket.TYPE_ACK
    #     packet.data = None
    #     packet.datalength = 0
    #     self.udp_sock.sendto(packet.pack(), address)
    # else:
    #     print('ignore packet')

    # def add_to_recv_wnd(self,packet):
    #     self.recv_wnd.append(packet)
    #     self.recv_wnd.sort(key=lambda p: p.ack_num)

    def write_to_file(self):
        if not self.recv_wnd or self.recv_wnd.get(self.seq) is None:
            return
        # print(f'writing buffer: {buffer}\nrec_wnd: {self.recv_wnd}')
        with open(self.file_name, 'ab') as f:
            p = self.recv_wnd.get(self.seq)
            last_ack_num = self.recv_wnd.get(self.seq).ack_num

            while self.recv_wnd and p is not None:
                last_ack_num = self.recv_wnd.get(p.seqnum).ack_num
                f.write(self.recv_wnd.pop(p.seqnum).data)
                p = self.recv_wnd.get(last_ack_num)

            self.seq = last_ack_num

    def handle_data(self, packet, address):
        p = RudpPacket()
        p.type = RudpPacket.TYPE_ACK
        p.data = None
        p.ack_num = packet.ack_num
        p.seqnum = self.seq
        p.datalength = 0
        p.recv_wnd = BUFFER_SIZE - self.recv_buffer_size

        if packet.seqnum == self.seq:
            self.cnt = 0
            self.recv_wnd[packet.seqnum] = packet
            self.write_to_file()
            percentage = int(self.seq / packet.content_len * 100)
            self.callback(percentage)
            print(self.seq, packet.seqnum, f'ACKED send recv window {packet.recv_wnd}')
            p.ack_num = self.seq
            pack = p.pack()
            self.udp_sock.sendto(pack, address)
        else:
            '''ACKS may get lost !!'''
            print(f'out of order current seq {self.seq} got seq {packet.seqnum} ack num {packet.ack_num}')
            self.cnt += 1
            if packet.seqnum > self.seq:
                self.recv_wnd[packet.seqnum] = packet
                p.ack_num = self.seq

            pack = p.pack()
            self.udp_sock.sendto(pack, address)

    def shut_down(self):
        if self.udp_sock is not None:
            self.is_done = True
            self.udp_sock.shutdown(socket.SHUT_RDWR)
            self.udp_sock.close()
            self.callback('Done')
