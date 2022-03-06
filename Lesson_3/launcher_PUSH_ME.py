import os
import subprocess

process = []

while True:
    action = input('Выберите действие: q - выход , s - запустить сервер, k - запустить клиенты x - закрыть все окна:')
    dir_path = os.path.dirname(os.path.realpath(__file__))
    if action == 'q':
        break
    elif action == 's':
        # Запускаем сервер!
        client_path = f"{dir_path}/{'server_app'}/{'server.py'}"
        process.append(subprocess.Popen(f'python {client_path}', creationflags=subprocess.CREATE_NEW_CONSOLE))
    elif action == 'k':
        clients_count = int(input('Введите количество тестовых клиентов для запуска: '))
        # Запускаем клиентов:
        client_path = f"{dir_path}/{'client_app'}/{'client.py'}"
        for i in range(clients_count):
            process.append(subprocess.Popen(f'python {client_path} -n test{i + 1} -p 1',
                                            creationflags=subprocess.CREATE_NEW_CONSOLE))
    elif action == 'x':
        while process:
            process.pop().kill()