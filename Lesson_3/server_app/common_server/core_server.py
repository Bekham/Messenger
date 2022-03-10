import os
import select
import socket
import sys
import threading
import json
import logging

import argparse
import binascii
import hmac

from server_app.common_server.descrptors import Port
from server_app.common_server.meta import ServerMaker
from server_app.common_server.decos import login_required, log
from server_app.common_server.variables import *

sys.path.append('../')

SERVER_LOGGER = logging.getLogger('server')
conflag_lock = threading.Lock()


@log
def arg_parser_server(default_port,
                      default_address):
    """Парсер аргументов коммандной строки"""
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', default=default_port, type=int, nargs='?')
    parser.add_argument('-a', default=default_address, nargs='?')
    parser.add_argument('--no_gui', action='store_true')
    namespace = parser.parse_args(sys.argv[1:])
    listen_address = namespace.a
    listen_port = namespace.p
    gui_flag = namespace.no_gui
    SERVER_LOGGER.debug('Аргументы успешно загружены.')
    return listen_address, listen_port, gui_flag


class MessengerServerCore(threading.Thread, metaclass=ServerMaker):
    """Принимает соединения, словари - пакеты
    от клиентов, обрабатывает поступающие сообщения.
    Работает в качестве отдельного потока."""
    listen_port = Port()

    # listen_address = Host()

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
        # Сокеты
        self.listen_sockets = None
        self.error_sockets = None
        # Флаг продолжения работы
        self.running = True

        super().__init__()

    def init_socket_server(self):
        """
        Метод обработчик клиента с которым прервана связь.
        Ищет клиента и удаляет его из списков и базы:
        """
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
        self.transport.listen(MAX_CONNECTIONS)

    def run(self):
        """Метод основной цикл потока."""
        self.init_socket_server()
        # список клиентов, очередь сообщений
        SERVER_LOGGER.info('Сервер запущен...')
        # Основной цикл программы сервера
        while self.running:
            try:
                client, client_address = self.transport.accept()
            except OSError:
                # print('OS ERROR')
                pass
            else:
                SERVER_LOGGER.info(
                    f'Установлено соедение с ПК {client_address}')
                client.settimeout(5)
                self.clients.append(client)
            recv_data_lst = []
            # Проверяем на наличие ждущих клиентов
            try:
                if self.clients:
                    recv_data_lst, self.listen_sockets, self.error_sockets = select.select(
                        self.clients, self.clients, [], 0)
            except OSError as err:
                SERVER_LOGGER.error(f'Ошибка работы с сокетами: {err}')
            if recv_data_lst:
                for client_with_message in recv_data_lst:
                    try:
                        self.process_client_message(
                            self.get_message(client_with_message), client_with_message)
                    except (OSError, json.JSONDecodeError, TypeError) as err:
                        SERVER_LOGGER.debug(
                            f'Клиент {client_with_message.getpeername()} '
                            f'отключился от сервера.', exc_info=err)
                        self.remove_client(client_with_message)

    def remove_client(self, client):
        """
        Метод обработчик клиента с которым прервана связь.
        Ищет клиента и удаляет его из списков и базы:
        """
        SERVER_LOGGER.info(
            f'Клиент {client.getpeername()} отключился от сервера.')
        for name in self.clients_names:
            if self.clients_names[name] == client:
                self.database.user_logout(name)
                del self.clients_names[name]
                break
        self.clients.remove(client)
        client.close()

    def process_message(self, message):
        """
        Функция адресной отправки сообщения определённому клиенту. Принимает словарь сообщение,
        список зарегистрированных пользователей и слушающие сокеты. Ничего не возвращает.
        :param message:
        :return:
        """
        if message[DESTINATION] in self.clients_names \
                and self.clients_names[message[DESTINATION]] in self.listen_sockets:
            try:
                self.send_message(
                    self.clients_names[message[DESTINATION]], message)
                self.database.add_message(
                    from_user=message[SENDER],
                    to_user=message[DESTINATION],
                    message=message[MESSAGE_TEXT])
                SERVER_LOGGER.info(
                    f'Отправлено сообщение пользователю {message[DESTINATION]} '
                    f'от пользователя {message[SENDER]}.')
            except OSError:
                self.remove_client(message[DESTINATION])

        elif message[DESTINATION] in self.clients_names \
                and self.clients_names[message[DESTINATION]] not in self.listen_sockets:
            SERVER_LOGGER.error(
                f'Связь с клиентом {message[DESTINATION]} была потеряна. '
                f'Соединение закрыто, доставка невозможна.')
            self.remove_client(self.clients_names[message[DESTINATION]])
        else:
            SERVER_LOGGER.error(
                f'Пользователь {message[DESTINATION]} не зарегистрирован '
                f'на сервере, отправка сообщения невозможна.')

    def get_message(self, client):
        """
        Утилита приёма и декодирования сообщения
        принимает байты, выдаёт словарь, если принято что-то другое отдаёт ошибку значения
        :param client:
        :return:
        """
        encoded_response = client.recv(MAX_PACKAGE_LENGTH)
        if isinstance(encoded_response, bytes):
            json_response = encoded_response.decode(ENCODING)
            response = json.loads(json_response)
            if isinstance(response, dict):
                return response
            raise ValueError
        raise ValueError

    @login_required
    def process_client_message(self, message, client):
        """Метод отбработчик поступающих сообщений."""
        SERVER_LOGGER.debug(f'Разбор сообщения от клиента : {message}')
        if ACTION in message \
                and message[ACTION] == PRESENCE \
                and TIME in message \
                and USER in message:
            self.autorize_user(message, client)

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

                self.database.process_message(
                    message[SENDER], message[DESTINATION])
                self.process_message(message)
                try:
                    self.send_message(client, RESPONSE_200)
                except OSError:
                    self.remove_client(client)
            elif message[DESTINATION] in all_users:
                print(all_users)
                response = RESPONSE_400
                response[ERROR] = f'Пользователь {message[DESTINATION]} офлайн. Напишите позже.'
                self.send_message(client, response)
            else:
                response = RESPONSE_400
                response[ERROR] = 'Пользователь не зарегистрирован на сервере.'
                try:
                    self.send_message(client, response)
                except OSError:
                    pass
            return
            # Если клиент выходит
        elif ACTION in message \
                and message[ACTION] == EXIT \
                and ACCOUNT_NAME in message \
                and self.clients_names[message[ACCOUNT_NAME]] == client:
            self.remove_client(client)
            SERVER_LOGGER.info(
                f'Пользователь {message[ACCOUNT_NAME]} отключился.')
        # Если это запрос контакт-листа
        elif ACTION in message \
                and message[ACTION] == GET_CONTACTS \
                and USER in message \
                and self.clients_names[message[USER]] == client:
            response = RESPONSE_202
            response[LIST_INFO] = self.database.get_contacts(message[USER])
            try:
                self.send_message(client, response)
            except OSError:
                self.remove_client(client)
        elif ACTION in message \
                and message[ACTION] == ADD_CONTACT \
                and ACCOUNT_NAME in message \
                and USER in message \
                and self.clients_names[message[USER]] == client:
            self.database.add_contact(message[USER], message[ACCOUNT_NAME])
            try:
                self.send_message(client, RESPONSE_200)
            except OSError:
                self.remove_client(client)
            # Если это удаление контакта
        elif ACTION in message \
                and message[ACTION] == REMOVE_CONTACT \
                and ACCOUNT_NAME in message \
                and USER in message \
                and self.clients_names[message[USER]] == client:
            self.database.remove_contact(message[USER], message[ACCOUNT_NAME])
            try:
                self.send_message(client, RESPONSE_200)
            except OSError:
                self.remove_client(client)
        # Если это запрос известных пользователей
        elif ACTION in message \
                and message[ACTION] == USERS_REQUEST \
                and ACCOUNT_NAME in message \
                and self.clients_names[message[ACCOUNT_NAME]] == client:
            response = RESPONSE_202
            response[LIST_INFO] = [user[0]
                                   for user in self.database.users_list()]
            try:
                self.send_message(client, response)
            except OSError:
                self.remove_client(client)
                # Если это запрос публичного ключа пользователя
        elif ACTION in message \
                and message[ACTION] == PUBLIC_KEY_REQUEST \
                and ACCOUNT_NAME in message:
            response = RESPONSE_511
            response[DATA] = self.database.get_pubkey(message[ACCOUNT_NAME])
            # может быть, что ключа ещё нет (пользователь никогда не логинился,
            # тогда шлём 400)
            if response[DATA]:
                try:
                    self.send_message(client, response)
                except OSError:
                    self.remove_client(client)
            else:
                response = RESPONSE_400
                response[ERROR] = 'Нет публичного ключа для данного пользователя'
                try:
                    self.send_message(client, response)
                except OSError:
                    self.remove_client(client)

        else:
            response = RESPONSE_400
            response[ERROR] = 'Запрос некорректен.'
            self.send_message(client, response)
            return

    def send_message(self, socket, message):
        """
        Функция приёма сообщений от удалённых компьютеров.
        Принимает сообщения JSON, декодирует полученное сообщение
        и проверяет что получен словарь.
        :param client: сокет для передачи данных.
        :return: словарь - сообщение.
        """
        js_message = json.dumps(message)
        encoded_message = js_message.encode(ENCODING)
        socket.send(encoded_message)

    def autorize_user(self, message, sock):
        """Метод реализующий авторизцию пользователей."""
        # Если имя пользователя уже занято то возвращаем 400
        SERVER_LOGGER.debug(f'Start auth process for {message[USER]}')
        if message[USER][ACCOUNT_NAME] in self.clients_names.keys():
            response = RESPONSE_400
            response[ERROR] = 'Имя пользователя уже занято.'
            try:
                SERVER_LOGGER.debug(f'Username busy, sending {response}')
                self.send_message(sock, response)
            except OSError:
                SERVER_LOGGER.debug('OS Error')
                pass
            self.clients.remove(sock)
            sock.close()
        # Проверяем что пользователь зарегистрирован на сервере.
        elif not self.database.check_user(message[USER][ACCOUNT_NAME]):
            response = RESPONSE_400
            response[ERROR] = 'Пользователь не зарегистрирован.'
            try:
                SERVER_LOGGER.debug(f'Unknown username, sending {response}')
                self.send_message(sock, response)
            except OSError:
                pass
            self.clients.remove(sock)
            sock.close()
        else:
            SERVER_LOGGER.debug('Correct username, starting passwd check.')
            # Иначе отвечаем 511 и проводим процедуру авторизации
            # Словарь - заготовка
            message_auth = RESPONSE_511
            # Набор байтов в hex представлении
            random_str = binascii.hexlify(os.urandom(64))
            # В словарь байты нельзя, декодируем (json.dumps -> TypeError)
            message_auth[DATA] = random_str.decode('ascii')
            # Создаём хэш пароля и связки с рандомной строкой, сохраняем
            # серверную версию ключа
            hash = hmac.new(
                self.database.get_hash(
                    message[USER][ACCOUNT_NAME]),
                random_str,
                'MD5')
            digest = hash.digest()
            SERVER_LOGGER.debug(f'Auth message = {message_auth}')
            try:
                # Обмен с клиентом
                self.send_message(sock, message_auth)
                ans = self.get_message(sock)
            except OSError as err:
                SERVER_LOGGER.debug('Error in auth, data:', exc_info=err)
                self.clients.remove(sock)
                sock.close()
                return
            client_digest = binascii.a2b_base64(ans[DATA])
            # Если ответ клиента корректный, то сохраняем его в список
            # пользователей.
            if RESPONSE in ans and ans[RESPONSE] == 511 and hmac.compare_digest(
                    digest, client_digest):
                self.clients_names[message[USER][ACCOUNT_NAME]] = sock
                client_ip, client_port = sock.getpeername()
                try:
                    self.send_message(sock, RESPONSE_200)
                except OSError:
                    self.remove_client(message[USER][ACCOUNT_NAME])
                # добавляем пользователя в список активных и если у него изменился открытый ключ
                # сохраняем новый
                self.database.user_login(
                    message[USER][ACCOUNT_NAME],
                    client_ip,
                    client_port,
                    message[USER][PUBLIC_KEY])
            else:
                response = RESPONSE_400
                response[ERROR] = 'Неверный пароль.'
                try:
                    self.send_message(sock, response)
                except OSError:
                    pass
                self.clients.remove(sock)
                sock.close()

    def service_update_lists(self):
        """Метод реализующий отправки сервисного сообщения 205 клиентам."""
        for client in self.clients_names:
            try:
                self.send_message(self.clients_names[client], RESPONSE_205)
            except OSError:
                self.remove_client(self.clients_names[client])
