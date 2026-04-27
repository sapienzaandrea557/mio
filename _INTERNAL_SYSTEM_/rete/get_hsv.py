import cv2
import numpy as np
import sys

def pick_color(image_path):
    if not image_path:
        print("Trascina un'immagine sullo script o fornisci il percorso.")
        return

    img = cv2.imread(image_path)
    if img is None:
        print("Errore: Impossibile caricare l'immagine.")
        return

    hsv_img = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    def mouse_callback(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            pixel_hsv = hsv_img[y, x]
            print(f"\n📍 Coordinate: {x}, {y}")
            print(f"🎨 Valore HSV: {pixel_hsv}")
            print(f"👉 Copia questo nel tuo script: np.array([{pixel_hsv[0]-10}, 100, 100]), np.array([{pixel_hsv[0]+10}, 255, 255])")

    cv2.namedWindow("Color Picker - Clicca sul nemico")
    cv2.setMouseCallback("Color Picker - Clicca sul nemico", mouse_callback)

    print("--- COLOR PICKER ---")
    print("1. Clicca su un punto dell'immagine per vedere i valori HSV.")
    print("2. Premi 'ESC' per chiudere.")
    
    while True:
        cv2.imshow("Color Picker - Clicca sul nemico", img)
        if cv2.waitKey(1) & 0xFF == 27:
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else None
    pick_color(path)
