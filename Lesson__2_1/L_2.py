"""Написать функцию host_range_ping() для перебора ip-адресов из заданного диапазона. Меняться должен только последний
октет каждого адреса. По результатам проверки должно выводиться соответствующее сообщение."""
from ipaddress import ip_address
from L_1 import host_ping


def host_range_ping(ip_range, timeout=5000):
    ip_address_dict = {}
    first_ip = ip_address(ip_range[0])
    last_ip = ip_address(ip_range[1])
    if first_ip < last_ip:
        while first_ip < last_ip + 1:
            ping_test = host_ping([str(first_ip)], timeout)
            ip_address_dict[str(first_ip)] = {'ping': ping_test}
            first_ip += 1
        return ip_address_dict
    else:
        print('Диапазон задан неверно')


if __name__ == '__main__':
    ip_range = ['192.168.0.1', '192.168.0.3']
    print(host_range_ping(ip_range))
