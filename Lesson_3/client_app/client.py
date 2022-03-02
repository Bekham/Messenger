import logging
import logs.config_client_log
import argparse
import configparser
import os
import sys
from PyQt5.QtWidgets import QApplication

from common.variables import *
from common.errors import ServerError
from common.decos import log
from client.database import ClientDatabase
from common.client_core import ClientTransport, arg_parser
from client.client_contacts import ClientMainWindow
from client.start_dialog import UserNameDialog

# Инициализация клиентского логера
logger = logging.getLogger('client')

# Парсер аргументов коммандной строки


# Основная функция клиента
if __name__ == '__main__':
    # Загружаем параметы коммандной строки
    config = configparser.ConfigParser()
    dir_path = os.path.dirname(os.path.realpath(__file__))
    config.read(f"{dir_path}/{'client.ini'}")
    server_address, server_port, client_name = arg_parser(
        config['SETTINGS']['Listen_Address'],
        config['SETTINGS']['Default_port'],
        config['SETTINGS']['Client_Name']
    )
    # Создаём клиентское приложение
    client_app = QApplication(sys.argv)

    # Если имя пользователя не было указано в командной строке то запросим его
    if not client_name:
        start_dialog = UserNameDialog()
        client_app.exec_()
        # Если пользователь ввёл имя и нажал ОК, то сохраняем ведённое и удаляем объект, инааче выходим
        if start_dialog.ok_pressed:
            client_name = start_dialog.client_name.text()
            del start_dialog
        else:
            exit(0)

    # Записываем логи
    logger.info(
        f'Запущен клиент с парамертами: адрес сервера: {server_address} , порт: {server_port}, имя пользователя: {client_name}')

    # Создаём объект базы данных
    database = ClientDatabase(client_name)

    # Создаём объект - транспорт и запускаем транспортный поток
    try:
        transport = ClientTransport(server_port, server_address, database, client_name)
    except ServerError as error:
        print(error.text)
        exit(1)
    else:
        transport.setDaemon(True)
        transport.start()

        # Создаём GUI
        main_window = ClientMainWindow(database, transport, client_app)
        main_window.make_connection(transport)
        main_window.setWindowTitle(f'GBMessApp - {client_name}')

        client_app.exec_()

        # Раз графическая оболочка закрылась, закрываем транспорт
        transport.transport_shutdown()
        transport.join()
