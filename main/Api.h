/**
 * @file    api.h
 * @brief   Declaraciones del módulo API-REST del ESP32.
 * @details Expone iniciarServidor() que registra todas las rutas
 *          REST sobre el WebServer de Arduino.
 * @author  [Diego Cardenas, Alexis Mendoza, Gabriela Soto]
 */
 
#ifndef API_H
#define API_H
 
#include "globals.h"
 
/**
 * @brief Inicializa y registra todas las rutas de la API-REST.
 * @param d Referencia a la estructura de datos globales.
 *
 * Rutas disponibles:
 *   GET  /api/estado      — sensores, actuadores y estado actual
 *   GET  /api/parametros  — umbrales configurables actuales
 *   POST /api/parametros  — modifica uno o ambos umbrales
 *   POST /api/reset       — solicita desbloquear la alarma
 */
void iniciarServidor(DatosGlobales& d);
 
#endif // API_H
 