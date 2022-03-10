"""Unit-тесты клиента"""

import sys
import os
import unittest
# sys.path.append(os.path.join(os.getcwd(), ''))
from common_server.variables import RESPONSE, ERROR, USER, ACCOUNT_NAME, TIME, ACTION, PRESENCE
from common_server.core_server import MessengerServerCore

class TestClass(unittest.TestCase):
    '''
    Класс с тестами
    '''

    def test_def_presense(self):
        """Тест коректного запроса"""

        test_client = MessengerCore()
        test = test_client.create_presence()
        test[TIME] = 1.1  # время необходимо приравнять принудительно
                          # иначе тест никогда не будет пройден
        self.assertEqual(test, {ACTION: PRESENCE, TIME: 1.1, USER: {ACCOUNT_NAME: 'Guest'}})

    def test_200_ans(self):
        """Тест корректтного разбора ответа 200"""
        test_client = MessengerCore()
        test_client.message_from_server = {RESPONSE: 200}
        self.assertEqual(test_client.process_ans(), 'Успешная авторизация... \n200 : OK')

    def test_400_ans(self):
        """Тест корректного разбора 400"""
        test_client = MessengerCore()
        test_client.message_from_server = {RESPONSE: 400, ERROR: 'Bad Request'}
        self.assertEqual(test_client.process_ans(), 'Ошибка 400 : Bad Request')

    def test_no_response(self):
        """Тест исключения без поля RESPONSE"""
        test_client = MessengerCore()
        test_client.message_from_server = {}
        self.assertRaises(TypeError, test_client.process_ans())


if __name__ == '__main__':
    unittest.main()

#