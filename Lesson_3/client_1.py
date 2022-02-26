import configparser
import os

from common.core_client import MessengerClientCore, arg_parser_client


def main():
    config = configparser.ConfigParser()

    dir_path = os.path.dirname(os.path.realpath(__file__))
    config.read(f"{dir_path}/{'server.ini'}")


    server_address, server_port, client_name, client_mode = arg_parser_client(config['SETTINGS']['Default_port'],
                                                    config['SETTINGS']['Listen_Address'])
    start_client = MessengerClientCore(server_address, server_port, client_name, client_mode)
    start_client.start_client_send()


if __name__ == '__main__':
    main()
