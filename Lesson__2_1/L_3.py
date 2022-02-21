"""
Написать функцию host_range_ping_tab(), возможности которой основаны на функции из примера 2.
Но в данном случае результат должен быть итоговым по всем ip-адресам, представленным в табличном формате
(использовать модуль tabulate). Таблица должна состоять из двух колонок и выглядеть примерно так:
Reachable
10.0.0.1
10.0.0.2

Unreachable
10.0.0.3
10.0.0.4
"""
from tabulate import tabulate

from L_2 import host_range_ping


def host_range_ping_tab(ip_range):
    ip_address_tabulate = {
        'Reachable' : [],
        'Unreachable': []
    }
    ip_address_dict = host_range_ping(ip_range, timeout=1000)
    if type(ip_address_dict) is dict:
        for key in ip_address_dict:
            if ip_address_dict[key]['ping']:
                ip_address_tabulate['Reachable'].append(key)
            else:
                ip_address_tabulate['Unreachable'].append(key)
        print('Сканирование завершено')
        print(tabulate(ip_address_tabulate, headers='keys'))
    else:
        print('Диапазон задан неверно')


if __name__ == '__main__':
    ip_range = ['77.88.55.50', '77.88.55.80']
    print(host_range_ping_tab(ip_range))

