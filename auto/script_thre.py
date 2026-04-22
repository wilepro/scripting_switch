from netmiko import ConnectHandler
from inventory import DEVICES
from rich import print

for device in DEVICES:
    with ConnectHandler(
        device_type="cisco_ios",
        host=device["host"],
        username="wilson",
        password="cisco"
    ) as connection:
        result = connection.send_command(command_string="show ip int brief")
        print(result)