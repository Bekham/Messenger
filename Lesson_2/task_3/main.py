"""
3. Задание на закрепление знаний по модулю yaml.
 Написать скрипт, автоматизирующий сохранение данных
 в файле YAML-формата.
Для этого:

Подготовить данные для записи в виде словаря, в котором
первому ключу соответствует список, второму — целое число,
третьему — вложенный словарь, где значение каждого ключа —
это целое число с юникод-символом, отсутствующим в кодировке
ASCII(например, €);

Реализовать сохранение данных в файл формата YAML — например,
в файл file.yaml. При этом обеспечить стилизацию файла с помощью
параметра default_flow_style, а также установить возможность работы
с юникодом: allow_unicode = True;

Реализовать считывание данных из созданного файла и проверить,
совпадают ли они с исходными.
"""
import yaml

lots = {
'computer': '200€-1000€',
'printer': '100€-300€',
'keyboard': '5€-50€',
'mouse': '4€-7€'
}
def yaml_create(lots):
    items = []
    items_ptice = lots
    items_quantity = len(lots)
    for key in lots.keys():
        items.append(key)
    DATA_TO_YAML = {'items': items, 'items_ptice': items_ptice, 'items_quantity': items_quantity}
    with open('file.yaml', 'w', encoding='utf-8') as f_n:
        yaml.dump(DATA_TO_YAML, f_n, allow_unicode = True)

yaml_create(lots)
with open('file.yaml', encoding='utf-8') as f_n:
    print(f_n.read())