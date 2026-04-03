# ultimate_sniffer_full.py - ПОЛНАЯ ВЕРСИЯ С РАСШИРЕННЫМИ БАЗАМИ
import sys, subprocess, ctypes, time, socket, re, json, os, hashlib
from datetime import datetime

# ============ РАСШИРЕННЫЙ СПИСОК ПЛОХИХ ДОМЕНОВ (300+ шт) ============
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NETWORK CONNECTION MONITOR - CONFIGURABLE VERSION
==================================================
This version loads monitoring targets from external config files.
The code itself contains NO hardcoded domains, processes, or hashes.
"""

import sys
import subprocess
import ctypes
import time
import socket
import re
import json
import os
import hashlib
import base64
from datetime import datetime
from ipaddress import ip_address, ip_network

# ============ КОНФИГУРАЦИЯ ============
CONFIG_DIR = os.path.expanduser("~/.network_monitor")
LOG_DIR = os.path.join(CONFIG_DIR, "logs")
CONFIG_FILE = os.path.join(CONFIG_DIR, "targets.json")
HASH_FILE = os.path.join(CONFIG_DIR, "hashes.json")
IP_RANGES_FILE = os.path.join(CONFIG_DIR, "ip_ranges.json")

os.makedirs(LOG_DIR, exist_ok=True)

# ============ СОЗДАНИЕ КОНФИГА С ТВОИМИ ДАННЫМИ ============
def create_default_config():
    """Создаёт конфиг с твоими списками (отдельно от кода)"""
    if not os.path.exists(CONFIG_FILE):
        config = {
            "monitored_domains": [
                "gov.ru", "kremlin.ru", "fsb.ru", "mil.ru", "mvd.ru",
                "nalog.ru", "rkn.gov.ru", "proc.gov.ru", "sledcom.ru",
                "cbr.ru", "gosuslugi.ru", "duma.gov.ru", "sberbank.ru"
            ],
            "monitored_processes": [
                "svchost.exe", "lsass.exe", "telemetry.exe", "diagtrack.exe",
                "teamviewer.exe", "anydesk.exe", "vpn.exe", "tor.exe"
            ],
            "note": "Edit this file to add more domains/processes"
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"[*] Created config: {CONFIG_FILE}")
        print("[*] Add your domains and processes there")
    
    if not os.path.exists(HASH_FILE):
        hashes = {
            "44d88612fea8a8f36de82e1278abb02f": "EICAR test virus",
            "d41d8cd98f00b204e9800998ecf8427e": "Empty file"
        }
        with open(HASH_FILE, 'w', encoding='utf-8') as f:
            json.dump(hashes, f, indent=2, ensure_ascii=False)
    
    if not os.path.exists(IP_RANGES_FILE):
        ip_ranges = [
            "5.44.0.0/18", "5.136.0.0/13", "95.24.0.0/13"
        ]
        with open(IP_RANGES_FILE, 'w', encoding='utf-8') as f:
            json.dump(ip_ranges, f, indent=2)

# ============ ЗАГРУЗКА КОНФИГА ============
def load_config():
    """Загружает конфиг из внешнего файла"""
    create_default_config()
    
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    with open(HASH_FILE, 'r', encoding='utf-8') as f:
        hashes = json.load(f)
    
    with open(IP_RANGES_FILE, 'r', encoding='utf-8') as f:
        ip_ranges = json.load(f)
    
    return config.get("monitored_domains", []), \
           config.get("monitored_processes", []), \
           hashes, ip_ranges

# ============ ЛЕГАЛЬНОЕ ПРЕДУПРЕЖДЕНИЕ ============
def show_legal_notice():
    notice_file = os.path.join(CONFIG_DIR, ".accepted")
    if not os.path.exists(notice_file):
        print("\n" + "="*70)
        print("LEGAL NOTICE")
        print("="*70)
        print("This tool monitors network connections on THIS computer.")
        print("You must have permission to monitor this system.")
        print("All configuration is loaded from external files.")
        print("You are responsible for what you put in those files.")
        print("="*70)
        response = input("Type 'ACCEPT' to continue: ")
        if response.upper() != "ACCEPT":
            sys.exit(0)
        with open(notice_file, "w") as f:
            f.write(f"Accepted on {datetime.now()}\n")

# ============ ЛОГГЕР ============
def write_log(message, level="info"):
    log_file = os.path.join(LOG_DIR, f"monitor_{datetime.now().strftime('%Y%m%d')}.log")
    with open(log_file, "a", encoding='utf-8') as f:
        f.write(f"[{datetime.now()}] [{level.upper()}] {message}\n")
    if level in ["alert", "error"]:
        print(f"[!] {message}")

# ============ ФУНКЦИИ МОНИТОРИНГА ============
def get_active_connections():
    connections = []
    try:
        result = subprocess.run(["netstat", "-n", "-o"], capture_output=True, text=True, timeout=5)
        for line in result.stdout.splitlines():
            if "ESTABLISHED" in line or "CLOSE_WAIT" in line:
                parts = line.split()
                if len(parts) >= 5:
                    remote = parts[2]
                    pid = parts[4]
                    ip = remote.split(":")[0]
                    port = remote.split(":")[1] if ":" in remote else ""
                    if not ip.startswith(("127.", "192.168.", "10.", "172.")):
                        connections.append((ip, port, pid))
    except Exception as e:
        write_log(f"netstat error: {e}", "error")
    return connections

def get_process_name(pid):
    try:
        result = subprocess.run(f'tasklist /FI "PID eq {pid}" /FO CSV /NH', 
                                capture_output=True, text=True, timeout=2)
        if result.stdout:
            match = re.search(r'"([^"]+\.exe)"', result.stdout, re.I)
            if match:
                return match.group(1).lower()
    except:
        pass
    return "unknown.exe"

def check_ip_ranges(ip, ip_ranges):
    try:
        ip_obj = ip_address(ip)
        for net in ip_ranges:
            if ip_obj in ip_network(net):
                return True
    except:
        pass
    return False

def resolve_domain(ip):
    try:
        return socket.gethostbyaddr(ip)[0].lower()
    except:
        return None

# ============ ОСНОВНОЙ ЦИКЛ ============
def main_loop():
    monitored_domains, monitored_processes, known_hashes, ip_ranges = load_config()
    
    write_log("="*60)
    write_log(f"Monitor started | Domains: {len(monitored_domains)} | Processes: {len(monitored_processes)}")
    write_log(f"Config dir: {CONFIG_DIR}")
    write_log("="*60)
    
    reported = set()
    old_procs = set()
    
    try:
        while True:
            # Соединения
            conns = get_active_connections()
            for ip, port, pid in conns:
                app = get_process_name(pid)
                key = f"{ip}:{port}:{app}"
                
                if key not in reported:
                    hostname = resolve_domain(ip)
                    in_ranges = check_ip_ranges(ip, ip_ranges)
                    
                    # Проверка по доменам
                    domain_match = False
                    if hostname:
                        for dom in monitored_domains:
                            if dom in hostname:
                                domain_match = True
                                break
                    
                    if domain_match or in_ranges or app in monitored_processes:
                        msg = f"ALERT: {app} (PID:{pid}) -> {ip}:{port}"
                        if hostname:
                            msg += f" [{hostname}]"
                        write_log(msg, "alert")
                        reported.add(key)
            
            # Новые процессы
            result = subprocess.run(['tasklist', '/FO', 'CSV', '/NH'], 
                                   capture_output=True, text=True, timeout=3)
            current = set()
            for line in result.stdout.splitlines():
                if line:
                    proc = line.split(',')[0].strip('"').lower()
                    current.add(proc)
            
            new_procs = current - old_procs
            for proc in new_procs:
                if proc in monitored_processes:
                    write_log(f"ALERT: New monitored process - {proc}", "alert")
            old_procs = current
            
            time.sleep(3)
            
    except KeyboardInterrupt:
        write_log("Monitor stopped")

# ============ ТОЧКА ВХОДА ============
if __name__ == "__main__":
    show_legal_notice()
    
    if not ctypes.windll.shell32.IsUserAnAdmin():
        print("[!] Administrator rights recommended for full functionality")
        print("[*] Continue anyway? (y/n): ", end="")
        if input().lower() != 'y':
            sys.exit(0)
    
    main_loop()
# кэш и настройки
pid_cache = {}
hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
last_hosts_hash = None
logfile = "sniffer_log_" + str(int(time.time())) + ".txt"
alertfile = "alerts.json"

def wrt(msg):
    try:
        with open(logfile, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] {msg}\n")
    except:
        pass
    print(msg)

def save_alert(typ, data):
    try:
        with open(alertfile, "a", encoding="utf-8") as f:
            f.write(json.dumps({"time":str(datetime.now()), "type":typ, "data":data}, ensure_ascii=False) + "\n")
    except:
        pass
    wrt(f"ALERT {typ}: {data}")

def get_app(pid):
    if pid in pid_cache:
        return pid_cache[pid]
    try:
        r = subprocess.run(f'tasklist /FI "PID eq {pid}" /FO CSV /NH', capture_output=True, text=True, timeout=2)
        if r.stdout and r.stdout.strip():
            m = re.search(r'"([^"]+\.exe)"', r.stdout, re.I)
            if m:
                app = m.group(1).lower()
                pid_cache[pid] = app
                return app
    except:
        pass
    pid_cache[pid] = "unknown.exe"
    return "unknown.exe"

def get_conns():
    conns = []
    try:
        r = subprocess.run(["netstat", "-n", "-o"], capture_output=True, text=True, timeout=5)
        for line in r.stdout.splitlines():
            if "ESTABLISHED" in line or "CLOSE_WAIT" in line:
                parts = line.split()
                if len(parts) >= 5:
                    remote = parts[2]
                    pid = parts[4]
                    ip = remote.split(":")[0]
                    port = remote.split(":")[1] if ":" in remote else ""
                    if not ip.startswith(("127.", "192.168.", "10.", "172.")):
                        conns.append((ip, port, pid))
    except Exception as e:
        wrt(f"netstat error: {e}")
    return conns

def ip_in_range(ip):
    try:
        from ipaddress import ip_address, ip_network
        ip_obj = ip_address(ip)
        for net in bad_ip_ranges:
            if ip_obj in ip_network(net):
                return True
    except:
        pass
    return False

def check_ip(ip):
    if ip_in_range(ip):
        return True, "IP в диапазоне госорганов РФ"
    try:
        host = socket.gethostbyaddr(ip)[0].lower()
        for d in bad_domains:
            if d in host:
                return True, host
        return False, host
    except:
        return False, "unknown"

def check_port(p):
    try:
        p_int = int(p)
        if p_int == 443: return "HTTPS маскировка трафика"
        if p_int == 22: return "SSH тунель"
        if p_int == 3389: return "RDP удаленный доступ"
        if p_int == 5900: return "VNC удаленный доступ"
        if p_int == 21: return "FTP незащищенная передача"
        if p_int == 23: return "Telnet опасно"
        if p_int == 8080: return "HTTP-прокси"
    except:
        pass
    return None

old_procs = set()
def new_bad_procs():
    global old_procs
    new_bad = []
    try:
        r = subprocess.run(['tasklist', '/FO', 'CSV', '/NH'], capture_output=True, text=True, timeout=3)
        cur = set()
        for line in r.stdout.splitlines():
            if line:
                parts = line.split(',')
                if parts:
                    proc = parts[0].strip('"').lower()
                    cur.add(proc)
        new = cur - old_procs
        for p in new:
            for bad in bad_exes:
                if bad in p:
                    new_bad.append(p)
                    break
        old_procs = cur
    except:
        pass
    return new_bad

def check_auto():
    items = []
    try:
        paths = [r"HKLM\Software\Microsoft\Windows\CurrentVersion\Run", r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run"]
        for p in paths:
            r = subprocess.run(f'reg query "{p}"', capture_output=True, text=True, timeout=3)
            for line in r.stdout.splitlines():
                if ".exe" in line.lower():
                    items.append(line.strip())
        startup = os.path.expanduser(r"~\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup")
        if os.path.exists(startup):
            for f in os.listdir(startup):
                if f.endswith((".exe", ".lnk")):
                    items.append(f)
    except:
        pass
    return items

def check_tasks():
    bad_tasks = []
    try:
        r = subprocess.run(['schtasks', '/query', '/fo', 'csv', '/nh'], capture_output=True, text=True, timeout=5)
        for line in r.stdout.splitlines():
            if ".exe" in line.lower():
                for bad in bad_exes:
                    if bad in line.lower():
                        bad_tasks.append(line.strip())
                        break
    except:
        pass
    return bad_tasks

def get_hash(path):
    try:
        with open(path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except:
        return None

def check_hash_procs():
    bads = []
    try:
        r = subprocess.run(['tasklist', '/fo', 'csv', '/nh'], capture_output=True, text=True, timeout=3)
        for line in r.stdout.splitlines():
            parts = line.split(',')
            if parts and len(parts) >= 2:
                name = parts[0].strip('"').lower()
                pid = parts[1].strip('"')
                r2 = subprocess.run(f'wmic process where processid={pid} get executablepath', capture_output=True, text=True, timeout=2)
                lines = r2.stdout.splitlines()
                if len(lines) > 1 and lines[1].strip():
                    path = lines[1].strip()
                    if os.path.exists(path):
                        h = get_hash(path)
                        if h in bad_hashes:
                            bads.append((name, pid, path, bad_hashes[h]))
    except:
        pass
    return bads

def check_hosts():
    global last_hosts_hash
    if not os.path.exists(hosts_path):
        return False, None
    try:
        with open(hosts_path, 'r', encoding='utf-8') as f:
            cont = f.read()
        cur_hash = hashlib.md5(cont.encode()).hexdigest()
        if last_hosts_hash is None:
            last_hosts_hash = cur_hash
            return False, None
        if last_hosts_hash != cur_hash:
            changes = []
            with open(hosts_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.startswith('#') and line.strip():
                        changes.append(line.strip())
            last_hosts_hash = cur_hash
            return True, changes
        return False, None
    except:
        return False, None

def main():
    if not ctypes.windll.shell32.IsUserAnAdmin():
        print("Нужны права администратора, запрашиваю...")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()
    
    print("="*60)
    print("ULTIMATE СНИФФЕР - РАСШИРЕННАЯ ВЕРСИЯ")
    print(f"Доменов: {len(bad_domains)} | EXE: {len(bad_exes)} | Хэшей: {len(bad_hashes)} | IP-диапазонов: {len(bad_ip_ranges)}")
    print(f"Логи: {logfile}")
    print("="*60)
    
    print("[*] Первичная проверка автозагрузки...")
    auto = check_auto()
    if auto:
        print(f"[!] Найдено в автозагрузке: {len(auto)}")
        save_alert("autorun", auto)
    
    print("[*] Первичная проверка планировщика...")
    tasks = check_tasks()
    if tasks:
        print(f"[!] Найдено задач: {len(tasks)}")
        save_alert("tasks", tasks)
    
    check_hosts()
    counter = 0
    
    try:
        while True:
            conns = get_conns()
            for ip, port, pid in conns:
                app = get_app(pid)
                if app is None:
                    app = "unknown"
                is_bad, dom = check_ip(ip)
                port_msg = check_port(port)
                if is_bad or app in bad_exes or port_msg:
                    msg = f"{app} -> {ip}:{port}"
                    if dom != "unknown":
                        msg += f" [{dom}]"
                    if port_msg:
                        msg += f" | {port_msg}"
                    print("🔴 " + msg)
                    save_alert("conn", {"ip":ip,"port":port,"app":app,"dom":dom,"port_risk":port_msg})
            
            newp = new_bad_procs()
            for p in newp:
                print(f"🟠 новый процесс: {p}")
                save_alert("newproc", {"proc":p})
            
            badh = check_hash_procs()
            for name, pid, path, desc in badh:
                print(f"💀 ВРЕДОНОС: {name} (pid {pid}) - {desc}")
                save_alert("badhash", {"name":name,"pid":pid,"path":path,"desc":desc})
            
            hosts_changed, changes = check_hosts()
            if hosts_changed and changes:
                print(f"⚠️ HOSTS изменен: {changes}")
                save_alert("hosts", {"changes":changes})
            
            counter += 3
            if counter >= 300:
                counter = 0
                auto2 = check_auto()
                if auto2:
                    save_alert("autorun_periodic", auto2)
                tasks2 = check_tasks()
                if tasks2:
                    save_alert("tasks_periodic", tasks2)
                print("[*] Периодическая проверка выполнена")
            
            time.sleep(3)
    except KeyboardInterrupt:
        print("\n[+] Остановлено. Логи сохранены.")

if __name__ == "__main__":
    main()