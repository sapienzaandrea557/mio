#include <windows.h>
#include <iostream>

/**
 * HIGH-SPEED MOUSE INJECTOR (C++)
 * 
 * Questo modulo è infinitamente più veloce di qualsiasi script Python
 * perché comunica direttamente con il kernel di Windows (user32.dll).
 */

extern "C" {
    __declspec(dllexport) void MoveMouse(int x, int y) {
        INPUT input = {0};
        input.type = INPUT_MOUSE;
        input.mi.dwFlags = MOUSEEVENTF_MOVE;
        input.mi.dx = x;
        input.mi.dy = y;
        SendInput(1, &input, sizeof(INPUT));
    }

    __declspec(dllexport) void LeftClick() {
        INPUT inputs[2] = {0};
        
        inputs[0].type = INPUT_MOUSE;
        inputs[0].mi.dwFlags = MOUSEEVENTF_LEFTDOWN;

        inputs[1].type = INPUT_MOUSE;
        inputs[1].mi.dwFlags = MOUSEEVENTF_LEFTUP;

        SendInput(2, inputs, sizeof(INPUT));
    }
}

// Per compilare: g++ -shared -o mouse_control.dll mouse_control.cpp
