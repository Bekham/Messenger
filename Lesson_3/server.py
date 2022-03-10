import configparser
import os
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from server_app.common_server.core_server import MessengerServerCore, arg_parser_server
from server_app.common_server.server_database import ServerStorage
from server_app.common_server.variables import DEFAULT_PORT
from server_app.server.main_window import MainWindow


# Загрузка файла конфигурации
def config_load():
    """Парсер конфигурационного ini файла."""
    config = configparser.ConfigParser()
    dir_path = os.path.dirname(os.path.realpath(__file__))
    config.read(f"{dir_path}/server_app/{'server.ini'}")
    # Если конфиг файл загружен правильно, запускаемся, иначе конфиг по
    # умолчанию.
    if 'SETTINGS' in config:
        return config
    else:
        config.add_section('SETTINGS')
        config.set('SETTINGS', 'Default_port', str(DEFAULT_PORT))
        config.set('SETTINGS', 'Listen_Address', '')
        config.set('SETTINGS', 'Database_path', '')
        config.set('SETTINGS', 'Database_file', 'server_database.db3')
        return config


def main():
    """Основная функция запуска серверного модуля"""
    # Загрузка файла конфигурации сервера
    config = config_load()
    listen_address, listen_port, gui_flag = arg_parser_server(
        config['SETTINGS']['Default_port'], config['SETTINGS']['Listen_Address'])
    # Инициализация базы данных
    database = ServerStorage(
        os.path.join(
            config['SETTINGS']['Database_path'],
            config['SETTINGS']['Database_file']))

    # Создание экземпляра класса - сервера и его запуск:
    start_server = MessengerServerCore(listen_address, listen_port, database)
    # new_connection = start_server.new_connection
    start_server.daemon = True
    start_server.start()

    # Если  указан параметр без GUI то запускаем простенький обработчик
    # консольного ввода
    if gui_flag:
        while True:
            command = input('Введите exit для завершения работы сервера.')
            if command == 'exit':
                # Если выход, то завршаем основной цикл сервера.
                start_server.running = False
                start_server.join()
                break
    # Если не указан запуск без GUI, то запускаем GUI:
    else:
        # Создаём графическое окуружение для сервера:
        server_app = QApplication(sys.argv)  # создаем приложение
        server_app.setAttribute(Qt.AA_DisableWindowContextHelpButton)
        main_window = MainWindow(database, start_server, config)
        # ЗАПУСК РАБОТАЕТ ПАРАЛЕЛЬНО СЕРВЕРА(К ОКНУ)
        # ГЛАВНОМ ПОТОКЕ ЗАПУСКАЕМ НАШ GUI - ГРАФИЧЕСКИЙ ИНТЕРФЕС ПОЛЬЗОВАТЕЛЯ

        # Запускаем GUI
        server_app.exec_()

        # По закрытию окон останавливаем обработчик сообщений
        start_server.running = False


if __name__ == '__main__':
    main()
