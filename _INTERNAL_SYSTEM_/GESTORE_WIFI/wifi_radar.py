import tkinter as tk
from tkinter import ttk
import subprocess
import re
import threading
import math
import time
from datetime import datetime

BG      = "#060a0f"
SURFACE = "#0d1520"
CARD    = "#111c2a"
BORDER  = "#1a2d42"
ACCENT  = "#00d4ff"
GREEN   = "#00ff88"
YELLOW  = "#ffcc00"
RED     = "#ff4466"
MUTED   = "#4a6080"
TEXT    = "#c8e0f0"

def parse_reti():
    out = subprocess.run(["netsh", "wlan", "show", "networks", "mode=bssid"],
                         capture_output=True, text=True).stdout
    reti = []
    blocchi = re.split(r"SSID \d+ :", out)[1:]
    for b in blocchi:
        ssid     = re.search(r"^\s*(.+)", b)
        bssid    = re.search(r"BSSID \d+\s*:\s*(.+)", b)
        segnale  = re.search(r"Segnale\s*:\s*(\d+)%|Signal\s*:\s*(\d+)%", b)
        canale   = re.search(r"Canale\s*:\s*(\d+)|Channel\s*:\s*(\d+)", b)
        radio    = re.search(r"Tipo di radio\s*:\s*(.+)|Radio type\s*:\s*(.+)", b)
        auth     = re.search(r"Autenticazione\s*:\s*(.+)|Authentication\s*:\s*(.+)", b)
        cifrat   = re.search(r"Crittografia\s*:\s*(.+)|Encryption\s*:\s*(.+)", b)
        velocita = re.search(r"Velocit[àa] base\s*:\s*([\d,. ]+)|Basic rates.*:\s*([\d. ]+)", b)

        segnale_v = int(segnale.group(1) or segnale.group(2)) if segnale else 0
        dbm = int((segnale_v / 2) - 100) if segnale_v else -100

        reti.append({
            "ssid":     (ssid.group(1).strip() if ssid else "?"),
            "bssid":    (bssid.group(1).strip() if bssid else "?"),
            "segnale":  segnale_v,
            "dbm":      dbm,
            "canale":   (canale.group(1) or canale.group(2) if canale else "?"),
            "radio":    ((radio.group(1) or radio.group(2) or "?").strip() if radio else "?"),
            "auth":     ((auth.group(1) or auth.group(2) or "?").strip() if auth else "?"),
            "cifrat":   ((cifrat.group(1) or cifrat.group(2) or "?").strip() if cifrat else "?"),
            "velocita": ((velocita.group(1) or velocita.group(2) or "?").strip() if velocita else "?"),
        })
    reti.sort(key=lambda x: x["segnale"], reverse=True)
    return reti

