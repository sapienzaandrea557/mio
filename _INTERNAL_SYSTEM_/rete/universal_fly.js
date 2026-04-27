/**
 * KRUNKER.IO FLY HACK (Updated & Fixed)
 * 
 * Istruzioni:
 * 1. Apri Krunker.io
 * 2. F12 -> Console
 * 3. Incolla questo codice e premi INVIO.
 */

(function() {
    console.log("🚀 KRUNKER ULTIMATE HACK INJECTED!");
    console.log("F1: Fly Mode | F2: No-Recoil | F3: ESP | F4: Silent Aim");

    let flyActive = false;
    let noRecoilActive = true;
    let espActive = true;
    let silentAimActive = true;
    let speed = 2.0;
    let keys = {};

    window.addEventListener('keydown', (e) => {
        keys[e.code] = true;
        if (e.key === 'F1') { e.preventDefault(); flyActive = !flyActive; console.log("Fly:", flyActive); }
        if (e.key === 'F2') { noRecoilActive = !noRecoilActive; console.log("NoRecoil:", noRecoilActive); }
        if (e.key === 'F3') { espActive = !espActive; console.log("ESP:", espActive); }
        if (e.key === 'F4') { silentAimActive = !silentAimActive; console.log("Silent Aim:", silentAimActive); }
    });

    window.addEventListener('keyup', (e) => { keys[e.code] = false; });

    function getDistance(p1, p2) {
        return Math.sqrt(Math.pow(p1.x - p2.x, 2) + Math.pow(p1.y - p2.y, 2) + Math.pow(p1.z - p2.z, 2));
    }

    function loop() {
        try {
            let game = window.game;
            let me = game ? game.players.me : null;
            
            if (me) {
                // 1. FLY MODE
                if (flyActive) {
                    me.velocity.y = 0;
                    if (keys['Space']) me.y += (speed * 0.5);
                    if (keys['ShiftLeft']) me.y -= (speed * 0.5);
                }

                // 2. NO RECOIL & NO SPREAD
                if (noRecoilActive) {
                    me.recoilAnimY = 0;
                    me.recoilAnimX = 0;
                    if (me.weapon) me.weapon.spread = 0;
                }

                // 3. ESP (Wallhack visivo)
                if (espActive && game.players.list) {
                    game.players.list.forEach(p => {
                        if (!p.me) p.inView = true;
                    });
                }

                // 4. SILENT AIM (Magic Bullets)
                if (silentAimActive && game.players.list) {
                    let target = null;
                    let minDist = Infinity;

                    // Trova il nemico più vicino
                    game.players.list.forEach(p => {
                        if (!p.me && p.active && p.health > 0) {
                            let dist = getDistance(me, p);
                            if (dist < minDist) {
                                minDist = dist;
                                target = p;
                            }
                        }
                    });

                    // Indirizza i proiettili verso il bersaglio (Silent)
                    if (target) {
                        let dx = target.x - me.x;
                        let dy = target.y - me.y;
                        let dz = target.z - me.z;
                        let pitch = Math.asin(dy / minDist);
                        let yaw = Math.atan2(dz, dx);
                        
                        // Applica la rotazione solo durante lo sparo o il calcolo traiettoria
                        // In Krunker 'xDire' e 'yDire' controllano dove guardi/spari
                        me.xDire = pitch;
                        me.yDire = yaw;
                    }
                }
            }
        } catch(err) {}
        requestAnimationFrame(loop);
    }
    loop();
})();
