from .repository import Repository
import threading
from .events import ChatEvents
from .ui_events import UIEvents


class Controller:

    def __init__(self, callback) -> None:
        self.__repo = Repository(callback , self.controller_callback)
        self.col = 0
        self.is_connected = False
        self.mutex = threading.Lock()

    def trigger_event(self, event):
        t1 = threading.Thread(target=self.__event_handler, args=(event,))
        t1.start()

    def controller_callback(self , data):
        if isinstance(data, UIEvents.Connect):
            self.is_connected = data.is_connected

    def __event_handler(self, event):
        if event is None:
            return
        try:
            if isinstance(event, ChatEvents.Connect):
                self.__connect_to_server(event.ip, event.name)

            if isinstance(event, ChatEvents.Disconnect):
                self.__close_connection()

            if isinstance(event, ChatEvents.SendMessage):
                if event.to is None or not event.to:
                    self.__send_msg(event.msg)
                else:
                    self.__send_msg_to(event.to, event.msg)

            if isinstance(event, ChatEvents.GetUsers):
                self.get_users()

            if isinstance(event, ChatEvents.GetFiles):
                self.get_files()

            if isinstance(event, ChatEvents.DownloadFile):
                self.download_file(event.filename)

            if isinstance(event, ChatEvents.PauseDownload):
                self.pause_download()
        except Exception as e:
            print(e)

    def pause_download(self):
        self.__repo.pause_download()

    def get_users(self):
        self.__repo.get_users()

    def get_files(self):
        self.__repo.get_files_list()

    def download_file(self, filename):
        self.__repo.get_file(filename)

    def __connect_to_server(self, ip, name):
        if name:
            self.__repo.connect_to_server(ip, name)

    def get_name(self):
        return self.__repo.name

    def __send_msg(self, msg):
        self.__repo.send_msg_to_all(msg)

    def __send_msg_to(self, to, msg):
        self.__repo.send_msg_to(to, msg)

    def __close_connection(self):
        self.__repo.disconnect()

