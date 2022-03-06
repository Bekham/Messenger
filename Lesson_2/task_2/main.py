"""
2. Задание на закрепление знаний по модулю json. Есть файл orders
в формате JSON с информацией о заказах. Написать скрипт, автоматизирующий
его заполнение данными.

Для этого:
Создать функцию write_order_to_json(), в которую передается
5 параметров — товар (item), количество (quantity), цена (price),
покупатель (buyer), дата (date). Функция должна предусматривать запись
данных в виде словаря в файл orders.json. При записи данных указать
величину отступа в 4 пробельных символа;
Проверить работу программы через вызов функции write_order_to_json()
с передачей в нее значений каждого параметра.

ПРОШУ ВАС НЕ УДАЛЯТЬ ИСХОДНЫЙ JSON-ФАЙЛ
ПРИМЕР ТОГО, ЧТО ДОЛЖНО ПОЛУЧИТЬСЯ

{
    "orders": [
        {
            "item": "принтер", (возможные проблемы с кирилицей)
            "quantity": "10",
            "price": "6700",
            "buyer": "Ivanov I.I.",
            "date": "24.09.2017"
        },
        {
            "item": "scaner",
            "quantity": "20",
            "price": "10000",
            "buyer": "Petrov P.P.",
            "date": "11.01.2018"
        },
        {
            "item": "scaner",
            "quantity": "20",
            "price": "10000",
            "buyer": "Petrov P.P.",
            "date": "11.01.2018"
        },
        {
            "item": "scaner",
            "quantity": "20",
            "price": "10000",
            "buyer": "Petrov P.P.",
            "date": "11.01.2018"
        }
    ]
}

вам нужно подгрузить JSON-объект
и достучаться до списка, который и нужно пополнять
а потом сохранять все в файл
"""
import json


def write_order_to_json(item, quantity, price, buyer, date):
    add_order = {
        "item": item,
        "quantity": quantity,
        "price": price,
        "buyer": buyer,
        "date": date
    }
    find_copy = False
    with open('orders.json', encoding='utf-8') as f_n:
        F_N_CONTENT = f_n.read()
        OBJ = json.loads(F_N_CONTENT)
    if len(OBJ["orders"]):
        for i in OBJ["orders"]:
            if i["item"] == add_order["item"] \
                    and i["quantity"] == add_order["quantity"] \
                    and i["price"] == add_order["price"] \
                    and i["buyer"] == add_order["buyer"] \
                    and i["date"] == add_order["date"]:
                find_copy = True
    if not find_copy:
        OBJ["orders"].append(add_order)
    with open('orders.json', 'w', encoding='utf-8') as f_n:
        json.dump(OBJ, f_n, sort_keys=False, indent=4, ensure_ascii=False)


write_order_to_json(item="принтер", quantity="10", price="6700", buyer="Ivanov I.I.", date="24.09.2017")
write_order_to_json(item="scaner", quantity="20", price="10000", buyer="Petrov P.P.", date="11.01.2018")
write_order_to_json(item="scaner", quantity="20", price="10000", buyer="Petrov P.P.", date="11.01.2018")
write_order_to_json('компьютер', '5', '40000', 'Sidorov S.S.', '2.05.2019')
