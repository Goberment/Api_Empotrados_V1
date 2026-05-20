/**
 * @file    globals.h
 * @brief   Estructura de datos globales y enumeración de estados.
 * @details Define DatosGlobales (sensores, actuadores, parámetros,
 *          flags de control) y el enum Estado compartido por todos
 *          los módulos del sistema.
 * @author  [Diego Cardenas, Alexis Mendoza, Gabriela Soto]
 */
 
#ifndef GLOBALS_H
#define GLOBALS_H
 
// ─────────────────────────────────────────────
// Enumeración de estados de la máquina
// ─────────────────────────────────────────────
/**
 * @enum Estado
 * @brief Estados posibles del sistema de seguridad.
 */
enum Estado {
    ESTADO_INIT,       ///< Inicialización (solo al arrancar)
    ESTADO_IDLE,       ///< Esperando próximo ciclo de sensado
    ESTADO_SENSANDO,   ///< Leyendo sensores y evaluando umbrales
    ESTADO_ALERTA,     ///< Umbral superado — activando alarma
    ESTADO_BLOQUEADO   ///< Alarma activa — esperando reset desde PC
};
 
// ─────────────────────────────────────────────
// Estructura de datos compartidos
// ─────────────────────────────────────────────
/**
 * @struct DatosGlobales
 * @brief  Concentra todos los valores de sensores, actuadores,
 *         parámetros configurables y flags de control.
 *         Se pasa por referencia a los módulos api y web.
 */
struct DatosGlobales {
 
    // ── Estado de la máquina ──────────────────
    Estado      estado_actual = ESTADO_INIT; ///< Estado actual del sistema
    const char* estado_str    = "INIT";      ///< Representación en texto
 
    // ── Lecturas de sensores ──────────────────
    float distancia_cm  = 0.0; ///< Distancia medida por HC-SR04 (cm)
    float vibracion_g   = 0.0; ///< Magnitud de vibración MPU-6050 (g)
    float temperatura_c = 0.0; ///< Temperatura DHT11 (°C)
    float humedad_pct   = 0.0; ///< Humedad relativa DHT11 (%)
 
    // ── Estado de actuadores ──────────────────
    bool buzzer_activo = false; ///< true = buzzer encendido
    bool led_activo    = false; ///< true = LED encendido
    bool servo_cerrado = false; ///< true = servo en posición cerrada (90°)
 
    // ── Parámetros configurables ──────────────
    float distancia_minima_cm = 50.0; ///< Umbral de distancia para alarma (cm)
    float umbral_vibracion_g  =  1.5; ///< Umbral de vibración para alarma (g)
 
    // ── Flags de control ─────────────────────
    bool reset_solicitado = false; ///< true cuando la PC pide desbloquear alarma
};
 
#endif // GLOBALS_H
 