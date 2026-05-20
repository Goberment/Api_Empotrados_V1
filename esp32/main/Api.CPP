/**
 * @file    api.cpp
 * @brief   Implementación de la API-REST del ESP32.
 * @details Registra cuatro rutas sobre WebServer:
 *            GET  /api/estado
 *            GET  /api/parametros
 *            POST /api/parametros
 *            POST /api/reset
 *          Todas las respuestas usan JSON y cabeceras CORS para
 *          permitir peticiones desde la GUI Python y el navegador.
 * @author  [Diego Cardenas, Alexis Mendoza, Gabriela Soto]
 */
 
#include <WebServer.h>
#include <ArduinoJson.h>
#include "api.h"
#include "globals.h"
 
// ─────────────────────────────────────────────
// Servidor HTTP (puerto 80)
// ─────────────────────────────────────────────
static WebServer server(80);
 
/// Puntero a los datos globales (se asigna en iniciarServidor)
static DatosGlobales* _datos = nullptr;
 
// ─────────────────────────────────────────────
// Helper: cabeceras comunes
// ─────────────────────────────────────────────
/**
 * @brief Agrega cabeceras CORS y Content-Type JSON a la respuesta.
 */
static void setCORS() {
    server.sendHeader("Access-Control-Allow-Origin",  "*");
    server.sendHeader("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
    server.sendHeader("Access-Control-Allow-Headers", "Content-Type");
}
 
// ─────────────────────────────────────────────
// Manejador: GET /api/estado
// ─────────────────────────────────────────────
/**
 * @brief Devuelve el estado completo del sistema en JSON.
 *
 * Respuesta:
 * @code
 * {
 *   "estado": "NORMAL",
 *   "sensores": {
 *     "distancia_cm": 82.3,
 *     "vibracion_g": 0.98,
 *     "temperatura_c": 24.5,
 *     "humedad_pct": 61.0
 *   },
 *   "actuadores": {
 *     "buzzer": false,
 *     "led": false,
 *     "servo_cerrado": false
 *   }
 * }
 * @endcode
 */
static void handleGetEstado() {
    setCORS();
    StaticJsonDocument<256> doc;
    doc["estado"] = _datos->estado_str;
 
    JsonObject s = doc.createNestedObject("sensores");
    s["distancia_cm"]  = _datos->distancia_cm;
    s["vibracion_g"]   = _datos->vibracion_g;
    s["temperatura_c"] = _datos->temperatura_c;
    s["humedad_pct"]   = _datos->humedad_pct;
 
    JsonObject a = doc.createNestedObject("actuadores");
    a["buzzer"]        = _datos->buzzer_activo;
    a["led"]           = _datos->led_activo;
    a["servo_cerrado"] = _datos->servo_cerrado;
 
    String json;
    serializeJson(doc, json);
    server.send(200, "application/json", json);
}
 
// ─────────────────────────────────────────────
// Manejador: GET /api/parametros
// ─────────────────────────────────────────────
/**
 * @brief Devuelve los parámetros configurables actuales.
 *
 * Respuesta:
 * @code
 * {
 *   "distancia_minima_cm": 50.0,
 *   "umbral_vibracion_g": 1.5
 * }
 * @endcode
 */
static void handleGetParametros() {
    setCORS();
    StaticJsonDocument<128> doc;
    doc["distancia_minima_cm"] = _datos->distancia_minima_cm;
    doc["umbral_vibracion_g"]  = _datos->umbral_vibracion_g;
 
    String json;
    serializeJson(doc, json);
    server.send(200, "application/json", json);
}
 
// ─────────────────────────────────────────────
// Manejador: POST /api/parametros
// ─────────────────────────────────────────────
/**
 * @brief Recibe y aplica nuevos valores de parámetros.
 *
 * Body esperado (JSON):
 * @code
 * {
 *   "distancia_minima_cm": 40.0,
 *   "umbral_vibracion_g": 2.0
 * }
 * @endcode
 * Los campos son opcionales; solo se actualiza lo que se envíe.
 */
static void handlePostParametros() {
    setCORS();
 
    if (!server.hasArg("plain")) {
        server.send(400, "application/json", "{\"error\":\"Sin body\"}");
        return;
    }
 
    StaticJsonDocument<128> doc;
    DeserializationError err = deserializeJson(doc, server.arg("plain"));
    if (err) {
        server.send(400, "application/json", "{\"error\":\"JSON invalido\"}");
        return;
    }
 
    if (doc.containsKey("distancia_minima_cm"))
        _datos->distancia_minima_cm = doc["distancia_minima_cm"].as<float>();
 
    if (doc.containsKey("umbral_vibracion_g"))
        _datos->umbral_vibracion_g = doc["umbral_vibracion_g"].as<float>();
 
    Serial.printf("[API] Parámetros actualizados: dist=%.1f cm  vib=%.2f g\n",
        _datos->distancia_minima_cm, _datos->umbral_vibracion_g);
 
    server.send(200, "application/json", "{\"ok\":true}");
}
 
// ─────────────────────────────────────────────
// Manejador: POST /api/reset
// ─────────────────────────────────────────────
/**
 * @brief Solicita el desbloqueo de la alarma.
 *        Activa el flag reset_solicitado; el loop() lo procesa.
 */
static void handlePostReset() {
    setCORS();
    _datos->reset_solicitado = true;
    Serial.println("[API] Reset de alarma solicitado desde PC");
    server.send(200, "application/json", "{\"ok\":true}");
}
 
// ─────────────────────────────────────────────
// Manejador: OPTIONS (preflight CORS)
// ─────────────────────────────────────────────
static void handleOptions() {
    setCORS();
    server.send(204);
}
 
// ═══════════════════════════════════════════════════════════
// iniciarServidor
// ═══════════════════════════════════════════════════════════
/**
 * @brief Registra rutas y arranca el WebServer en puerto 80.
 * @param d Referencia a la estructura de datos globales.
 */
void iniciarServidor(DatosGlobales& d) {
    _datos = &d;
 
    server.on("/api/estado",     HTTP_GET,     handleGetEstado);
    server.on("/api/parametros", HTTP_GET,     handleGetParametros);
    server.on("/api/parametros", HTTP_POST,    handlePostParametros);
    server.on("/api/reset",      HTTP_POST,    handlePostReset);
    server.on("/api/estado",     HTTP_OPTIONS, handleOptions);
    server.on("/api/parametros", HTTP_OPTIONS, handleOptions);
    server.on("/api/reset",      HTTP_OPTIONS, handleOptions);
 
    server.begin();
    Serial.println("[API] Servidor REST iniciado en puerto 80");
}
 