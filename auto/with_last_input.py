from netmiko import ConnectHandler
import re
import csv
from datetime import datetime

THRESHOLD_WEEKS = 24
THRESHOLD_SECONDS = THRESHOLD_WEEKS * 7 * 24 * 3600

DRY_RUN = True  # 🔒 True = simulation / False = applique

def convert_to_seconds(time_str):
    # 🔧 nettoyage
    time_str = time_str.strip().replace(",", "")

    if "never" in time_str:
        return float("inf")

    total = 0

    if ":" in time_str:
        parts = time_str.split(":")
        if len(parts) == 3:
            h, m, s = map(int, parts)
            return h*3600 + m*60 + s

    import re
    matches = re.findall(r'(\d+)([wdhm])', time_str)

    for value, unit in matches:
        value = int(value)
        if unit == 'w':
            total += value * 7 * 24 * 3600
        elif unit == 'd':
            total += value * 24 * 3600
        elif unit == 'h':
            total += value * 3600
        elif unit == 'm':
            total += value * 60

    return total


device = {
    "device_type": "cisco_ios",
    "host": "192.168.10.1",
    "username": "cisco1",
    "password": "cisco123",
    
}

conn = ConnectHandler(**device)
conn.enable()

status_output = conn.send_command("show interfaces status")

interfaces = []
for line in status_output.splitlines():
    if line.startswith("Gi"):
        interfaces.append(line.split()[0])

results = []
to_shutdown = []

for intf in interfaces:
    details = conn.send_command(f"show interface {intf}")
    run_conf = conn.send_command(f"show run interface {intf}")

    # --- Extraction last input ---
    match = re.search(r"Last input (\S+)", details)
    last_input = match.group(1) if match else "unknown"

    seconds = convert_to_seconds(last_input)

    # --- Critères ---
    is_old = (seconds == float("inf") or seconds > THRESHOLD_SECONDS)
    is_down = "line protocol is down" in details
    has_description = "description" in run_conf.lower()
    is_trunk = "trunk" in run_conf.lower()
    is_connected = "connected" in details

    decision = "KEEP"

    if is_old and is_down and not has_description and not is_trunk and not is_connected:
        decision = "SHUTDOWN"
        to_shutdown.append(intf)

    results.append({
        "interface": intf,
        "last_input": last_input,
        "seconds": seconds,
        "description": has_description,
        "trunk": is_trunk,
        "status": "DOWN" if is_down else "UP",
        "decision": decision
    })


# --- Rapport CSV ---
filename = f"report_interfaces_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

with open(filename, mode="w", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=results[0].keys())
    writer.writeheader()
    writer.writerows(results)

print(f"\n📄 Rapport généré : {filename}")

# --- Affichage ---
print("\nInterfaces à shutdown :")
for i in to_shutdown:
    print(i)

# --- Action ---
if not DRY_RUN and to_shutdown:
    confirm = input("\nConfirmer shutdown ? (yes/no): ")

    if confirm.lower() == "yes":
        config = []
        for intf in to_shutdown:
            config.append(f"interface {intf}")
            config.append("shutdown")

        conn.send_config_set(config)
        print("✅ Shutdown effectué")
    else:
        print("❌ Annulé")
else:
    print("\n🔒 Mode DRY-RUN actif (aucune modification)")

conn.disconnect()
