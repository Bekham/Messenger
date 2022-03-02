import argparse
import json
import socket
import sys
import threading
import time
import logging

from client_database import ClientDatabase
from common.meta import ClientMaker
from common.utils import send_message, get_message

sys.path.append('../')
from common.decos import Log
from common.decos import log
from errors import ReqFieldMissingError, IncorrectDataRecivedError, ServerError
from common.variables import DEFAULT_PORT, DEFAULT_IP_ADDRESS, \
    ACTION, TIME, USER, ACCOUNT_NAME, SENDER, PRESENCE, RESPONSE, ERROR, MESSAGE, MESSAGE_TEXT, \
    ENCODING, MAX_CONNECTIONS, MAX_PACKAGE_LENGTH, DESTINATION, EXIT, USERS_REQUEST, LIST_INFO, GET_CONTACTS, \
    ADD_CONTACT, REMOVE_CONTACT

CLIENT_LOGGER = logging.getLogger('client')

sock_lock = threading.Lock()
database_lock = threading.Lock()


# @log
def arg_parser_client(default_port,
                      default_address):
    '''Загружаем параметы коммандной строки'''
    # client_1.py 192.168.1.2 8079
    parser = argparse.ArgumentParser()
    parser.add_argument('addr', default=default_address, nargs='?')
    parser.add_argument('port', default=default_port, type=int, nargs='?')
    parser.add_argument('-n', '--name', default=None, nargs='?')
    parser.add_argument('-m', '--mode', default='chat', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.addr
    server_port = namespace.port
    client_name = namespace.name
    client_mode = namespace.mode

    return server_address, server_port, client_name, client_mode


class ClientSender(threading.Thread, metaclass=ClientMaker):
    def __init__(self, account_name, sock, database):
        self.account_name = account_name
        self.sock = sock
        self.database = database
        super().__init__()

    # Функция создаёт словарь с сообщением о выходе.
    def create_exit_message(self):
        return {
            ACTION: EXIT,
            TIME: time.time(),
            ACCOUNT_NAME: self.account_name
        }

    # Функция запрашивает кому отправить сообщение и само сообщение, и отправляет полученные данные на сервер.
    def create_message(self, to, message):
        # to = input('Введите получателя сообщения: ')
        # message = input('Введите сообщение для отправки: ')

        # Проверим, что получатель существует
        with database_lock:
            if not self.database.check_user(to):
                print(f'Попытка отправить сообщение незарегистрированому получателю: {to}')
                CLIENT_LOGGER.error(f'Попытка отправить сообщение незарегистрированому получателю: {to}')
                return

        message_dict = {
            ACTION: MESSAGE,
            SENDER: self.account_name,
            DESTINATION: to,
            TIME: time.time(),
            MESSAGE_TEXT: message
        }
        CLIENT_LOGGER.debug(f'Сформирован словарь сообщения: {message_dict}')

        # Сохраняем сообщения для истории
        with database_lock:
            self.database.save_message(self.account_name, to, message)

        # Необходимо дождаться освобождения сокета для отправки сообщения
        with sock_lock:
            try:
                send_message(self.sock, message_dict)
                CLIENT_LOGGER.info(f'Отправлено сообщение для пользователя {to}')
            except OSError as err:
                if err.errno:
                    CLIENT_LOGGER.critical('Потеряно соединение с сервером.')
                    exit(1)
                else:
                    CLIENT_LOGGER.error('Не удалось передать сообщение. Таймаут соединения')

    # Функция взаимодействия с пользователем, запрашивает команды, отправляет сообщения
    def run(self):
        self.print_help()
        while True:
            command = input(f'{self.account_name}: ')
            if command.startswith('/help'.lower()):
                self.print_help()
            elif command.startswith('/exit'.lower()):
                with sock_lock:
                    try:
                        send_message(self.sock, self.create_exit_message())
                    except:
                        pass
                    print('Завершение соединения.')
                    CLIENT_LOGGER.info('Завершение работы по команде пользователя.')
                # Задержка неоходима, чтобы успело уйти сообщение о выходе
                time.sleep(0.5)
                break

            elif command == '/contacts':
                with database_lock:
                    contacts_list = self.database.get_contacts()
                for contact in contacts_list:
                    print(contact)

            # Редактирование контактов
            elif command == '/edit':
                self.edit_contacts()

            # история сообщений.
            elif command == '/history':
                self.print_history()

            elif len(command.split(' ')) >= 2:
                msg_to_user = ' '.join(command.split(' ')[1:])
                to_user = command.split(' ')[0]
                self.create_message(to=to_user, message=msg_to_user)
            else:
                print('Команда не распознана, попробойте снова. /help - вывести поддерживаемые команды.')

    # Функция выводящяя справку по использованию.
    def print_help(self):
        print('Поддерживаемые команды:')
        print('[Имя получателя] [Текст сообщения] - отправить сообщение')
        print('/history - история сообщений')
        print('/contacts - список контактов')
        print('/edit - редактирование списка контактов')
        print('/help - вывести подсказки по командам')
        print('/exit - выход из программы')

    # Функция выводящяя историю сообщений
    def print_history(self):
        ask = input('Показать входящие сообщения - in, исходящие - out, все - просто Enter: ')
        with database_lock:
            if ask == 'in':
                history_list = self.database.get_history(to_who=self.account_name)
                for message in history_list:
                    print(f'\nСообщение от пользователя: {message[0]} от {message[3]}:\n{message[2]}')
            elif ask == 'out':
                history_list = self.database.get_history(from_who=self.account_name)
                for message in history_list:
                    print(f'\nСообщение пользователю: {message[1]} от {message[3]}:\n{message[2]}')
            else:
                history_list = self.database.get_history()
                for message in history_list:
                    print(
                        f'\nСообщение от пользователя: {message[0]}, пользователю {message[1]} от {message[3]}\n{message[2]}')

    # Функция изменеия контактов
    def edit_contacts(self):
        ans = input('Для удаления введите del, для добавления add: ')
        if ans == 'del':
            edit = input('Введите имя удаляемного контакта: ')
            with database_lock:
                if self.database.check_contact(edit):
                    self.database.del_contact(edit)
                else:
                    CLIENT_LOGGER.error('Попытка удаления несуществующего контакта.')
        elif ans == 'add':
            # Проверка на возможность такого контакта
            edit = input('Введите имя создаваемого контакта: ')
            if self.database.check_user(edit):
                with database_lock:
                    self.database.add_contact(edit)
                with sock_lock:
                    try:
                        add_contact(self.sock, self.account_name, edit)
                    except ServerError:
                        CLIENT_LOGGER.error('Не удалось отправить информацию на сервер.')


# Класс-приёмник сообщений с сервера. Принимает сообщения, выводит в консоль , сохраняет в базу.
class ClientReader(threading.Thread, metaclass=ClientMaker):
    def __init__(self, account_name, sock, database):
        self.account_name = account_name
        self.sock = sock
        self.database = database
        super().__init__()

    # Основной цикл приёмника сообщений, принимает сообщения, выводит в консоль. Завершается при потере соединения.
    def run(self):
        while True:
            # Отдыхаем секунду и снова пробуем захватить сокет.
            # если не сделать тут задержку, то второй поток может достаточно долго ждать освобождения сокета.
            time.sleep(1)
            with sock_lock:
                try:
                    message = get_message(self.sock)

                # Принято некорректное сообщение
                except IncorrectDataRecivedError:
                    CLIENT_LOGGER.error(f'Не удалось декодировать полученное сообщение.')
                # Вышел таймаут соединения если errno = None, иначе обрыв соединения.
                except OSError as err:
                    if err.errno:
                        CLIENT_LOGGER.critical(f'Потеряно соединение с сервером.')
                        break
                # Проблемы с соединением
                except (ConnectionError, ConnectionAbortedError, ConnectionResetError, json.JSONDecodeError):
                    CLIENT_LOGGER.critical(f'Потеряно соединение с сервером.')
                    break
                # Если пакет корретно получен выводим в консоль и записываем в базу.
                else:
                    if ACTION in message and message[ACTION] == MESSAGE and SENDER in message and DESTINATION in message \
                            and MESSAGE_TEXT in message and message[DESTINATION] == self.account_name:
                        # print(f'\nПолучено сообщение от пользователя {message[SENDER]}:\n{message[MESSAGE_TEXT]}')
                        print(f'\n{message[SENDER]}: '
                              f'{message[MESSAGE_TEXT]}')
                        print(f'{self.account_name}: ', end='')
                        # Захватываем работу с базой данных и сохраняем в неё сообщение
                        with database_lock:
                            try:
                                self.database.save_message(message[SENDER], self.account_name, message[MESSAGE_TEXT])
                            except:
                                CLIENT_LOGGER.error('Ошибка взаимодействия с базой данных')

                        CLIENT_LOGGER.info(
                            f'Получено сообщение от пользователя {message[SENDER]}:\n{message[MESSAGE_TEXT]}')
                    else:
                        CLIENT_LOGGER.error(f'Получено некорректное сообщение с сервера: {message}')


# Функция добавления пользователя в контакт лист
def add_contact(sock, username, contact):
    CLIENT_LOGGER.debug(f'Создание контакта {contact}')
    req = {
        ACTION: ADD_CONTACT,
        TIME: time.time(),
        USER: username,
        ACCOUNT_NAME: contact
    }
    send_message(sock, req)
    ans = get_message(sock)
    if RESPONSE in ans and ans[RESPONSE] == 200:
        pass
    else:
        raise ServerError('Ошибка создания контакта')
    print('Удачное создание контакта.')


# Функция запроса списка известных пользователей
def user_list_request(sock, username):
    CLIENT_LOGGER.debug(f'Запрос списка известных пользователей {username}')
    req = {
        ACTION: USERS_REQUEST,
        TIME: time.time(),
        ACCOUNT_NAME: username
    }
    send_message(sock, req)
    ans = get_message(sock)
    if RESPONSE in ans and ans[RESPONSE] == 202:
        return ans[LIST_INFO]
    else:
        raise ServerError


# Функция удаления пользователя из контакт листа
def remove_contact(sock, username, contact):
    CLIENT_LOGGER.debug(f'Создание контакта {contact}')
    req = {
        ACTION: REMOVE_CONTACT,
        TIME: time.time(),
        USER: username,
        ACCOUNT_NAME: contact
    }
    send_message(sock, req)
    ans = get_message(sock)
    if RESPONSE in ans and ans[RESPONSE] == 200:
        pass
    else:
        raise ServerError('Ошибка удаления клиента')
    print('Удачное удаление')


class MessengerClientCore:
    @log
    def __init__(self, server_address, server_port, client_name, client_mode):
        self.client_name = client_name
        self.message = None
        # self.transport = None
        self.message_from_server = None
        # self.CLIENT_LOGGER = logging.getLogger('client')
        # self.arg_parser_client()
        self.server_address = server_address
        self.server_port = server_port
        self.client_mode = client_mode
        self.init_socket_client()
        self.database = None

    @log
    def init_socket_client(self):
        try:
            self.transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.transport.settimeout(1)
            self.transport.connect((self.server_address, self.server_port))
            CLIENT_LOGGER.info(
                f'Запущен клиент с парамертами: адрес сервера: {self.server_address}, '
                f'порт: {self.server_port}, режим работы: {self.client_mode}')
        except ConnectionRefusedError:
            CLIENT_LOGGER.critical(f'Не удалось подключиться к серверу {self.server_address}:{self.server_port}, '
                                   f'конечный компьютер отверг запрос на подключение.')
            sys.exit(1)

    @log
    def start_client_send(self):
        if not self.client_name:
            self.client_name = input('Введите имя пользователя: ')
        else:
            print(f'Клиентский модуль запущен с именем: {self.client_name}')
        # self.client_name = input('Авторизуйтесь, пожалуйста! Введите Ваш логин: ')

        if len(self.client_name) > 0:
            message_to_server = self.create_presence(account_name=self.client_name)
            self.message = message_to_server
        else:
            print('Данные введены неверно!')
            self.start_client_send()

        CLIENT_LOGGER.info(
            f'Запущен клиент с парамертами: адрес сервера: {self.server_address} , '
            f'порт: {self.server_port}, имя пользователя: {self.client_name}')

        try:
            send_message(self.transport, self.message)
            CLIENT_LOGGER.info('Отправка запроса авторизации...')
            self.auth_message_from_server = get_message(self.transport)
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
            self.database = ClientDatabase(self.client_name)
            self.database_load()
            CLIENT_LOGGER.info('Режим работы - чат.')
            # Если соединение с сервером установлено корректно,
            # запускаем клиенский процесс приёма сообщний
            # Инициализация БД
            # Если соединение с сервером установлено корректно, запускаем поток взаимодействия с пользователем
            module_sender = ClientSender(self.client_name, self.transport, self.database)
            module_sender.daemon = True
            module_sender.start()

            module_receiver = ClientReader(self.client_name, self.transport, self.database)
            module_receiver.daemon = True
            module_receiver.start()
            CLIENT_LOGGER.debug('Запущены процессы')

            # Watchdog основной цикл, если один из потоков завершён,
            # то значит или потеряно соединение или пользователь
            # ввёл exit. Поскольку все события обработываются в потоках,
            # достаточно просто завершить цикл.
            while True:
                time.sleep(1)
                if module_receiver.is_alive() and module_sender.is_alive():
                    continue
                break

    # Функция инициализатор базы данных. Запускается при запуске, загружает данные в базу с сервера.
    def database_load(self):
        # Загружаем список известных пользователей
        try:
            users_list = self.user_list_request()
            # print(users_list)
        except ServerError:
            CLIENT_LOGGER.error('Ошибка запроса списка известных пользователей.')
        else:
            self.database.add_users(users_list)

        # Загружаем список контактов
        try:
            contacts_list = self.contacts_list_request()
            # print(contacts_list)
        except ServerError:
            CLIENT_LOGGER.error('Ошибка запроса списка контактов.')
        else:
            for contact in contacts_list:
                self.database.add_contact(contact)

    # Функция запроса списка известных пользователей
    def user_list_request(self):
        CLIENT_LOGGER.debug(f'Запрос списка известных пользователей {self.client_name}')
        self.message = {
            ACTION: USERS_REQUEST,
            TIME: time.time(),
            ACCOUNT_NAME: self.client_name
        }
        send_message(self.transport, self.message)
        ans = get_message(self.transport)
        if RESPONSE in ans and ans[RESPONSE] == 202:
            return ans[LIST_INFO]
        else:
            raise ServerError

    def contacts_list_request(self):
        CLIENT_LOGGER.debug(f'Запрос контакт листа для пользователся {self.client_name}')
        self.message = {
            ACTION: GET_CONTACTS,
            TIME: time.time(),
            USER: self.client_name
        }
        CLIENT_LOGGER.debug(f'Сформирован запрос {self.message}')
        send_message(self.transport, self.message)
        ans = get_message(self.transport)
        CLIENT_LOGGER.debug(f'Получен ответ {ans}')
        if RESPONSE in ans and ans[RESPONSE] == 202:
            return ans[LIST_INFO]
        else:
            raise ServerError

    @log
    def create_presence(self, account_name='Guest'):
        '''
            Функция генерирует запрос о присутствии клиента
            :param account_name:
            :return:
            '''
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
