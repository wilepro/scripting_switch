from netmiko import ConnectHandler
from rich import print

my_device = {
    "device_type": "cisco_ios",
    "host": "192.168.1.141",
    "username": "learner",
    "password": "password1"
}

ospf_configs = ["router ospf 1", "router-id 1.1.1.1", "network 10.0.0.0 0.0.0.255 area 0"]

with ConnectHandler(**my_device) as connection:
    ospf_result = connection.send_config_set(config_commands=ospf_configs)
    print(ospf_result)
