Common package
=================================================

Пакет общих утилит, использующихся в разных модулях проекта.

core_server.py
~~~~~~~~~~~

.. autoclass:: server_app.common_server.core_server.MessengerServerCore
	:members:

database.py
~~~~~~~~~~~

.. autoclass:: server_app.common_server.server_database.ServerStorage
	:members:

Скрипт decos.py
---------------

.. automodule:: server_app.common_server.decos.log
	:members:

.. automodule:: server_app.common_server.decos.login_required
	:members:
	
Скрипт descrptors.py
---------------------

.. autoclass:: server_app.common_server.descrptors.Port
    :members:

.. autoclass:: server_app.common_server.descrptors.Host
    :members:
   
Скрипт errors.py
---------------------
   
.. autoclass:: server_app.common_server.errors.ServerError
   :members:
   
Скрипт meta.py
-----------------------

.. autoclass:: server_app.common_server.meta.ServerMaker
   :members:
   
.. autoclass:: server_app.common_server.meta.ClientMaker
   :members:

Скрипт variables.py
---------------------

Содержит разные глобальные переменные проекта.