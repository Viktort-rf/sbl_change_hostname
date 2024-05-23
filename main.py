import logging
import getpass
import re
from netmiko import ConnectHandler
from pynetbox import api

netbox_url = "https://netbox.example.ru"
# Regex для поиска устройств согласно шаблона не учитывая регистр
name_regex = [re.compile(r"^skd.*", re.IGNORECASE),
              re.compile(r"^skr.*", re.IGNORECASE)]
# Включение логирования ssh сессий для платформы
enable_cisco_sessions_log = False
enable_mes23_sessions_log = False
enable_mes24_sessions_log = False
enable_esr_sessions_log = False
enable_qsw46_sessions_log = False
enable_qsw33_sessions_log = False
enable_qsr_sessions_log = False
# Название платформ, как в NetBox
cisco = "cisco"
mes23 = "eltex-mesos23"
mes24 = "eltex-mesos24"
esr = "eltex-esros"
qtech46 = "qtech"
qtech33 = "qsw33"
qsr = "qsr"
username = input("Enter your device login: ")
password = getpass.getpass("Enter your device password: ")
netbox_token = getpass.getpass("Enter your NetBox TOKEN: ")


logging.basicConfig(filename='error.log', filemode='w', level=logging.ERROR, format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')


def remove_parentheses_substrings(s: str) -> str:
    """
    Удаляет подстроки, заключенные в круглые скобки, из входной строки.

    Параметры:
        s (str): Входная строка, из которой нужно удалить содержимое скобок вместе с самими скобками.

    Возвращает:
        str: Строку без подстрок в круглых скобках.
    
    Примеры:
        >>> remove_parentheses_substrings("skd020-brcsw01(1)")
        'skd020-brcsw01'
        
        >>> remove_parentheses_substrings("example(text)string")
        'examplestring'
        
        >>> remove_parentheses_substrings("no_parentheses_here")
        'no_parentheses_here'
    """
    pattern = r'\(.*?\)'
    result = re.sub(pattern, '', s)
    return result


def get_devices(nb_url, nb_token, device_name_regex):
    """
    Функция получает список активных устройств из NetBox, фильтрует их по регулярному выражению для имен устройств
    и возвращает вложенный словарь с IP-адресами устройств, их именами и платформами.

    Параметры:
        nb_url (str): URL для доступа к API NetBox.
        nb_token (str): Токен для аутентификации в API NetBox.
        device_name_regex (list of re.Pattern): Список регулярных выражений для фильтрации имен устройств.

    Возвращает:
        dict: Словарь, где ключи - IP-адреса устройств, а значения - вложенные словари с именем устройства
        и его платформой.
    """
    nb = api(url=nb_url, token=nb_token)
    devices = nb.dcim.devices.filter(status="active", has_primary_ip=True)
    filtered_devices = {}
    for device in devices:
        for regex in device_name_regex:
            if regex.match(device.name):
                filtered_devices[device.primary_ip.address.split("/")[0]] = {
                    "device_platform": device.platform.slug,
                    "device_name": remove_parentheses_substrings(device.name).lower()
                }
    return filtered_devices


def change_hostname_cisco(cisco_ip_address, cisco_username, cisco_password, cisco_dev_name, cisco_session_log=None):
    """
    Функция меняет hostname железки, если оно не соответствует имени в netbox

    Параметры:
        cisco_ip_address (str): ip address устройства.
        cisco_username (str): Имя пользователя для устройства.
        cisco_password (str): Пароль для устройства.
        cisco_dev_name (str): Имя устройства в netbox
        cisco_session_log (bool, optional): Включение/выключение логирования ssh сессий

    Возвращает:
        bool: True, если имя устройства было изменено.
              False, если имя устройства уже соответствует имени в NetBox.
    """
    device_info = {
        "device_type": "cisco_xe",
        "ip": cisco_ip_address,
        "username": cisco_username,
        "password": cisco_password,
        "read_timeout_override": 30,
    }
    if cisco_session_log:
        device_info["session_log"] = f"{cisco_ip_address}.log"

    net_connect = ConnectHandler(**device_info)
    sh_cisco_hostname = net_connect.send_command("show running-config | include hostname")
    sh_cisco_hostname = sh_cisco_hostname.split("\n")
    for i in sh_cisco_hostname:
        if i.startswith("hostname"):
            sh_cisco_hostname = i[9::]
            break
    if cisco_dev_name != sh_cisco_hostname:
        net_connect.send_config_set(f"hostname {cisco_dev_name}")
        net_connect.send_command("write memory")
        net_connect.disconnect()
        return True
    else:
        net_connect.disconnect()
        return False


def change_hostname_mes23(mes23_ip_address, mes23_username, mes23_password, mes23_dev_name, mes23_session_log=None):
    """
    Функция меняет hostname железки, если оно не соответствует имени в netbox

    Параметры:
        mes23_ip_address (str): ip address устройства.
        mes23_username (str): Имя пользователя для устройства.
        mes23_password (str): Пароль для устройства.
        mes23_dev_name (str): Имя устройства в netbox
        mes23_session_log (bool, optional): Включение/выключение логирования ssh сессий

    Возвращает:
        bool: True, если имя устройства было изменено.
              False, если имя устройства уже соответствует имени в NetBox.
    """
    device_info = {
        "device_type": "eltex",
        "ip": mes23_ip_address,
        "username": mes23_username,
        "password": mes23_password,
        "read_timeout_override": 30,
    }
    if mes23_session_log:
        device_info["session_log"] = f"{mes23_ip_address}.log"

    net_connect = ConnectHandler(**device_info)
    sh_mes23_hostname = net_connect.send_command("show running-config | include hostname")
    sh_mes23_hostname = sh_mes23_hostname.split("\n")
    for i in sh_mes23_hostname:
        if i.startswith("hostname"):
            sh_mes23_hostname = i[9::]
            break
    if mes23_dev_name != sh_mes23_hostname:
        net_connect.send_config_set(f"hostname {mes23_dev_name}", cmd_verify=False)
        wr_mem = net_connect.send_command_timing("write memory")
        if "Overwrite file [startup-config]" in wr_mem:
            wr_mem += net_connect.send_command_timing("Y")
        net_connect.disconnect()
        return True
    else:
        net_connect.disconnect()
        return False


def change_hostname_mes24(mes24_ip_address, mes24_username, mes24_password, mes24_dev_name, mes24_session_log=None):
    """
    Функция меняет hostname железки, если оно не соответствует имени в netbox

    Параметры:
        mes24_ip_address (str): ip address устройства.
        mes24_username (str): Имя пользователя для устройства.
        mes24_password (str): Пароль для устройства.
        mes24_dev_name (str): Имя устройства в netbox
        mes24_session_log (bool, optional): Включение/выключение логирования ssh сессий

    Возвращает:
        bool: True, если имя устройства было изменено.
              False, если имя устройства уже соответствует имени в NetBox.
    """
    device_info = {
        "device_type": "eltex",
        "ip": mes24_ip_address,
        "username": mes24_username,
        "password": mes24_password,
        "read_timeout_override": 30,
    }
    if mes24_session_log:
        device_info["session_log"] = f"{mes24_ip_address}.log"

    net_connect = ConnectHandler(**device_info)
    net_connect.send_command("set cli pagination off")
    sh_mes24_hostname = net_connect.send_command("show running-config | grep hostname")
    sh_mes24_hostname = sh_mes24_hostname.split("\n")
    for i in sh_mes24_hostname:
        if i.startswith("hostname"):
            sh_mes24_hostname = i[9::].replace('"','').strip()
            break
    if mes24_dev_name != sh_mes24_hostname:
        net_connect.send_config_set(f"hostname {mes24_dev_name}", cmd_verify=False)
        net_connect.send_command("write startup-config")
        net_connect.disconnect()
        return True
    else:
        net_connect.disconnect()
        return False


def change_hostname_esr(esr_ip_address, esr_username, esr_password, esr_dev_name, esr_session_log=None):
    """
    Функция меняет hostname железки, если оно не соответствует имени в netbox

    Параметры:
        esr_ip_address (str): ip address устройства.
        esr_username (str): Имя пользователя для устройства.
        esr_password (str): Пароль для устройства.
        esr_dev_name (str): Имя устройства в netbox
        esr_session_log (bool, optional): Включение/выключение логирования ssh сессий

    Возвращает:
        bool: True, если имя устройства было изменено.
              False, если имя устройства уже соответствует имени в NetBox.
    """
    device_info = {
        "device_type": "eltex_esr",
        "ip": esr_ip_address,
        "username": esr_username,
        "password": esr_password,
        "read_timeout_override": 30,
    }
    if esr_session_log:
        device_info["session_log"] = f"{esr_ip_address}.log"

    net_connect = ConnectHandler(**device_info)
    sh_esr_hostname = net_connect.send_command("show running-config | include hostname")
    sh_esr_hostname = sh_esr_hostname.split("\n")
    for i in sh_esr_hostname:
        if i.startswith("hostname"):
            sh_esr_hostname = i[9::]
            break
    if esr_dev_name != sh_esr_hostname:
        net_connect.send_config_set([f"hostname {esr_dev_name}",
                                     "do commit",
                                     "do confirm",
                                     "do save"])
        net_connect.disconnect()
        return True
    else:
        net_connect.disconnect()
        return False


def change_hostname_qsw46(qsw46_ip_address, qsw46_username, qsw46_password, qsw46_dev_name, qsw46_session_log=None):
    """
    Функция меняет hostname железки, если оно не соответствует имени в netbox

    Параметры:
        qsw46_ip_address (str): ip address устройства.
        qsw46_username (str): Имя пользователя для устройства.
        qsw46_password (str): Пароль для устройства.
        qsw46_dev_name (str): Имя устройства в netbox
        qsw46_session_log (bool, optional): Включение/выключение логирования ssh сессий

    Возвращает:
        bool: True, если имя устройства было изменено.
              False, если имя устройства уже соответствует имени в NetBox.
    """
    device_info = {
        "device_type": "cisco_xe",
        "ip": qsw46_ip_address,
        "username": qsw46_username,
        "password": qsw46_password,
        "read_timeout_override": 30,
    }
    if qsw46_session_log:
        device_info["session_log"] = f"{qsw46_ip_address}.log"

    net_connect = ConnectHandler(**device_info)
    sh_qsw46_hostname = net_connect.send_command("show running-config | include hostname")
    sh_qsw46_hostname = sh_qsw46_hostname.split("\n")
    for i in sh_qsw46_hostname:
        if i.startswith("hostname"):
            sh_qsw46_hostname = i[9::]
            break
    if qsw46_dev_name != sh_qsw46_hostname:
        net_connect.send_config_set(f"hostname {qsw46_dev_name}", config_mode_command="config terminal")
        wr_mem = net_connect.send_command_timing("write running-config")
        if "Confirm to overwrite current startup-config configuration [Y/N]:" in wr_mem:
            wr_mem += net_connect.send_command_timing("Y")
        net_connect.disconnect()
        return True
    else:
        net_connect.disconnect()
        return False


def change_hostname_qsw33(qsw33_ip_address, qsw33_username, qsw33_password, qsw33_dev_name, qsw33_session_log=None):
    """
    Функция меняет hostname железки, если оно не соответствует имени в netbox

    Параметры:
        qsw33_ip_address (str): ip address устройства.
        qsw33_username (str): Имя пользователя для устройства.
        qsw33_password (str): Пароль для устройства.
        qsw33_dev_name (str): Имя устройства в netbox
        qsw33_session_log (bool, optional): Включение/выключение логирования ssh сессий

    Возвращает:
        bool: True, если имя устройства было изменено.
              False, если имя устройства уже соответствует имени в NetBox.
    """
    device_info = {
        "device_type": "cisco_xe",
        "ip": qsw33_ip_address,
        "username": qsw33_username,
        "password": qsw33_password,
        "read_timeout_override": 30,
    }
    if qsw33_session_log:
        device_info["session_log"] = f"{qsw33_ip_address}.log"

    net_connect = ConnectHandler(**device_info)
    sh_qsw33_hostname = net_connect.send_command("show running-config | include hostname")
    sh_qsw33_hostname = sh_qsw33_hostname.split("\n")
    for i in sh_qsw33_hostname:
        if i.startswith("hostname"):
            sh_qsw33_hostname = i[9::].replace('"','').strip()
            break
    if qsw33_dev_name != sh_qsw33_hostname:
        net_connect.send_config_set(f"hostname {qsw33_dev_name}")
        wr_mem = net_connect.send_command_timing("write memory")
        if "Are you sure you want to save?" in wr_mem:
            wr_mem += net_connect.send_command_timing("Y")
        net_connect.disconnect()
        return True
    else:
        net_connect.disconnect()
        return False


def change_hostname_qsr(qsr_ip_address, qsr_username, qsr_password, qsr_dev_name, qsr_session_log=None):
    """
    Функция меняет hostname железки, если оно не соответствует имени в netbox

    Параметры:
        qsr_ip_address (str): ip address устройства.
        qsr_username (str): Имя пользователя для устройства.
        qsr_password (str): Пароль для устройства.
        qsr_dev_name (str): Имя устройства в netbox
        qsr_session_log (bool, optional): Включение/выключение логирования ssh сессий

    Возвращает:
        bool: True, если имя устройства было изменено.
              False, если имя устройства уже соответствует имени в NetBox.
    """
    device_info = {
        "device_type": "cisco_xe",
        "ip": qsr_ip_address,
        "username": qsr_username,
        "password": qsr_password,
        "read_timeout_override": 30,
    }
    if qsr_session_log:
        device_info["session_log"] = f"{qsr_ip_address}.log"

    net_connect = ConnectHandler(**device_info)
    net_connect.send_command("more off")
    sh_qsr_hostname = net_connect.send_command("show running-config | include hostname")
    sh_qsr_hostname = sh_qsr_hostname.split("\n")
    for i in sh_qsr_hostname:
        if i.startswith("hostname"):
            sh_qsr_hostname = i[9::]
            break
    if qsr_dev_name != sh_qsr_hostname:
        net_connect.send_config_set(f"hostname {qsr_dev_name}")
        wr_mem = net_connect.send_command_timing("write")
        if "Are you sure to overwrite" in wr_mem:
            wr_mem += net_connect.send_command_timing("Y")
        net_connect.disconnect()
        return True
    else:
        net_connect.disconnect()
        return False


# Получаем словарь с объектами
devices_dict = get_devices(netbox_url, netbox_token, name_regex)

if devices_dict:
    # Считаем кол-во устройств, для вывода инфо
    all_keys_count = len(devices_dict.keys())
    print(f"Summary device get from NetBox is {all_keys_count}\n\n")
    # Фиктивная переменная, для паузы скрипта до ввода любого символа
    garbage = input("Please ENTER for start script")

    # Итерируемся по словарю и получаем значения ключей
    for ip, dev_info in devices_dict.items():

        # Проверяем hostname устройств с платформой cisco
        if dev_info["device_platform"] == cisco:
            try:
                print(f"Connected to {dev_info['device_name']} (ip {ip})")
                if change_hostname_cisco(ip, username, password, dev_info['device_name'], enable_cisco_sessions_log):
                    print("Hostname change")
                else:
                    print(f"Hostname is already sync with NetBox")
            except Exception as e:
                error_msg = f"Failed to connect to {dev_info['device_name']} (ip {ip}): {e}"
                print(error_msg)
                logging.error(error_msg)

        # Проверяем hostname устройств с платформой mesos23
        elif dev_info["device_platform"] == mes23:
            try:
                print(f"Connected to {dev_info['device_name']} (ip {ip})")
                if change_hostname_mes23(ip, username, password, dev_info['device_name'], enable_mes23_sessions_log):
                    print("Hostname change")
                else:
                    print(f"Hostname is already sync with NetBox")
            except Exception as e:
                error_msg = f"Failed to connect to {dev_info['device_name']} (ip {ip}): {e}"
                print(error_msg)
                logging.error(error_msg)

        # Проверяем hostname устройств с платформой mesos24
        elif dev_info["device_platform"] == mes24:
            try:
                print(f"Connected to {dev_info['device_name']} (ip {ip})")
                if change_hostname_mes24(ip, username, password, dev_info['device_name'], enable_mes24_sessions_log):
                    print("Hostname change")
                else:
                    print(f"Hostname is already sync with NetBox")
            except Exception as e:
                error_msg = f"Failed to connect to {dev_info['device_name']} (ip {ip}): {e}"
                print(error_msg)
                logging.error(error_msg)

        # Проверяем hostname устройств с платформой eltex esr
        elif dev_info["device_platform"] == esr:
            try:
                print(f"Connected to {dev_info['device_name']} (ip {ip})")
                if change_hostname_esr(ip, username, password, dev_info['device_name'], enable_esr_sessions_log):
                    print("Hostname change")
                else:
                    print(f"Hostname is already sync with NetBox")
            except Exception as e:
                error_msg = f"Failed to connect to {dev_info['device_name']} (ip {ip}): {e}"
                print(error_msg)
                logging.error(error_msg)

        # Проверяем hostname устройств с платформой qtech (это qsw46)
        elif dev_info["device_platform"] == qtech46:
            try:
                print(f"Connected to {dev_info['device_name']} (ip {ip})")
                if change_hostname_qsw46(ip, username, password, dev_info['device_name'], enable_qsw46_sessions_log):
                    print("Hostname change")
                else:
                    print(f"Hostname is already sync with NetBox")
            except Exception as e:
                error_msg = f"Failed to connect to {dev_info['device_name']} (ip {ip}): {e}"
                print(error_msg)
                logging.error(error_msg)

        # Проверяем hostname устройств с платформой qsw33
        elif dev_info["device_platform"] == qtech33:
            try:
                print(f"Connected to {dev_info['device_name']} (ip {ip})")
                if change_hostname_qsw33(ip, username, password, dev_info['device_name'], enable_qsw33_sessions_log):
                    print("Hostname change")
                else:
                    print(f"Hostname is already sync with NetBox")
            except Exception as e:
                error_msg = f"Failed to connect to {dev_info['device_name']} (ip {ip}): {e}"
                print(error_msg)
                logging.error(error_msg)

        # Проверяем hostname устройств с платформой qsr
        elif dev_info["device_platform"] == qsr:
            try:
                print(f"Connected to {dev_info['device_name']} (ip {ip})")
                if change_hostname_qsw33(ip, username, password, dev_info['device_name'], enable_qsr_sessions_log):
                    print("Hostname change")
                else:
                    print(f"Hostname is already sync with NetBox")
            except Exception as e:
                error_msg = f"Failed to connect to {dev_info['device_name']} (ip {ip}): {e}"
                print(error_msg)
                logging.error(error_msg)

        else:
            print(f"Device {dev_info['device_name']} ({dev_info['device_platform']}) is not a known platform.")

        all_keys_count -= 1
        print(f"Remaining device count: {all_keys_count}\n")
else:
    print("Not device name match regex in NetBox.")

print("Скрипт завершен")
