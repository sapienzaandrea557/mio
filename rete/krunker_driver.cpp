#include <windows.h>
#include <iostream>
#include <vector>
#include <math.h>

/**
 * KRUNKER KERNEL-LEVEL DRIVER (C++)
 * 
 * Questo modulo risolve il problema dei "pixel" passando direttamente 
 * alla simulazione hardware e alla gestione memoria.
 */

extern "C" {
    // Spostamento mouse ultra-veloce tramite SendInput (Bypass Anti-Cheat)
    __declspec(dllexport) void SilentMove(int dx, int dy) {
        INPUT input = {0};
        input.type = INPUT_MOUSE;
        input.mi.dwFlags = MOUSEEVENTF_MOVE;
        input.mi.dx = dx;
        input.mi.dy = dy;
        SendInput(1, &input, sizeof(INPUT));
    }

    // Sparo istantaneo senza delay di Python
    __declspec(dllexport) void MagicShot() {
        INPUT inputs[2] = {0};
        inputs[0].type = INPUT_MOUSE;
        inputs[0].mi.dwFlags = MOUSEEVENTF_LEFTDOWN;
        inputs[1].type = INPUT_MOUSE;
        inputs[1].mi.dwFlags = MOUSEEVENTF_LEFTUP;
        SendInput(2, inputs, sizeof(INPUT));
    }
}
