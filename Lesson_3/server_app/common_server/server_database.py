from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, ForeignKey, DateTime, Text
from sqlalchemy.orm import mapper, sessionmaker
import datetime


# Класс - серверная база данных:
class ServerStorage:
    """Класс - серверная база данных"""
    # Экземпляр этого класса = запись в таблице AllUsers
    class AllUsers:
        """Класс - отображение таблицы всех пользователей
        Экземпляр этого класса = запись в таблице AllUsers"""

        def __init__(self, username, passwd_hash):
            self.name = username
            self.last_login = datetime.datetime.now()
            self.id = None
            self.passwd_hash = passwd_hash
            self.pubkey = None

    # Класс - отображение таблицы активных пользователей:
    # Экземпляр этого класса = запись в таблице ActiveUsers
    class ActiveUsers:
        """Класс - отображение таблицы активных пользователей:
        Экземпляр этого класса = запись в таблице ActiveUsers"""

        def __init__(self, user_id, ip_address, port, login_time):
            self.user = user_id
            self.ip_address = ip_address
            self.port = port
            self.login_time = login_time
            self.id = None

    # Класс - отображение таблицы истории входов
    # Экземпляр этого класса = запись в таблице LoginHistory

    class LoginHistory:
        """Класс - отображение таблицы истории входов
        Экземпляр этого класса = запись в таблице LoginHistory"""

        def __init__(self, name, date, ip, port):
            self.id = None
            self.name = name
            self.date_time = date
            self.ip = ip
            self.port = port

    class MessageHistory:
        """Класс - отображение таблицы истории сообщений
        Экземпляр этого класса = запись в таблице MessageHistory"""

        def __init__(self, from_id, to_id, message, date):
            self.id = None
            self.from_id = from_id
            self.to_id = to_id
            self.message = message
            self.date_time = date

    # Класс - отображение таблицы контактов пользователей
    class UsersContacts:  # add_new
        """Класс - отображение таблицы контактов пользователей"""

        def __init__(self, user, contact):
            self.id = None
            self.user = user
            self.contact = contact

    # Класс отображение таблицы истории действий
    class UsersHistory:  # add_new
        """Класс отображение таблицы истории действий"""

        def __init__(self, user):
            self.id = None
            self.user = user
            self.sent = 0
            self.accepted = 0

    def __init__(self, path):
        # Создаём движок базы данных
        # SERVER_DATABASE - sqlite:///server_base.db3
        # echo=False - отключаем ведение лога (вывод sql-запросов)
        # pool_recycle - По умолчанию соединение с БД через 8 часов простоя обрывается.
        # Чтобы это не случилось нужно добавить опцию pool_recycle = 7200 (переуст-ка соед-я через 2 часа)
        # print(path)
        self.database_engine = create_engine(
            f'sqlite:///{path}',
            echo=False,
            pool_recycle=7200,
            connect_args={
                'check_same_thread': False})

        # Создаём объект MetaData
        self.metadata = MetaData()

        # Создаём таблицу пользователей
        users_table = Table('Users', self.metadata,
                            Column('id', Integer, primary_key=True),
                            Column('name', String, unique=True),
                            Column('last_login', DateTime),
                            Column('passwd_hash', String),
                            Column('pubkey', Text)
                            )

        # Создаём таблицу активных пользователей
        active_users_table = Table(
            'Active_users', self.metadata, Column(
                'id', Integer, primary_key=True), Column(
                'user', ForeignKey('Users.id'), unique=True), Column(
                'ip_address', String), Column(
                    'port', Integer), Column(
                        'login_time', DateTime))

        # Создаём таблицу истории входов
        user_login_history = Table('Login_history', self.metadata,
                                   Column('id', Integer, primary_key=True),
                                   Column('name', ForeignKey('Users.id')),
                                   Column('date_time', DateTime),
                                   Column('ip', String),
                                   Column('port', String)
                                   )

        message_history = Table('Message_history', self.metadata,
                                Column('id', Integer, primary_key=True),
                                Column('from_id', ForeignKey('Users.id')),
                                Column('to_id', ForeignKey('Users.id')),
                                Column('message', String),
                                Column('date_time', DateTime)
                                )

        # Создаём таблицу контактов пользователей add_new
        contacts = Table('Contacts', self.metadata,
                         Column('id', Integer, primary_key=True),
                         Column('user', ForeignKey('Users.id')),
                         Column('contact', ForeignKey('Users.id'))
                         )

        # Создаём таблицу истории пользователей add_new
        users_history_table = Table('History', self.metadata,
                                    Column('id', Integer, primary_key=True),
                                    Column('user', ForeignKey('Users.id')),
                                    Column('sent', Integer),
                                    Column('accepted', Integer)
                                    )

        # Создаём таблицы
        self.metadata.create_all(self.database_engine)

        # Создаём отображения
        # Связываем класс в ORM с таблицей
        mapper(self.AllUsers, users_table)
        mapper(self.ActiveUsers, active_users_table)
        mapper(self.LoginHistory, user_login_history)
        mapper(self.MessageHistory, message_history)
        mapper(self.UsersContacts, contacts)
        mapper(self.UsersHistory, users_history_table)

        # Создаём сессию
        Session = sessionmaker(bind=self.database_engine)
        self.session = Session()

        # Если в таблице активных пользователей есть записи, то их необходимо удалить
        # Когда устанавливаем соединение, очищаем таблицу активных
        # пользователей
        self.session.query(self.ActiveUsers).delete()
        self.session.commit()

    # Функция выполняющяяся при входе пользователя, записывает в базу факт
    # входа
    def user_login(self, username, ip_address, port, key):
        """Функция выполняющаяся при входе пользователя, записывает в базу факт
        входа"""
        print(f'\n{username} {ip_address} {port}')
        # Запрос в таблицу пользователей на наличие там пользователя с таким
        # именем
        rez = self.session.query(self.AllUsers).filter_by(name=username)
        # print(type(rez))
        # Если имя пользователя уже присутствует в таблице, обновляем время
        # последнего входа
        if rez.count():
            user = rez.first()
            user.last_login = datetime.datetime.now()
            if user.pubkey != key:
                user.pubkey = key
        # Если нет, то создаздаём нового пользователя
        else:
            raise ValueError('Пользователь не зарегистрирован.')
            # Создаем экземпляр класса self.AllUsers, через который передаем данные в таблицу
            # user = self.AllUsers(username)
            # self.session.add(user)
            # # Комит здесь нужен, чтобы присвоился ID
            # self.session.commit()
            # user_in_history = self.UsersHistory(user.id)
            # self.session.add(user_in_history)

        # Теперь можно создать запись в таблицу активных пользователей о факте входа.
        # Создаем экземпляр класса self.ActiveUsers, через который передаем
        # данные в таблицу
        new_active_user = self.ActiveUsers(user.id,
                                           ip_address,
                                           port,
                                           datetime.datetime.now())
        self.session.add(new_active_user)
        self.session.commit()
        # и сохранить в историю входов
        # Создаем экземпляр класса self.LoginHistory, через который передаем
        # данные в таблицу
        history = self.LoginHistory(user.id,
                                    datetime.datetime.now(),
                                    ip_address,
                                    port)
        self.session.add(history)

        # Сохраняем изменения
        self.session.commit()

    def add_user(self, name, passwd_hash):
        """
        Метод регистрации пользователя.
        Принимает имя и хэш пароля, создаёт запись в таблице статистики.
        """
        user_row = self.AllUsers(name, passwd_hash)
        self.session.add(user_row)
        self.session.commit()
        history_row = self.UsersHistory(user_row.id)
        self.session.add(history_row)
        self.session.commit()

    def remove_user(self, name):
        """Метод удаляющий пользователя из базы."""
        user = self.session.query(self.AllUsers).filter_by(name=name).first()
        self.session.query(self.ActiveUsers).filter_by(user=user.id).delete()
        self.session.query(self.LoginHistory).filter_by(name=user.id).delete()
        self.session.query(self.UsersContacts).filter_by(user=user.id).delete()
        self.session.query(
            self.UsersContacts).filter_by(
            contact=user.id).delete()
        self.session.query(self.UsersHistory).filter_by(user=user.id).delete()
        self.session.query(self.AllUsers).filter_by(name=name).delete()
        self.session.commit()

    def get_hash(self, name):
        """Метод получения хэша пароля пользователя."""
        user = self.session.query(self.AllUsers).filter_by(name=name).first()
        return user.passwd_hash

    def get_pubkey(self, name):
        """Метод получения публичного ключа пользователя."""
        user = self.session.query(self.AllUsers).filter_by(name=name).first()
        return user.pubkey

    def check_user(self, name):
        """Метод проверяющий существование пользователя."""
        if self.session.query(self.AllUsers).filter_by(name=name).count():
            return True
        else:
            return False

    # Функция фиксирующая отключение пользователя
    def user_logout(self, username):
        """Функция фиксирующая отключение пользователя"""
        # Запрашиваем пользователя, что покидает нас
        # получаем запись из таблицы AllUsers
        user = self.session.query(
            self.AllUsers).filter_by(
            name=username).first()

        # Удаляем его из таблицы активных пользователей.
        # Удаляем запись из таблицы ActiveUsers
        self.session.query(self.ActiveUsers).filter_by(user=user.id).delete()

        # Применяем изменения
        self.session.commit()

    def process_message(self, sender, recipient):
        """Получаем ID отправителя и получателя"""
        sender = self.session.query(
            self.AllUsers).filter_by(
            name=sender).first().id
        recipient = self.session.query(
            self.AllUsers).filter_by(
            name=recipient).first().id
        # Запрашиваем строки из истории и увеличиваем счётчики
        sender_row = self.session.query(
            self.UsersHistory).filter_by(
            user=sender).first()
        sender_row.sent += 1
        recipient_row = self.session.query(
            self.UsersHistory).filter_by(
            user=recipient).first()
        recipient_row.accepted += 1

        self.session.commit()  # add_new

    # Функция добавляет контакт для пользователя.

    def add_contact(self, user, contact):
        """Получаем ID пользователей"""
        user = self.session.query(self.AllUsers).filter_by(name=user).first()
        contact = self.session.query(
            self.AllUsers).filter_by(
            name=contact).first()

        # Проверяем что не дубль и что контакт может существовать (полю
        # пользователь мы доверяем)
        if not contact or self.session.query(
                self.UsersContacts).filter_by(
                user=user.id,
                contact=contact.id).count():
            return

        # Создаём объект и заносим его в базу
        contact_row = self.UsersContacts(user.id, contact.id)
        self.session.add(contact_row)
        self.session.commit()  # add_new

    # Функция удаляет контакт из базы данных
    def remove_contact(self, user, contact):
        """Функция удаляет контакт из базы данных"""
        # Получаем ID пользователей
        user = self.session.query(self.AllUsers).filter_by(name=user).first()
        contact = self.session.query(
            self.AllUsers).filter_by(
            name=contact).first()

        # Проверяем что контакт может существовать (полю пользователь мы
        # доверяем)
        if not contact:
            return
        # Удаляем требуемое
        print(self.session.query(self.UsersContacts).filter(
            self.UsersContacts.user == user.id,
            self.UsersContacts.contact == contact.id
        ).delete())
        self.session.commit()  # add_new

    # Функция возвращает список известных пользователей со временем последнего
    # входа.
    def users_list(self):
        """Функция возвращает список известных пользователей со временем последнего
        входа."""
        query = self.session.query(
            self.AllUsers.name,
            self.AllUsers.last_login,
        )
        # Возвращаем список кортежей
        return query.all()

    # Функция возвращает список активных пользователей
    def active_users_list(self):
        """Функция возвращает список активных пользователей"""
        # Запрашиваем соединение таблиц и собираем кортежи имя, адрес, порт,
        # время.
        query = self.session.query(
            self.AllUsers.name,
            self.ActiveUsers.ip_address,
            self.ActiveUsers.port,
            self.ActiveUsers.login_time
        ).join(self.AllUsers)
        # Возвращаем список кортежей
        return query.all()

    # Функция возвращающая историю входов по пользователю или всем
    # пользователям
    def login_history(self, username=None):
        """Функция возвращающая историю входов по пользователю или всем
        пользователям"""
        # Запрашиваем историю входа
        query = self.session.query(self.AllUsers.name,
                                   self.LoginHistory.date_time,
                                   self.LoginHistory.ip,
                                   self.LoginHistory.port
                                   ).join(self.AllUsers)
        # Если было указано имя пользователя, то фильтруем по нему
        if username:
            query = query.filter(self.AllUsers.name == username)
        return query.all()

    def add_message(self, from_user, to_user, message):
        """Запись сообщений в базу данных MessageHistory"""
        try:
            user_from = self.session.query(
                self.AllUsers).filter_by(
                name=from_user).first()
            user_to = self.session.query(
                self.AllUsers).filter_by(
                name=to_user).first()
            new_message = self.MessageHistory(
                user_from.id,
                user_to.id,
                message,
                datetime.datetime.now())
            self.session.add(new_message)
            self.session.commit()
        except BaseException:
            print(Exception)

    # Функция возвращает список контактов пользователя.
    def get_contacts(self, username):
        """Функция возвращает список контактов пользователя."""
        # Запрашивааем указанного пользователя
        user = self.session.query(self.AllUsers).filter_by(name=username).one()

        # Запрашиваем его список контактов
        query = self.session.query(self.UsersContacts, self.AllUsers.name). \
            filter_by(user=user.id). \
            join(self.AllUsers, self.UsersContacts.contact == self.AllUsers.id)

        # выбираем только имена пользователей и возвращаем их.
        return [contact[1] for contact in query.all()]  # add_new

    # Функция возвращает количество переданных и полученных сообщений
    def message_history(self):  # add_new
        """Функция возвращает количество переданных и полученных сообщений"""
        query = self.session.query(
            self.AllUsers.name,
            self.AllUsers.last_login,
            self.UsersHistory.sent,
            self.UsersHistory.accepted
        ).join(self.AllUsers)
        # Возвращаем список кортежей
        return query.all()


# Отладка
if __name__ == '__main__':
    path = 'C:\\GB_Projects\\Server_Client\\Messenger\\Lesson_3'
    test_db = ServerStorage(path)
    # выполняем 'подключение' пользователя
    test_db.user_login('client_1', '192.168.1.4', 8888)
    test_db.user_login('client_2', '192.168.1.5', 7777)
    # выводим список кортежей - активных пользователей
    print(test_db.active_users_list())
    # выполянем 'отключение' пользователя
    test_db.user_logout('client_1')
    # выводим список активных пользователей
    print(test_db.active_users_list())
    # запрашиваем историю входов по пользователю
    test_db.login_history('client_1')
    # выводим список известных пользователей
    print(test_db.users_list())
