"""
1. Задание на закрепление знаний по модулю CSV. Написать скрипт,
осуществляющий выборку определенных данных из файлов info_1.txt, info_2.txt,
info_3.txt и формирующий новый «отчетный» файл в формате CSV.

Для этого:

Создать функцию get_data(), в которой в цикле осуществляется перебор файлов
с данными, их открытие и считывание данных. В этой функции из считанных данных
необходимо с помощью регулярных выражений или другого инструмента извлечь значения параметров
«Изготовитель системы», «Название ОС», «Код продукта», «Тип системы».
Значения каждого параметра поместить в соответствующий список. Должно
получиться четыре списка — например, os_prod_list, os_name_list,
os_code_list, os_type_list. В этой же функции создать главный список
для хранения данных отчета — например, main_data — и поместить в него
названия столбцов отчета в виде списка: «Изготовитель системы»,
«Название ОС», «Код продукта», «Тип системы». Значения для этих
столбцов также оформить в виде списка и поместить в файл main_data
(также для каждого файла);

Создать функцию write_to_csv(), в которую передавать ссылку на CSV-файл.
В этой функции реализовать получение данных через вызов функции get_data(),
а также сохранение подготовленных данных в соответствующий CSV-файл;

Пример того, что должно получиться:

Изготовитель системы,Название ОС,Код продукта,Тип системы

1,LENOVO,Windows 7,00971-OEM-1982661-00231,x64-based

2,ACER,Windows 10,00971-OEM-1982661-00231,x64-based

3,DELL,Windows 8.1,00971-OEM-1982661-00231,x86-based

Обязательно проверьте, что у вас получается примерно то же самое.

ПРОШУ ВАС НЕ УДАЛЯТЬ СЛУЖЕБНЫЕ ФАЙЛЫ TXT И ИТОГОВЫЙ ФАЙЛ CSV!!!
"""
import csv

import chardet


def get_data():
    headers = ['Изготовитель системы', 'Название ОС', 'Код продукта', 'Тип системы']
    os_prod_list = []
    os_name_list = []
    os_code_list = []
    os_type_list = []
    for i in range(1, 4):
        with open(f'info_{i}.txt', 'rb') as f:
            content_b = f.read()
            result = chardet.detect(content_b)
            result_text = content_b.decode(result['encoding'])
            result_text_list = result_text.split('\r\n')
            for header in headers:
                for row in result_text_list:
                    if row.startswith(header):
                        if header == 'Изготовитель системы':
                            os_prod_list.append(row.split(":")[-1].strip())
                        if header == 'Название ОС':
                            os_name_list.append(row.split(":")[-1].strip())
                        if header == 'Код продукта':
                            os_code_list.append(row.split(":")[-1].strip())
                        if header == 'Тип системы':
                            os_type_list.append(row.split(":")[-1].strip())
    main_data = [headers]
    for i in range(0, 3):
        row_data = []
        row_data.append(os_prod_list[i])
        row_data.append(os_name_list[i])
        row_data.append(os_code_list[i])
        row_data.append(os_type_list[i])
        main_data.append(row_data)
    return main_data


def write_to_csv(filename):
    main_data = get_data()
    with open(filename, 'w', encoding='utf-8') as f_n:
        F_N_WRITER = csv.writer(f_n, quoting=csv.QUOTE_NONNUMERIC)
        F_N_WRITER.writerows(main_data)


write_to_csv('data_report.csv')
