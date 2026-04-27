import cv2
import numpy as np
import mss
import keyboard
import time
import ctypes # Chiamate dirette alle funzioni C di Windows

# --- OTTIMIZZAZIONE C-STYLE (User32.dll) ---
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

def move_mouse(x, y):
    """Sposta il mouse usando SendInput (C++ style), molto più veloce e stealth."""
    user32.mouse_event(0x0001, int(x), int(y), 0, 0)

def click():
    """Click fulmineo tramite chiamate dirette alla DLL."""
    user32.mouse_event(0x0002, 0, 0, 0, 0) # Left Down
    user32.mouse_event(0x0004, 0, 0, 0, 0) # Left Up

# --- CONFIGURAZIONE KRUNKER TOP MODE ---
FOV_SIZE = 140        # Più piccolo per massima velocità su Krunker
SCREEN_WIDTH = user32.GetSystemMetrics(0)
SCREEN_HEIGHT = user32.GetSystemMetrics(1)
SMOOTHING = 0.4       # Aumentato per "snap" più veloce sui bersagli
TRIGGERBOT = True
AUTO_FIRE_DELAY = 0.03 # Fuoco rapidissimo
DEADZONE = 1
MAX_MOVE = 35         # Permette scatti più veloci per i pro-player che saltano
MIN_AREA = 40         # Sensibilità maggiore per nemici lontani

# Colore Krunker Standard (Rosso Nemico)
target_low = np.array([0, 160, 160], dtype=np.uint8)
target_high = np.array([5, 255, 255], dtype=np.uint8)

# Tasti di controllo
TOGGLE_KEY = 'v'
LEARN_KEY = 'c'
RESET_KEY = 'r'
FLY_KEY = 'space'     # BHOP Mode
AUTO_SLIDE = True     # Slide-hop automatico quando premi spazio

# Stato Iniziale
is_active = False
fly_mode = False      # Se True, attiva il salto a raffica


# Memoria per predizione movimento
last_target_pos = None
last_time = time.time()

def press_key(key_code):
    """Simula la pressione di un tasto a basso livello (C++ Style)."""
    user32.keybd_event(key_code, 0, 0, 0)
    user32.keybd_event(key_code, 0, 0x0002, 0) # KEYUP

def auto_learn_color(sct, monitor):
    """Cattura il colore esattamente al centro del mirino e adatta il range."""
    img = np.array(sct.grab(monitor))
    hsv = cv2.cvtColor(cv2.cvtColor(img, cv2.COLOR_BGRA2BGR), cv2.COLOR_BGR2HSV)
    
    # Prendi un piccolo quadrato centrale (5x5 pixel)
    mid = FOV_SIZE // 2
    sample = hsv[mid-2:mid+2, mid-2:mid+2]
    avg_hsv = np.mean(sample, axis=(0, 1))
    
    low = np.array([max(0, avg_hsv[0]-15), 80, 80], dtype=np.uint8)
    high = np.array([min(180, avg_hsv[0]+15), 255, 255], dtype=np.uint8)
    
    print(f"🎯 COLORE APPRESO: HSV {avg_hsv.astype(int)}")
    return low, high

def main():
    global is_active, target_low, target_high, last_target_pos, last_time, fly_mode
    
    print(f"--- INTELLIGENT BROWSER ASSIST v2.0 ---")
    print(f"[{TOGGLE_KEY.upper()}] On/Off | [{LEARN_KEY.upper()}] Apprendi Colore | [{RESET_KEY.upper()}] Reset")
    print(f"[{FLY_KEY.upper()}] Fly/Jump Mode (Mantieni premuto)")
    
    with mss.mss() as sct:
        monitor = {
            "top": SCREEN_HEIGHT // 2 - FOV_SIZE // 2,
            "left": SCREEN_WIDTH // 2 - FOV_SIZE // 2,
            "width": FOV_SIZE,
            "height": FOV_SIZE,
        }

        while True:
            # 1. Comandi Rapidi
            if keyboard.is_pressed(TOGGLE_KEY):
                is_active = not is_active
                print(">>> STATO: ATTIVO <<<" if is_active else "--- STATO: PAUSA ---")
                time.sleep(0.3)

            # Fly Mode (Rapid Jump / Slide Hop)
            if keyboard.is_pressed(FLY_KEY):
                # Simula la pressione veloce di Space (VK_SPACE = 0x20)
                press_key(0x20)
                if AUTO_SLIDE:
                    # Simula lo slide (Shift) subito dopo il salto per Krunker
                    time.sleep(0.02)
                    press_key(0x10) # VK_LSHIFT = 0x10

            if keyboard.is_pressed(LEARN_KEY):
                target_low, target_high = auto_learn_color(sct, monitor)
                time.sleep(0.3)

            if keyboard.is_pressed(RESET_KEY):
                target_low = np.array([0, 150, 150], dtype=np.uint8)
                target_high = np.array([10, 255, 255], dtype=np.uint8)
                print("♻️ RESET COLORE: Rosso predefinito")
                time.sleep(0.3)

            if is_active:
                # 2. Visione Artificiale
                img = np.array(sct.grab(monitor))
                frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

                mask = cv2.inRange(hsv, target_low, target_high)
                # Pulizia immagine (rimuove puntini piccoli)
                mask = cv2.erode(mask, None, iterations=2)
                mask = cv2.dilate(mask, None, iterations=2)
                
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                if contours:
                    # Filtro "Intelligente": Cerca il contorno che sembra più un nemico
                    targets = []
                    for c in contours:
                        area = cv2.contourArea(c)
                        if area > MIN_AREA: # Ignora particelle troppo piccole
                            x, y, w, h = cv2.boundingRect(c)
                            aspect_ratio = h / w
                            # Un nemico di solito è più alto che largo (humanoid ratio)
                            if 0.5 < aspect_ratio < 5.0:
                                targets.append((c, area, x + w//2, y + h//2))

                    if targets:
                        # Prendi il target più vicino al centro del mirino
                        best_target = min(targets, key=lambda t: (t[2]-FOV_SIZE//2)**2 + (t[3]-FOV_SIZE//2)**2)
                        _, _, tx, ty = best_target

                        # 3. Calcolo Spostamento
                        diff_x = tx - FOV_SIZE // 2
                        diff_y = ty - FOV_SIZE // 2
                        
                        # Applica Deadzone
                        if abs(diff_x) < DEADZONE: diff_x = 0
                        if abs(diff_y) < DEADZONE: diff_y = 0

                        # Limita lo spostamento massimo per frame (evita feedback loop)
                        move_x = max(-MAX_MOVE, min(MAX_MOVE, diff_x * SMOOTHING))
                        move_y = max(-MAX_MOVE, min(MAX_MOVE, diff_y * SMOOTHING))

                        # 4. Azione
                        if move_x != 0 or move_y != 0:
                            move_mouse(move_x, move_y)

                        if TRIGGERBOT and abs(diff_x) < 8 and abs(diff_y) < 8:
                            click()
                            time.sleep(AUTO_FIRE_DELAY)
                else:
                    last_target_pos = None

            if keyboard.is_pressed('esc'):
                break

if __name__ == "__main__":
    main()
