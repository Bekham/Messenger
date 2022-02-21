from common.core_server import MessengerServerCore, arg_parser_server



def main():
    listen_address, listen_port = arg_parser_server()
    start_server = MessengerServerCore(listen_address, listen_port)
    start_server.start_server_listen()


if __name__ == '__main__':
    main()
