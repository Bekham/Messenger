import sys
import logging
import base64
from client_app.common_client.errors import ServerError
from client_app.client.del_contact import DelContactDialog
from client_app.client.add_contact import AddContactDialog
from client_app.client.client_contacts_conv import Ui_MainClientWindow
from client_app.client.client_chat import ClientChatWindow

from Crypto.Cipher import PKCS1_OAEP
from PyQt5.QtWidgets import QMainWindow, qApp, QMessageBox
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import pyqtSlot, QObject

from client_app.common_client.variables import MESSAGE_TEXT, SENDER

sys.path.append('../')

logger = logging.getLogger('client')


class ClientMainWindow(QMainWindow, QObject):
    """Класс основного окна выбора контактов для общения"""

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
        """При закрытии текущего окна обмена сообщениями идет передача сигнала
        фукцции close_current_chats"""
        self.close_current_chats()
        event.accept()

    def close_current_chats(self):
        """При закрытии текущего (основного) окна автоматически
        закрываются все окна открытых чатов"""
        if len(self.chats):
            chats_list = []
            for chat in self.chats.keys():
                chats_list.append(self.chats[chat])
            for chat in chats_list:
                chat.close()
        self.close()

    def select_active_user(self):
        """Функция обработчик даблклика по контакту"""
        # Выбранный пользователем (даблклик) находится в выделеном элементе в
        # QListView
        self.current_chat = self.ui.list_contacts.currentIndex().data()
        self.current_chat = self.current_chat.split('***Новое сообщение***')[0]
        self.start_new_chat()
        # вызываем основную функцию
        # self.set_active_user()

    def start_new_chat(self):
        """Функция, создающая новый экземпляр класса диалогового окна с выбранным собеседником"""
        self.chats[self.current_chat] = ClientChatWindow(self.database,
                                                         self.transport,
                                                         self.current_chat,
                                                         self.client_name)
        if self.current_chat in self.new_msg_alert:
            self.new_msg_alert.remove(self.current_chat)
        self.clients_list_update()
        self.chats[self.current_chat].set_active_user()
        self.chats[self.current_chat].setWindowTitle(
            f'Чат - {self.current_chat}')
        self.chats[self.current_chat].show()
        self.close_chat_window()

    def close_chat_window(self):
        """Фукнция обработчик - при закрытии окна чата -
        экземпляр класса данного чата удаляется из списка self.chats"""
        for chat in self.chats:
            self.chats[chat].close_chat.connect(self.close_chat)

    @pyqtSlot(str)
    def close_chat(self, current_chat):
        """Экземпляр класса закрытого чата удаляется из списка self.chats"""
        del self.chats[current_chat]

    def clients_list_update(self):
        """Функция обновляющяя контакт лист"""
        contacts_list = self.database.get_contacts()
        self.contacts_model = QStandardItemModel()
        for i in sorted(contacts_list):
            if i in self.new_msg_alert:
                i = f'{i}***Новое сообщение***'
            item = QStandardItem(i)
            item.setEditable(False)
            self.contacts_model.appendRow(item)
        self.ui.list_contacts.setModel(self.contacts_model)

    def add_contact_window(self):
        """Функция добавления контакта"""
        global select_dialog
        select_dialog = AddContactDialog(self.transport, self.database)
        select_dialog.btn_ok.clicked.connect(
            lambda: self.add_contact_action(select_dialog))
        select_dialog.show()

    def add_contact_action(self, item):
        """Функция - обработчик добавления, сообщает серверу, обновляет таблицу и
     список контактов"""
        new_contact = item.selector.currentText()
        self.add_contact(new_contact)
        item.close()

    def add_contact(self, new_contact):
        """Функция добавляющяя контакт в базы"""
        try:
            self.transport.add_contact(new_contact)
        except ServerError as err:
            self.messages.critical(self, 'Ошибка сервера', err.text)
        except OSError as err:
            if err.errno:
                self.messages.critical(
                    self, 'Ошибка', 'Потеряно соединение с сервером!')
                self.close()
            self.messages.critical(self, 'Ошибка', 'Таймаут соединения!')
        else:
            self.database.add_contact(new_contact)
            new_contact = QStandardItem(new_contact)
            new_contact.setEditable(False)
            self.contacts_model.appendRow(new_contact)
            logger.info(f'Успешно добавлен контакт {new_contact}')
            self.messages.information(
                self, 'Успех', 'Контакт успешно добавлен.')

    def delete_contact_window(self):
        """Функция удаления контакта"""
        global remove_dialog
        remove_dialog = DelContactDialog(self.database)
        remove_dialog.btn_ok.clicked.connect(
            lambda: self.delete_contact(remove_dialog))
        remove_dialog.show()

    def delete_contact(self, item):
        """ Функция обработчик удаления контакта, сообщает на сервер,
        обновляет таблицу контактов """
        selected = item.selector.currentText()
        try:
            self.transport.remove_contact(selected)
        except ServerError as err:
            self.messages.critical(self, 'Ошибка сервера', err.text)
        except OSError as err:
            if err.errno:
                self.messages.critical(
                    self, 'Ошибка', 'Потеряно соединение с сервером!')
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

    @pyqtSlot(dict)
    def message(self, message):
        """Слот приёма нового сообщений"""
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
            if self.database.check_contact(message[SENDER]):
                self.current_chat = message[SENDER]
                self.new_msg_alert.append(message[SENDER])
                self.clients_list_update()
            else:
                print('NO')
                # Раз нету,спрашиваем хотим ли добавить юзера в контакты.
                if self.messages.question(
                    self,
                    'Новое сообщение',
                    f'Получено новое сообщение от {message[SENDER]}.\n '
                    f'Данного пользователя нет в вашем контакт-листе.\n '
                    f'Добавить в контакты и открыть чат с ним?',
                    QMessageBox.Yes,
                        QMessageBox.No) == QMessageBox.Yes:
                    self.add_contact(message[SENDER])
                    self.current_chat = message[SENDER]
                    self.start_new_chat()

    @pyqtSlot()
    def connection_lost(self):
        """Слот потери соединения
    Выдаёт сообщение о ошибке и завершает работу приложения"""
        self.messages.warning(
            self,
            'Сбой соединения',
            'Потеряно соединение с сервером. ')
        self.close()

    @pyqtSlot()
    def sig_205(self):
        """Слот выполняющий обновление баз данных по команде сервера."""
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
        """Функция, обрабатывающая сигналы получения нового сообщения, потери соединения"""
        trans_obj.new_message.connect(self.message)
        trans_obj.connection_lost.connect(self.connection_lost)
        trans_obj.message_205.connect(self.sig_205)
