from netmiko import ConnectHandler
import re

device = {
    "device_type": "cisco_ios",
    "host": "192.168.10.1",
    "username": "cisco1",
    "password": "cisco123",
    
}

conn = ConnectHandler(**device)
conn.enable()

# Récupérer les interfaces Gigabit
output = conn.send_command("show interfaces status")

interfaces = []
for line in output.splitlines():
    if line.startswith("Gi"):
        interfaces.append(line.split()[0])

unused_interfaces = []

# Vérifier "Last input never"
for intf in interfaces:
    details = conn.send_command(f"show interface {intf}")
    
    if "Last input never" in details:
        unused_interfaces.append(intf)

# 🔒 (option safe) afficher avant action
print("Interfaces jamais utilisées :")
for i in unused_interfaces:
    print(i)

# ⚠️ Shutdown
if unused_interfaces:
    config_commands = []
    
    for intf in unused_interfaces:
        config_commands.append(f"interface {intf}")
        config_commands.append("shutdown")
    
    conn.send_config_set(config_commands)

    print("\nInterfaces mises en shutdown.")
else:
    print("\nAucune interface concernée.")

conn.disconnect()