"""Unit-тесты сервера"""

import sys
import os
import unittest
# sys.path.append(os.path.join(os.getcwd(), ''))
from common_server.variables import RESPONSE, ERROR, USER, ACCOUNT_NAME, TIME, ACTION, PRESENCE
from common_server.core_server import MessengerServerCore

class TestServer(unittest.TestCase):
    '''
    В сервере только 1 функция для тестирования
    '''
    err_dict = {
        RESPONSE: 400,
        ERROR: 'Bad Request'
    }
    ok_dict = {RESPONSE: 200}
    test_server = MessengerCore()


    def test_no_action(self):
        """Ошибка если нет действия"""
        self.test_server.message_from_client = {TIME: '1.1', USER: {ACCOUNT_NAME: 'Guest'}}
        self.assertEqual(self.test_server.process_client_message(), self.err_dict)

    def test_wrong_action(self):
        """Ошибка если неизвестное действие"""
        self.test_server.message_from_client = {ACTION: 'Wrong', TIME: '1.1', USER: {ACCOUNT_NAME: 'Guest'}}
        self.assertEqual(self.test_server.process_client_message(), self.err_dict)

    def test_no_time(self):
        """Ошибка, если  запрос не содержит штампа времени"""
        self.test_server.message_from_client = {ACTION: PRESENCE, USER: {ACCOUNT_NAME: 'Guest'}}
        self.assertEqual(self.test_server.process_client_message(), self.err_dict)

    def test_no_user(self):
        """Ошибка - нет пользователя"""
        self.test_server.message_from_client = {ACTION: PRESENCE, TIME: '1.1'}
        self.assertEqual(self.test_server.process_client_message(), self.err_dict)

    def test_unknown_user(self):
        """Ошибка - не Guest"""
        self.test_server.message_from_client = {ACTION: PRESENCE, TIME: 1.1, USER: {ACCOUNT_NAME: 'Guest1'}}
        self.assertEqual(self.test_server.process_client_message(), self.err_dict)

    def test_ok_check(self):
        """Корректный запрос"""
        self.test_server.message_from_client = {ACTION: PRESENCE, TIME: 1.1, USER: {ACCOUNT_NAME: 'Guest'}}
        self.assertEqual(self.test_server.process_client_message(), self.ok_dict)


if __name__ == '__main__':
    unittest.main()
