import json
import sys
import threading
import time

import PyQt5
from PyQt5 import QtCore, QtGui
from PyQt5 import QtWidgets
from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QPushButton, QProgressBar
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QMessageBox, QTabWidget
from PyQt5.QtWidgets import QGridLayout, QScrollArea, QLabel, QListView
from PyQt5.QtWidgets import QLineEdit, QComboBox, QGroupBox, QAction
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QFont

from client_files.controller import Controller
from client_files.events import ChatEvents
from client_files.ui_events import UIEvents

lock = threading.Lock()

BUTTON_STYLE = """
QPushButton {
    background-color: #2B5DD1;
    color: #FFFFFF;
    padding: 10px 0;
    font-size: 20px;
    border-radius: 5px;
}

QPushButton:hover {
    background-color: #cecece;
}
"""


class GUI(QWidget):
    class Changes(QObject):
        progress_changed = QtCore.pyqtSignal(int)
        download_btn_click = QtCore.pyqtSignal(str)
        pause = QtCore.pyqtSignal(bool)

    def __init__(self, parent) -> None:
        super(QWidget, self).__init__(parent)
        self.controller = Controller(callback=self.callback)
        self.users = {}
        self.changes = self.Changes()
        self.GUI_grid()

    def update_download_btn(self, str):
        if str == 'download_done':
            self.pbar.setValue(0)
            self.sendFileButtom.setText("Start Download")
            self.sendFileButtom.clicked.disconnect()
            self.sendFileButtom.clicked.connect(self.download_file)

    def set_pause_state(self, paused):
        print('aaaaaaa ', paused)
        if paused:
            self.sendFileButtom.setText("Start Download")
        else:
            self.sendFileButtom.setText("Pause Download")

    def callback(self, data):
        lock.acquire()

        if isinstance(data, UIEvents.PublicMessage):
            print(data.msg)
            self.display_message(f'{data.msg}', "#006600")

        if isinstance(data, UIEvents.PrivateMessage):
            self.display_message(f'{data.msg}', "#FF0000")

        if isinstance(data, UIEvents.Pause):
            self.changes.pause.emit(data.is_paused)

        if isinstance(data, UIEvents.Message):
            self.display_message(f'{data.msg}')

        if isinstance(data, UIEvents.FilesList):
            self.display_message(f'Server Files {data.files_list}', "#006600")

        if isinstance(data, UIEvents.UpdateDownloadPercentage):
            print(f'per {data.download_percentage}')
            self.changes.progress_changed.emit(int(data.download_percentage))
            if data.download_percentage >= 100:
                self.changes.download_btn_click.emit('download_done')

        if isinstance(data, UIEvents.Connect):
            print(f'is connected {data.is_connected}')
            if data.is_connected:
                self.connEvent.setText('Connected')
                self.connBtn.setDisabled(True)
                self.disconnBtn.setDisabled(False)
                self.tabs.setTabEnabled(1, True)
            else:
                self.connEvent.setText('Not Connected')
                self.connBtn.setDisabled(False)
                self.disconnBtn.setDisabled(True)
                self.tabs.setTabEnabled(1, False)
                self.clear_display_message()

        if isinstance(data, UIEvents.OnlineUsers):
            for user in data.users:
                self.users[user] = user
            self.update_activeFriends_list(data.users)
            self.update_send_to_list(self.users)

        if isinstance(data, UIEvents.UserDisconnected):
            self.users.pop(data.user)
            self.update_activeFriends_list(self.users)
            self.update_send_to_list(self.users)

        if isinstance(data, UIEvents.NewUser):
            self.users[data.user] = data.user
            self.update_activeFriends_list(self.users)
            self.update_send_to_list(self.users)

        lock.release()

    def login(self):
        ip = self.IP_TextLine.text()
        port = self.Port_TextLine.text()

        if port == "" or not port.isnumeric():
            self.Port_TextLine.setText("5000")
            self.connEvent.setText("Event: " + "Error Port Format")
        else:
            port = int(port)

        if not self.controller.is_connected:
            self.controller.trigger_event(ChatEvents.Connect(ip, port, self.nameLineEdit.text()))
        else:
            self.controller.trigger_event(ChatEvents.Disconnect())

    def get_users(self):
        self.controller.trigger_event(ChatEvents.GetUsers())

    def get_files(self):
        self.controller.trigger_event(ChatEvents.GetFiles())

    def send_message(self):
        if self.lineEdit.text() == '':
            return
        self.controller.trigger_event(ChatEvents.SendMessage(
            msg=self.lineEdit.text(), to=self.send_to if self.send_to != 'ALL' else None))
        self.lineEdit.setText('')

    def download_file(self):
        file_name = self.fileEnterText.text()
        # need to check if file in the list
        if file_name == '':
            return
        self.controller.trigger_event(ChatEvents.DownloadFile(file_name))
        self.sendFileButtom.setText("Pause Download")
        self.sendFileButtom.clicked.disconnect()
        self.sendFileButtom.clicked.connect(self.pause_download)

    def pause_download(self):
        self.controller.trigger_event(ChatEvents.PauseDownload())

    def update_activeFriends_list(self, list):
        self.model.clear()
        for person in list:
            item = QStandardItem(person)
            item.setCheckable(False)
            self.model.appendRow(item)

    def update_send_to_list(self, list):
        self.sendComboBox.clear()
        self.sendComboBox.addItem("ALL")
        for name in list:
            if name != self.controller.get_name():
                self.sendComboBox.addItem(name)
        previous = self.send_to
        index = self.sendComboBox.findText(previous)

        # current name we are at
        if index != -1:
            self.sendComboBox.setCurrentIndex(index)
        else:
            self.sendComboBox.setCurrentIndex(0)

    def clear_display_message(self):
        appendText = "" + '<font color=\"#000000\">Welcome to chat room</font>' + ""
        self.messageRecords.setText(appendText)
        time.sleep(0.2)
        self.scrollRecords.verticalScrollBar().setValue(self.scrollRecords.verticalScrollBar().maximum())

    def display_message(self, newMessage, textColor="#000000"):
        oldText = self.messageRecords.text()
        appendText = oldText + "<br /><font color=\"" + textColor + "\">" + newMessage + "</font><font color=\"#000000\"></font>"
        self.messageRecords.setText(appendText)
        time.sleep(0.2)
        self.scrollRecords.verticalScrollBar().setValue(self.scrollRecords.verticalScrollBar().maximum())

    def send_choice(self, text):
        self.send_to = text
        self.sendChoice.setText("Talking with: " + text)

    def GUI_grid(self):
        self.layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tabs.resize(300, 200)
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tabs.addTab(self.tab1, "Home")
        self.tabs.addTab(self.tab2, "Chat Room")
        self.tabs.setTabEnabled(1, False)
        # <Home>
        gridHome = QGridLayout()
        self.tab1.setLayout(gridHome)

        self.IP_Box = QGroupBox("IP")
        self.IP_TextLine = QLineEdit()
        self.IP_TextLine.setText("127.0.0.1")
        IPBoxLayout = QVBoxLayout()
        IPBoxLayout.addWidget(self.IP_TextLine)
        self.IP_Box.setLayout(IPBoxLayout)

        self.Port_Box = QGroupBox("Port")
        self.Port_TextLine = QLineEdit()
        self.Port_TextLine.setText("5000")
        portBoxLayout = QVBoxLayout()
        portBoxLayout.addWidget(self.Port_TextLine)
        self.Port_Box.setLayout(portBoxLayout)

        self.nameBox = QGroupBox("Name")
        self.nameLineEdit = QtWidgets.QLineEdit()
        self.nameLineEdit.setStyleSheet(
            """QLineEdit { background-color: green; color: white; padding:20px;  font-size:26px; }""")
        nameBoxLayout = QVBoxLayout()
        nameBoxLayout.addWidget(self.nameLineEdit)
        self.nameBox.setLayout(nameBoxLayout)
        self.connEvent = QLabel("Event:", self)
        font = QFont()
        font.setPointSize(16)
        self.connEvent.setFont(font)
        self.connEvent.setText('Not Connected')
        self.connBtn = QPushButton("Connect")
        self.connBtn.setStyleSheet(BUTTON_STYLE)
        self.connBtn.clicked.connect(self.login)
        self.disconnBtn = QPushButton("Disconnect")
        self.disconnBtn.setStyleSheet(BUTTON_STYLE)
        self.disconnBtn.setDisabled(True)
        self.disconnBtn.clicked.connect(self.login)
        gridHome.addWidget(self.IP_Box, 0, 0, 1, 1)
        gridHome.addWidget(self.Port_Box, 0, 1, 1, 1)
        gridHome.addWidget(self.nameBox, 1, 0, 1, 1)
        gridHome.addWidget(self.connEvent, 1, 1, 1, 1)
        gridHome.addWidget(self.connBtn, 2, 0, 1, 1)
        gridHome.addWidget(self.disconnBtn, 2, 1, 1, 1)
        gridHome.setColumnStretch(0, 1)
        gridHome.setColumnStretch(1, 1)
        gridHome.setRowStretch(0, 0)
        gridHome.setRowStretch(1, 0)
        gridHome.setRowStretch(2, 9)
        # home
        gridChatRoom = QGridLayout()
        self.tab2.setLayout(gridChatRoom)
        self.messageRecords = QLabel("<font color=\"#000000\">Welcome to chat room</font>", self)
        self.messageRecords.setStyleSheet("background-color: white;")
        self.messageRecords.setAlignment(QtCore.Qt.AlignTop)
        self.messageRecords.setAutoFillBackground(True)
        self.scrollRecords = QScrollArea()
        self.scrollRecords.setWidget(self.messageRecords)
        self.scrollRecords.setWidgetResizable(True)
        self.send_to = "ALL"
        self.sendChoice = QLabel("Talking to :ALL", self)
        self.sendComboBox = QComboBox(self)
        self.sendComboBox.addItem("ALL")
        self.sendComboBox.activated[str].connect(self.send_choice)
        self.lineEdit = QLineEdit()

        self.lineEnterBtn = QPushButton("Send")
        self.lineEnterBtn.clicked.connect(self.send_message)

        # self.lineEdit.returnPressed.connect(self.enter_line)
        self.friendList = QListView()
        self.friendList.setWindowTitle('Room List')
        self.model = QStandardItemModel(self.friendList)
        self.friendList.setModel(self.model)
        # chat room

        self.activeFriends = QPushButton("Active Friends")
        self.currentFiles = QPushButton("Files")

        self.sendFileButtom = QPushButton("Download File")
        self.changes.pause.connect(self.set_pause_state)
        self.changes.download_btn_click.connect(self.update_download_btn)
        self.sendFileButtom.clicked.connect(self.download_file)
        self.pbar = QProgressBar(self)
        self.changes.progress_changed.connect(self.pbar.setValue)
        self.fileEnterText = QLineEdit()
        self.fileEnterText.setText("a1.pdf")

        self.activeFriends.clicked.connect(self.get_users)
        self.currentFiles.clicked.connect(self.get_files)
        gridChatRoom.addWidget(self.scrollRecords, 0, 0, 1, 3)
        gridChatRoom.addWidget(self.sendFileButtom, 3, 0, 1, 1)
        gridChatRoom.addWidget(self.pbar, 3, 2, 1, 2)
        gridChatRoom.addWidget(self.currentFiles, 1, 1, 1, 1)
        gridChatRoom.addWidget(self.fileEnterText, 3, 1, 1, 1)
        gridChatRoom.addWidget(self.friendList, 0, 3, 1, 1)
        gridChatRoom.addWidget(self.sendComboBox, 1, 0, 1, 1)
        gridChatRoom.addWidget(self.sendChoice, 1, 2, 1, 1)
        gridChatRoom.addWidget(self.lineEdit, 2, 0, 1, 1)
        gridChatRoom.addWidget(self.lineEnterBtn, 2, 1, 1, 1)
        gridChatRoom.setColumnStretch(0, 8)
        gridChatRoom.setColumnStretch(1, 8)
        gridChatRoom.setColumnStretch(2, 8)
        gridChatRoom.setColumnStretch(3, 1)
        gridChatRoom.setRowStretch(0, 8)

        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)


class MainWindow(QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()
        # self.setStyleSheet("background-color: cyan;")
        self.setGeometry(50, 50, 600, 500)
        self.center()
        self.setWindowTitle("Messenger")
        self.table_widget = GUI(self)
        self.setCentralWidget(self.table_widget)

    def center(self):
        frameGm = self.frameGeometry()
        screen = PyQt5.QtWidgets.QApplication.desktop().screenNumber(
            PyQt5.QtWidgets.QApplication.desktop().cursor().pos())
        centerPoint = PyQt5.QtWidgets.QApplication.desktop().screenGeometry(screen).center()
        frameGm.moveCenter(centerPoint)
        self.move(frameGm.topLeft())


stylesheet = """
    MainWindow {
        background-image: url("server_files//data//back.jpg"); 
        background-repeat: no-repeat; 
        background-position: center;
    }
"""

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(stylesheet)
    GUI = MainWindow()
    GUI.show()
    sys.exit(app.exec_())
