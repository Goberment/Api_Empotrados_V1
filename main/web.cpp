/**
 * @file    web.cpp
 * @brief   Implementación del servidor web estático con LittleFS.
 * @details Sirve index.html desde Flash cuando el navegador
 *          accede a la IP del ESP32. El WebServer también procesa
 *          las peticiones de la API en cada ciclo del loop()
 *          mediante handleClient().
 * @author  [Diego Cardenas, Alexis Mendoza, Gabriela Soto]
 */
 
#include "web.h"
 
// ─────────────────────────────────────────────
// Referencia al mismo WebServer declarado en api.cpp
// ─────────────────────────────────────────────
extern WebServer server;
 
// ─────────────────────────────────────────────
// Manejador: GET /
// ─────────────────────────────────────────────
/**
 * @brief Sirve /index.html desde LittleFS al navegador.
 *        Si el archivo no existe responde 404.
 */
static void handleRoot() {
    if (!LittleFS.exists("/index.html")) {
        server.send(404, "text/plain", "index.html no encontrado en LittleFS");
        Serial.println("[WEB] ERROR: /index.html no existe en LittleFS");
        return;
    }
 
    File archivo = LittleFS.open("/index.html", "r");
    server.streamFile(archivo, "text/html");
    archivo.close();
    Serial.println("[WEB] index.html servido correctamente");
}
 
// ─────────────────────────────────────────────
// Manejador: cualquier ruta no definida
// ─────────────────────────────────────────────
/**
 * @brief Redirige rutas desconocidas a la raíz.
 */
static void handleNotFound() {
    server.sendHeader("Location", "/", true);
    server.send(302, "text/plain", "");
}
 
// ═══════════════════════════════════════════════════════════
// iniciarWeb
// ═══════════════════════════════════════════════════════════
/**
 * @brief Registra las rutas web y configura el manejador 404.
 * @note  El servidor ya fue iniciado en iniciarServidor().
 *        Esta función solo agrega las rutas de contenido estático.
 */
void iniciarWeb() {
    server.on("/",          HTTP_GET, handleRoot);
    server.onNotFound(handleNotFound);
    Serial.println("[WEB] Rutas web registradas");
}
 