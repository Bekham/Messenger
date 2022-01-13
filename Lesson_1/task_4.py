"""
Задание 4.

Преобразовать слова «разработка», «администрирование», «protocol»,
«standard» из строкового представления в байтовое и выполнить
обратное преобразование (используя методы encode и decode).

Подсказки:
--- используйте списки и циклы, не дублируйте функции
"""
words_list = ["разработка", "администрирование", "protocol", "standard"]
count = 1
for word in words_list:
    print(f"{count}. Word : {word}")
    code_point = word.encode("utf-8")
    print(f'Encode: {code_point} : {type(code_point)}')
    code_point_str = code_point.decode('utf-8')
    print(f'Decode: {code_point_str} : {type(code_point_str)}')
    count += 1