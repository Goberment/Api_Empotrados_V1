/**
 * @file    main.ino
 * @brief   Sistema de Seguridad para Hogar - ESP32
 * @details Implementa la máquina de estados principal del sistema.
 *          Gestiona el sensado periódico con NoDelay, el servidor web,
 *          y la API-REST. Sin uso de delay().
 * @author  [Diego Cardenas, Alexis Mendoza, Gabriela Soto]
 */

#include <WiFi.h>
#include <LittleFS.h>
#include <NoDelay.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <DHT.h>
#include <ESP32Servo.h>
#include "api.h"
#include "web.h"
#include "globals.h"

// ─────────────────────────────────────────────
// Configuración WiFi
// ─────────────────────────────────────────────
const char* WIFI_SSID     = "DESKTOP-QMI89N4 9509";
const char* WIFI_PASSWORD = "/8B6701x";

// ─────────────────────────────────────────────
// Pines de hardware
// ─────────────────────────────────────────────
#define PIN_TRIG      5    ///< HC-SR04 Trigger
#define PIN_ECHO      18   ///< HC-SR04 Echo
#define PIN_DHT       19   ///< DHT11 data
#define PIN_BUZZER    21   ///< Buzzer pasivo
#define PIN_LED       22   ///< LED de alarma
#define PIN_SERVO     23   ///< Servo SG90
#define DHT_TYPE      DHT11

// ─────────────────────────────────────────────
// Estados de la máquina de estados
// ─────────────────────────────────────────────
/**
 * @enum Estado
 * @brief Estados posibles del sistema de seguridad.
 */

DatosGlobales datos;

// ─────────────────────────────────────────────
// Objetos de sensores y actuadores
// ─────────────────────────────────────────────
DHT dht(PIN_DHT, DHT_TYPE);
Adafruit_MPU6050 mpu;
Servo         servo;

/// Timer de sensado periódico (500 ms, sin delay)
noDelay timerSensado(500);

// ─────────────────────────────────────────────
// Prototipos de funciones
// ─────────────────────────────────────────────
void estadoInit();
void estadoIdle();
void estadoSensando();
void estadoAlerta();
void estadoBloqueado();
float leerDistancia();
float leerVibracion();
void activarAlarma();
void desactivarAlarma();
void actualizarEstadoStr();

// ═══════════════════════════════════════════════════════════
// SETUP
// ═══════════════════════════════════════════════════════════
/**
 * @brief Inicialización del sistema. Se ejecuta una sola vez al arrancar.
 */
void setup() {
    Serial.begin(115200);
    Serial.println("[SISTEMA] Iniciando...");

    // Pines de actuadores
    pinMode(PIN_TRIG,   OUTPUT);
    pinMode(PIN_ECHO,   INPUT);
    pinMode(PIN_BUZZER, OUTPUT);
    pinMode(PIN_LED,    OUTPUT);

    // Servo
    servo.attach(PIN_SERVO);
    servo.write(0); // Posición abierta inicial

    // DHT11
    dht.begin();

    // MPU-6050
    if (!mpu.begin()) {
        Serial.println("[ERROR] MPU-6050 no encontrado");
    } else {
        mpu.setAccelerometerRange(MPU6050_RANGE_2_G);
        Serial.println("[OK] MPU-6050 listo");
    }

    // LittleFS
    if (!LittleFS.begin(true)) {
        Serial.println("[ERROR] LittleFS no montado");
    } else {
        Serial.println("[OK] LittleFS montado");
    }

    // WiFi
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    Serial.print("[WiFi] Conectando");
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println();
    Serial.print("[WiFi] IP: ");
    Serial.println(WiFi.localIP());

    // Servidor web y API-REST
    iniciarServidor(datos);
    iniciarWeb();

    datos.estado_actual = ESTADO_IDLE;
    datos.estado_str    = "IDLE";
    Serial.println("[SISTEMA] Listo");
}

// ═══════════════════════════════════════════════════════════
// LOOP
// ═══════════════════════════════════════════════════════════
/**
 * @brief Ciclo principal. Ejecuta la máquina de estados sin delay().
 */
void loop() {
    switch (datos.estado_actual) {
        case ESTADO_INIT:      estadoInit();      break;
        case ESTADO_IDLE:      estadoIdle();      break;
        case ESTADO_SENSANDO:  estadoSensando();  break;
        case ESTADO_ALERTA:    estadoAlerta();    break;
        case ESTADO_BLOQUEADO: estadoBloqueado(); break;
    }
}

// ═══════════════════════════════════════════════════════════
// FUNCIONES DE ESTADO
// ═══════════════════════════════════════════════════════════

/**
 * @brief Estado INIT: ya fue manejado en setup(). Transición inmediata a IDLE.
 */
void estadoInit() {
    datos.estado_actual = ESTADO_IDLE;
    datos.estado_str    = "IDLE";
}

