"""
Задание 3.

Определить, какие из слов «attribute», «класс», «функция», «type»
невозможно записать в байтовом типе с помощью маркировки b'' (без encode decode).

Подсказки:
--- используйте списки и циклы, не дублируйте функции
--- обязательно!!! усложните задачу, "отловив" и обработав исключение,
придумайте как это сделать
"""
text_list = ['attribute', 'класс', 'функция', 'type']
for word in text_list:
    try:
        word_b = bytes(word, 'ascii')
        print(f'Word: {word_b} - type {type(word_b)} - len {len(word_b)}')
    except:
        print(f'This word: "{word}" impossibible to write in byte view with mark "b" ')