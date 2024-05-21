Данный скрипт изменяет hostname активного сетевого оборудования на то, как указано в **NetBox**.

Для его работы нужно:
- учетка с правами конфигурировать сетевые устройства.
- токен для NetBox с правами на чтение. 

Токен и пароль от устройства запрашиваются в **secure** формате.

Логика работы следующая:

1. Выполняется api запрос в netbox, откуда выгружаются все устройства, которые имеют статус **active** и отмечен любой из ip устройства, как **primary_ip**.
2. Далее, скрипт локально проходится по объектам выгрузки и выбирает только устройства, которые попадают под **regex**. В данном примере - **"^skd.*" и "^skr.*"**.
3. Из полученных устройств собирается вложенный словарь, где ключом является **primary_ip**, а значением - вложенные поля **device_platform** и **device_name**.
   - **device_platform** позволяет определить синтаксис даже в разрезе одного вендора.
   - **device_name** используется для передачи в функцию для дальнейшего сравнения реального имени с тем, которое указано в **SoT**.
4. Далее, идет итерация по полученному словарю и в зависимости от **device_platform** выбирается функция, которая будет править hostname. 
5. Скрипт является идемпотентным, т.е. конфигурирование устройства выполняется только в случае, если оно необходимо.

Значения переменных:
- *netbox_url* - url экземпляра netbox.
- *name_regex* - список регулярок, на основе которых будет составлен локальный словарь с устройствами.
- **sessions_log* - включение логирования ssh сессии и команд per platform. Будет создаваться лог файл в корне директории скрипта с ip устройства.
- *cisco, mes23, esr* и тд - переменные для платформ, которые используется в netbox.