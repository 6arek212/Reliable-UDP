import _thread
import os
import select
import socket
import threading
import time
from math import ceil

from rudp import RudpPacket
from timer import Timer

BUFFER_SIZE = 10000
FRAGMENT_SIZE = 500
SLEEP_INTERVAL = 0.05

DUPLICATE_EVENT = 1
WAIT_FOR_WND_PASS = 2
PAUSE = 3
END = 4
SHUT_DOWN = 5
MAX_TRIES = 10


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
        self.cwd = FRAGMENT_SIZE
        self.ssthresh = FRAGMENT_SIZE * 8
        self.seq = 0
        # self.rev_buffer = []
        self.recv_buffer_size = 0
        self.send_buffer = []
        self.content_length = 0
        self.dup_ack_cnt = 0
        self.send_all_wind = False
        self.recv_wnd_size = BUFFER_SIZE
        self.mutex = threading.Lock()
        self.recv_lock = threading.Lock()
        self.send_timer = Timer(self.time_out)
        self.cv = threading.Condition()

    def start(self):
        try:
            self.content_length = os.stat(f'data/{self.file_name}').st_size
        except Exception as e:
            print(e)
            return
        # threading.Thread(target=self.recv_buffer_handler).start()
        threading.Thread(target=self.listen_to_client).start()
        threading.Thread(target=self.send_file).start()

    def set_is_paused(self, val):
        print('pausing !!!!!!!!!!!!!!!!!!!!!!!!!!!')
        if val:
            # self.socket.setblocking(False)
            # self.socket.shutdown(socket.SHUT_RDWR)
            self.state = PAUSE
            self.send_buffer = []
            self.cwd = FRAGMENT_SIZE
            self.ssthresh = FRAGMENT_SIZE * 8
            self.dup_ack_cnt = 0
        if val is False:
            self.state = None
            self.cv.acquire()
            self.cv.notify_all()
            self.cv.release()

    #
    # def recv_buffer_handler(self):
    #     while not self.is_paused:
    #         try:
    #             data, address = self.socket.recvfrom(BUFFER_SIZE)
    #             packet = RudpPacket().unpack(data)
    #
    #             if not (packet.type == RudpPacket.TYPE_ACK and self.state == DUPLICATE_EVENT and packet.ack_num == self.seq):
    #
    #                 if self.recv_buffer_size + len(data) <= BUFFER_SIZE:
    #                     self.recv_lock.acquire()
    #                     self.recv_buffer_size += len(data)
    #                     self.rev_buffer.append((packet,len(data)))
    #                     self.recv_lock.release()
    #                 else:
    #                     packet = RudpPacket().unpack(data)
    #                     print('packet was thrown because buffer is full ',packet)
    #
    #             else:
    #                 print('packet was thrown we are in DUPLICATE state')
    #
    #         except socket.timeout as e:
    #             print('listen_to_client', e)
    #             self.send_all_wind = True
    #             self.ssthresh = self.cwd / 2
    #             self.cwd = FRAGMENT_SIZE * 10
    #             self.dup_ack_cnt = 0
    #         except Exception as e:
    #             print('recv_buffer_handler',e)
    #

    def listen_to_client(self):
        tries = MAX_TRIES
        while self.state != END and tries != 0:
            try:
                data = self.socket.recv(BUFFER_SIZE)
                packet = RudpPacket().unpack(data)
                tries = MAX_TRIES

                if not ((
                                packet.type == RudpPacket.TYPE_ACK and self.state == DUPLICATE_EVENT and packet.ack_num == self.seq) or packet.seqnum > packet.ack_num):
                    self.mutex.acquire()

                    if packet.type == RudpPacket.TYPE_ACK:
                        self.handle_acks(packet)

                    if packet.type == RudpPacket.TYPE_FINACK:
                        print('FINACK')
                        self.state = END
                    self.mutex.release()

                else:
                    if packet.seqnum > packet.ack_num:
                        print(f'ack_num < seqnum {packet.seqnum}   {packet.ack_num}')
                    else:
                        print(f'packet was thrown we are in DUPLICATE state {packet.seqnum}   {packet.ack_num}')
                        self.remove_acked_packets(packet.seqnum)
            except socket.timeout as e:
                print('listen_to_client', e)
                tries -= 1
                while self.state == PAUSE:
                    self.cv.acquire()
                    self.cv.wait()
                    self.cv.release()
                else:
                    self.send_all_wind = True
                    self.ssthresh = self.cwd / 2
                    self.cwd = FRAGMENT_SIZE * 10
                    self.dup_ack_cnt = 0
            except Exception as e:
                print('listen_to_client', e)

        if tries == 0:
            self.shut_down()

        print('listen stopped')

    def remove_acked_packets(self, ack_num):
        while self.send_buffer and self.send_buffer[0].ack_num <= ack_num:
            self.send_buffer.pop(0)

    def handle_acks(self, packet: RudpPacket):
        if self.state == END or self.state == PAUSE:
            return

        self.recv_wnd_size = packet.recv_wnd

        if packet.ack_num > self.seq:
            if self.state == DUPLICATE_EVENT:
                self.state = WAIT_FOR_WND_PASS
                self.cwd = self.ssthresh
                print('FAST RECOVERY ENDS')

            self.seq = packet.ack_num
            self.remove_acked_packets(packet.ack_num)

            if self.cwd > self.ssthresh * 2:
                self.ssthresh *= 2

            if self.cwd < self.ssthresh / 2:
                self.cwd *= 2
            else:
                self.cwd += FRAGMENT_SIZE

            self.dup_ack_cnt = 0
            print(f'packet seq {packet.seqnum}  ack {packet.ack_num} was ACKED  revwnd {packet.recv_wnd}')
            print(f'cwnd {ceil(self.cwd / FRAGMENT_SIZE)}  ssthresh {ceil(self.ssthresh / FRAGMENT_SIZE)}')

        elif packet.ack_num == self.seq and self.send_buffer:
            print(f'may be a packet was lost or took longer time seq {self.seq}  packet ack {packet.ack_num}')
            self.dup_ack_cnt += 1
            if self.dup_ack_cnt == 3 and not self.send_all_wind:
                self.ssthresh /= 2
                self.cwd = self.ssthresh + 3 * FRAGMENT_SIZE
                if self.send_buffer and packet.ack_num == self.send_buffer[0].seqnum:
                    print(
                        f'3 duplicate ACKs  fast transmit : {packet.ack_num} first in buffer {self.send_buffer[0].seqnum}')
                    self.socket.sendto(self.send_buffer[0].pack(), self.address)
                    self.state = DUPLICATE_EVENT
                self.dup_ack_cnt = 0

    def load_packets(self):
        if self.content_length == self.seq:
            return

        try:
            file = open(f'data/{self.file_name}', 'rb')
        except IOError:
            print('Unable to open  file')
            self.shut_down()
            return

        i = 0
        datalen = 0
        # print(f'loading packets send buffer size {len(self.send_buffer)}  cwd {self.cwd /FRAGMENT_SIZE}')

        if self.send_buffer:
            # print(self.send_buffer)
            packet_sent_cnt = ceil(self.send_buffer[len(self.send_buffer) - 1].ack_num / FRAGMENT_SIZE)
            ss = self.send_buffer[len(self.send_buffer) - 1].ack_num
        else:
            packet_sent_cnt = ceil(self.seq / FRAGMENT_SIZE)
            ss = self.seq

        # print(f'packet cnt {packet_sent_cnt}')
        while len(self.send_buffer) < ceil(
                self.cwd / FRAGMENT_SIZE) and self.seq + datalen < self.content_length and not (
                self.state == END or self.state == PAUSE):
            file.seek(FRAGMENT_SIZE * (packet_sent_cnt + i))
            data = file.read(FRAGMENT_SIZE)

            if len(data) != 0:
                packet = RudpPacket()
                packet.type = RudpPacket.TYPE_DATA
                packet.seqnum = ss + datalen
                packet.ack_num = ss + datalen + len(data)
                packet.data = data
                packet.content_len = self.content_length
                packet.recv_wnd = BUFFER_SIZE - self.recv_buffer_size
                packet_bytes = packet.pack()
                if self.recv_wnd_size < len(packet_bytes):
                    break
                datalen += len(data)
                self.send_buffer.append(packet)
                print('Sending packet', packet.seqnum, self.seq, packet.is_sent, self.cwd,
                      f'recv wnd {self.recv_wnd_size}')
                self.socket.sendto(packet_bytes, self.address)
                packet.is_sent = True
                self.recv_wnd_size -= len(packet_bytes)
                i += 1
            else:
                break
        file.close()

    def send_file(self):
        self.socket.settimeout(2)
        print('sending length ', self.seq, self.content_length)
        while self.seq < self.content_length and self.state != END:
            if self.recv_wnd_size > FRAGMENT_SIZE + 30:
                self.mutex.acquire()
                if self.state == END:
                    break
                try:
                    while self.state == PAUSE:
                        self.cv.acquire()
                        self.cv.wait()
                        self.cv.release()

                    if self.send_all_wind:
                        print(
                            f'send all wnd cwnd {ceil(self.cwd / FRAGMENT_SIZE)}  ssthresh {self.ssthresh / FRAGMENT_SIZE} buffer size {len(self.send_buffer)} revwind {self.recv_wnd_size}')

                        i = 0
                        flag = True
                        for pkt in self.send_buffer:
                            dlen = len(pkt.pack())
                            if i < ceil(self.cwd / FRAGMENT_SIZE) and dlen < self.recv_wnd_size and flag:
                                pkt.recv_wnd = BUFFER_SIZE - self.recv_buffer_size
                                self.socket.sendto(pkt.pack(), self.address)
                                print('Sending all packet', pkt.seqnum)
                                pkt.is_sent = True
                                self.recv_wnd_size -= dlen
                            else:
                                flag = False
                                pkt.is_sent = False
                            i += 1
                        self.send_all_wind = False

                    elif self.send_buffer and not self.send_buffer[0].is_sent:
                        i = 0
                        for pkt in self.send_buffer:
                            dlen = len(pkt.pack())
                            if i < ceil(self.cwd / FRAGMENT_SIZE) and dlen < self.recv_wnd_size and not pkt.is_sent:
                                pkt.recv_wnd = BUFFER_SIZE - self.recv_buffer_size
                                self.socket.sendto(pkt.pack(), self.address)
                                print('Sending not sent packet', pkt.seqnum)
                                pkt.is_sent = True
                                self.recv_wnd_size -= dlen
                            i += 1

                    self.load_packets()
                except Exception as e:
                    print('send ', e)
                self.mutex.release()

        tries = MAX_TRIES
        while self.state != END and self.content_length == self.seq and tries > 0:
            self.mutex.acquire()
            print('sending FIN')
            p = RudpPacket()
            p.type = RudpPacket.TYPE_FIN
            p.ack_num = 0
            p.seqnum = 0
            self.socket.sendto(p.pack(), self.address)
            self.socket.settimeout(5)
            self.mutex.release()
            time.sleep(0.3)
            tries -= 1

        if self.state == END or tries == 0:
            self.shut_down()

    def shut_down(self):
        self.state = SHUT_DOWN
        self.socket.shutdown(socket.SHUT_RDWR)
        self.state = END
        self.socket.close()
        self.finish_callback()