class WifiRadar(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("WiFi Radar")
        self.geometry("1100x700")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.reti = []
        self.sel = [None]
        self.scan_running = [False]
        self.radar_angle = [0]
        self._build_ui()
        self._scan()
        self._animate_radar()

    def _build_ui(self):
        # header
        hdr = tk.Frame(self, bg=BG)
        hdr.pack(fill="x", padx=20, pady=(16, 0))

        tk.Label(hdr, text="WIFI RADAR", font=("Courier New", 22, "bold"),
                 bg=BG, fg=ACCENT).pack(side="left")

        self.stato_lbl = tk.Label(hdr, text="scansione...",
                                   font=("Courier New", 10), bg=BG, fg=MUTED)
        self.stato_lbl.pack(side="left", padx=16)

        self.count_lbl = tk.Label(hdr, text="",
                                   font=("Courier New", 10, "bold"), bg=BG, fg=GREEN)
        self.count_lbl.pack(side="left")

        self.scan_btn = tk.Button(hdr, text="↻  SCANSIONA",
                                   font=("Courier New", 10, "bold"),
                                   bg=SURFACE, fg=ACCENT, relief="flat",
                                   padx=14, pady=4, cursor="hand2",
                                   command=self._scan)
        self.scan_btn.pack(side="right")

        self.time_lbl = tk.Label(hdr, text="",
                                  font=("Courier New", 9), bg=BG, fg=MUTED)
        self.time_lbl.pack(side="right", padx=12)

        # corpo
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=12)

        # radar canvas (sinistra)
        radar_frame = tk.Frame(body, bg=CARD, bd=0,
                                highlightthickness=1, highlightbackground=BORDER)
        radar_frame.pack(side="left", fill="y")

        self.radar = tk.Canvas(radar_frame, width=300, height=300,
                                bg=BG, highlightthickness=0)
        self.radar.pack(padx=12, pady=12)

        # lista reti (destra)
        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=(12, 0))

        # header tabella
        th = tk.Frame(right, bg=SURFACE)
        th.pack(fill="x")
        for txt, w in [("SSID", 200), ("BSSID", 150), ("SEGNALE", 100),
                        ("CH", 40), ("RADIO", 90), ("SICUREZZA", 100), ("dBm", 60)]:
            tk.Label(th, text=txt, font=("Courier New", 9, "bold"),
                     bg=SURFACE, fg=MUTED, width=w//7, anchor="w",
                     padx=6).pack(side="left")

        # scrollable lista
        canvas2 = tk.Canvas(right, bg=BG, highlightthickness=0)
        vsb = ttk.Scrollbar(right, orient="vertical", command=canvas2.yview)
        self.lista_frame = tk.Frame(canvas2, bg=BG)
        self.lista_frame.bind("<Configure>",
            lambda e: canvas2.configure(scrollregion=canvas2.bbox("all")))
        canvas2.create_window((0, 0), window=self.lista_frame, anchor="nw")
        canvas2.configure(yscrollcommand=vsb.set)
        canvas2.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        canvas2.bind("<MouseWheel>",
            lambda e: canvas2.yview_scroll(int(-1*(e.delta/120)), "units"))

        # dettaglio in basso
        self.detail = tk.Frame(self, bg=CARD, bd=0,
                                highlightthickness=1, highlightbackground=BORDER)
        self.detail.pack(fill="x", padx=20, pady=(0, 16))
        self.detail_lbl = tk.Label(self.detail,
                                    text="Clicca una rete per vedere i dettagli",
                                    font=("Courier New", 10), bg=CARD, fg=MUTED,
                                    pady=10)
        self.detail_lbl.pack()

    def _segnale_color(self, pct):
        if pct >= 70: return GREEN
        if pct >= 40: return YELLOW
        return RED

    def _barre(self, pct):
        filled = round(pct / 20)
        return "█" * filled + "░" * (5 - filled)

    def _render_lista(self):
        for w in self.lista_frame.winfo_children():
            w.destroy()

        for i, r in enumerate(self.reti):
            col = self._segnale_color(r["segnale"])
            bg = CARD if i % 2 == 0 else SURFACE
            row = tk.Frame(self.lista_frame, bg=bg, cursor="hand2")
            row.pack(fill="x")

            # sicurezza icon
            sec = "🔒" if "WPA" in r["auth"] or "WPA" in r["cifrat"] else "🔓"

            cells = [
                (r["ssid"][:22], 200, ACCENT),
                (r["bssid"], 150, MUTED),
                (f"{self._barre(r['segnale'])} {r['segnale']}%", 100, col),
                (r["canale"], 40, TEXT),
                (r["radio"][:10], 90, MUTED),
                (f"{sec} {r['auth'][:8]}", 100, TEXT),
                (str(r["dbm"]), 60, MUTED),
            ]
            for txt, w, fg in cells:
                tk.Label(row, text=txt, font=("Courier New", 9),
                         bg=bg, fg=fg, width=w//7, anchor="w",
                         padx=6, pady=6).pack(side="left")

            row.bind("<Button-1>", lambda e, rete=r: self._select(rete))
            for child in row.winfo_children():
                child.bind("<Button-1>", lambda e, rete=r: self._select(rete))

        self._render_radar()

    def _select(self, rete):
        self.sel[0] = rete
        col = self._segnale_color(rete["segnale"])
        txt = (f"  {rete['ssid']}   │   BSSID: {rete['bssid']}   │   "
               f"Segnale: {rete['segnale']}% ({rete['dbm']} dBm)   │   "
               f"Canale: {rete['canale']}   │   Radio: {rete['radio']}   │   "
               f"Auth: {rete['auth']}   │   Cifrat: {rete['cifrat']}   │   "
               f"Velocità: {rete['velocita']} Mbps")
        self.detail_lbl.configure(text=txt, fg=col)

    def _render_radar(self):
        c = self.radar
        c.delete("static")
        cx, cy, r = 150, 150, 130

        # cerchi concentrici
        for i in range(1, 5):
            rr = r * i // 4
            c.create_oval(cx-rr, cy-rr, cx+rr, cy+rr,
                          outline=BORDER, tags="static")

        # croci
        c.create_line(cx-r, cy, cx+r, cy, fill=BORDER, tags="static")
        c.create_line(cx, cy-r, cx, cy+r, fill=BORDER, tags="static")

        # label dBm
        for i, dbm in enumerate([-50, -65, -80, -95]):
            rr = r * (i+1) // 4
            c.create_text(cx+4, cy-rr+8, text=str(dbm),
                          font=("Courier New", 7), fill=MUTED, tags="static")

        # punti reti
        for rete in self.reti:
            dist = max(0, min(1, (-rete["dbm"] - 40) / 60))
            rr = dist * r
            # angolo basato su canale
            try:
                ang = (int(rete["canale"]) * 25) % 360
            except:
                ang = hash(rete["ssid"]) % 360
            rad = math.radians(ang)
            x = cx + rr * math.cos(rad)
            y = cy + rr * math.sin(rad)
            col = self._segnale_color(rete["segnale"])
            size = 5 + rete["segnale"] // 25
            c.create_oval(x-size, y-size, x+size, y+size,
                          fill=col, outline="", tags="static")
            c.create_text(x, y-size-8, text=rete["ssid"][:10],
                          font=("Courier New", 7), fill=col, tags="static")

    def _animate_radar(self):
        c = self.radar
        c.delete("sweep")
        cx, cy, r = 150, 150, 130
        ang = self.radar_angle[0]
        rad = math.radians(ang)

        # linea sweep
        x = cx + r * math.cos(rad)
        y = cy + r * math.sin(rad)
        c.create_line(cx, cy, x, y, fill=ACCENT, width=2, tags="sweep")

        # scia
        for i in range(1, 8):
            a2 = math.radians(ang - i * 5)
            x2 = cx + r * math.cos(a2)
            y2 = cy + r * math.sin(a2)
            alpha = max(0, 255 - i * 30)
            col = f"#{0:02x}{int(alpha*0.8):02x}{int(alpha):02x}"
            c.create_line(cx, cy, x2, y2, fill=col, width=1, tags="sweep")

        self.radar_angle[0] = (ang + 3) % 360
        self.after(50, self._animate_radar)

    def _scan(self):
        if self.scan_running[0]:
            return
        self.scan_running[0] = True
        self.scan_btn.configure(state="disabled")
        self.stato_lbl.configure(text="scansione in corso...", fg=YELLOW)

        def worker():
            reti = parse_reti()
            self.reti = reti
            self.after(0, self._scan_done)

        threading.Thread(target=worker, daemon=True).start()

    def _scan_done(self):
        self.scan_running[0] = False
        self.scan_btn.configure(state="normal")
        n = len(self.reti)
        self.stato_lbl.configure(text="completata", fg=GREEN)
        self.count_lbl.configure(text=f"{n} reti trovate")
        self.time_lbl.configure(text=datetime.now().strftime("%H:%M:%S"))
        self._render_lista()

if __name__ == "__main__":
    app = WifiRadar()
    app.mainloop()
