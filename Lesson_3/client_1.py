from common.core_client import MessengerClientCore, arg_parser_client


def main():
    server_address, server_port, client_mode = arg_parser_client()
    start_client = MessengerClientCore(server_address, server_port, client_mode)
    start_client.start_client_send()


if __name__ == '__main__':
    main()
