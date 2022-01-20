import json
import socket
import sys
import time

from common.variables import ACTION, ACCOUNT_NAME, RESPONSE, MAX_CONNECTIONS, \
    PRESENCE, TIME, USER, ERROR, DEFAULT_PORT, MAX_PACKAGE_LENGTH, ENCODING, DEFAULT_IP_ADDRESS


class MessengerCore:

    def __init__(self, start_server=False, start_client=False):
        # self.listen_port = None
        # self.listen_address = None
        # self.transport = None
        # self.message_from_client = None
        # self.server_response = None
        if start_server:
            self.check_port_server()
            self.check_address_server()
            self.init_socket_server()
        elif start_client:
            self.check_port_address_client()
            self.init_socket_client()

    def check_port_server(self):
        try:
            if '-p' in sys.argv:
                self.listen_port = int(sys.argv[sys.argv.index('-p') + 1])
            else:
                self.listen_port = DEFAULT_PORT
            if self.listen_port < 1024 or self.listen_port > 65535:
                raise ValueError
        except IndexError:
            print('После параметра -\'p\' необходимо указать номер порта.')
            sys.exit(1)
        except ValueError:
            print(
                'В качастве порта может быть указано только число в диапазоне от 1024 до 65535.')
            sys.exit(1)
        else:
            print(f'Задан порт сервера номер: {self.listen_port}')

    def check_address_server(self):
        try:
            if '-a' in sys.argv:
                self.listen_address = sys.argv[sys.argv.index('-a') + 1]
            else:
                self.listen_address = ''

        except IndexError:
            print(
                'После параметра \'a\'- необходимо указать адрес, который будет слушать сервер.')
            sys.exit(1)
        else:
            if self.listen_address == '':
                print(f'Задан сетевой адрес сервера: 0.0.0.0')
            else:
                print(f'Задан сетевой адрес сервера: {self.listen_address}')

    def init_socket_server(self):
        self.transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.transport.bind((self.listen_address, self.listen_port))

    def start_server_listen(self):
        self.transport.listen(MAX_CONNECTIONS)
        print('Сервер запущен...')
        while True:
            client, client_address = self.transport.accept()
            try:
                self.message_from_client = self.get_message(client)

                print(f"Авторизация нового пользователя: {self.message_from_client['user']['account_name']}\n",
                      self.message_from_client)
                # {'action': 'presence', 'time': 1573760672.167031, 'user': {'account_name': 'Guest'}}
                self.server_response = self.process_client_message()
                self.message = self.server_response
                self.send_message(client)
                client.close()
            except (ValueError, json.JSONDecodeError):
                print('Принято некорретное сообщение от клиента.')
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
            self.server_address = sys.argv[1]
            self.server_port = int(sys.argv[2])
            if self.server_port < 1024 or self.server_port > 65535:
                raise ValueError
        except IndexError:
            self.server_address = DEFAULT_IP_ADDRESS
            self.server_port = DEFAULT_PORT
        except ValueError:
            print('В качестве порта может быть указано только число в диапазоне от 1024 до 65535.')
            sys.exit(1)

    def init_socket_client(self):
        self.transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.transport.connect((self.server_address, self.server_port))

    def start_client_send(self):
        message_to_server = self.create_presence()
        self.message = message_to_server
        self.send_message(self.transport)
        print('Отправка запроса авторизации...')
        try:
            self.message_from_server = self.get_message(self.transport)
            answer = self.process_ans()
            print(answer)
        except (ValueError, json.JSONDecodeError):
            print('Не удалось декодировать сообщение сервера.')

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
        return out

    def process_ans(self):
        '''
        Функция разбирает ответ сервера
        :param message:
        :return:
        '''
        if RESPONSE in self.message_from_server:
            if self.message_from_server[RESPONSE] == 200:
                return 'Успешная авторизация... \n200 : OK'
            return f'Ошибка 400 : {self.message_from_server[ERROR]}'
        raise ValueError



