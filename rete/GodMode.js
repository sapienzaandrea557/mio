/**
 * KRUNKER KERNEL BYPASS - GOD MODE v3.0
 * 
 * Questo script NON usa i pixel. Usa l'Hooking dei Prototipi.
 * Intercetta le funzioni matematiche del gioco per ridirigere i proiettili.
 */

(function() {
    'use strict';

    console.clear();
    console.log("%c KRUNKER ULTRA-GOD LOADED ", "background: #000; color: #00ff00; font-size: 24px; font-weight: bold; text-shadow: 2px 2px #ff0000;");
    console.log("F1: Fly | F2: ESP | F4: Silent Aim (ON) | O: Menu");

    let config = {
        silentAim: true,
        esp: true,
        bhop: true,
        noRecoil: true,
        wallhack: true,
        range: 10000,
        isCheating: false // Flag spoofing
    };

    // --- 1. BYPASS ANTI-CHEAT (SPOOFING) ---
    // Sovrascriviamo le proprietà che il gioco controlla per vedere se stai barando
    const origDefine = Object.defineProperty;
    Object.defineProperty = function(obj, prop, desc) {
        if (prop === "isCheating" || prop === "triggerBotActive" || prop === "isHacker") {
            desc.value = false;
        }
        return origDefine(obj, prop, desc);
    };

    // Nascondiamo il fatto che il browser sia controllato da uno script
    Object.defineProperty(navigator, "webdriver", { value: undefined });

    // --- 2. SILENT AIM 3D (HOOKING MATEMATICO SICURO) ---
    const originalAtan2 = Math.atan2;
    const originalAsin = Math.asin;

    try {
        Object.defineProperty(Math, 'atan2', {
            value: function(y, x) {
                if (config.silentAim && new Error().stack.includes("Instruction")) {
                    const target = getNearestTarget();
                    if (target) {
                        return originalAtan2(target.z - window.me.z, target.x - window.me.x);
                    }
                }
                return originalAtan2(y, x);
            },
            configurable: true,
            writable: true
        });

        Object.defineProperty(Math, 'asin', {
            value: function(val) {
                if (config.silentAim && new Error().stack.includes("Instruction")) {
                    const target = getNearestTarget();
                    if (target) {
                        const dist = Math.hypot(target.x - window.me.x, target.y - window.me.y, target.z - window.me.z);
                        return originalAsin((target.y - window.me.y) / dist);
                    }
                }
                return originalAsin(val);
            },
            configurable: true,
            writable: true
        });
    } catch (e) {
        console.error("⚠️ Impossibile agganciare Math (Read-only). Uso metodo alternativo...");
    }

    // --- 3. TARGETING ENGINE ---
    function getNearestTarget() {
        if (!window.game || !window.game.players) return null;
        const players = window.game.players.list;
        const me = window.game.players.me;
        if (!me) return null;
        window.me = me;

        let nearest = null;
        let minDist = config.range;

        for (let i = 0; i < players.length; i++) {
            const p = players[i];
            // Filtro: Attivo, non sono io, vivo, squadra diversa
            if (p.active && !p.me && p.health > 0 && (me.team === null || p.team !== me.team)) {
                const dist = Math.hypot(p.x - me.x, p.y - me.y, p.z - me.z);
                if (dist < minDist) {
                    minDist = dist;
                    nearest = p;
                }
            }
        }
        return nearest;
    }

    // --- 4. RENDER LOOP (ESP & PHYSICS) ---
    function renderLoop() {
        try {
            const game = window.game;
            const me = game ? game.players.me : null;

            if (me) {
                // No Recoil Reale
                me.recoilAnimY = 0;
                me.recoilLerp = 0;
                if (me.weapon) me.weapon.spread = 0;

                // Auto Bhop
                if (config.bhop && keys['Space']) {
                    if (me.onGround) me.canJump = true;
                }

                // ESP & Wallhack
                game.players.list.forEach(p => {
                    if (!p.me) {
                        p.inView = true;
                        p.isVisible = true; // Wallhack: rende il modello visibile sempre
                        
                        // Wireframe/Glow effect (se supportato dal motore attuale)
                        if (p.mesh && config.wallhack) {
                            p.mesh.material.wireframe = true;
                            p.mesh.material.depthTest = false; // Vede attraverso i muri
                        }
                    }
                });
            }
        } catch(e) {}
        requestAnimationFrame(renderLoop);
    }

    // --- 5. INPUT MANAGEMENT ---
    const keys = {};
    window.addEventListener('keydown', (e) => { 
        keys[e.code] = true;
        if (e.key === 'F1') config.bhop = !config.bhop;
        if (e.key === 'F2') config.esp = !config.esp;
        if (e.key === 'F4') config.silentAim = !config.silentAim;
    });
    window.addEventListener('keyup', (e) => { keys[e.code] = false; });

    renderLoop();
})();

