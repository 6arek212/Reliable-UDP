

class Message():
    def __init__(self, msg: str, to: int = None):
        self.msg = msg
        self.to = to


class DownloadFile():
    def __init__(self, filename: str , callback):
        self.filename = filename
        self.callback=callback

class PauseDownload():
    pass




class Connect():
    def __init__(self, ip: str, name: str):
        self.ip = ip
        self.name = name


class Disconnect():
    pass


class GetUsers():
    pass

class GetFiles():
    pass
