import _thread
import os
import select
import socket
import threading
import time
from math import ceil

from rudp import RudpPacket
from timer import Timer

BUFFER_SIZE = 4096
FRAGMENT_SIZE = 500
SLEEP_INTERVAL = 0.05


class FileDownload2:

    def __init__(self, file_name, ip, address, finish_callback):
        self.finish_callback = finish_callback
        self.file_name = file_name
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((ip, 0))
        self.ip = ip
        self.address = address
        self.state = None
        self.time_out = 0.5
        self.cwd = 10
        self.seq = 0
        self.send_cwnd = []
        self.window = {}
        self.rev_buffer = []
        self.is_paused = False
        self.content_length = 0
        self.dup_ack_cnt = 0
        self.is_end = False
        self.send_all_wind = False
        self.mutex = threading.Lock()
        self.send_timer = Timer(self.time_out)

    def start(self):
        try:
            self.content_length = os.stat(f'data/{self.file_name}').st_size
        except Exception as e:
            print(e)
            return
        threading.Thread(target=self.handle_recv_buffer).start()
        threading.Thread(target=self.listen_to_client).start()
        threading.Thread(target=self.send_file).start()

    def set_is_paused(self, val):
        self.mutex.acquire()
        self.is_paused = val
        if val:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.send_cwnd = []
            self.cwd = 1
            self.dup_ack_cnt = 0
        if val is False:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind((self.ip, 0))
            self.start()
        self.mutex.release()

    def handle_recv_buffer(self):
        while not self.is_paused:
            try:
                data = self.socket.recv(BUFFER_SIZE)
                self.rev_buffer.append(data)
            except Exception as e:
                print(e)

    def listen_to_client(self):
        while not self.is_paused:
            try:
                if self.rev_buffer:
                    data = self.rev_buffer.pop(0)
                    packet = RudpPacket().unpack(data)
                    self.mutex.acquire()

                    if packet.type == RudpPacket.TYPE_ACK:
                        self.handle_acks(packet)

                    self.mutex.release()
            except Exception as e:
                print('listen_to_client', e)

        print('done')
        if self.seq == self.content_length:
            self.shut_down()
            self.finish_callback()
        print('listen stopped')

    def handle_acks(self, packet: RudpPacket):
        if self.is_paused:
            return

        # print(f'packet {self.seq} {packet.ack_num}')

        if packet.ack_num > self.seq:

            self.seq = packet.ack_num
            while self.send_cwnd and self.send_cwnd[0].ack_num <= packet.ack_num:
                self.send_cwnd.pop(0)
            if self.cwd < 100000:
                self.cwd *= 2
            self.dup_ack_cnt = 0
            print(f'packet {packet.seqnum} was ACKED')


        elif packet.ack_num == self.seq:
            print(f'may be a packet was lost or took longer time seq {self.seq}  packet ack {packet.ack_num}')
            self.dup_ack_cnt += 1
            if self.dup_ack_cnt == 3 and not self.send_all_wind:
                self.cwd /= 2
                print(f'3 duplicate ACKs sending : {packet.ack_num} first in buffer {self.send_cwnd[0].seqnum}')
                if self.send_cwnd and packet.ack_num == self.send_cwnd[0].seqnum:
                    # self.send_cwnd[0].is_sent = False
                    self.send_all_wind = True
                self.dup_ack_cnt = 0

        if self.content_length == self.seq:
            self.is_paused = True




    def load_packets(self):
        if self.content_length == self.seq:
            return

        try:
            file = open(f'data/{self.file_name}', 'rb')
        except IOError:
            print('Unable to open  file')
            self.shut_down()
            self.finish_callback()
            return

        i = 0
        datalen = 0
        # print('loading packets cwnd size ', len(self.send_cwnd))

        if self.send_cwnd:
            # print(self.send_cwnd)
            packet_sent_cnt = ceil(self.send_cwnd[len(self.send_cwnd) - 1].ack_num / FRAGMENT_SIZE)
            ss = self.send_cwnd[len(self.send_cwnd) - 1].ack_num
        else:
            packet_sent_cnt = ceil(self.seq / FRAGMENT_SIZE)
            ss = self.seq

        # print(f'packet cnt {packet_sent_cnt}')
        while len(self.send_cwnd) < self.cwd and self.seq + datalen < self.content_length:
            file.seek(FRAGMENT_SIZE * (packet_sent_cnt + i))
            data = file.read(FRAGMENT_SIZE)

            if len(data) != 0:
                packet = RudpPacket()
                packet.type = RudpPacket.TYPE_DATA
                packet.seqnum = ss + datalen
                packet.ack_num = ss + datalen + len(data)
                packet.data = data
                packet.content_len = self.content_length
                datalen += len(data)
                self.send_cwnd.append(packet)
                print('Sending packet', packet.seqnum, self.seq, packet.is_sent, self.cwd)
                self.socket.sendto(packet.pack(), self.address)
                packet.is_sent = True

                i += 1
            else:
                break

        file.close()

    def send_file(self):
        print('sending length ', self.seq, self.content_length, ' is paused ', self.is_paused)
        while self.seq < self.content_length and not self.is_paused:

            self.mutex.acquire()
            self.load_packets()
            if self.send_all_wind:
                for pkt in self.send_cwnd:
                    # print('Sending All window', pkt.seqnum, self.seq, pkt.is_sent, self.cwd)
                    self.socket.sendto(pkt.pack(), self.address)
                self.send_all_wind = False
            self.mutex.release()

    def shut_down(self):
        self.socket.shutdown(socket.SHUT_RDWR)
        self.is_paused = True
        self.socket.close()
