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
    self.nameBox = QGroupBox("Name")
    self.nameLineEdit = QtWidgets.QLineEdit()
    nameBoxLayout = QVBoxLayout()
    nameBoxLayout.addWidget(self.nameLineEdit)
    self.nameBox.setLayout(nameBoxLayout)
    self.connEvent = QLabel("Event:", self)
    font = QFont()
    font.setPointSize(16)
    self.connEvent.setFont(font)
    self.connBtn = QPushButton("Connect")
    self.connBtn.clicked.connect(self.connect_to_server)
    self.disconnBtn = QPushButton("Disconnect")
    self.disconnBtn.clicked.connect(self.disconnect)
    gridHome.addWidget(self.nameBox, 0, 0, 1, 1)
    gridHome.addWidget(self.connEvent, 0, 1)
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
    self.sendTo = "ALL"
    self.sendChoice = QLabel("Talking to :ALL", self)
    self.sendComboBox = QComboBox(self)
    self.sendComboBox.addItem("ALL")
    self.sendComboBox.activated[str].connect(self.send_choice)
    self.lineEdit = QLineEdit()

    self.lineEnterBtn = QPushButton("Send")
    self.lineEnterBtn.clicked.connect(self.enter_line)
    self.lineEdit.returnPressed.connect(self.enter_line)
    self.friendList = QListView()
    self.friendList.setWindowTitle('Room List')
    self.model = QStandardItemModel(self.friendList)
    self.friendList.setModel(self.model)
    # chat room
    self.sendFileButtom = QPushButton("Download File")
    self.sendFileButtom.clicked.connect(self.get_file)

    self.activeFriends = QPushButton("Active Friends")
    self.currentFiles = QPushButton("Files")
    self.pauseBtn = QPushButton("Pause")
    self.pauseBtn.clicked.connect(self.pause_download)
    self.activeFriends.clicked.connect(self.get_users)
    self.currentFiles.clicked.connect(self.get_files_list)
    gridChatRoom.addWidget(self.scrollRecords, 0, 0, 1, 3)
    gridChatRoom.addWidget(self.sendFileButtom, 3, 0, 1, 1)
    gridChatRoom.addWidget(self.activeFriends, 1, 1, 1, 1)
    gridChatRoom.addWidget(self.currentFiles, 3, 2, 1, 2)
    gridChatRoom.addWidget(self.pauseBtn, 3, 1, 1, 1)
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