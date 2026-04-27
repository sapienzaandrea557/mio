import cv2
import numpy as np
import sys
import os
import json

def find_template(screenshot_path, template_path, threshold=0.8):
    """
    Cerca un template in uno screenshot e restituisce le coordinate del centro.
    """
    if not os.path.exists(screenshot_path) or not os.path.exists(template_path):
        return None

    img_rgb = cv2.imread(screenshot_path)
    img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
    template = cv2.imread(template_path, 0)
    w, h = template.shape[::-1]

    res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
    loc = np.where(res >= threshold)
    
    # Prendi il match migliore
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    
    if max_val >= threshold:
        center_x = max_loc[0] + w // 2
        center_y = max_loc[1] + h // 2
        return {
            "x": int(center_x),
            "y": int(center_y),
            "confidence": float(max_val),
            "width": int(w),
            "height": int(h)
        }
    return None

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Uso: python visual_bridge.py [screenshot] [template] [threshold]"}))
        sys.exit(1)

    screenshot = sys.argv[1]
    template = sys.argv[2]
    threshold = float(sys.argv[3]) if len(sys.argv) > 3 else 0.8

    result = find_template(screenshot, template, threshold)
    if result:
        print(json.dumps(result))
    else:
        print(json.dumps({"found": False}))
