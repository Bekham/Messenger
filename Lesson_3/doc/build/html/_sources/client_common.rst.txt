Common package
=================================================

Пакет общих утилит, использующихся в разных модулях проекта.

client_core.py
~~~~~~~~~~~~~~

.. autoclass:: client_app.common_client.client_core.ClientTransport
	:members:

Скрипт decos.py
---------------

.. automodule:: client_app.common_client.decos
	:members:


Скрипт errors.py
---------------------

.. autoclass:: client_app.common_client.errors.ServerError
   :members:

.. autoclass:: client_app.common_client.errors.ReqFieldMissingError
   :members:


   
Скрипт utils.py
---------------------

client_app.common_client.utils. **get_message** (client)


	Функция приёма сообщений от удалённых компьютеров. Принимает сообщения JSON,
	декодирует полученное сообщение и проверяет что получен словарь.

client_app.common_client.utils. **send_message** (sock, message)


	Функция отправки словарей через сокет. Кодирует словарь в формат JSON и отправляет через сокет.


Скрипт variables.py
---------------------

Содержит разные глобальные переменные проекта.