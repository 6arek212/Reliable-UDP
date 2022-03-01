class ChatEvents:
    class SendMessage():
        def __init__(self, msg: str, to: int = None):
            self.msg = msg
            self.to = to

    class DownloadFile():
        def __init__(self, filename: str):
            self.filename = filename

    class PauseDownload():
        pass

    class Connect():
        def __init__(self, ip: str, port: int, name: str):
            self.ip = ip
            self.port = port
            self.name = name

    class Disconnect():
        pass

    class GetUsers():
        pass

    class GetFiles():
        pass
