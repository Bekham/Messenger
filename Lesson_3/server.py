from common.core import MessengerCore

def main():
    start_server = MessengerCore(start_server=True)
    start_server.start_server_listen()
if __name__ == '__main__':
    main()