/**
 * @brief Estado IDLE: espera que el timer de NoDelay venza para sensar.
 */
void estadoIdle() {
    if (timerSensado.update()) {
        datos.estado_actual = ESTADO_SENSANDO;
        datos.estado_str    = "SENSANDO";
    }

    // Verificar reset desde PC
    if (datos.reset_solicitado) {
        datos.reset_solicitado = false;
        desactivarAlarma();
    }
}

/**
 * @brief Estado SENSANDO: lee los 3 sensores y evalúa umbrales.
 *        Conserva únicamente la última lectura obtenida.
 */
void estadoSensando() {
    // Leer sensores
    datos.distancia_cm  = leerDistancia();
    datos.vibracion_g   = leerVibracion();
    datos.temperatura_c = dht.readTemperature(); 
    datos.humedad_pct   = dht.readHumidity();

    Serial.printf("[SENSOR] Dist: %.1f cm | Vib: %.2f g | Temp: %.1f C | Hum: %.1f%%\n",
        datos.distancia_cm, datos.vibracion_g,
        datos.temperatura_c, datos.humedad_pct);

    // Evaluar umbrales
    bool alerta_distancia  = (datos.distancia_cm < datos.distancia_minima_cm);
    bool alerta_vibracion  = (datos.vibracion_g  > datos.umbral_vibracion_g);

    if (alerta_distancia || alerta_vibracion) {
        datos.estado_actual = ESTADO_ALERTA;
        datos.estado_str    = "ALERTA";
    } else {
        datos.estado_actual = ESTADO_IDLE;
        datos.estado_str    = "NORMAL";
    }
}

/**
 * @brief Estado ALERTA: activa buzzer, LED y cierra cerradura.
 *        Transiciona a BLOQUEADO. Acepta reset desde PC.
 */
void estadoAlerta() {
    activarAlarma();

    // Si la PC manda reset, regresar a IDLE
    if (datos.reset_solicitado) {
        datos.reset_solicitado = false;
        desactivarAlarma();
        datos.estado_actual = ESTADO_IDLE;
        datos.estado_str    = "IDLE";
        return;
    }

    // Confirmar alerta → BLOQUEADO
    datos.estado_actual = ESTADO_BLOQUEADO;
    datos.estado_str    = "BLOQUEADO";
}

/**
 * @brief Estado BLOQUEADO: alarma activa hasta desbloqueo desde PC.
 */
void estadoBloqueado() {
    // Mantener actuadores activos
    digitalWrite(PIN_BUZZER, HIGH);
    digitalWrite(PIN_LED,    HIGH);

    // Solo la PC puede desbloquear
    if (datos.reset_solicitado) {
        datos.reset_solicitado = false;
        desactivarAlarma();
        datos.estado_actual = ESTADO_IDLE;
        datos.estado_str    = "IDLE";
    }
}

// ═══════════════════════════════════════════════════════════
// FUNCIONES DE SENSORES
// ═══════════════════════════════════════════════════════════

/**
 * @brief Lee la distancia del HC-SR04 en centímetros.
 * @return Distancia medida en cm. Retorna 999.0 si hay error.
 */
float leerDistancia() {
    digitalWrite(PIN_TRIG, LOW);
    delayMicroseconds(2);
    digitalWrite(PIN_TRIG, HIGH);
    delayMicroseconds(10);
    digitalWrite(PIN_TRIG, LOW);

    long duracion = pulseIn(PIN_ECHO, HIGH, 30000);
    if (duracion == 0) return 999.0;
    return duracion * 0.034 / 2.0;
}

/**
 * @brief Lee la magnitud de vibración del MPU-6050 en g.
 * @return Magnitud del vector de aceleración en g.
 */
float leerVibracion() {
    sensors_event_t a, g, temp;
    mpu.getEvent(&a, &g, &temp);
    float ax = a.acceleration.x / 9.81;
    float ay = a.acceleration.y / 9.81;
    float az = a.acceleration.z / 9.81;
    return sqrt(ax*ax + ay*ay + az*az);
}

// ═══════════════════════════════════════════════════════════
// FUNCIONES DE ACTUADORES
// ═══════════════════════════════════════════════════════════

/**
 * @brief Activa buzzer, LED y cierra el servo (cerradura).
 */
void activarAlarma() {
    digitalWrite(PIN_BUZZER, HIGH);
    digitalWrite(PIN_LED,    HIGH);
    servo.write(90); // Posición cerrada
    datos.buzzer_activo  = true;
    datos.led_activo     = true;
    datos.servo_cerrado  = true;
}

/**
 * @brief Desactiva buzzer, LED y abre el servo (cerradura).
 */
void desactivarAlarma() {
    digitalWrite(PIN_BUZZER, LOW);
    digitalWrite(PIN_LED,    LOW);
    servo.write(0); // Posición abierta
    datos.buzzer_activo  = false;
    datos.led_activo     = false;
    datos.servo_cerrado  = false;
}