import socket
import threading
from time import sleep

from rudp import RudpPacket

IP = "192.168.1.21"
PORT = 5000
BUFFER_SIZE = 4096
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
                self.rev_buffer.append((data,address))
            except Exception as e:
                print(e)

        self.is_working = False


    def buffer_handler(self):
        while not self.is_done:
            if self.rev_buffer:
                data ,address = self.rev_buffer.pop(0)
                packet = RudpPacket().unpack(data)
                if packet.type == RudpPacket.TYPE_DATA:
                    self.handle_data(packet, address)




    def handle_data(self, packet, address):
        if packet.seqnum == self.seq:
            self.seq = packet.ack_num
            with open(self.file_name, 'ab') as f:
                f.write(packet.data)
            self.cnt+=1
            print(self.seq, packet.seqnum, packet.ack_num, 'ACKED')
            self.cnt = 0
            percentage = self.seq / packet.content_len * 100
            self.callback(percentage)

        else:
            print(f'out of order current seq {self.seq} got seq {packet.seqnum} ack num {packet.ack_num}')
            packet.ack_num = self.seq


        packet.type = RudpPacket.TYPE_ACK
        packet.data = None
        packet.datalength = 0
        self.udp_sock.sendto(packet.pack(), address)

        if self.seq == packet.content_len:
            self.shut_down()

    # def write_to_file(self, buffer):
    #     with open(self.file_name, 'ab') as f:
    #         ff = None
    #         while buffer:
    #             last = buffer.pop(0)
    #             if ff is None:
    #                 ff = last
    #                 f.write(last.data)
    #             elif ff.ack_num == last.seqnum:
    #                 f.write(last.data)
    #             else:
    #                 break
    #         self.seq = last.ack_num
    #
    # def handle_data(self, packet, address):
    #     p = RudpPacket()
    #
    #     if packet.seqnum == self.seq:
    #         # self.seq = packet.ack_num
    #         print(self.rev_buffer)
    #
    #         if self.rev_buffer and self.rev_buffer[0].seqnum == packet.ack_num:
    #             self.rev_buffer.insert(0, packet)
    #             self.write_to_file(self.rev_buffer)
    #         else:
    #             self.write_to_file([packet])
    #
    #         percentage = int(self.seq / packet.content_len * 100)
    #         self.callback(percentage)
    #         print(self.seq, packet.seqnum, 'ACKED')
    #         p.ack_num = packet.ack_num
    #
    #     else:
    #         print(f'out of order current seq {self.seq} got seq {packet.seqnum} ack num {packet.ack_num}')
    #         if packet.seqnum > self.seq:
    #             self.rev_buffer.append(packet)
    #             self.rev_buffer.sort(key=lambda p: p.ack_num)
    #         p.ack_num = self.seq
    #
    #     p.seqnum = packet.seqnum
    #     p.type = RudpPacket.TYPE_ACK
    #     p.data = None
    #     p.datalength = 0
    #     self.udp_sock.sendto(p.pack(), address)
    #
    #     if self.seq == packet.content_len:
    #         self.shut_down()

    def shut_down(self):
        if self.udp_sock is not None:
            self.is_done = True
            self.udp_sock.shutdown(socket.SHUT_RDWR)
            self.udp_sock.close()
            self.callback('Done')

# def connect_to_server():
#     sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     name = 'tarik'
#     print('ip is ', IP)
#     sock.connect((IP, PORT))
#     sock.send(f'{{"name": "{name}","type":"connect"}}'.encode())
#     sleep(0.1)
#     return sock

# repo = FileRepository2(connect_to_server())
# repo.get_file('')
