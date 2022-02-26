from concurrent.futures import ThreadPoolExecutor
from repository import Repository
import threading
import events


class Controller:

    def __init__(self, callback) -> None:
        self.__repo = Repository(callback)
        self.col = 0
        self.is_connected = False
        self.mutex = threading.Lock()

    def trigger_event(self, event):
        executor = ThreadPoolExecutor(max_workers=1)
        executor.submit(self.__event_handler, event)
        # t1 = threading.Thread(target=self.__event_handler, args=(event,))
        # t1.start()

    def __event_handler(self, event):
        if event is None:
            return
        try:
            if isinstance(event, events.Connect):
                self.__connect_to_server(event.ip, event.name)

            if isinstance(event, events.Disconnect):
                self.__close_connection()

            if isinstance(event, events.Message):
                if event.to is None or not event.to:
                    self.__send_msg(event.msg)
                else:
                    self.__send_msg_to(event.to, event.msg)

            if isinstance(event, events.GetUsers):
                self.get_users()

            if isinstance(event, events.GetFiles):
                self.get_files()

            if isinstance(event, events.DownloadFile):
                self.download_file(event.filename, event.callback)

            if isinstance(event, events.PauseDownload):
                self.pause_download()
        except Exception as e:
            print(e)

    def pause_download(self):
        self.__repo.pause_download()

    def get_users(self):
        self.__repo.get_users()

    def get_files(self):
        self.__repo.get_files_list()

    def download_file(self, filename, callback):
        self.__repo.get_file(filename, callback)

    def __connect_to_server(self, ip, name):
        self.__repo.connect_to_server(ip, name)
        if self.__repo.is_connected == True:
            self.is_connected = True

    def __send_msg(self, msg):
        self.__repo.send_msg_to_all(msg)

    def __send_msg_to(self, to, msg):
        self.__repo.send_msg_to(to, msg)

    def __close_connection(self):
        self.__repo.disconnect()
        if self.__repo.is_connected == False:
            self.is_connected = False
