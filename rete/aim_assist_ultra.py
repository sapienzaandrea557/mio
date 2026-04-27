import cv2
import numpy as np
import mss
import keyboard
import time
import ctypes
import math

# --- KERNEL LEVEL CONFIGURATION ---
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Ottimizzazione estrema: FOV Totale
# Analizziamo una porzione enorme dello schermo per trovare nemici ovunque
SCREEN_W = user32.GetSystemMetrics(0)
SCREEN_H = user32.GetSystemMetrics(1)
FOV_W = 600  # Area di scansione massiccia
FOV_H = 400

# Parametri God-Mode (Massima Efficacia)
SMOOTHING = 0.5        # Più veloce per agganciare bersagli in corsa
AUTO_FIRE = True
SILENT_AIM = True      # Se premi il tasto di sparo, il mirino scatta sul nemico
FIRE_THRESHOLD = 100   # Area di "Magic Bullets" (molto ampia)
MIN_AREA = 30          # Sensibilità alta per colpire anche piccoli pixel
MAX_MOVE_PER_FRAME = 60 # Permette scatti fulminei

# Tasti
TOGGLE_KEY = 'v'
is_active = False

def move_mouse_rel(x, y):
    """Sposta il mouse istantaneamente (Snap)."""
    user32.mouse_event(0x0001, int(x), int(y), 0, 0)

low_target = np.array([0, 200, 200], dtype=np.uint8) # Solo rossi ultra-saturi
high_target = np.array([5, 255, 255], dtype=np.uint8)

FOV_W = 400  # Ridotto per precisione chirurgica
FOV_H = 300
SMOOTHING = 0.6
MIN_AREA = 150 # Ignora macchie piccole, punta solo a corpi/nomi grandi

def click_and_snap(dx, dy):
    """Silent Aim: Scatto e sparo in un solo ciclo hardware."""
    user32.mouse_event(0x0001, int(dx), int(dy), 0, 0)
    user32.mouse_event(0x0002, 0, 0, 0, 0) # Down
    user32.mouse_event(0x0004, 0, 0, 0, 0) # Up

def main():
    global is_active
    print("💀 KRUNKER EXTREME OVERHAUL - C++ HYBRID 💀")
    
    with mss.mss() as sct:
        monitor = {
            "top": SCREEN_H // 2 - FOV_H // 2,
            "left": SCREEN_W // 2 - FOV_W // 2,
            "width": FOV_W,
            "height": FOV_H,
        }

        while True:
            if keyboard.is_pressed(TOGGLE_KEY):
                is_active = not is_active
                print("⚡ EXTREME MODE: ON" if is_active else "💤 EXTREME MODE: OFF")
                time.sleep(0.3)

            if is_active:
                img = np.array(sct.grab(monitor))
                frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                
                # Maschera ultra-selettiva per evitare il pavimento
                mask = cv2.inRange(hsv, low_target, high_target)
                mask = cv2.erode(mask, None, iterations=3) 
                mask = cv2.dilate(mask, None, iterations=3)
                
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                if contours:
                    # Prendi solo il contorno più grande e più "verticale" (umanoide)
                    best_target = None
                    max_area = 0
                    
                    for c in contours:
                        area = cv2.contourArea(c)
                        if area > MIN_AREA:
                            x, y, w, h = cv2.boundingRect(c)
                            if h > w * 1.2: # Filtro verticale: deve essere un nemico in piedi
                                if area > max_area:
                                    max_area = area
                                    best_target = (x + w//2, y + h//2)

                    if best_target:
                        dx = best_target[0] - FOV_W // 2
                        dy = best_target[1] - FOV_H // 2

                        # MAGIC BULLET LOGIC
                        if user32.GetAsyncKeyState(0x01) or AUTO_FIRE:
                            click_and_snap(dx, dy)
                            time.sleep(0.01)
                        else:
                            # Inseguimento fluido
                            user32.mouse_event(0x0001, int(dx * SMOOTHING), int(dy * SMOOTHING), 0, 0)


            if keyboard.is_pressed('esc'):
                break

if __name__ == "__main__":
    main()
