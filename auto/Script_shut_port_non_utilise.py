import re
import csv
from datetime import datetime
from netmiko import ConnectHandler

# ================= CONFIG =================
THRESHOLD_WEEKS = 9
THRESHOLD_SECONDS = THRESHOLD_WEEKS * 7 * 24 * 3600

DRY_RUN = False  # True pour executer no

DEVICE = {
    "device_type": "cisco_ios",
    "host": "10.49.82.174",
    "username": "rancid",
    "password": "monit0r R@ncid",
    
}

# ================= UTILS =================
def convert_to_seconds(time_str):
    time_str = time_str.strip().replace(",", "")

    if "never" in time_str:
        return float("inf")

    if ":" in time_str:
        h, m, s = map(int, time_str.split(":"))
        return h*3600 + m*60 + s

    total = 0
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


def has_description(run_conf):
    return re.search(r"^\s*description\s+", run_conf, re.MULTILINE) is not None


def is_trunk(run_conf):
    return "switchport mode trunk" in run_conf.lower()


# ================= MAIN =================
conn = ConnectHandler(**DEVICE)
conn.enable()

print("📡 Collecte des données...")

# 1️⃣ Status interfaces (rapide)
status_output = conn.send_command("show interfaces status")

status_dict = {}
interfaces = []

for line in status_output.splitlines():
    if re.match(r"^(Gi|Fi)", line):
        parts = line.split()
        intf = parts[0]
        status = parts[1]
        status_dict[intf] = status
        interfaces.append(intf)

# 2️⃣ Running-config complet (1 seule commande ⚡)
running_config = conn.send_command("show running-config")

# Split par interface
interface_configs = {}
current_intf = None

for line in running_config.splitlines():
    if line.startswith("interface"):
        current_intf = line.split()[1]
        interface_configs[current_intf] = []
    elif current_intf:
        interface_configs[current_intf].append(line)

# ================= ANALYSE =================
results = []
to_shutdown = []

for intf in interfaces:
    details = conn.send_command(f"show interface {intf}")

    run_conf = "\n".join(interface_configs.get(intf, []))

    # Vérifie si interface totalement inactive
    never_used = bool(re.search(
    r"Last input never,\s*output never,\s*output hang never",
    details,
    re.IGNORECASE
    ))

# Extraction Last input classique
    match = re.search(r"Last input ([^,]+)", details)
    last_input = match.group(1).strip() if match else "unknown"

    seconds = convert_to_seconds(last_input)

# Interface considérée ancienne/inactive
    is_old = never_used or (seconds > THRESHOLD_SECONDS)
    is_down = "line protocol is down" in details
    connected = status_dict.get(intf) == "connected"

    desc = has_description(run_conf)
    trunk = is_trunk(run_conf)

    decision = "KEEP"

    if is_old and is_down and not desc and not trunk and not connected:
        decision = "SHUTDOWN"
        to_shutdown.append(intf)

    print(f"{intf:12} | last={last_input:10} | down={is_down} | decision={decision}")

    results.append({
        "interface": intf,
        "last_input": last_input,
        "seconds": seconds,
        "description": desc,
        "trunk": trunk,
        "status": status_dict.get(intf),
        "decision": decision
    })

# ================= REPORT =================
filename = f"report_interfaces_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

if results:
 with open(filename, mode="w", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=results[0].keys())
    writer.writeheader()
    writer.writerows(results)

 print(f"\n📄 Rapport généré : {filename}")

else:
 print("\n⚠️ Aucun résultat trouvé — fichier CSV non généré")

# ================= SUMMARY =================
print("\n📊 Résumé :")
print(f"Total interfaces : {len(interfaces)}")
print(f"À shutdown       : {len(to_shutdown)}")

# ================= ACTION =================
if DRY_RUN:
    print("\n🔒 DRY-RUN actif — aucune modification effectuée")
else:
    if to_shutdown:
        confirm = input(f"\nConfirmer shutdown de {len(to_shutdown)} interfaces ? (yes/no): ")

        if confirm.lower() == "yes":
            config = []

            for intf in to_shutdown:
                config.extend([
                    f"interface {intf}",
                    "shutdown"
                ])

            conn.send_config_set(config)
            conn.send_command("write memory")

            print("✅ Shutdown effectué + config sauvegardée")
        else:
            print("❌ Annulé")
    else:
        print("✅ Rien à shutdown")

conn.disconnect()
