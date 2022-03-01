import threading
from tkinter import *
from tkinter import ttk
from client_files.events import ChatEvents
from client_files.controller import Controller
from client_files.ui_events import UIEvents

lock = threading.Lock()

users = {}

def callback(data):
    lock.acquire()
    if isinstance(data, UIEvents.Message):
        Label(second_frame, text=data.msg).grid(row=controller.col)
        controller.col = controller.col + 1

    if isinstance(data, UIEvents.UpdateDownloadPercentage):
        if data.download_percentage < 100:
            download_btn.config(text='Pause')
            file_dow_per.config(text='%.2f' % data.download_percentage)
        else:
            download_btn.config(text='Download')
            file_dow_per.config(text='Done')

    if isinstance(data, UIEvents.Connect):
        print(f'is connected {data.is_connected}')

    if isinstance(data, UIEvents.OnlineUsers):
        print(f'users {data.users}')

    if isinstance(data, UIEvents.UserDisconnected):
        print(f'disconnected {data.user}')
        users.pop(data.user)
    if isinstance(data, UIEvents.NewUser):
        print(f'connected {data.user}')
        users[data.user] = data.user
    lock.release()

def login():
    if not bool(controller.is_connected):
        controller.trigger_event(ChatEvents.Connect(address_e.get(), name_e.get()))
        login_btn.configure(text='Logout')
    else:
        controller.trigger_event(ChatEvents.Disconnect())
        login_btn.configure(text='Login')


def get_users():
    controller.trigger_event(ChatEvents.GetUsers())


def get_files():
    controller.trigger_event(ChatEvents.GetFiles())


def send_message():
    controller.trigger_event(ChatEvents.Message(
        msg=msg_e.get(), to=to_e.get().strip()))


def download_file():
    print(download_btn['text'])
    if download_btn['text'] == 'Download':
        controller.trigger_event(ChatEvents.DownloadFile(file_name_en.get()))
    else:
        controller.trigger_event(ChatEvents.PauseDownload())


controller = Controller(callback=callback)

FONT = ("Ariel", 10)

root = Tk()
root.geometry('1000x500')
root.title('Chat')

login_btn = Button(root, text='Login',
                   font=FONT, padx=30, command=login)
name_lable = Label(root, text="name", font=FONT, padx=5)
name_e = Entry(root, width=25)

address_lable = Label(root, text="address", font=FONT, padx=5)
address_e = Entry(root, width=25)

show_online = Button(root, text='show online',
                     font=FONT, padx=30, command=get_users)
clear_btn = Button(root, text='Clear', font=FONT, padx=30)

show_server_files = Button(
    root, text='Show Server Files', font=FONT, padx=5, command=get_files)

to_lable = Label(root, text="To (blank to all):", font=FONT)
msg_lable = Label(root, text="Message:", font=FONT)
to_e = Entry(root, width=20)
msg_e = Entry(root, width=40)
send = Button(root, text='Send', font=FONT, padx=5, command=send_message)

messages_frame = Frame(root)
messages_frame.grid(row=2, column=0, columnspan=50)

canvas = Canvas(messages_frame)
canvas.pack(side=LEFT, fill=BOTH, expand=1)

scrollbar = ttk.Scrollbar(
    messages_frame, orient=VERTICAL, command=canvas.yview)
scrollbar.pack(side=RIGHT, fill=Y)

canvas.config(yscrollcommand=scrollbar.set)
canvas.bind('<Configure>', lambda e: canvas.configure(
    scrollregion=canvas.bbox("all")))

second_frame = Frame(canvas)
canvas.create_window((0, 0), window=second_frame, anchor="nw")

file_name = Label(root, text="File Name", font=FONT)
file_name_en = Entry(root, width=40, font=FONT)
file_dow_per = Label(root, text="0%", font=FONT)
download_btn = Button(root, text='Download', font=FONT, padx=5, command=download_file)

# positioning

# row 0
login_btn.grid(row=0, column=0)

name_lable.grid(row=0, column=1)
name_e.grid(row=0, column=2)

address_lable.grid(row=0, column=3)
address_e.grid(row=0, column=4)

show_online.grid(row=0, column=5, padx=10)
clear_btn.grid(row=0, column=6)

# row 1
show_server_files.grid(row=1, column=0, pady=10)

# row3

to_lable.grid(row=3, column=1, pady=10)
to_e.grid(row=3, column=2, pady=10)

msg_lable.grid(row=3, column=3, pady=10)
msg_e.grid(row=3, column=4, pady=10)

send.grid(row=3, column=5, pady=10)

# row4


file_name.grid(row=4, column=1, pady=10)
file_name_en.grid(row=4, column=2, pady=10)
file_dow_per.grid(row=4, column=3, pady=10)
download_btn.grid(row=4, column=4, pady=10)

root.mainloop()