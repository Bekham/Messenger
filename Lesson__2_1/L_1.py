"""
Написать функцию host_ping(), в которой с помощью утилиты ping будет проверяться доступность сетевых узлов.
Аргументом функции является список, в котором каждый сетевой узел должен быть представлен именем хоста или ip-адресом.
 В функции необходимо перебирать ip-адреса и проверять их доступность с выводом соответствующего сообщения
 («Узел доступен», «Узел недоступен»). При этом ip-адрес сетевого узла должен создаваться с помощью функции
 ip_address().
 """

from subprocess import Popen, PIPE
from ipaddress import ip_address as ip


def host_ping(ip_address_list, timeout=5000, requests=1):
    for ip_address in ip_address_list:
        try:
            ip_address = ip(ip_address)
        except ValueError:
            pass
        args = f'ping {ip_address} -n {requests} -w {timeout}'
        reply = Popen(args, stdout=PIPE, stderr=PIPE)
        code = reply.wait()
        if code:
            print(f'{ip_address} : Узел недоступен')
            return False
        else:
            print(f'{ip_address} : Узел доступен')
            return True


if __name__ == '__main__':
    ip_addresses = ['google.com', 'f', 'ya.ru', '77.88.55.70']
    host_ping(ip_addresses)
