import argparse
import json
import socket
import sys
import time
import logging

sys.path.append('../')
import logs.config_client_log
import logs.config_server_log
from errors import ReqFieldMissingError, IncorrectDataRecivedError
from common.variables import ACTION, ACCOUNT_NAME, RESPONSE, MAX_CONNECTIONS, \
    PRESENCE, TIME, USER, ERROR, DEFAULT_PORT, MAX_PACKAGE_LENGTH, ENCODING, DEFAULT_IP_ADDRESS


class MessengerCore:

    def __init__(self, start_server=False, start_client=False):

        self.create_arg_parser()
        if start_server:
            self.SERVER_LOGGER = logging.getLogger('server')
            self.check_address_port_server()
            self.init_socket_server()
        elif start_client:
            self.CLIENT_LOGGER = logging.getLogger('client')
            self.check_port_address_client()
            self.init_socket_client()

    def create_arg_parser(self):
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument('-p', default=DEFAULT_PORT, type=int, nargs='?')
        self.parser.add_argument('-a', default='', nargs='?')
        self.parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
        self.parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')


    def check_address_port_server(self):
        try:
            namespace = self.parser.parse_args(sys.argv[1:])
            self.listen_address = namespace.a
            self.listen_port = namespace.p
            if self.listen_port < 1024 or self.listen_port > 65535:
                raise ValueError
        except ValueError:
            self.SERVER_LOGGER.critical(f'Попытка запуска сервера с указанием неподходящего порта '
                               f'{self.listen_port}. Допустимы адреса с 1024 до 65535.')
            sys.exit(1)
        else:
            self.SERVER_LOGGER.info(f'Запущен сервер, порт для подключений: {self.listen_port}, '
                               f'адрес с которого принимаются подключения: {self.listen_address}. '
                               f'Если адрес не указан, принимаются соединения с любых адресов.')

    def init_socket_server(self):
        self.transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.transport.bind((self.listen_address, self.listen_port))

    def start_server_listen(self):
        self.transport.listen(MAX_CONNECTIONS)
        self.SERVER_LOGGER.info('Сервер запущен...')
        while True:
            client, client_address = self.transport.accept()
            self.SERVER_LOGGER.info(f'Установлено соедение с ПК {client_address}')
            try:
                self.message_from_client = self.get_message(client)
                self.SERVER_LOGGER.debug(f'Получено сообщение {self.message_from_client}')
                # {'action': 'presence', 'time': 1573760672.167031, 'user': {'account_name': 'Guest'}}
                self.server_response = self.process_client_message()
                self.SERVER_LOGGER.info(f'Cформирован ответ клиенту {self.server_response}')
                self.message = self.server_response
                self.send_message(client)
                self.SERVER_LOGGER.debug(f'Соединение с клиентом {client_address} закрывается.')
                client.close()
            except json.JSONDecodeError:
                self.SERVER_LOGGER.error(f'Не удалось декодировать JSON строку, полученную от '
                                    f'клиента {client_address}. Соединение закрывается.')
                client.close()
            except IncorrectDataRecivedError:
                self.SERVER_LOGGER.error(f'От клиента {client_address} приняты некорректные данные. '
                                    f'Соединение закрывается.')
                client.close()

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

    def process_client_message(self):
        '''
            Обработчик сообщений от клиентов, принимает словарь -
            сообщение от клиtнта, проверяет корректность,
            возвращает словарь-ответ для клиента

            :param message:
            :return:
            '''
        self.SERVER_LOGGER.debug(f'Разбор сообщения от клиента : {self.message_from_client}')
        if ACTION in self.message_from_client \
                and self.message_from_client[ACTION] == PRESENCE \
                and TIME in self.message_from_client \
                and USER in self.message_from_client \
                and self.message_from_client[USER][ACCOUNT_NAME] == 'Guest':
            return {RESPONSE: 200}
        return {
            RESPONSE: 400,
            ERROR: 'Bad Request'
        }

    def send_message(self, socket):
        js_message = json.dumps(self.message)
        encoded_message = js_message.encode(ENCODING)
        socket.send(encoded_message)

    def check_port_address_client(self):
        '''Загружаем параметы коммандной строки'''
        # client.py 192.168.1.2 8079
        try:
            namespace = self.parser.parse_args(sys.argv[1:])
            self.server_address = namespace.addr
            self.server_port = namespace.port
            if self.server_port < 1024 or self.server_port > 65535:
                raise ValueError
        # except IndexError:
        #     self.server_address = DEFAULT_IP_ADDRESS
        #     self.server_port = DEFAULT_PORT
        except ValueError:
            self.CLIENT_LOGGER.critical(
                f'Попытка запуска клиента с неподходящим номером порта: {self.server_port}.'
                f' Допустимы адреса с 1024 до 65535. Клиент завершается.')
            sys.exit(1)

    def init_socket_client(self):
        self.transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.transport.connect((self.server_address, self.server_port))

    def start_client_send(self):
        message_to_server = self.create_presence()
        self.message = message_to_server
        try:
            self.send_message(self.transport)
            self.CLIENT_LOGGER.info('Отправка запроса авторизации...')
            self.message_from_server = self.get_message(self.transport)
            answer = self.process_ans()
            self.CLIENT_LOGGER.info(f'Принят ответ от сервера {answer}')
            # print(answer)
        except (ValueError, json.JSONDecodeError):
            self.CLIENT_LOGGER.error('Не удалось декодировать полученную Json строку.')
        except ReqFieldMissingError as missing_error:
            self.CLIENT_LOGGER.error(f'В ответе сервера отсутствует необходимое поле '
                                f'{missing_error.missing_field}')
        except ConnectionRefusedError:
            self.CLIENT_LOGGER.critical(f'Не удалось подключиться к серверу {self.server_address}:{self.server_port}, '
                                   f'конечный компьютер отверг запрос на подключение.')

    def create_presence(self, account_name='Guest'):
        '''
            Функция генерирует запрос о присутствии клиента
            :param account_name:
            :return:
            '''
        # {'action': 'presence', 'time': 1573760672.167031, 'user': {'account_name': 'Guest'}}
        out = {
            ACTION: PRESENCE,
            TIME: time.time(),
            USER: {
                ACCOUNT_NAME: account_name
            }
        }
        self.CLIENT_LOGGER.debug(f'Сформировано {PRESENCE} сообщение для пользователя {account_name}')
        return out

    def process_ans(self):
        '''
        Функция разбирает ответ сервера
        :param message:
        :return:
        '''
        self.CLIENT_LOGGER.debug(f'Разбор сообщения от сервера: {self.message_from_server}')
        try:
            if RESPONSE in self.message_from_server:
                if self.message_from_server[RESPONSE] == 200:
                    return 'Успешная авторизация... 200 : OK'
                return f'Ошибка 400 : {self.message_from_server[ERROR]}'
            raise ReqFieldMissingError(RESPONSE)
        except TypeError:
            self.CLIENT_LOGGER.critical(
                f'Критическая ошибка! Неверный формат/тип сообщения от сервера: {self.message_from_server}')
            raise TypeError
