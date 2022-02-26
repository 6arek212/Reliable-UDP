import socket
import threading

from src.rudp import RudpPacket

IP = "192.168.1.21"
PORT = 5000
BUFFER_SIZE = 10000
lock = threading.Lock()
MAX_TIME_OUT = 10
FRAGMENT_SIZE = 500


class FileRepository:
    DONE = 1

    def __init__(self, sock):
        self.sock = sock
        self.is_working = False
        self.udp_sock = None
        self.callback = None
        self.file_name = None
        self.state = None
        self.is_paused = False
        self.rev_buffer = []
        self.recv_wnd = {}
        self.recv_buffer_size = 0
        self.seq = 0
        self.lock = threading.Condition()

    def get_file(self, filename, callback):
        """
        Downlaod file from the server_files
        :param filename: name of the file to download
        :param callback: callback for the GUI
        :return:
        """
        self.file_name = filename
        lock.acquire()
        self.callback = callback
        if self.is_working:
            return
        self.is_working = True
        lock.release()
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_sock.bind((IP, 0))
        self.udp_sock.settimeout(MAX_TIME_OUT)
        self.sock.send(
            f'{{"type":"get_file" , "filename":"{filename}" , "port":"{self.udp_sock.getsockname()[1]}"}}'.encode())
        threading.Thread(target=self.listen_for_udp).start()
        threading.Thread(target=self.buffer_handler()).start()

    def pause(self):
        """
        Pause downloading :D
        :return: None
        """
        self.is_paused = not self.is_paused
        if not self.is_paused:
            self.lock.acquire()
            self.state = None
            self.lock.notify_all()
            self.lock.release()

    def listen_for_udp(self):
        """
        A separate Thread for listening for the udp socket and appending the incoming data to the rev_buffer
        :return: None
        """
        while self.state != FileRepository.DONE:
            try:
                data, address = self.udp_sock.recvfrom(BUFFER_SIZE)
                self.lock.acquire()
                # ra = random.uniform(0, 1)
                #
                # if ra < 0.95:
                if self.recv_buffer_size + len(data) < BUFFER_SIZE:
                    self.recv_buffer_size += len(data)
                    self.rev_buffer.append((data, address))
                else:
                    packet = RudpPacket().unpack(data)
                    print('packet was thrown because buffer is full ', packet)
                # else:
                #     print('throw')
                self.lock.release()
            except socket.timeout as e:
                print(e, self.is_paused)
                if not self.is_paused:
                    self.shut_down()

                while self.is_paused:
                    self.lock.acquire()
                    self.lock.wait()
                    self.lock.release()

            except Exception as e:
                print('listening stopped', e)

    def buffer_handler(self):
        """
        A Thread for handling the packets in the rev_buffer
        """
        while self.state != FileRepository.DONE:
            try:
                while self.is_paused:
                    self.lock.acquire()
                    self.lock.wait()
                    self.lock.release()

                self.lock.acquire()
                if self.rev_buffer:
                    data, address = self.rev_buffer.pop(0)
                    self.recv_buffer_size -= len(data)
                    packet = RudpPacket().unpack(data)

                    if packet.type == RudpPacket.TYPE_DATA:
                        self.handle_data(packet, address)

                    elif packet.type == RudpPacket.TYPE_FIN:
                        print('FIN REQUEST')
                        p = RudpPacket()
                        p.type = RudpPacket.TYPE_FINACK
                        p.ack_num = 0
                        p.seqnum = 0
                        self.udp_sock.sendto(p.pack(), address)
                        self.shut_down()
                self.lock.release()
            except Exception as e:
                print('buffer_handler', e)

    def write_to_file(self):
        """
        Writing the data to the file
        """
        if not self.recv_wnd or self.recv_wnd.get(self.seq) is None:
            return
        with open(self.file_name, 'ab') as f:
            p = self.recv_wnd.get(self.seq)
            last_ack_num = self.recv_wnd.get(self.seq).ack_num

            while self.recv_wnd and p is not None:
                last_ack_num = self.recv_wnd.get(p.seqnum).ack_num
                f.write(self.recv_wnd.pop(p.seqnum).data)
                p = self.recv_wnd.get(last_ack_num)

            self.seq = last_ack_num

    def handle_data(self, packet, address):
        """
        handling the received packet
        ACK -> if: the seqnum > self.seq  else: DUPACK
        :param packet: received packet
        :param address: server_files udp socket address
        :return: None
        """
        p = RudpPacket()
        p.type = RudpPacket.TYPE_ACK
        p.data = None
        p.ack_num = packet.ack_num
        p.seqnum = self.seq
        p.datalength = 0
        p.recv_wnd = BUFFER_SIZE - self.recv_buffer_size
        if p.recv_wnd < 0:
            p.recv_wnd = 0

        if packet.seqnum == self.seq:
            self.recv_wnd[packet.seqnum] = packet
            self.write_to_file()
            percentage = self.seq / packet.content_len * 100
            self.callback(percentage)
            print(self.seq, packet.seqnum, f'ACKED send recv window {packet.recv_wnd}')
            p.ack_num = self.seq
            self.udp_sock.sendto(p.pack(), address)
        else:
            '''ACKS may get lost !!'''
            print(f'out of order current seq {self.seq} got seq {packet.seqnum} ack num {packet.ack_num}')
            if packet.seqnum > self.seq:
                self.recv_wnd[packet.seqnum] = packet
                p.ack_num = self.seq

            pack = p.pack()
            self.udp_sock.sendto(pack, address)

    def shut_down(self):
        """
        shut down this file downloader
        :return: None
        """
        if self.state != FileRepository.DONE:
            print('Shutting Down')
            self.state = FileRepository.DONE
            self.udp_sock.close()
            self.callback('Done')
