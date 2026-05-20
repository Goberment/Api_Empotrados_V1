/**
 * @file    web.h
 * @brief   Módulo del servidor web estático con LittleFS.
 * @details Sirve el archivo index.html almacenado en la memoria
 *          Flash del ESP32 mediante LittleFS.
 *          La función iniciarWeb() debe llamarse después de
 *          iniciarServidor() en setup().
 * @author  [Diego Cardenas, Alexis Mendoza, Gabriela Soto]
 */
 
#ifndef WEB_H
#define WEB_H
 
#include <WebServer.h>
#include <LittleFS.h>
 
/**
 * @brief Registra la ruta raíz "/" para servir index.html desde LittleFS.
 * @note  Llama a esta función después de iniciarServidor().
 *        El archivo /index.html debe existir en LittleFS.
 */
void iniciarWeb();
 
#endif // WEB_H
 