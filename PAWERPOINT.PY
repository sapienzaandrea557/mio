import os
import requests
import subprocess
import platform
import time
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

class PPTSmartAssistant:
    def __init__(self):
        self.prs = Presentation()
        self.file_name = "Presentazione_Roma_Monumenti.pptx"
        self.slides_data = []
        self.tema = ""

    def genera_struttura(self, tema, numero_slide):
        """Genera una lista di slide basata sul numero richiesto."""
        self.tema = tema
        self.slides_data = []
        
        # Concetti base per espandere la presentazione
        concetti_base = [
            {"t": "Introduzione", "k": "panorama, city view"},
            {"t": "Storia e Fondazione", "k": "ancient history, ruins"},
            {"t": "Architettura Iconica", "k": "monument, architecture"},
            {"t": "Simboli del Potere", "k": "empire, palace"},
            {"t": "Arte e Cultura", "k": "museum, art"},
            {"t": "La Vita Quotidiana", "k": "piazza, street life"},
            {"t": "Conclusioni e Futuro", "k": "modern city, sunset"}
        ]

        for i in range(numero_slide):
            # Se chiedi più di 7 slide, ricomincia il giro dei concetti o usa quelli generici
            base = concetti_base[i % len(concetti_base)]
            self.slides_data.append({
                "titolo": f"{base['t']}: {tema}",
                "testo": f"Analisi approfondita del tema: {tema}. Esplorazione dei dettagli storici, architettonici e dell'impatto culturale nel contesto di riferimento.",
                "keyword": f"{tema} {base['k']} cinematic lighting, professional photography"
            })

    def scarica_immagine(self, query, i):
        """Scarica l'immagine con controllo dell'integrità."""
        print(f"🎨 Generazione immagine AI per Slide {i+1}...")
        query_encoded = query.replace(" ", "%20")
        url = f"https://image.pollinations.ai/prompt/{query_encoded}?width=1920&height=1080&nologo=true&seed={int(time.time())+i}"
        path = f"temp_img_{i}.jpg"
        
        try:
            r = requests.get(url, timeout=20)
            # Verifica che la risposta sia un'immagine e non un errore HTML
            if r.status_code == 200 and "image" in r.headers.get("Content-Type", ""):
                with open(path, 'wb') as f:
                    f.write(r.content)
                return path
            else:
                print(f"⚠️ Immagine {i+1} non disponibile, userò uno sfondo neutro.")
                return None
        except Exception as e:
            print(f"❌ Errore durante il download: {e}")
            return None

    def costruisci_slide(self):
        """Assembla la presentazione gestendo eventuali immagini mancanti."""
        self.prs = Presentation()
        for i, slide_info in enumerate(self.slides_data):
            slide = self.prs.slides.add_slide(self.prs.slide_layouts[6]) # Vuota
            
            img_path = self.scarica_immagine(slide_info['keyword'], i)
            
            # Se l'immagine esiste ed è valida, la inserisce
            if img_path and os.path.exists(img_path):
                try:
                    self.prs.slides[i].shapes.add_picture(img_path, 0, 0, width=self.prs.slide_width, height=self.prs.slide_height)
                    os.remove(img_path)
                except:
                    # Se PIL fallisce comunque a leggere il file, crea uno sfondo colorato
                    print(f"⚠️ File immagine corrotto per slide {i+1}, procedo con sfondo colorato.")
                    self._crea_sfondo_pieno(slide)
            else:
                self._crea_sfondo_pieno(slide)

            # Fascia scura per testo
            shape = slide.shapes.add_shape(1, Inches(0), Inches(5.5), self.prs.slide_width, Inches(3.5))
            shape.fill.solid()
            shape.fill.fore_color.rgb = RGBColor(10, 10, 10)
            shape.line.fill.background()

            # Titolo
            box_t = slide.shapes.add_textbox(Inches(0.5), Inches(5.8), Inches(9), Inches(1))
            p_t = box_t.text_frame.paragraphs[0]
            p_t.text = slide_info['titolo'].upper()
            p_t.font.size = Pt(36)
            p_t.font.bold = True
            p_t.font.color.rgb = RGBColor(255, 215, 0) # Oro

            # Testo
            box_b = slide.shapes.add_textbox(Inches(0.5), Inches(6.8), Inches(9), Inches(2))
            p_b = box_b.text_frame.paragraphs[0]
            p_b.text = slide_info['testo']
            p_b.font.size = Pt(20)
            p_b.font.color.rgb = RGBColor(255, 255, 255)

        self.prs.save(self.file_name)
        self.apri_file()

    def _crea_sfondo_pieno(self, slide):
        """Crea uno sfondo blu scuro elegante se l'immagine fallisce."""
        rect = slide.shapes.add_shape(1, 0, 0, self.prs.slide_width, self.prs.slide_height)
        rect.fill.solid()
        rect.fill.fore_color.rgb = RGBColor(20, 40, 60)
        rect.line.fill.background()

    def apri_file(self):
        full_path = os.path.abspath(self.file_name)
        print(f"\n✅ Presentazione salvata: {full_path}")
        try:
            if platform.system() == "Windows": os.startfile(self.file_name)
            else: subprocess.call(["open" if platform.system() == "Darwin" else "xdg-open", self.file_name])
        except: pass

def main():
    bot = PPTSmartAssistant()
    print("--- ASSISTENTE POWERPOINT INTELLIGENTE v2 ---")
    tema = input("💡 Tema della presentazione (es: Roma Imperiale): ")
    try:
        num_slide = int(input("🔢 Quante slide vuoi? "))
    except:
        num_slide = 5
    
    bot.genera_struttura(tema, num_slide)
    bot.costruisci_slide()

    while True:
        print("\n" + "="*40)
        print("COSA VUOI FARE?")
        print("1) Cambia immagine a UNA slide")
        print("2) Cambia stile a TUTTE le slide")
        print("3) Esci")
        scelta = input("👉 ")

        if scelta == '1':
            idx = int(input(f"Numero slide (1-{len(bot.slides_data)}): ")) - 1
            if 0 <= idx < len(bot.slides_data):
                bot.slides_data[idx]['keyword'] = input("Nuova descrizione immagine (in inglese): ")
                bot.costruisci_slide()
        elif scelta == '2':
            stile = input("Nuovo stile (es: 'vintage photography', 'digital art'): ")
            for s in bot.slides_data:
                s['keyword'] = f"{bot.tema} {stile}"
            bot.costruisci_slide()
        elif scelta == '3':
            break

if __name__ == "__main__":
    main()