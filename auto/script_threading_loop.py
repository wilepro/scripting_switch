from netmiko import ConnectHandler
from inventory import DEVICES
from concurrent.futures import ThreadPoolExecutor
from rich import print



def send_show_command(device):
    with ConnectHandler(
        device_type="cisco_ios",
        host=device["host"],
        username="wilson",
        password="cisco"
    ) as connection:
        result = connection.send_command(command_string="show ip int brief")
        return result

with ThreadPoolExecutor() as executor:
    results = executor.map(send_show_command, DEVICES)
    for result in results:
        print(result)