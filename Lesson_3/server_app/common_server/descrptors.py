import ipaddress
import logging
import sys

# Инициализиция логера
# метод определения модуля, источника запуска.
if sys.argv[0].find('client') == -1:
    # если не клиент то сервер!
    logger = logging.getLogger('server')
else:
    # ну, раз не сервер, то клиент
    logger = logging.getLogger('client')


# Дескриптор для описания порта:
class Port:
    """Дескриптор для описания порта"""
    def __set__(self, instance, value):
        # instance - <__main__.Server object at 0x000000D582740C50>
        # value - 7777
        if not 1023 < value < 65536:
            logger.critical(
                f'Попытка запуска сервера с указанием неподходящего порта {value}. Допустимы адреса с 1024 до 65535.')
            exit(1)
        # Если порт прошел проверку, добавляем его в список атрибутов
        # экземпляра
        instance.__dict__[self.name] = value

    def __set_name__(self, owner, name):
        # owner - <class '__main__.Server'>
        # name - port
        self.name = name


class Host:
    """Дескриптор для описания хоста"""
    def __set__(self, instance, value):
        if value:
            try:
                ip = ipaddress.ip_address(value)
            except ValueError:
                logger.critical(
                    f'Значение ip адреса: {value} - введено неверно.')
                exit(1)
        instance.__dict__[self.name] = value

    def __set_name__(self, owner, name):
        self.name = name
