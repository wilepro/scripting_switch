from netmiko import ConnectHandler
from rich import print 

my_device = {
    "device_type": "cisco_ios",
    "host": "192.168.2.50",
    "username": "wilson",
    "password": "cisco"
}

with ConnectHandler(**my_device) as connection:
    interfaces = connection.send_command(command_string="show interface ", use_textfsm=True)
    for interface in interfaces :
        print(interface ["mac_address"])