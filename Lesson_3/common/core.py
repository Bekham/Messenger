import argparse
import json
import select
import socket
import sys
import threading
import time
import logging
from threading import Thread

sys.path.append('../')
from common.decos import Log
from errors import ReqFieldMissingError, IncorrectDataRecivedError, ServerError
from common.variables import DEFAULT_PORT, DEFAULT_IP_ADDRESS, \
    ACTION, TIME, USER, ACCOUNT_NAME, SENDER, PRESENCE, RESPONSE, ERROR, MESSAGE, MESSAGE_TEXT, \
    ENCODING, MAX_CONNECTIONS, MAX_PACKAGE_LENGTH, DESTINATION, EXIT


class MessengerCore:
    @Log()
    def __init__(self, start_server=False, start_client=False):
        self.message = None
        self.listen_port = None
        self.listen_address = None
        self.parser = None
        self.transport = None
        self.messages = []
        self.message_from_client = None
        self.message_from_server = None
        self.clients_names = {}
        self.clients_list = []


        # self.create_arg_parser()
        if start_server:
            self.SERVER_LOGGER = logging.getLogger('server')
            self.arg_parser_server()
            self.init_socket_server()
        elif start_client:
            self.CLIENT_LOGGER = logging.getLogger('client')
            self.arg_parser_client()
            self.init_socket_client()

    def create_arg_parser(self):
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument('-p', default=DEFAULT_PORT, type=int, nargs='?')
        self.parser.add_argument('-a', default='', nargs='?')
        self.parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
        self.parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')

    @Log()
    def arg_parser_server(self):
        try:
            """Парсер аргументов коммандной строки"""
            parser = argparse.ArgumentParser()
            parser.add_argument('-p', default=DEFAULT_PORT, type=int, nargs='?')
            parser.add_argument('-a', default='', nargs='?')
            namespace = parser.parse_args(sys.argv[1:])
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

    @Log()
    def init_socket_server(self):
        self.SERVER_LOGGER.info(
            f'Запущен сервер, порт для подключений: {self.listen_port}, '
            f'адрес с которого принимаются подключения: {self.listen_address}. '
            f'Если адрес не указан, принимаются соединения с любых адресов.')
        self.transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.transport.bind((self.listen_address, self.listen_port))
        except OSError:
            print()
            self.SERVER_LOGGER.info(
                f'Порт для подключений {self.listen_port} занят!'
                f'Производится смена порта на: {self.listen_port + 1}. ')
            self.listen_port += self.listen_port
            try:
                self.transport.bind((self.listen_address, self.listen_port))
            except OSError:
                self.init_socket_server()
        self.transport.settimeout(0.5)

    @Log()
    def start_server_listen(self):
        # список клиентов , очередь сообщений
        self.clients_list = []
        self.messages = []
        # Слушаем порт
        self.transport.listen(MAX_CONNECTIONS)
        self.SERVER_LOGGER.info('Сервер запущен...')
        # Основной цикл программы сервера
        while True:
            try:
                client, client_address = self.transport.accept()
            except OSError:
                pass

            else:
                self.SERVER_LOGGER.info(f'Установлено соедение с ПК {client_address}')
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
                        self.SERVER_LOGGER.info(f'Клиент {client_with_message.getpeername()} '
                                                f'отключился от сервера.')
                        self.clients_list.remove(client_with_message)
            if self.messages and send_data_lst:
                for i in self.messages:
                    try:
                        self.message = i
                        self.process_message(send_data_lst)
                    except Exception:
                        self.SERVER_LOGGER.info(f'Связь с клиентом с именем {i[DESTINATION]} была потеряна')
                        self.clients_list.remove(self.clients_names[i[DESTINATION]])
                        del self.clients_names[i[DESTINATION]]
                self.messages.clear()
                # self.message = {
                #     ACTION: MESSAGE,
                #     SENDER: self.messages[0][0],
                #     TIME: time.time(),
                #     MESSAGE_TEXT: self.messages[0][1]
                # }
                # del self.messages[0]
                # for waiting_client in send_data_lst:
                #     try:
                #         self.send_message(waiting_client)
                #     except:
                #         self.SERVER_LOGGER.info(f'Клиент {waiting_client.getpeername()} отключился от сервера.')
                #         self.clients_list.remove(waiting_client)

    @Log()
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
            self.SERVER_LOGGER.info(f'Отправлено сообщение пользователю {self.message[DESTINATION]} '
                        f'от пользователя {self.message[SENDER]}.')
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
                    self.SERVER_LOGGER.info(f'Клиент {waiting_client.getpeername()} отключился от сервера.')
                    self.clients_list.remove(waiting_client)
            return
        else:
            self.SERVER_LOGGER.error(
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

    @Log()
    def process_client_message(self, client_with_message):
        '''
        Обработчик сообщений от клиентов, принимает словарь -
        сообщение от клиtнта, проверяет корректность,
        возвращает словарь-ответ для клиента
        :param client:
        :return:
        '''
        self.SERVER_LOGGER.debug(f'Разбор сообщения от клиента : {self.message_from_client}')
        if ACTION in self.message_from_client \
                and self.message_from_client[ACTION] == PRESENCE \
                and TIME in self.message_from_client \
                and USER in self.message_from_client \
                and len(self.message_from_client[USER][ACCOUNT_NAME]) > 0:
            if self.message_from_client[USER][ACCOUNT_NAME] not in self.clients_names.keys():
                self.clients_names[self.message_from_client[USER][ACCOUNT_NAME]] = client_with_message
                self.message = {RESPONSE: 200}
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
            self.clients_list.remove(self.clients_names[self.message_from_client[ACCOUNT_NAME]])
            self.clients_names[self.message_from_client[ACCOUNT_NAME]].close()
            del self.clients_names[self.message_from_client[ACCOUNT_NAME]]
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

    @Log()
    def arg_parser_client(self):
        '''Загружаем параметы коммандной строки'''
        # client_1.py 192.168.1.2 8079
        parser = argparse.ArgumentParser()
        parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
        parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
        parser.add_argument('-m', '--mode', default='chat', nargs='?')
        namespace = parser.parse_args(sys.argv[1:])
        self.server_address = namespace.addr
        self.server_port = namespace.port
        self.client_mode = namespace.mode

        # проверим подходящий номер порта
        if not 1023 < self.server_port < 65536:
            self.CLIENT_LOGGER.critical(
                f'Попытка запуска клиента с неподходящим номером порта: {self.server_port}. '
                f'Допустимы адреса с 1024 до 65535. Клиент завершается.')
            sys.exit(1)

        # Проверим допустим ли выбранный режим работы клиента
        if self.client_mode not in ('listen', 'send', 'chat'):
            self.CLIENT_LOGGER.critical(f'Указан недопустимый режим работы {self.client_mode}, '
                                        f'допустимые режимы: listen , send, chat')
            sys.exit(1)
        return self.server_address, self.server_port, self.client_mode

    @Log()
    def init_socket_client(self):
        try:
            self.transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.transport.connect((self.server_address, self.server_port))
            self.CLIENT_LOGGER.info(
                f'Запущен клиент с парамертами: адрес сервера: {self.server_address}, '
                f'порт: {self.server_port}, режим работы: {self.client_mode}')
        except ConnectionRefusedError:
            self.CLIENT_LOGGER.critical(f'Не удалось подключиться к серверу {self.server_address}:{self.server_port}, '
                                        f'конечный компьютер отверг запрос на подключение.')
            sys.exit(1)

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
            self.CLIENT_LOGGER.info('Отправка запроса авторизации...')
            self.auth_message_from_server = self.get_message(self.transport)
            answer = self.process_ans()
            self.CLIENT_LOGGER.info(f'Принят ответ от сервера {answer}')
            print(f'Установлено соединение с сервером.')
        except (ValueError, json.JSONDecodeError):
            self.CLIENT_LOGGER.error('Не удалось декодировать полученную Json строку.')
        except ServerError as error:
            self.CLIENT_LOGGER.error(f'При установке соединения сервер вернул ошибку: {error.text}')
            sys.exit(1)
        except ReqFieldMissingError as missing_error:
            self.CLIENT_LOGGER.error(f'В ответе сервера отсутствует необходимое поле '
                                     f'{missing_error.missing_field}')
            sys.exit(1)
        except (ConnectionRefusedError, ConnectionError):
            self.CLIENT_LOGGER.critical (f'Не удалось подключиться к серверу {self.server_address}:{self.server_port}, '
            f'конечный компьютер отверг запрос на подключение.')
            sys.exit(1)
        else:
            # Если соединение с сервером установлено корректно,
            # начинаем обмен с ним, согласно требуемому режиму.
            # основной цикл прогрммы:

            if self.client_mode == 'send':
                self.CLIENT_LOGGER.info('Режим работы - отправка сообщений.')
                print('Режим работы - отправка сообщений.')
                while True:
                    # режим работы - отправка сообщений
                    if self.client_mode == 'send':
                        try:
                            self.message = self.create_message()
                            self.send_message(self.transport)
                        except (ConnectionResetError, ConnectionError, ConnectionAbortedError):
                            self.CLIENT_LOGGER.error(f'Соединение с сервером {self.server_address} было потеряно.')
                            sys.exit(1)
            elif self.client_mode == 'listen':
                self.CLIENT_LOGGER.info('Режим работы - приём сообщений.')
                print('Режим работы - приём сообщений.')
                while True:
                    # Режим работы приём:
                    if self.client_mode == 'listen':
                        try:
                            self.message_from_server = self.get_message(self.transport)
                            self.read_message_from_server()
                        except (ConnectionResetError, ConnectionError, ConnectionAbortedError):
                            self.CLIENT_LOGGER.error(f'Соединение с сервером {self.server_address} было потеряно.')
                            sys.exit(1)

            else:
                self.CLIENT_LOGGER.info('Режим работы - чат.')
                # Если соединение с сервером установлено корректно,
                # запускаем клиенский процесс приёма сообщний
                receiver = threading.Thread(target=self.message_from_server_chat_mode, args=())
                receiver.daemon = True
                receiver.start()

                # затем запускаем отправку сообщений и взаимодействие с пользователем.
                user_interface = threading.Thread(target=self.user_interactive, args=())
                user_interface.daemon = True
                user_interface.start()
                self.CLIENT_LOGGER.debug('Запущены процессы')

                # Watchdog основной цикл, если один из потоков завершён,
                # то значит или потеряно соединение или пользователь
                # ввёл exit. Поскольку все события обработываются в потоках,
                # достаточно просто завершить цикл.
                while True:
                    time.sleep(1)
                    if receiver.is_alive() and user_interface.is_alive():
                        continue
                    break


    @Log()
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
        self.CLIENT_LOGGER.debug(f'Сформировано {PRESENCE} сообщение для пользователя {account_name}')
        return out

    @Log()
    def process_ans(self):
        '''
        Функция разбирает ответ сервера
        :param message:
        :return:
        '''
        self.CLIENT_LOGGER.debug(f'Разбор сообщения от сервера: {self.auth_message_from_server}')
        try:
            if RESPONSE in self.auth_message_from_server:
                if self.auth_message_from_server[RESPONSE] == 200:
                    return 'Успешная авторизация... 200 : OK'
                elif self.auth_message_from_server[RESPONSE] == 400:
                    raise ServerError(f'400 : {self.auth_message_from_server[ERROR]}')

            raise ReqFieldMissingError(RESPONSE)
        except TypeError:
            self.CLIENT_LOGGER.critical(
                f'Критическая ошибка! Неверный формат/тип сообщения от сервера: {self.auth_message_from_server}')
            raise TypeError

    @Log()
    def create_message(self, account_name='Guest'):
        """Функция запрашивает текст сообщения и возвращает его.
            Так же завершает работу при вводе подобной комманды
            """
        message = input('Введите сообщение для отправки или \'!!!\' для завершения работы: ')
        if message == '!!!':
            self.transport.close()
            self.CLIENT_LOGGER.info('Завершение работы по команде пользователя.')
            print('Спасибо за использование нашего сервиса!')
            sys.exit(0)
        message_dict = {
            ACTION: MESSAGE,
            TIME: time.time(),
            ACCOUNT_NAME: self.client_name,
            MESSAGE_TEXT: message
        }
        self.CLIENT_LOGGER.debug(f'Сформирован словарь сообщения: {message_dict}')
        return message_dict

    @Log()
    def read_message_from_server(self):
        """Функция - обработчик сообщений других пользователей, поступающих с сервера"""
        if ACTION in self.message_from_server and self.message_from_server[ACTION] == MESSAGE and \
                SENDER in self.message_from_server and MESSAGE_TEXT in self.message_from_server:
            print(f'Получено сообщение от пользователя '
                  f'{self.message_from_server[SENDER]}:\n{self.message_from_server[MESSAGE_TEXT]}')
            self.CLIENT_LOGGER.info(f'Получено сообщение от пользователя '
                                    f'{self.message_from_server[SENDER]}:\n{self.message_from_server[MESSAGE_TEXT]}')
        else:
            self.CLIENT_LOGGER.error(f'Получено некорректное сообщение с сервера: {self.message_from_server}')

    @Log()
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
                    self.CLIENT_LOGGER.info(f'Получено сообщение от пользователя {message[SENDER]}:'
                                f'\n{message[MESSAGE_TEXT]}')
                else:
                    self.CLIENT_LOGGER.error(f'Получено некорректное сообщение с сервера: {message}')
            except IncorrectDataRecivedError:
                self.CLIENT_LOGGER.error(f'Не удалось декодировать полученное сообщение.')
            except (OSError, ConnectionError, ConnectionAbortedError,
                    ConnectionResetError, json.JSONDecodeError):
                self.CLIENT_LOGGER.critical(f'Потеряно соединение с сервером.')
                break

    @Log()
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
                self.CLIENT_LOGGER.info('Завершение работы по команде пользователя.')
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

    @Log()
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
        self.CLIENT_LOGGER.debug(f'Сформирован словарь сообщения: {self.message}')
        try:
            self.send_message(self.transport)
            self.CLIENT_LOGGER.info(f'Отправлено сообщение для пользователя {to_user}')
        except:
            self.CLIENT_LOGGER.critical('Потеряно соединение с сервером.')
            sys.exit(1)
