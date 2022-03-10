import os
import sys
import datetime
from client_app.common_client.variables import *

sys.path.append('../')
from sqlalchemy import create_engine, Table, Column, Integer, String, Text, MetaData, DateTime
from sqlalchemy.orm import mapper, sessionmaker


class ClientDatabase:
    """Класс - база данных клиента"""

    class KnownUsers:
        """Класс - отображение таблицы известных пользователей."""

        def __init__(self, user):
            self.id = None
            self.username = user

    class MessageHistory:
        """Класс - отображение таблицы истории сообщений"""

        def __init__(self, contact, direction, message):
            self.id = None
            self.contact = contact
            self.direction = direction
            self.message = message
            self.date = datetime.datetime.now()

    class Contacts:
        """Класс - отображение списка контактов"""

        def __init__(self, contact):
            self.id = None
            self.name = contact

    def __init__(self, name):
        """Конструктор класса"""
        # Создаём движок базы данных, поскольку разрешено несколько клиентов одновременно, каждый должен иметь свою БД
        # Поскольку клиент мультипоточный необходимо отключить проверки на подключения с разных потоков,
        # иначе sqlite3.ProgrammingError
        path = os.path.dirname(os.path.realpath(__file__))
        filename = f'client_{name}.db3'
        self.database_engine = create_engine(
            f'sqlite:///{os.path.join(path, filename)}',
            echo=False,
            pool_recycle=7200,
            connect_args={
                'check_same_thread': False})

        # Создаём объект MetaData
        self.metadata = MetaData()

        # Создаём таблицу известных пользователей
        users = Table('known_users', self.metadata,
                      Column('id', Integer, primary_key=True),
                      Column('username', String)
                      )

        # Создаём таблицу истории сообщений
        history = Table('message_history', self.metadata,
                        Column('id', Integer, primary_key=True),
                        Column('contact', String),
                        Column('direction', String),
                        Column('message', Text),
                        Column('date', DateTime)
                        )

        # Создаём таблицу контактов
        contacts = Table('contacts', self.metadata,
                         Column('id', Integer, primary_key=True),
                         Column('name', String, unique=True)
                         )

        # Создаём таблицы
        self.metadata.create_all(self.database_engine)

        # Создаём отображения
        mapper(self.KnownUsers, users)
        mapper(self.MessageHistory, history)
        mapper(self.Contacts, contacts)

        # Создаём сессию
        session_create = sessionmaker(bind=self.database_engine)
        self.session = session_create()

        # Необходимо очистить таблицу контактов, т.к. при запуске они
        # подгружаются с сервера.
        self.session.query(self.Contacts).delete()
        self.session.commit()

    def add_contact(self, contact):
        """Функция добавления контактов"""
        if not self.session.query(
                self.Contacts).filter_by(
            name=contact).count():
            contact_row = self.Contacts(contact)
            self.session.add(contact_row)
            self.session.commit()

    def del_contact(self, contact):
        """Функция удаления контакта"""
        self.session.query(self.Contacts).filter_by(name=contact).delete()

    def add_users(self, users_list):
        """Функция добавления известных пользователей.
    Пользователи получаются только с сервера, поэтому таблица очищается."""
        self.session.query(self.KnownUsers).delete()
        for user in users_list:
            user_row = self.KnownUsers(user)
            self.session.add(user_row)
        self.session.commit()

    def save_message(self, contact, direction, message):
        """Функция, сохраняющая сообщения"""
        message_row = self.MessageHistory(contact, direction, message)
        self.session.add(message_row)
        self.session.commit()

    def get_contacts(self):
        """Функция, возвращающая контакты"""
        return [contact[0]
                for contact in self.session.query(self.Contacts.name).all()]

    def get_users(self):
        """Функция, возвращающая список известных пользователей"""
        return [user[0]
                for user in self.session.query(self.KnownUsers.username).all()]

    def check_user(self, user):
        """Функция проверяющая наличие пользователя в известных"""
        if self.session.query(
                self.KnownUsers).filter_by(
            username=user).count():
            return True
        else:
            return False

    def check_contact(self, contact):
        """Функция проверяющая наличие пользователя контактах"""
        if self.session.query(self.Contacts).filter_by(name=contact).count():
            return True
        else:
            return False

    def get_history(self, contact):
        """Функция возвращающая историю переписки"""
        query = self.session.query(
            self.MessageHistory).filter_by(
            contact=contact)
        return [(history_row.contact,
                 history_row.direction,
                 history_row.message,
                 history_row.date) for history_row in query.all()]

    def contacts_clear(self):
        """Метод очищающий таблицу со списком контактов."""
        self.session.query(self.Contacts).delete()


if __name__ == '__main__':
    pass
