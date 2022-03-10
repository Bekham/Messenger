import os
import sys
import configparser
from Crypto.PublicKey import RSA
from PyQt5.QtWidgets import QApplication, QMessageBox

from client_app.common_client.variables import *
from client_app.common_client.errors import ServerError
from client_app.common_client.client_core import ClientTransport, arg_parser
from client_app.client.database import ClientDatabase
from client_app.client.client_contacts import ClientMainWindow
from client_app.client.start_dialog import UserNameDialog
import logging
import client_app.logs_client.config_client_log

# Инициализация клиентского логера
logger = logging.getLogger('client')

# Парсер аргументов коммандной строки


# Основная функция клиента
if __name__ == '__main__':
    # Загружаем параметы коммандной строки
    config = configparser.ConfigParser()
    dir_path = os.path.dirname(os.path.realpath(__file__))
    config.read(f"{dir_path}/client_app/{'client.ini'}")
    server_address, server_port, client_name, client_passwd = arg_parser(
        config['SETTINGS']['Listen_Address'],
        config['SETTINGS']['Default_port'],
        config['SETTINGS']['Client_Name'],
        config['SETTINGS']['Client_Password'],
    )

    # Создаём клиентское приложение
    client_app = QApplication(sys.argv)

    # Если имя пользователя не было указано в командной строке, то запросим его
    start_dialog = UserNameDialog()
    if not client_name or not client_passwd:
        client_app.exec_()
        # Если пользователь ввёл имя и нажал ОК, то сохраняем ведённое и
        # удаляем объект, иначе выходим
        if start_dialog.ok_pressed:
            client_name = start_dialog.client_name.text()
            client_passwd = start_dialog.client_passwd.text()
            logger.debug(
                f'Using USERNAME = {client_name}, PASSWD = {client_passwd}.')
        else:
            sys.exit(0)

    # Записываем логи
    logger.info(
        f'Запущен клиент с парамертами: адрес сервера: {server_address} '
        f', порт: {server_port}, имя пользователя: {client_name}')
    # Загружаем ключи с файла, если же файла нет, то генерируем новую пару.
    dir_path = os.path.dirname(os.path.realpath(__file__))
    key_file = os.path.join(dir_path, f'client_app/{client_name}.key')
    if not os.path.exists(key_file):
        keys = RSA.generate(2048, os.urandom)
        with open(key_file, 'wb') as key:
            key.write(keys.export_key())
    else:
        with open(key_file, 'rb') as key:
            keys = RSA.import_key(key.read())

    # !!!keys.publickey().export_key()
    logger.debug("Keys sucsessfully loaded.")
    # Создаём объект базы данных
    database = ClientDatabase(client_name)
    transport = None
    # Создаём объект - транспорт и запускаем транспортный поток
    try:
        transport = ClientTransport(server_port,
                                    server_address,
                                    database,
                                    client_name,
                                    client_passwd,
                                    keys)
        logger.debug("Transport ready.")
    except ServerError as error:
        message = QMessageBox()
        message.critical(start_dialog, 'Ошибка сервера', error.text)
        sys.exit(1)
    transport.setDaemon(True)
    transport.start()
    # Удалим объект диалога за ненадобностью
    del start_dialog

    # Создаём GUI
    main_window = ClientMainWindow(
        database, transport, client_app, client_name, keys)
    main_window.make_connection(transport)
    main_window.setWindowTitle(f'GBMessApp - {client_name}')
    client_app.exec_()

    # Раз графическая оболочка закрылась, закрываем транспорт
    transport.transport_shutdown()
    transport.join()
