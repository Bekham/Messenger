import base64

from Crypto.Cipher import PKCS1_OAEP
from PyQt5.QtWidgets import QMainWindow, qApp, QMessageBox, QApplication, QListView
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QBrush, QColor
from PyQt5.QtCore import pyqtSlot, QEvent, Qt, QObject
import sys
import json
import logging

from client.client_chat import ClientChatWindow
from common.variables import MESSAGE_TEXT, SENDER

sys.path.append('../')
from client.client_contacts_conv import Ui_MainClientWindow
from client.add_contact import AddContactDialog
from client.del_contact import DelContactDialog
from common.errors import ServerError

logger = logging.getLogger('client')


# Класс основного окна
class ClientMainWindow(QMainWindow, QObject):
    def __init__(self, database, transport, client_app, client_name, keys):
        super().__init__()
        # основные переменные
        self.database = database
        self.transport = transport

        # объект - дешифорвщик сообщений с предзагруженным ключём
        self.decrypter = PKCS1_OAEP.new(keys)

        self.client_app = client_app
        self.client_name = client_name
        # Загружаем конфигурацию окна из дизайнера
        self.ui = Ui_MainClientWindow()
        self.ui.setupUi(self)
        self.chats = {}

        # Кнопка "Выход"
        self.ui.menu_exit.triggered.connect(qApp.exit)

        # # Кнопка отправить сообщение
        # self.ui.btn_send.clicked.connect(self.send_message)

        # "добавить контакт"
        self.ui.btn_add_contact.clicked.connect(self.add_contact_window)
        self.ui.menu_add_contact.triggered.connect(self.add_contact_window)

        # Удалить контакт
        self.ui.btn_remove_contact.clicked.connect(self.delete_contact_window)
        self.ui.menu_del_contact.triggered.connect(self.delete_contact_window)

        # Дополнительные требующиеся атрибуты
        self.contacts_model = None
        # self.history_model = None
        self.messages = QMessageBox()
        self.current_chat = None
        self.current_chat_key = None
        self.encryptor = None
        self.new_msg_alert = []
        # Даблклик по листу контактов отправляется в обработчик
        self.ui.list_contacts.doubleClicked.connect(self.select_active_user)

        self.clients_list_update()
        self.show()

    def closeEvent(self, event):
        self.close_current_chats()
        event.accept()

    def close_current_chats(self):#Г-о код
        if len(self.chats):
            chats_list = []
            for chat in self.chats.keys():
                chats_list.append(self.chats[chat])
            for chat in chats_list:
                chat.close()
        self.close()

    # Функция обработчик даблклика по контакту
    def select_active_user(self):
        # Выбранный пользователем (даблклик) находится в выделеном элементе в QListView
        self.current_chat = self.ui.list_contacts.currentIndex().data()
        self.current_chat = self.current_chat.split('***Новое сообщение***')[0]
        self.start_new_chat()
        # вызываем основную функцию
        # self.set_active_user()

    def start_new_chat(self):
        self.chats[self.current_chat] = ClientChatWindow(self.database,
                                                         self.transport,
                                                         self.current_chat,
                                                         self.client_name)
        # new_chat = ClientChatWindow(self.database, self.transport, self.current_chat)
        if self.current_chat in self.new_msg_alert:
            self.new_msg_alert.remove(self.current_chat)
        self.clients_list_update()
        self.chats[self.current_chat].set_active_user()
        self.chats[self.current_chat].setWindowTitle(f'Чат - {self.current_chat}')
        self.chats[self.current_chat].show()
        self.close_chat_window()

    def close_chat_window(self):
        for chat in self.chats:
            self.chats[chat].close_chat.connect(self.close_chat)

    @pyqtSlot(str)
    def close_chat(self, current_chat):
        del self.chats[current_chat]
        print(self.chats.keys())


    # Функция обновляющяя контакт лист
    def clients_list_update(self):
        contacts_list = self.database.get_contacts()
        self.contacts_model = QStandardItemModel()
        for i in sorted(contacts_list):
            if i in self.new_msg_alert:
                i = f'{i}***Новое сообщение***'
            item = QStandardItem(i)
            item.setEditable(False)
            self.contacts_model.appendRow(item)
        self.ui.list_contacts.setModel(self.contacts_model)

    # Функция добавления контакта
    def add_contact_window(self):
        global select_dialog
        select_dialog = AddContactDialog(self.transport, self.database)
        select_dialog.btn_ok.clicked.connect(lambda: self.add_contact_action(select_dialog))
        select_dialog.show()

    # Функция - обработчик добавления, сообщает серверу, обновляет таблицу и список контактов
    def add_contact_action(self, item):
        new_contact = item.selector.currentText()
        self.add_contact(new_contact)
        item.close()

    # Функция добавляющяя контакт в базы
    def add_contact(self, new_contact):
        try:
            self.transport.add_contact(new_contact)
        except ServerError as err:
            self.messages.critical(self, 'Ошибка сервера', err.text)
        except OSError as err:
            if err.errno:
                self.messages.critical(self, 'Ошибка', 'Потеряно соединение с сервером!')
                self.close()
            self.messages.critical(self, 'Ошибка', 'Таймаут соединения!')
        else:
            self.database.add_contact(new_contact)
            new_contact = QStandardItem(new_contact)
            new_contact.setEditable(False)
            self.contacts_model.appendRow(new_contact)
            logger.info(f'Успешно добавлен контакт {new_contact}')
            self.messages.information(self, 'Успех', 'Контакт успешно добавлен.')

    # Функция удаления контакта
    def delete_contact_window(self):
        global remove_dialog
        remove_dialog = DelContactDialog(self.database)
        remove_dialog.btn_ok.clicked.connect(lambda: self.delete_contact(remove_dialog))
        remove_dialog.show()

    # Функция обработчик удаления контакта, сообщает на сервер, обновляет таблицу контактов
    def delete_contact(self, item):
        selected = item.selector.currentText()
        try:
            self.transport.remove_contact(selected)
        except ServerError as err:
            self.messages.critical(self, 'Ошибка сервера', err.text)
        except OSError as err:
            if err.errno:
                self.messages.critical(self, 'Ошибка', 'Потеряно соединение с сервером!')
                self.close()
            self.messages.critical(self, 'Ошибка', 'Таймаут соединения!')
        else:
            self.database.del_contact(selected)
            self.clients_list_update()
            logger.info(f'Успешно удалён контакт {selected}')
            self.messages.information(self, 'Успех', 'Контакт успешно удалён.')
            item.close()
            # Если удалён активный пользователь, то деактивируем поля ввода.
            if selected == self.current_chat:
                self.current_chat = None
                self.set_disabled_input()

    # Слот приёма нового сообщений
    @pyqtSlot(dict)
    def message(self, message):
        encrypted_message = base64.b64decode(message[MESSAGE_TEXT])
        # Декодируем строку, при ошибке выдаём сообщение и завершаем функцию
        try:
            decrypted_message = self.decrypter.decrypt(encrypted_message)
        except (ValueError, TypeError):
            self.messages.warning(
                self, 'Ошибка', 'Не удалось декодировать сообщение.')
            return
        self.database.save_message(
            message[SENDER],
            'in',
            decrypted_message.decode('utf8'))
        sender_window_active = False
        if len(self.chats):
            for chat in self.chats:
                if message[SENDER] == chat:
                    self.chats[chat].history_list_update()
                    sender_window_active = True
        if not sender_window_active:
            #     self.history_list_update()
            # else:
            # Проверим есть ли такой пользователь у нас в контактах:
            if self.database.check_contact(message[SENDER]):
                # Если есть, спрашиваем и желании открыть с ним чат и открываем при желании
                # if self.messages.question(self, 'Новое сообщение', \
                #                           f'Получено новое сообщение от {message[SENDER]}, открыть чат с ним?', QMessageBox.Yes,
                #                           QMessageBox.No) == QMessageBox.Yes:
                #     self.current_chat = message[SENDER]
                #     self.start_new_chat()
                self.current_chat = message[SENDER]
                self.new_msg_alert.append(message[SENDER])
                self.clients_list_update()
            else:
                print('NO')
                # Раз нету,спрашиваем хотим ли добавить юзера в контакты.
                if self.messages.question(self, 'Новое сообщение', \
                                          f'Получено новое сообщение от {message[SENDER]}.\n Данного пользователя нет в вашем контакт-листе.\n Добавить в контакты и открыть чат с ним?',
                                          QMessageBox.Yes,
                                          QMessageBox.No) == QMessageBox.Yes:
                    self.add_contact(message[SENDER])
                    self.current_chat = message[SENDER]
                    self.start_new_chat()

    # Слот потери соединения
    # Выдаёт сообщение о ошибке и завершает работу приложения
    @pyqtSlot()
    def connection_lost(self):
        self.messages.warning(self, 'Сбой соединения', 'Потеряно соединение с сервером. ')
        self.close()

    @pyqtSlot()
    def sig_205(self):
        '''
        Слот выполняющий обновление баз данных по команде сервера.
        '''
        if len(self.chats):
            for chat in self.chats:
                if chat and not self.database.check_user(
                        chat):
                    self.messages.warning(
                        self,
                        'Сочувствую',
                        'К сожалению собеседник был удалён с сервера.')
                    # self.set_disabled_input()
                    # self.current_chat = None
                    self.close_chat(chat)
        self.clients_list_update()

    def make_connection(self, trans_obj):
        trans_obj.new_message.connect(self.message)
        trans_obj.connection_lost.connect(self.connection_lost)
        trans_obj.message_205.connect(self.sig_205)