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

HEADER_SIZE = 32
MAX_TIME_OUT = 5
SHUT_DOWN = 5
MAX_TRIES = 10
ALPHA = 0.125


class FileDownload:
    PAUSE = 3
    END = 4
    DUPLICATE_EVENT = 1
    FAST_TRANSMIT = 2

    def __init__(self, file_name, ip, address, finish_callback):
        self.finish_callback = finish_callback
        self.file_name = file_name
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((ip, 0))
        self.socket.settimeout(MAX_TIME_OUT)
        self.ip = ip
        self.address = address
        self.state = None
        self.cwd = FRAGMENT_SIZE
        self.ssthresh = FRAGMENT_SIZE * 8
        self.seq = 0
        self.recv_buffer_size = 0
        self.send_buffer = []
        self.content_length = 0
        self.dup_ack_cnt = 0
        self.send_all_wind = False
        self.recv_wnd_size = BUFFER_SIZE
        self.rtt = 0.5
        self.send_timer = Timer(self.rtt)
        self.lock = threading.Condition()

    def start(self):
        """
        Main starting point for the file downloader ,
         starts 2 threads one for sending the file , and the other for listening for client
        :return: None
        """
        try:
            self.content_length = os.stat(f'data/{self.file_name}').st_size
        except Exception as e:
            print(e)
            return
        threading.Thread(target=self.listen_to_client).start()
        threading.Thread(target=self.send_file).start()

    def set_is_paused(self, val):
        """
        Pause file downloader
        :param val: True , False
        :return: None
        """
        print(f'Pausing ! , seq {self.seq}')
        if val:
            self.state = FileDownload3.PAUSE
            self.send_timer.stop()
            self.send_all_wind = False

        if val is False:
            self.lock.acquire()
            self.send_buffer = []
            self.cwd = FRAGMENT_SIZE
            self.ssthresh = FRAGMENT_SIZE * 8
            self.dup_ack_cnt = 0
            self.recv_wnd_size = BUFFER_SIZE
            self.state = None
            self.lock.notify_all()
            self.lock.release()

    def listen_to_client(self):
        """
        Separate thread for listening for client
        :return: None
        """
        while self.state != FileDownload3.END:
            try:
                data = self.socket.recv(BUFFER_SIZE)
                packet = RudpPacket().unpack(data)

                if not ((
                                packet.type == RudpPacket.TYPE_ACK and self.state == FileDownload3.DUPLICATE_EVENT and packet.ack_num == self.seq) or packet.seqnum > packet.ack_num):
                    self.lock.acquire()

                    if packet.type == RudpPacket.TYPE_ACK:
                        self.handle_acks(packet)

                    if packet.type == RudpPacket.TYPE_FINACK:
                        print('FINACK')
                        self.state = FileDownload3.END
                    self.lock.release()

                else:
                    if packet.seqnum > packet.ack_num:
                        print(f'ack_num < seqnum , Looks like client holding packet till   {packet.seqnum}')
                    else:
                        print(f'packet was thrown we are in DUPLICATE state {packet.seqnum}   {packet.ack_num}')
                        self.remove_acked_packets(packet.seqnum)


            except socket.timeout as e:
                print('listen_to_client', e)
                if self.state != FileDownload3.PAUSE:
                    self.lock.acquire()
                    self.state = FileDownload3.END
                    self.shut_down()
                    self.lock.release()

                while self.state == FileDownload3.PAUSE:
                    self.lock.acquire()
                    self.lock.wait()
                    self.lock.release()



            except Exception as e:
                print('listen_to_client', e)

        print('listen stopped')

    def remove_acked_packets(self, ack_num):
        """
        Removing all packets from send_buffer that already ACKed
        :param ack_num: sequence number of last ACK
        :return: None
        """
        while self.send_buffer and self.send_buffer[0].ack_num <= ack_num:
            self.send_buffer.pop(0)

    def handle_acks(self, packet: RudpPacket):
        """
        Handle incoming ACK packets
        :param packet: ACK packet
        :return: None
        """
        if self.state == FileDownload3.END or self.state == FileDownload3.PAUSE:
            return

        self.recv_wnd_size = packet.recv_wnd

        if packet.ack_num > self.seq:
            if self.send_timer.running():
                self.rtt = (1 - ALPHA) * self.rtt + ALPHA * (time.time() - self.send_timer._start_time)
                print(f'new RTT {self.rtt}')

            self.send_timer.stop()
            if self.state == FileDownload3.FAST_TRANSMIT:
                self.cwd = self.ssthresh
                self.state = None
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
                if self.send_buffer and packet.ack_num == self.send_buffer[0].seqnum:
                    self.state = FileDownload3.DUPLICATE_EVENT
                self.dup_ack_cnt = 0




    def duplicate_event(self):
        """
        Duplicated packets event handling
        """
        print(
            f'3 duplicate ACKs  fast transmit : first in buffer {self.send_buffer[0].seqnum}')
        self.ssthresh /= 2
        self.cwd = self.ssthresh + 3 * FRAGMENT_SIZE
        self.socket.sendto(self.send_buffer[0].pack(), self.address)
        self.send_timer.start(self.rtt)
        self.state = FileDownload3.FAST_TRANSMIT

    def time_out_event(self):
        """
        Timeout event handling
        """
        print('Timeout')
        self.send_timer.stop()
        self.send_all_wind = True
        self.cwd = FRAGMENT_SIZE
        self.ssthresh = FRAGMENT_SIZE * 8
        self.dup_ack_cnt = 0


    def send_all_window(self):
        """
        Send all the packets in the current window
        """
        print(
            f'send all wnd cwnd {ceil(self.cwd / FRAGMENT_SIZE)}  ssthresh {self.ssthresh / FRAGMENT_SIZE} buffer size {len(self.send_buffer)} revwind {self.recv_wnd_size}')
        i = 0
        flag = True
        for pkt in self.send_buffer:
            if i < ceil(self.cwd / FRAGMENT_SIZE) and flag:
                pkt.recv_wnd = BUFFER_SIZE - self.recv_buffer_size
                self.socket.sendto(pkt.pack(), self.address)
                print('Sending all packet', pkt.seqnum)
                pkt.is_sent = True
            else:
                flag = False
                pkt.is_sent = False
            i += 1
        self.send_all_wind = False


    def send_not_sent_packets(self):
        """
        Sending the packets with is_sent = False ,
        Taking count of cwd size and flow control
        """
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




    def send_file(self):
        """
        Separate thread for sending packets
        """
        print('sending length ', self.seq, self.content_length)

        tries = MAX_TRIES
        while self.seq < self.content_length and self.state != FileDownload3.END and tries > 0:
            self.lock.acquire()
            if self.state == FileDownload3.END:
                break
            try:
                while self.state == FileDownload3.PAUSE:
                    self.lock.acquire()
                    self.lock.wait()
                    self.lock.release()

                if self.send_all_wind:
                    self.send_all_window()

                elif self.send_buffer and not self.send_buffer[0].is_sent:
                    self.send_not_sent_packets()

                self.load_and_send_packets()

                # Start Timer
                if not self.send_timer.running():
                    print('Starting timer')
                    self.send_timer.start(self.rtt)

                # Wait until a timer goes off or we get an ACK
                while self.send_timer.running() and not self.send_timer.timeout():
                    self.lock.release()
                    if self.state == FileDownload3.DUPLICATE_EVENT:
                        self.duplicate_event()
                    print('Sleeping')
                    time.sleep(SLEEP_INTERVAL)
                    self.lock.acquire()

                if self.send_timer.timeout():
                    # Looks like we timed out
                    self.time_out_event()
                    tries -= 1
                else:
                    tries = MAX_TRIES
                self.lock.release()

            except Exception as e:
                print('send ', e)

        if tries > 0:
            self.fin_request()
        else:
            print('Tries 0 , Looks like client is dead')
            self.shut_down()



    def load_and_send_packets(self):
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

        if self.send_buffer:
            packet_sent_cnt = ceil(self.send_buffer[len(self.send_buffer) - 1].ack_num / FRAGMENT_SIZE)
            ss = self.send_buffer[len(self.send_buffer) - 1].ack_num
        else:
            packet_sent_cnt = ceil(self.seq / FRAGMENT_SIZE)
            ss = self.seq

        while len(self.send_buffer) < ceil(
                self.cwd / FRAGMENT_SIZE) and self.seq + datalen < self.content_length and not (
                self.state == FileDownload3.END or self.state == FileDownload3.PAUSE):
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



    def fin_request(self):
        """
        Gracefully request for closing connection
        :return: None
        """
        self.lock.acquire()
        tries = MAX_TRIES
        while self.state != FileDownload3.END and self.content_length == self.seq and tries > 0:
            print('sending FIN')
            p = RudpPacket()
            p.type = RudpPacket.TYPE_FIN
            p.ack_num = 0
            p.seqnum = 0
            self.socket.sendto(p.pack(), self.address)
            self.socket.settimeout(5)
            self.lock.release()
            time.sleep(0.3)
            tries -= 1

        if self.state == FileDownload3.END or tries == 0:
            self.shut_down()


    def shut_down(self):
        """
        Shutting down this file downloader
        :return: None
        """
        self.socket.shutdown(socket.SHUT_RDWR)
        self.state = FileDownload3.END
        self.socket.close()
        self.finish_callback()
