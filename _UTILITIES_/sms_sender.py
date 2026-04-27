import os
# Per usare questo script devi installare la libreria: pip install twilio
try:
    from twilio.rest import Client
except ImportError:
    print("Errore: Installa la libreria con 'pip install twilio'")
    exit()

def invia_notifica_personale():
    """
    Script per inviare messaggi/codici al proprio numero usando l'API ufficiale di Twilio.
    Nota: Non è possibile automatizzare l'invio di codici da siti terzi (Google, WhatsApp, ecc.) 
    perché i loro sistemi di sicurezza bloccano i bot.
    """
    
    # Ottieni questi dati creando un account gratuito su https://www.twilio.com
    account_sid = 'IL_TUO_ACCOUNT_SID'
    auth_token = 'IL_TUO_AUTH_TOKEN'
    numero_twilio = 'IL_TUO_NUMERO_TWILIO'
    
    client = Client(account_sid, auth_token)

    mio_numero = input("Inserisci il tuo numero di telefono (es. +39351...): ")
    codice_o_testo = input("Inserisci il messaggio o codice da inviare: ")

    try:
        message = client.messages.create(
            body=f"Promemoria/Codice: {codice_o_testo}",
            from_=numero_twilio,
            to=mio_numero
        )
        print(f"Fatto tutto! Messaggio inviato con successo. SID: {message.sid}")
    except Exception as e:
        print(f"Errore durante l'invio: {e}")

if __name__ == "__main__":
    invia_notifica_personale()
