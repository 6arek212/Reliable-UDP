class UIEvents:
    class Connect:
        def __init__(self, is_connected: bool):
            self.is_connected = is_connected

    class UpdateDownloadPercentage:
        def __init__(self, download_percentage):
            self.download_percentage = download_percentage

    class PublicMessage:
        def __init__(self, msg):
            self.msg = msg

    class PrivateMessage:
        def __init__(self, msg):
            self.msg = msg

    class Message:
        def __init__(self, msg):
            self.msg = msg

    class OnlineUsers:
        def __init__(self, users):
            self.users = users

    class NewUser:
        def __init__(self, user):
            self.user = user

    class UserDisconnected:
        def __init__(self, user):
            self.user = user

    class FilesList:
        def __init__(self, files_list):
            self.files_list = files_list

    class Pause:
        def __init__(self, val):
            self.is_paused = val
