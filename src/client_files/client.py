import events
from controller import Controller



def callback(data):
    print(data)


controller = Controller(callback=callback)


flag = True

m = '1- Connect to server_files\n2- Send msg \n3- Exist\n'


while flag:
    val = input(m)

    if val == '1':
        ip = input('Enter servers ip: ')
        name = input('enter your name: ')
        controller.trigger_event(events.Connect(val, name))

    if val == '2':
        message = input('Enter message : ')
        controller.trigger_event(events.Message(msg=message))

    if val == '3':
        message = input('Enter message : ')
        to = input('Enter to : ')
        controller.trigger_event(events.Message(msg=message, to=to))

    if val == '4':
        controller.trigger_event(events.GetUsers())

    if val == '5':
        controller.trigger_event(events.GetFiles())

    if val == '6':
        controller.trigger_event(events.Disconnect())

    if val == '7':
        controller.trigger_event(events.Disconnect())
        flag = False    
