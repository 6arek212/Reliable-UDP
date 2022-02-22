import _thread
import os
import socket
import threading
import time
from math import ceil

from rudp import RudpPacket
from timer import Timer

BUFFER_SIZE = 4096
FRAGMENT_SIZE = 500
SLEEP_INTERVAL = 0.05


class FileDownload:

    def __init__(self, file_name, ip, address, finish_callback):
        self.finish_callback = finish_callback
        self.file_name = file_name
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((ip, 0))
        self.ip = ip
        self.address = address
        self.state = None
        self.time_out = 0.5
        self.cwd = 1
        self.seq = 0
        self.send_cwnd = []
        self.is_paused = False
        self.content_length = 0
        self.last_packet_in_cwd = None
        self.dup_ack_cnt = 0
        self.is_end = False
        self.mutex = _thread.allocate_lock()
        self.send_timer = Timer(self.time_out)

    def start(self):
        try:
            self.content_length = os.stat(f'data/{self.file_name}').st_size
        except Exception as e:
            print(e)
            return
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

    def listen_to_client(self):
        while not self.is_paused:
            try:
                data, address = self.socket.recvfrom(BUFFER_SIZE)
                packet = RudpPacket().unpack(data)

                if packet.type == RudpPacket.TYPE_DATA:
                    '''PAUSE OR CONTINUE'''
                    pass

                if packet.type == RudpPacket.TYPE_ACK:
                    self.handle_acks(packet)

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
        self.mutex.acquire()

        # print(f'packet {self.seq} {packet.ack_num}')

        if packet.ack_num > self.seq:
            self.seq = packet.ack_num
            self.send_timer.stop()

            if self.seq == self.last_packet_in_cwd.ack_num:
                # if self.cwd < 64:
                self.cwd *= 2
                self.dup_ack_cnt = 0
            print(f'packet {self.seq} was ACKED')

        elif packet.ack_num == self.seq:
            print(f'may be a packet was lost or took longer time seq {self.seq}  packet ack {packet.ack_num}')
            self.dup_ack_cnt += 1
            if self.dup_ack_cnt == 3:
                self.cwd /= 2
                print(f'3 duplicate ACKs sending : {packet.ack_num}')

        if self.content_length == self.seq:
            self.is_paused = True
        self.mutex.release()

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
        print('loading packets cwnd size ', len(self.send_cwnd))
        while len(self.send_cwnd) < self.cwd and self.seq + datalen < self.content_length:
            packet_sent_cnt = ceil(self.seq / FRAGMENT_SIZE)
            file.seek(FRAGMENT_SIZE * (packet_sent_cnt + i))
            data = file.read(FRAGMENT_SIZE)
            packet = RudpPacket()
            packet.type = RudpPacket.TYPE_DATA
            packet.seqnum = self.seq + datalen
            packet.ack_num = self.seq + datalen + len(data)
            packet.data = data
            packet.content_len = self.content_length
            datalen += len(data)
            self.send_cwnd.append(packet)
            i += 1

        self.last_packet_in_cwd = self.send_cwnd[len(self.send_cwnd) - 1]
        file.close()

    def send_file(self):
        print('sending length ', self.seq, self.content_length, ' is paused ', self.is_paused)
        while self.seq < self.content_length and not self.is_paused:
            self.mutex.acquire()
            self.load_packets()

            # Send all the packets in the window
            while self.send_cwnd:
                print('Sending packet', self.send_cwnd[0].seqnum, self.seq)
                self.socket.sendto(self.send_cwnd.pop(0).pack(), self.address)

            # Start the timer
            if not self.send_timer.running():
                # print('Starting timer')
                self.send_timer.start()

            # Wait until a timer goes off or we get an ACK
            while self.send_timer.running() and not self.send_timer.timeout():
                self.mutex.release()
                # print('Sleeping')
                time.sleep(SLEEP_INTERVAL)
                self.mutex.acquire()

            if self.send_timer.timeout():
                # Looks like we timed out
                print('Timeout')
                self.cwd = 1
                self.send_timer.stop()

            self.mutex.release()

    def shut_down(self):
        self.socket.shutdown(socket.SHUT_RDWR)
        self.is_paused = True
        self.socket.close()
