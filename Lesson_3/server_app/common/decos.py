"""Декораторы"""

import sys
import logging
import traceback
import inspect
import socket

from common.meta import ServerMaker

sys.path.append('../')
import logs.config_server_log
import logs.config_client_log


# метод определения модуля, источника запуска.
# Метод find () возвращает индекс первого вхождения искомой подстроки,
# если он найден в данной строке.
# Если его не найдено, - возвращает -1.
# os.path.split(sys.argv[0])[1]
if sys.argv[0].find('client') == -1:
    # если не клиент то сервер!
    LOGGER = logging.getLogger('server')
else:
    # ну, раз не сервер, то клиент
    LOGGER = logging.getLogger('client')


# Реализация в виде класса
class Log:
    """Класс-декоратор"""
    def __call__(self, func_to_log):
        def log_saver(*args, **kwargs):
            """Обертка"""

            ret = func_to_log(*args, **kwargs)
            if args and kwargs:
                args_kwargs = f'{args}, {kwargs}'
            elif args:
                args_kwargs = f'{args}'
            else:
                args_kwargs = f'{kwargs}'
            LOGGER.debug(f'Была вызвана функция {func_to_log.__name__} c параметрами {args_kwargs}. '
                         f'Вызов из модуля {func_to_log.__module__}. Вызов из'
                         f' функции {traceback.format_stack()[0].strip().split()[-1]}.'
                         f'Вызов из функции {inspect.stack()[1][3]}')
            return ret
        return log_saver

def log(func_to_log):
    def log_saver(*args , **kwargs):
        LOGGER.debug(f'Была вызвана функция {func_to_log.__name__} c параметрами {args} , {kwargs}. Вызов из модуля {func_to_log.__module__}')
        ret = func_to_log(*args , **kwargs)
        return ret
    return log_saver

def login_required(func):
    '''
    Декоратор, проверяющий, что клиент авторизован на сервере.
    Проверяет, что передаваемый объект сокета находится в
    списке авторизованных клиентов.
    За исключением передачи словаря-запроса
    на авторизацию. Если клиент не авторизован,
    генерирует исключение TypeError
    '''

    def checker(*args, **kwargs):
        # проверяем, что первый аргумент - экземпляр MessageProcessor
        # Импортить необходимо тут, иначе ошибка рекурсивного импорта.
        from common.core_server import MessengerServerCore
        from common.variables import ACTION, PRESENCE
        if isinstance(args[0], MessengerServerCore):
            found = False
            for arg in args:
                if isinstance(arg, socket.socket):
                    # Проверяем, что данный сокет есть в списке names класса
                    # MessageProcessor
                    for client in args[0].clients_names:
                        if args[0].clients_names[client] == arg:
                            found = True

            # Теперь надо проверить, что передаваемые аргументы не presence
            # сообщение. Если presense, то разрешаем
            for arg in args:
                if isinstance(arg, dict):
                    if ACTION in arg and arg[ACTION] == PRESENCE:
                        found = True
            # Если не не авторизован и не сообщение начала авторизации, то
            # вызываем исключение.
            if not found:
                raise TypeError
        return func(*args, **kwargs)

    return checker

