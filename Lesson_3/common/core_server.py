import argparse
import json
import select
import socket
import sys
import threading
import time
import logging
from common.descrptors import Port, Host
from common.meta import ServerMaker

sys.path.append('../')
from common.decos import Log
from common.decos import log
from common.variables import DEFAULT_PORT, DEFAULT_IP_ADDRESS, \
    ACTION, TIME, USER, ACCOUNT_NAME, SENDER, PRESENCE, RESPONSE, ERROR, MESSAGE, MESSAGE_TEXT, \
    ENCODING, MAX_CONNECTIONS, MAX_PACKAGE_LENGTH, DESTINATION, EXIT, RESPONSE_202, GET_CONTACTS, LIST_INFO, \
    RESPONSE_400, REMOVE_CONTACT, RESPONSE_200, USERS_REQUEST, ADD_CONTACT

SERVER_LOGGER = logging.getLogger('server')
# new_connection = False
conflag_lock = threading.Lock()

@log
def arg_parser_server(default_port,
                      default_address):
    """Парсер аргументов коммандной строки"""
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', default=default_port, type=int, nargs='?')
    parser.add_argument('-a', default=default_address, nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    listen_address = namespace.a
    listen_port = namespace.p
    #     if listen_port < 1024 or listen_port > 65535:
    #         raise ValueError
    # except ValueError:
    #     SERVER_LOGGER.critical(f'Попытка запуска сервера с указанием неподходящего порта '
    #                            f'Допустимы адреса с 1024 до 65535.')
    #     sys.exit(1)
    # else:
    #     SERVER_LOGGER.info(f'Запущен сервер, порт для подключений: {listen_port}, '
    #                        f'адрес с которого принимаются подключения: {listen_address}. '
    #                        f'Если адрес не указан, принимаются соединения с любых адресов.')
    return listen_address, listen_port


class MessengerServerCore(threading.Thread, metaclass=ServerMaker):
    listen_port = Port()
    # listen_address = Host()

    # @Log()
    def __init__(self, listen_address, listen_port, database):
        # self.message = None
        self.listen_port = listen_port
        self.listen_address = listen_address
        self.transport = None
        self.clients = []
        self.messages = []
        self.message_from_client = None
        self.clients_names = {}
        # База данных сервера
        self.database = database
        self.new_connection = False
        # self.SERVER_LOGGER = logging.getLogger('server')
        # self.arg_parser_server()
        super().__init__()

    # @Log()
    def init_socket_server(self):
        SERVER_LOGGER.info(
            f'Запущен сервер, порт для подключений: {self.listen_port}, '
            f'адрес с которого принимаются подключения: {self.listen_address}. '
            f'Если адрес не указан, принимаются соединения с любых адресов.')
        self.transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.transport.bind((self.listen_address, self.listen_port))
        except OSError:
            print(f'Порт для подключений {self.listen_port} занят!'
                f'Производится смена порта на: {self.listen_port + 1}. ')
            SERVER_LOGGER.info(
                f'Порт для подключений {self.listen_port} занят!'
                f'Производится смена порта на: {self.listen_port + 1}. ')
            self.listen_port += self.listen_port
            try:
                self.transport.bind((self.listen_address, self.listen_port))
            except OSError:
                self.init_socket_server()
        # Слушаем порт
        self.transport.settimeout(0.5)
        self.transport.listen()

    # @Log()
    def run(self):
        self.init_socket_server()
        # список клиентов, очередь сообщений
        SERVER_LOGGER.info('Сервер запущен...')
        # Основной цикл программы сервера
        while True:
            try:
                client, client_address = self.transport.accept()
            except OSError:
                # print('OS ERROR')
                pass
            else:
                SERVER_LOGGER.info(f'Установлено соедение с ПК {client_address}')
                self.clients.append(client)
            recv_data_lst = []
            send_data_lst = []
            err_lst = []
            # Проверяем на наличие ждущих клиентов
            try:
                if self.clients:
                    recv_data_lst, send_data_lst, err_lst = select.select(self.clients, self.clients, [], 0)
            except OSError as err:
                SERVER_LOGGER.error(f'Ошибка работы с сокетами: {err}')
            if recv_data_lst:
                for client_with_message in recv_data_lst:
                    try:
                        self.process_client_message(self.get_message(client_with_message), client_with_message)
                    except (OSError):
                        SERVER_LOGGER.info(f'Клиент {client_with_message.getpeername()} '
                                           f'отключился от сервера.')
                        for name in self.clients_names:#add_new
                            if self.clients_names[name] == client_with_message:
                                self.database.user_logout(name)
                                del self.clients_names[name]
                                break
                        self.clients.remove(client_with_message)
                        with conflag_lock:
                            self.new_connection = True
            if self.messages:
                for i in self.messages:
                    try:
                        self.process_message(i, send_data_lst)
                    except (ConnectionAbortedError, ConnectionError, ConnectionResetError, ConnectionRefusedError):
                        SERVER_LOGGER.info(f'Связь с клиентом с именем {i[DESTINATION]} была потеряна')
                        self.clients.remove(self.clients_names[i[DESTINATION]])
                        del self.clients_names[i[DESTINATION]]
                        with conflag_lock:
                            self.new_connection = True
                self.messages.clear()

    @log
    def process_message(self, message, listen_socks):
        """
        Функция адресной отправки сообщения определённому клиенту. Принимает словарь сообщение,
        список зарегистрированых пользователей и слушающие сокеты. Ничего не возвращает.
        :param message:
        :param names:
        :param listen_socks:
        :return:
        """
        if message[DESTINATION] in self.clients_names \
                and self.clients_names[message[DESTINATION]] in listen_socks:
            self.send_message(self.clients_names[message[DESTINATION]], message)
            SERVER_LOGGER.info(f'Отправлено сообщение пользователю {message[DESTINATION]} '
                               f'от пользователя {message[SENDER]}.')
            self.database.add_message(
                from_user=message[SENDER],
                to_user=message[DESTINATION],
                message=message[MESSAGE_TEXT])
        elif message[DESTINATION] in self.clients_names \
                and self.clients_names[message[DESTINATION]] not in listen_socks:
            raise ConnectionError
        else:
            SERVER_LOGGER.error(
                f'Пользователь {message[DESTINATION]} не зарегистрирован на сервере, '
                f'отправка сообщения невозможна.')

    def get_message(self, client):
        '''
        Утилита приёма и декодирования сообщения
        принимает байты выдаёт словарь, если приняточто-то другое отдаёт ошибку значения
        :param client:
        :return:
        '''

        encoded_response = client.recv(MAX_PACKAGE_LENGTH)
        if isinstance(encoded_response, bytes):
            json_response = encoded_response.decode(ENCODING)
            response = json.loads(json_response)
            if isinstance(response, dict):
                return response
            raise ValueError
        raise ValueError

    # @Log()
    def process_client_message(self, message, client):
        # global new_connection
        SERVER_LOGGER.debug(f'Разбор сообщения от клиента : {self.message_from_client}')
        if ACTION in message \
                and message[ACTION] == PRESENCE \
                and TIME in message \
                and USER in message:
            if message[USER][ACCOUNT_NAME] not in self.clients_names.keys():
                self.clients_names[message[USER][ACCOUNT_NAME]] = client
                client_ip, client_port = client.getpeername()
                self.database.user_login(message[USER][ACCOUNT_NAME], client_ip, client_port)
                self.send_message(client, {RESPONSE: 200})
                # print(f'Send presence OK to {message[USER][ACCOUNT_NAME]}')
                with conflag_lock:#add_new
                    self.new_connection = True
            else:
                message_error = {RESPONSE: 400}
                message_error[ERROR] = 'Имя пользователя уже занято.'
                print(message_error)
                self.send_message(client, message_error)
                self.clients.remove(client)
                client.close()
            return

        # Если это сообщение, то добавляем его в очередь сообщений.
        # Ответ не требуется.
        elif ACTION in message \
                and message[ACTION] == MESSAGE \
                and DESTINATION in message \
                and TIME in message \
                and SENDER in message \
                and MESSAGE_TEXT in message \
                and self.clients_names[message[SENDER]] == client:

            all_users = [contact[0] for contact in self.database.users_list()]
            if message[DESTINATION] in self.clients_names:
                self.messages.append(message)
                self.database.process_message(message[SENDER], message[DESTINATION])
                self.send_message(client, RESPONSE_200)
            elif message[DESTINATION] in all_users:
                print(all_users)
                response = RESPONSE_400
                response[ERROR] = f'Пользователь {message[DESTINATION]} офлайн. Напишите позже.'
                self.send_message(client, response)
            else:
                response = RESPONSE_400
                response[ERROR] = 'Пользователь не зарегистрирован на сервере.'
                self.send_message(client, response)
            return

            # Если клиент выходит
        elif ACTION in message \
                and message[ACTION] == EXIT \
                and ACCOUNT_NAME in message \
                and self.clients_names[message[ACCOUNT_NAME]] == client:
            # print(self.clients_names, self.clients_list)
            self.database.user_logout(message[ACCOUNT_NAME])
            SERVER_LOGGER.info(f'Пользователь {message[ACCOUNT_NAME]} отключился.')
            self.clients.remove(self.clients_names[message[ACCOUNT_NAME]])
            self.clients_names[message[ACCOUNT_NAME]].close()
            del self.clients_names[message[ACCOUNT_NAME]]
            # print(self.clients_names, self.clients_list)
            with conflag_lock:#add_new
                self.new_connection = True
            return
        # Если это запрос контакт-листа
        elif ACTION in message \
                and message[ACTION] == GET_CONTACTS \
                and USER in message \
                and self.clients_names[message[USER]] == client:
            response = RESPONSE_202
            response[LIST_INFO] = self.database.get_contacts(message[USER])
            self.send_message(client, response)#add_new

        elif ACTION in message \
                and message[ACTION] == ADD_CONTACT \
                and ACCOUNT_NAME in message \
                and USER in message \
                and self.clients_names[message[USER]] == client:
            self.database.add_contact(message[USER], message[ACCOUNT_NAME])
            self.send_message(client, RESPONSE_200)  # add_new

            # Если это удаление контакта
        elif ACTION in message \
                and message[ACTION] == REMOVE_CONTACT \
                and ACCOUNT_NAME in message \
                and USER in message \
                and self.clients_names[message[USER]] == client:
            self.database.remove_contact(message[USER], message[ACCOUNT_NAME])
            self.send_message(client, RESPONSE_200)  # add_new

        # Если это запрос известных пользователей
        elif ACTION in message \
                and message[ACTION] == USERS_REQUEST \
                and ACCOUNT_NAME in message \
                and self.clients_names[message[ACCOUNT_NAME]] == client:
            response = RESPONSE_202
            response[LIST_INFO] = [user[0] for user in self.database.users_list()]
            self.send_message(client, response)  # add_new
        else:
            response = RESPONSE_400
            response[ERROR] = 'Запрос некорректен.'
            self.send_message(client, response)
            return

    def send_message(self, socket, message):
        js_message = json.dumps(message)
        encoded_message = js_message.encode(ENCODING)
        socket.send(encoded_message)
