"""Декораторы"""

import sys
import logging
import traceback
import inspect

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
