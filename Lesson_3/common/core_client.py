import argparse
import json
import socket
import sys
import threading
import time
import logging

from common.meta import ClientMaker

sys.path.append('../')
from common.decos import Log
# from common.decos import log
from errors import ReqFieldMissingError, IncorrectDataRecivedError, ServerError
from common.variables import DEFAULT_PORT, DEFAULT_IP_ADDRESS, \
    ACTION, TIME, USER, ACCOUNT_NAME, SENDER, PRESENCE, RESPONSE, ERROR, MESSAGE, MESSAGE_TEXT, \
    ENCODING, MAX_CONNECTIONS, MAX_PACKAGE_LENGTH, DESTINATION, EXIT

CLIENT_LOGGER = logging.getLogger('client')


# @log
def arg_parser_client():
    '''Загружаем параметы коммандной строки'''
    # client.py 192.168.1.2 8079
    parser = argparse.ArgumentParser()
    parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-m', '--mode', default='chat', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.addr
    server_port = namespace.port
    client_mode = namespace.mode
    return server_address, server_port, client_mode


class MessengerClientCore(metaclass=ClientMaker):

    # @log
    def __init__(self, server_address, server_port, client_mode):
        self.message = None
        # self.transport = None
        self.message_from_server = None
        # self.CLIENT_LOGGER = logging.getLogger('client')
        # self.arg_parser_client()
        self.server_address = server_address
        self.server_port = server_port
        self.client_mode = client_mode
        self.init_socket_client()

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

    def send_message(self, client_socket):
        js_message = json.dumps(self.message)
        encoded_message = js_message.encode(ENCODING)
        client_socket.send(encoded_message)

        # проверим подходящий номер порта
        if not 1023 < self.server_port < 65536:
            CLIENT_LOGGER.critical(
                f'Попытка запуска клиента с неподходящим номером порта: {self.server_port}. '
                f'Допустимы адреса с 1024 до 65535. Клиент завершается.')
            sys.exit(1)

        # Проверим допустим ли выбранный режим работы клиента
        if self.client_mode not in ('send', 'chat'):
            CLIENT_LOGGER.critical(f'Указан недопустимый режим работы {self.client_mode}, '
                                   f'допустимые режимы: send, chat')
            sys.exit(1)
        return self.server_address, self.server_port, self.client_mode

    # @log
    def init_socket_client(self):
        try:
            self.transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.transport.connect((self.server_address, self.server_port))
            CLIENT_LOGGER.info(
                f'Запущен клиент с парамертами: адрес сервера: {self.server_address}, '
                f'порт: {self.server_port}, режим работы: {self.client_mode}')
        except ConnectionRefusedError:
            CLIENT_LOGGER.critical(f'Не удалось подключиться к серверу {self.server_address}:{self.server_port}, '
                                   f'конечный компьютер отверг запрос на подключение.')
            sys.exit(1)

    # @log
    def start_client_send(self):
        self.client_name = input('Авторизуйтесь, пожалуйста! Введите Ваш логин: ')

        if len(self.client_name) > 0:
            message_to_server = self.create_presence(account_name=self.client_name)
            self.message = message_to_server
        else:
            print('Данные введены неверно!')
            self.start_client_send()

        try:
            self.send_message(self.transport)
            CLIENT_LOGGER.info('Отправка запроса авторизации...')
            self.auth_message_from_server = self.get_message(self.transport)
            answer = self.process_ans()
            CLIENT_LOGGER.info(f'Принят ответ от сервера {answer}')
            print(f'Установлено соединение с сервером.')
        except (ValueError, json.JSONDecodeError):
            CLIENT_LOGGER.error('Не удалось декодировать полученную Json строку.')
        except ServerError as error:
            CLIENT_LOGGER.error(f'При установке соединения сервер вернул ошибку: {error.text}')
            sys.exit(1)
        except ReqFieldMissingError as missing_error:
            CLIENT_LOGGER.error(f'В ответе сервера отсутствует необходимое поле '
                                f'{missing_error.missing_field}')
            sys.exit(1)
        except (ConnectionRefusedError, ConnectionError):
            CLIENT_LOGGER.critical(f'Не удалось подключиться к серверу {self.server_address}:{self.server_port}, '
                                   f'конечный компьютер отверг запрос на подключение.')
            sys.exit(1)
        else:
            # Если соединение с сервером установлено корректно,
            # начинаем обмен с ним, согласно требуемому режиму.
            # основной цикл прогрммы:

            if self.client_mode == 'send':
                CLIENT_LOGGER.info('Режим работы - отправка сообщений.')
                print('Режим работы - отправка сообщений.')
                while True:
                    # режим работы - отправка сообщений
                    if self.client_mode == 'send':
                        try:
                            self.message = self.create_message()
                            self.send_message(self.transport)
                        except (ConnectionResetError, ConnectionError, ConnectionAbortedError):
                            CLIENT_LOGGER.error(f'Соединение с сервером {self.server_address} было потеряно.')
                            sys.exit(1)
            # elif self.client_mode == 'listen':
            #     CLIENT_LOGGER.info('Режим работы - приём сообщений.')
            #     print('Режим работы - приём сообщений.')
            #     while True:
            #         # Режим работы приём:
            #         if self.client_mode == 'listen':
            #             try:
            #                 self.message_from_server = self.get_message(self.transport)
            #                 self.read_message_from_server()
            #             except (ConnectionResetError, ConnectionError, ConnectionAbortedError):
            #                 CLIENT_LOGGER.error(f'Соединение с сервером {self.server_address} было потеряно.')
            #                 sys.exit(1)

            else:
                CLIENT_LOGGER.info('Режим работы - чат.')
                # Если соединение с сервером установлено корректно,
                # запускаем клиенский процесс приёма сообщний
                receiver = threading.Thread(target=self.message_from_server_chat_mode, args=())
                receiver.daemon = True
                receiver.start()

                # затем запускаем отправку сообщений и взаимодействие с пользователем.
                user_interface = threading.Thread(target=self.user_interactive, args=())
                user_interface.daemon = True
                user_interface.start()
                CLIENT_LOGGER.debug('Запущены процессы')

                # Watchdog основной цикл, если один из потоков завершён,
                # то значит или потеряно соединение или пользователь
                # ввёл exit. Поскольку все события обработываются в потоках,
                # достаточно просто завершить цикл.
                while True:
                    time.sleep(1)
                    if receiver.is_alive() and user_interface.is_alive():
                        continue
                    break

    # @log
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
                ACCOUNT_NAME: self.client_name
            }
        }
        CLIENT_LOGGER.debug(f'Сформировано {PRESENCE} сообщение для пользователя {account_name}')
        return out

    # @log
    def process_ans(self):
        '''
        Функция разбирает ответ сервера
        :param message:
        :return:
        '''
        CLIENT_LOGGER.debug(f'Разбор сообщения от сервера: {self.auth_message_from_server}')
        try:
            if RESPONSE in self.auth_message_from_server:
                if self.auth_message_from_server[RESPONSE] == 200:
                    return 'Успешная авторизация... 200 : OK'
                elif self.auth_message_from_server[RESPONSE] == 400:
                    raise ServerError(f'400 : {self.auth_message_from_server[ERROR]}')

            raise ReqFieldMissingError(RESPONSE)
        except TypeError:
            CLIENT_LOGGER.critical(
                f'Критическая ошибка! Неверный формат/тип сообщения от сервера: {self.auth_message_from_server}')
            raise TypeError

    # @log
    def create_message(self, account_name='Guest'):
        """Функция запрашивает текст сообщения и возвращает его.
            Так же завершает работу при вводе подобной комманды
            """
        message = input('Введите сообщение для отправки или \'!!!\' для завершения работы: ')
        if message == '!!!':
            self.transport.close()
            CLIENT_LOGGER.info('Завершение работы по команде пользователя.')
            print('Спасибо за использование нашего сервиса!')
            sys.exit(0)
        message_dict = {
            ACTION: MESSAGE,
            TIME: time.time(),
            ACCOUNT_NAME: self.client_name,
            MESSAGE_TEXT: message
        }
        CLIENT_LOGGER.debug(f'Сформирован словарь сообщения: {message_dict}')
        return message_dict

    # @log
    def read_message_from_server(self):
        """Функция - обработчик сообщений других пользователей, поступающих с сервера"""
        if ACTION in self.message_from_server and self.message_from_server[ACTION] == MESSAGE and \
                SENDER in self.message_from_server and MESSAGE_TEXT in self.message_from_server:
            print(f'Получено сообщение от пользователя '
                  f'{self.message_from_server[SENDER]}:\n{self.message_from_server[MESSAGE_TEXT]}')
            CLIENT_LOGGER.info(f'Получено сообщение от пользователя '
                               f'{self.message_from_server[SENDER]}:\n{self.message_from_server[MESSAGE_TEXT]}')
        else:
            CLIENT_LOGGER.error(f'Получено некорректное сообщение с сервера: {self.message_from_server}')

    # @log
    def message_from_server_chat_mode(self):
        """Функция - обработчик сообщений других пользователей, поступающих с сервера"""
        while True:
            try:
                message = self.get_message(self.transport)
                if ACTION in message and message[ACTION] == MESSAGE and \
                        SENDER in message and DESTINATION in message \
                        and MESSAGE_TEXT in message and message[DESTINATION] == self.client_name:
                    print(f'\n{message[SENDER]}: '
                          f'{message[MESSAGE_TEXT]}')
                    print(f'{self.client_name}: ', end='')
                    CLIENT_LOGGER.info(f'Получено сообщение от пользователя {message[SENDER]}:'
                                       f'\n{message[MESSAGE_TEXT]}')
                else:
                    CLIENT_LOGGER.error(f'Получено некорректное сообщение с сервера: {message}')
            except IncorrectDataRecivedError:
                CLIENT_LOGGER.error(f'Не удалось декодировать полученное сообщение.')
            except (OSError, ConnectionError, ConnectionAbortedError,
                    ConnectionResetError, json.JSONDecodeError):
                CLIENT_LOGGER.critical(f'Потеряно соединение с сервером.')
                break

    # @log
    def user_interactive(self):
        """Функция взаимодействия с пользователем, запрашивает команды, отправляет сообщения"""
        self.print_help()
        while True:
            command = input(f'{self.client_name}: ')
            if command.startswith('/help'.lower()):
                self.print_help()
            elif command.startswith('/exit'.lower()):
                self.message = self.create_exit_message()
                self.send_message(self.transport)
                print('Завершение соединения.')
                CLIENT_LOGGER.info('Завершение работы по команде пользователя.')
                # Задержка неоходима, чтобы успело уйти сообщение о выходе
                time.sleep(0.5)
                break
            elif len(command.split(' ')) >= 2:
                msg_to_user = ' '.join(command.split(' ')[1:])
                to_user = command.split(' ')[0]
                self.create_chat_message(to_user=to_user, msg_to_user=msg_to_user)
            else:
                print('Команда не распознана, попробойте снова. /help - вывести поддерживаемые команды.')

    def print_help(self):
        """Функция выводящяя справку по использованию"""
        print('Поддерживаемые команды:')
        print('[Имя получателя] [Текст сообщения] - отправить сообщение')
        print('/help - вывести подсказки по командам')
        print('/exit - выход из программы')

    def create_exit_message(self):
        return {
            ACTION: EXIT,
            TIME: time.time(),
            ACCOUNT_NAME: self.client_name
        }

    # @log
    def create_chat_message(self, to_user, msg_to_user):
        """
        Функция запрашивает кому отправить сообщение и само сообщение,
        и отправляет полученные данные на сервер
        :param sock:
        :param account_name:
        :return:
        """
        self.message = {
            ACTION: MESSAGE,
            SENDER: self.client_name,
            DESTINATION: to_user,
            TIME: time.time(),
            MESSAGE_TEXT: msg_to_user
        }
        CLIENT_LOGGER.debug(f'Сформирован словарь сообщения: {self.message}')
        try:
            self.send_message(self.transport)
            CLIENT_LOGGER.info(f'Отправлено сообщение для пользователя {to_user}')
        except Exception:
            CLIENT_LOGGER.critical('Потеряно соединение с сервером.')
            sys.exit(1)
