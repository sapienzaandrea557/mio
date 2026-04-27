import unittest
import os
import json
import sys
from datetime import datetime

# Aggiungiamo il path per importare i moduli core
sys.path.append(os.path.dirname(__file__))
import scuole_sicurezza_stradale as core

class TestSuperAgents(unittest.TestCase):
    
    def setUp(self):
        # Mocking minimal config if needed
        core.CONFIG["tua_email"] = "test@example.com"

    def test_email_template_rendering(self):
        """Verifica che il template email sostituisca correttamente i placeholder."""
        context = {"nome_scuola": "Liceo Test", "citta": "Roma"}
        # Usiamo una stringa di fallback se il file non esiste per il test unitario
        html = core.carica_template_email("non_existent.html", context)
        self.assertIn("Liceo Test", html)
        self.assertIn("Roma", html)

    def test_miur_match_logic(self):
        """Verifica la logica di ricerca nel database MIUR (se esistente)."""
        if os.path.exists(core.MIUR_DB_FILE):
            # Proviamo a cercare una scuola che sappiamo esistere o usiamo il mock
            res = core.cerca_in_database_miur("NOME INESISTENTE", "COMUNE INESISTENTE")
            self.assertIsNone(res)
        else:
            print("Skip MIUR test: database non ancora scaricato.")

    def test_distanza_calcolo(self):
        """Verifica il calcolo della distanza tra due coordinate."""
        # Roma - Milano circa 470-480km
        d = core.calcola_distanza_km(41.89, 12.49, 45.46, 9.18)
        self.assertTrue(470 < d < 490)

    def test_tracking_logic_exists(self):
        """Verifica che la logica di tracking sia presente nel codice di invio."""
        import inspect
        source = inspect.getsource(core.invia_email)
        self.assertIn("email_id =", source)
        self.assertIn("tracking_pixel =", source)

if __name__ == "__main__":
    unittest.main()
