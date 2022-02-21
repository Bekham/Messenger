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
    ENCODING, MAX_CONNECTIONS, MAX_PACKAGE_LENGTH, DESTINATION, EXIT

SERVER_LOGGER = logging.getLogger('server')


@log
def arg_parser_server():
    try:
        """Парсер аргументов коммандной строки"""
        parser = argparse.ArgumentParser()
        parser.add_argument('-p', default=DEFAULT_PORT, type=int, nargs='?')
        parser.add_argument('-a', default='', nargs='?')
        namespace = parser.parse_args(sys.argv[1:])
        listen_address = namespace.a
        listen_port = namespace.p
        if listen_port < 1024 or listen_port > 65535:
            raise ValueError
    except ValueError:
        SERVER_LOGGER.critical(f'Попытка запуска сервера с указанием неподходящего порта '
                               f'Допустимы адреса с 1024 до 65535.')
        sys.exit(1)
    else:
        SERVER_LOGGER.info(f'Запущен сервер, порт для подключений: {listen_port}, '
                           f'адрес с которого принимаются подключения: {listen_address}. '
                           f'Если адрес не указан, принимаются соединения с любых адресов.')
        return listen_address, listen_port


class MessengerServerCore(threading.Thread, metaclass=ServerMaker):
    listen_port = Port()
    listen_address = Host()

    # @Log()
    def __init__(self, listen_address, listen_port, database):
        self.message = None
        self.listen_port = listen_port
        self.listen_address = listen_address
        self.transport = None
        self.messages = []
        self.message_from_client = None
        self.clients_names = {}
        self.clients_list = []
        # База данных сервера
        self.database = database
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
            print()
            SERVER_LOGGER.info(
                f'Порт для подключений {self.listen_port} занят!'
                f'Производится смена порта на: {self.listen_port + 1}. ')
            self.listen_port += self.listen_port
            try:
                self.transport.bind((self.listen_address, self.listen_port))
            except OSError:
                self.init_socket_server()
        self.transport.settimeout(0.5)

    # @Log()
    def run(self):
        self.init_socket_server()
        # список клиентов , очередь сообщений
        self.clients_list = []
        self.messages = []
        # Слушаем порт
        self.transport.listen(MAX_CONNECTIONS)
        SERVER_LOGGER.info('Сервер запущен...')
        # Основной цикл программы сервера
        while True:
            try:
                client, client_address = self.transport.accept()
            except OSError:
                pass

            else:
                SERVER_LOGGER.info(f'Установлено соедение с ПК {client_address}')
                self.clients_list.append(client)
            recv_data_lst = []
            send_data_lst = []
            err_lst = []
            # Проверяем на наличие ждущих клиентов
            try:
                if self.clients_list:
                    recv_data_lst, send_data_lst, err_lst = select.select(self.clients_list, self.clients_list, [], 0)
            except OSError:
                pass
            if recv_data_lst:
                for client_with_message in recv_data_lst:
                    try:
                        self.message_from_client = self.get_message(client_with_message)
                        self.process_client_message(client_with_message)
                    except:
                        SERVER_LOGGER.info(f'Клиент {client_with_message.getpeername()} '
                                           f'отключился от сервера.')
                        self.clients_list.remove(client_with_message)
            if self.messages and send_data_lst:
                for i in self.messages:
                    try:
                        self.message = i
                        self.process_message(send_data_lst)
                    except Exception:
                        SERVER_LOGGER.info(f'Связь с клиентом с именем {i[DESTINATION]} была потеряна')
                        self.clients_list.remove(self.clients_names[i[DESTINATION]])
                        del self.clients_names[i[DESTINATION]]
                self.messages.clear()

    # @Log()
    def process_message(self, listen_socks):
        """
        Функция адресной отправки сообщения определённому клиенту. Принимает словарь сообщение,
        список зарегистрированых пользователей и слушающие сокеты. Ничего не возвращает.
        :param message:
        :param names:
        :param listen_socks:
        :return:
        """

        if self.message[DESTINATION] in self.clients_names \
                and self.clients_names[self.message[DESTINATION]] in listen_socks:
            self.send_message(self.clients_names[self.message[DESTINATION]])
            SERVER_LOGGER.info(f'Отправлено сообщение пользователю {self.message[DESTINATION]} '
                               f'от пользователя {self.message[SENDER]}.')
            self.database.add_message(
                from_user=self.message[SENDER],
                to_user=self.message[DESTINATION],
                message=self.message[MESSAGE_TEXT])
        elif self.message[DESTINATION] in self.clients_names \
                and self.clients_names[self.message[DESTINATION]] not in listen_socks:
            raise ConnectionError

        elif ACTION in self.message \
                and self.message[ACTION] == MESSAGE \
                and DESTINATION not in self.message \
                and SENDER not in self.message:
            self.message = {
                ACTION: MESSAGE,
                SENDER: self.message[0],
                TIME: time.time(),
                MESSAGE_TEXT: self.message[1]
            }
            for waiting_client in listen_socks:
                try:
                    self.send_message(waiting_client)
                except:
                    SERVER_LOGGER.info(f'Клиент {waiting_client.getpeername()} отключился от сервера.')
                    self.clients_list.remove(waiting_client)
            return
        else:
            SERVER_LOGGER.error(
                f'Пользователь {self.message[DESTINATION]} не зарегистрирован на сервере, '
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
    def process_client_message(self, client_with_message):
        SERVER_LOGGER.debug(f'Разбор сообщения от клиента : {self.message_from_client}')
        if ACTION in self.message_from_client \
                and self.message_from_client[ACTION] == PRESENCE \
                and TIME in self.message_from_client \
                and USER in self.message_from_client \
                and len(self.message_from_client[USER][ACCOUNT_NAME]) > 0:
            if self.message_from_client[USER][ACCOUNT_NAME] not in self.clients_names.keys():
                self.clients_names[self.message_from_client[USER][ACCOUNT_NAME]] = client_with_message
                self.message = {RESPONSE: 200}
                client_ip, client_port = client_with_message.getpeername()
                self.database.user_login(self.message_from_client[USER][ACCOUNT_NAME], client_ip, client_port)
                self.send_message(client_with_message)
            else:
                self.message = {RESPONSE: 400}
                self.message[ERROR] = 'Имя пользователя уже занято.'
                self.send_message(client_with_message)
                self.clients_list.remove(client_with_message)
                client_with_message.close()
            return
        elif ACTION in self.message_from_client \
                and self.message_from_client[ACTION] == MESSAGE \
                and TIME in self.message_from_client \
                and DESTINATION not in self.message_from_client \
                and SENDER not in self.message_from_client \
                and MESSAGE_TEXT in self.message_from_client:
            self.messages.append(self.message_from_client)
            return
        # Если это сообщение, то добавляем его в очередь сообщений.
        # Ответ не требуется.
        elif ACTION in self.message_from_client \
                and self.message_from_client[ACTION] == MESSAGE \
                and DESTINATION in self.message_from_client \
                and TIME in self.message_from_client \
                and SENDER in self.message_from_client \
                and MESSAGE_TEXT in self.message_from_client:
            self.messages.append(self.message_from_client)
            return
            # Если клиент выходит
        elif ACTION in self.message_from_client \
                and self.message_from_client[ACTION] == EXIT \
                and ACCOUNT_NAME in self.message_from_client:
            # print(self.clients_names, self.clients_list)
            print(f'Пользователь {self.message_from_client[ACCOUNT_NAME]} отключился.')
            self.database.user_logout(self.message_from_client[ACCOUNT_NAME])
            self.clients_list.remove(self.clients_names[self.message_from_client[ACCOUNT_NAME]])
            self.clients_names[self.message_from_client[ACCOUNT_NAME]].close()
            del self.clients_names[self.message_from_client[ACCOUNT_NAME]]
            # print(self.clients_names, self.clients_list)
            return
        else:
            self.message = {
                RESPONSE: 400,
                ERROR: 'Запрос некорректен.'
            }
            self.send_message(client_with_message)
            return

    def send_message(self, socket):
        js_message = json.dumps(self.message)
        encoded_message = js_message.encode(ENCODING)
        socket.send(encoded_message)
