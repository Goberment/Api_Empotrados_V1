"""
gui.py
======
Subsistema Principal — Sistema de Seguridad ESP32
--------------------------------------------------
Interfaz gráfica en Tkinter que se comunica con la API REST
(main.py / uvicorn) para mostrar y controlar el sistema.
 
Funciones:
  - Mostrar estado en tiempo real de sensores y actuadores
  - Modificar parámetros configurables via API REST
  - Representación gráfica del sistema físico
  - Estadísticas con gráficas de líneas por período
 
Requisitos:
    pip install requests matplotlib
 
Uso:
    python gui.py
 
Autores: [Diego Montes, Ulises Felix, Gabriela Soto]
Materia: Sistemas Empotrados — ITSON 2026
"""
 
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import requests
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime
 
# ─────────────────────────────────────────────
# Configuración
# ─────────────────────────────────────────────
API_URL        = "http://localhost:8000"
INTERVALO_MS   = 2000   # Refresco automático en milisegundos
 
 
# ─────────────────────────────────────────────
# Helpers HTTP
# ─────────────────────────────────────────────
 
def api_get(ruta: str):
    """GET a la API REST. Devuelve dict o None si falla."""
    try:
        r = requests.get(f"{API_URL}{ruta}", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[GET {ruta}] Error: {e}")
        return None
 
 
def api_post(ruta: str, payload: dict):
    """POST a la API REST. Devuelve dict o None si falla."""
    try:
        r = requests.post(f"{API_URL}{ruta}", json=payload, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[POST {ruta}] Error: {e}")
        return None
 
 
# ═══════════════════════════════════════════════════════════
# Aplicación principal
# ═══════════════════════════════════════════════════════════
 
class AppSeguridad(tk.Tk):
 
    def __init__(self):
        super().__init__()
        self.title("Sistema de Seguridad ESP32")
        self.geometry("950x680")
        self.resizable(True, True)
        self.configure(bg="#1e1e2e")
 
        # Colores
        self.C_BG      = "#1e1e2e"
        self.C_PANEL   = "#2a2a3e"
        self.C_ACCENT  = "#7c3aed"
        self.C_GREEN   = "#22c55e"
        self.C_RED     = "#ef4444"
        self.C_YELLOW  = "#f59e0b"
        self.C_TEXT    = "#e2e8f0"
        self.C_MUTED   = "#94a3b8"
 
        self._build_ui()
        self._actualizar()   # Primer ciclo de refresco
 
    # ─────────────────────────────────────────────
    # Construcción de la UI
    # ─────────────────────────────────────────────
 
    def _build_ui(self):
        # Título
        tk.Label(
            self, text="🔒  Sistema de Seguridad ESP32",
            bg=self.C_BG, fg=self.C_TEXT,
            font=("Segoe UI", 16, "bold")
        ).pack(pady=(14, 4))
 
        # Estado de conexión
        self.lbl_conexion = tk.Label(
            self, text="⏳ Conectando...",
            bg=self.C_BG, fg=self.C_YELLOW,
            font=("Segoe UI", 10)
        )
        self.lbl_conexion.pack(pady=(0, 8))
 
        # Notebook (pestañas)
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "TNotebook",
            background=self.C_BG, borderwidth=0
        )
        style.configure(
            "TNotebook.Tab",
            background=self.C_PANEL, foreground=self.C_TEXT,
            padding=[14, 6], font=("Segoe UI", 10)
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", self.C_ACCENT)],
            foreground=[("selected", "#ffffff")]
        )
 
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=14, pady=(0, 14))
 
        self._tab_estado()
        self._tab_parametros()
        self._tab_estadisticas()
 
    # ── Pestaña 1: Estado ──────────────────────────────────
 
    def _tab_estado(self):
        frame = tk.Frame(self.notebook, bg=self.C_BG)
        self.notebook.add(frame, text="  📡 Estado en vivo  ")
 
        # ── Representación gráfica del sistema físico ──
        grafico = tk.Frame(frame, bg=self.C_PANEL, bd=0, relief="flat")
        grafico.pack(fill="x", padx=16, pady=(14, 8))
 
        tk.Label(
            grafico, text="Representación del Sistema",
            bg=self.C_PANEL, fg=self.C_MUTED,
            font=("Segoe UI", 9, "italic")
        ).pack(pady=(8, 4))
 
        canvas = tk.Canvas(grafico, bg=self.C_PANEL, height=110,
                           highlightthickness=0)
        canvas.pack(fill="x", padx=20, pady=(0, 10))
        self.canvas_sistema = canvas
        self._dibujar_sistema(canvas)
 
        # ── Sensores ──
        sec_sensores = self._seccion(frame, "Sensores")
        grid = tk.Frame(sec_sensores, bg=self.C_PANEL)
        grid.pack(fill="x", padx=8, pady=6)
 
        self.vars_sensores = {}
        sensores = [
            ("📏 Distancia",    "distancia_cm",  "cm"),
            ("〰️ Vibración",    "vibracion_g",   "g"),
            ("🌡️ Temperatura",  "temperatura_c", "°C"),
            ("💧 Humedad",      "humedad_pct",   "%"),
        ]
        for col, (etiqueta, clave, unidad) in enumerate(sensores):
            card = tk.Frame(grid, bg="#12122a", padx=12, pady=10)
            card.grid(row=0, column=col, padx=6, pady=4, sticky="nsew")
            grid.columnconfigure(col, weight=1)
 
            tk.Label(card, text=etiqueta, bg="#12122a",
                     fg=self.C_MUTED, font=("Segoe UI", 9)).pack()
            var = tk.StringVar(value="—")
            self.vars_sensores[clave] = var
            tk.Label(card, textvariable=var, bg="#12122a",
                     fg=self.C_TEXT, font=("Segoe UI", 15, "bold")).pack()
            tk.Label(card, text=unidad, bg="#12122a",
                     fg=self.C_MUTED, font=("Segoe UI", 8)).pack()
 
        # ── Estado máquina + actuadores ──
        fila_baja = tk.Frame(frame, bg=self.C_BG)
        fila_baja.pack(fill="x", padx=16, pady=4)
 
        # Estado máquina
        sec_estado = self._seccion(fila_baja, "Estado del Sistema")
        sec_estado.pack(side="left", fill="both", expand=True, padx=(0, 6))
        self.lbl_estado = tk.Label(
            sec_estado, text="—",
            bg=self.C_PANEL, fg=self.C_TEXT,
            font=("Segoe UI", 20, "bold")
        )
        self.lbl_estado.pack(pady=14)
 
        # Botón reset
        self.btn_reset = tk.Button(
            sec_estado, text="🔓 Desbloquear Alarma",
            bg=self.C_RED, fg="white",
            font=("Segoe UI", 10, "bold"),
            relief="flat", cursor="hand2",
            command=self._reset_alarma
        )
        self.btn_reset.pack(pady=(0, 12))
 
        # Actuadores
        sec_act = self._seccion(fila_baja, "Actuadores")
        sec_act.pack(side="left", fill="both", expand=True, padx=(6, 0))
        act_grid = tk.Frame(sec_act, bg=self.C_PANEL)
        act_grid.pack(pady=10)
 
        self.leds_actuadores = {}
        actuadores = [("🔔 Buzzer", "buzzer"),
                      ("💡 LED",    "led"),
                      ("🚪 Servo",  "servo_cerrado")]
        for nombre, clave in actuadores:
            fila = tk.Frame(act_grid, bg=self.C_PANEL)
            fila.pack(fill="x", pady=3)
            tk.Label(fila, text=nombre, bg=self.C_PANEL,
                     fg=self.C_TEXT, font=("Segoe UI", 10),
                     width=12, anchor="w").pack(side="left")
            indicador = tk.Label(fila, text="●", bg=self.C_PANEL,
                                 fg=self.C_MUTED,
                                 font=("Segoe UI", 14))
            indicador.pack(side="left", padx=6)
            self.leds_actuadores[clave] = indicador
 
        # Última actualización
        self.lbl_hora = tk.Label(
            frame, text="", bg=self.C_BG,
            fg=self.C_MUTED, font=("Segoe UI", 8)
        )
        self.lbl_hora.pack(pady=(4, 2))
 
    def _dibujar_sistema(self, canvas):
        """Dibuja esquema estático del sistema físico."""
        canvas.update_idletasks()
        w = canvas.winfo_width() or 900
 
        # ESP32
        cx = w // 2
        canvas.create_rectangle(cx-60, 20, cx+60, 90,
                                 fill="#3b3b5c", outline=self.C_ACCENT, width=2)
        canvas.create_text(cx, 55, text="ESP32",
                           fill=self.C_TEXT, font=("Segoe UI", 11, "bold"))
 
        # Sensores (izquierda)
        sensores_pos = [
            ("Ultrasónico", 0.15),
            ("Vibración",   0.28),
            ("DHT22",       0.41),
        ]
        for nombre, xf in sensores_pos:
            x = int(w * xf)
            canvas.create_rectangle(x-38, 30, x+38, 80,
                                     fill="#1a3a2a", outline=self.C_GREEN, width=1)
            canvas.create_text(x, 55, text=nombre,
                               fill=self.C_GREEN, font=("Segoe UI", 8))
            canvas.create_line(x+38, 55, cx-60, 55,
                               fill=self.C_GREEN, dash=(4, 3))
 
        # Actuadores (derecha)
        actuadores_pos = [
            ("Buzzer", 0.62),
            ("LED",    0.75),
            ("Servo",  0.88),
        ]
        for nombre, xf in actuadores_pos:
            x = int(w * xf)
            canvas.create_rectangle(x-30, 30, x+30, 80,
                                     fill="#3a1a1a", outline=self.C_RED, width=1)
            canvas.create_text(x, 55, text=nombre,
                               fill=self.C_RED, font=("Segoe UI", 8))
            canvas.create_line(cx+60, 55, x-30, 55,
                               fill=self.C_RED, dash=(4, 3))
 
    # ── Pestaña 2: Parámetros ──────────────────────────────
 
    def _tab_parametros(self):
        frame = tk.Frame(self.notebook, bg=self.C_BG)
        self.notebook.add(frame, text="  ⚙️ Parámetros  ")
 
        sec = self._seccion(frame, "Umbrales configurables")
        sec.pack(padx=20, pady=20, fill="x")
 
        info = tk.Label(
            sec,
            text="Modifica los umbrales y presiona 'Guardar' para enviarlos al ESP32.",
            bg=self.C_PANEL, fg=self.C_MUTED, font=("Segoe UI", 9)
        )
        info.pack(pady=(4, 12))
 
        form = tk.Frame(sec, bg=self.C_PANEL)
        form.pack(padx=16, pady=(0, 12))
 
        self.entries_params = {}
        campos = [
            ("📏 Distancia mínima (cm)",  "distancia_minima_cm",
             "Distancia en cm bajo la cual se activa la alarma ultrasónica"),
            ("〰️ Umbral de vibración (g)", "umbral_vibracion_g",
             "Magnitud de vibración en g para activar la alarma"),
        ]
        for row, (etiqueta, clave, descripcion) in enumerate(campos):
            tk.Label(form, text=etiqueta, bg=self.C_PANEL,
                     fg=self.C_TEXT, font=("Segoe UI", 10, "bold"),
                     anchor="w").grid(row=row*2, column=0, sticky="w",
                                      padx=8, pady=(10, 0))
            tk.Label(form, text=descripcion, bg=self.C_PANEL,
                     fg=self.C_MUTED, font=("Segoe UI", 8),
                     anchor="w").grid(row=row*2+1, column=0, sticky="w",
                                      padx=8, pady=(0, 4))
            entry = tk.Entry(form, width=12, bg="#12122a",
                             fg=self.C_TEXT, insertbackground=self.C_TEXT,
                             font=("Segoe UI", 12), relief="flat",
                             bd=4)
            entry.grid(row=row*2, column=1, rowspan=2,
                       padx=16, pady=6, sticky="ns")
            self.entries_params[clave] = entry
 
        # Botones
        fila_btn = tk.Frame(sec, bg=self.C_PANEL)
        fila_btn.pack(pady=(4, 14))
 
        tk.Button(
            fila_btn, text="🔄 Cargar desde ESP32",
            bg=self.C_PANEL, fg=self.C_TEXT,
            font=("Segoe UI", 10), relief="flat", cursor="hand2",
            highlightbackground=self.C_ACCENT,
            command=self._cargar_parametros
        ).pack(side="left", padx=8)
 
        tk.Button(
            fila_btn, text="💾 Guardar en ESP32",
            bg=self.C_ACCENT, fg="white",
            font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2",
            command=self._guardar_parametros
        ).pack(side="left", padx=8)
 
        self.lbl_params_status = tk.Label(
            sec, text="", bg=self.C_PANEL,
            fg=self.C_GREEN, font=("Segoe UI", 9)
        )
        self.lbl_params_status.pack(pady=(0, 8))
 
        # Cargar valores al abrir
        self._cargar_parametros()
 
    # ── Pestaña 3: Estadísticas ────────────────────────────
 
    def _tab_estadisticas(self):
        frame = tk.Frame(self.notebook, bg=self.C_BG)
        self.notebook.add(frame, text="  📊 Estadísticas  ")
 
        # Controles
        ctrl = tk.Frame(frame, bg=self.C_BG)
        ctrl.pack(fill="x", padx=16, pady=12)
 
        tk.Label(ctrl, text="Período:",
                 bg=self.C_BG, fg=self.C_TEXT,
                 font=("Segoe UI", 10)).pack(side="left")
 
        self.combo_horas = ttk.Combobox(
            ctrl, width=14,
            values=["Última 1 hora", "Últimas 6 horas",
                    "Últimas 24 horas", "Últimos 3 días",
                    "Última semana"],
            state="readonly"
        )
        self.combo_horas.current(2)
        self.combo_horas.pack(side="left", padx=10)
 
        tk.Button(
            ctrl, text="📈 Generar gráficas",
            bg=self.C_ACCENT, fg="white",
            font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2",
            command=self._generar_graficas
        ).pack(side="left")
 
        self.lbl_graf_status = tk.Label(
            ctrl, text="", bg=self.C_BG,
            fg=self.C_MUTED, font=("Segoe UI", 9)
        )
        self.lbl_graf_status.pack(side="left", padx=12)
 
        # Contenedor de la figura
        self.frame_graf = tk.Frame(frame, bg=self.C_BG)
        self.frame_graf.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        self.canvas_graf = None
 
    # ─────────────────────────────────────────────
    # Helpers de UI
    # ─────────────────────────────────────────────
 
    def _seccion(self, parent, titulo: str) -> tk.Frame:
        """Crea un panel con título y fondo oscuro."""
        wrapper = tk.Frame(parent, bg=self.C_BG)
 
        tk.Label(wrapper, text=titulo,
                 bg=self.C_BG, fg=self.C_MUTED,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=4)
 
        panel = tk.Frame(wrapper, bg=self.C_PANEL,
                         padx=10, pady=6)
        panel.pack(fill="both", expand=True)
        return panel
 
    # ─────────────────────────────────────────────
    # Lógica — Estado en vivo
    # ─────────────────────────────────────────────
 
    def _actualizar(self):
        """Consulta la API y refresca la UI. Se llama cada INTERVALO_MS."""
        def tarea():
            datos = api_get("/esp32/estado")
            self.after(0, self._refrescar_estado, datos)
 
        threading.Thread(target=tarea, daemon=True).start()
        self.after(INTERVALO_MS, self._actualizar)
 
    def _refrescar_estado(self, datos):
        if datos is None:
            self.lbl_conexion.config(
                text="❌ Sin conexión con la API", fg=self.C_RED)
            return
 
        self.lbl_conexion.config(
            text="✅ Conectado a la API REST", fg=self.C_GREEN)
 
        # Sensores
        s = datos.get("sensores", {})
        self.vars_sensores["distancia_cm"].set(
            f"{s.get('distancia_cm', 0):.1f}")
        self.vars_sensores["vibracion_g"].set(
            f"{s.get('vibracion_g', 0):.2f}")
        self.vars_sensores["temperatura_c"].set(
            f"{s.get('temperatura_c', 0):.1f}")
        self.vars_sensores["humedad_pct"].set(
            f"{s.get('humedad_pct', 0):.1f}")
 
        # Estado máquina
        estado = datos.get("estado", "—")
        colores = {
            "NORMAL":   self.C_GREEN,
            "ALERTA":   self.C_YELLOW,
            "BLOQUEADO": self.C_RED,
        }
        self.lbl_estado.config(
            text=estado,
            fg=colores.get(estado, self.C_TEXT)
        )
 
        # Actuadores
        act = datos.get("actuadores", {})
        for clave, indicador in self.leds_actuadores.items():
            encendido = act.get(clave, False)
            indicador.config(
                fg=self.C_GREEN if encendido else self.C_MUTED,
                text="●"
            )
 
        # Hora
        self.lbl_hora.config(
            text=f"Última actualización: {datetime.now().strftime('%H:%M:%S')}"
        )
 
    def _reset_alarma(self):
        def tarea():
            resultado = api_post("/esp32/reset", {})
            msg = "Alarma desbloqueada correctamente." \
                  if resultado else "No se pudo enviar el reset."
            self.after(0, lambda: messagebox.showinfo("Reset", msg))
 
        threading.Thread(target=tarea, daemon=True).start()
 
    # ─────────────────────────────────────────────
    # Lógica — Parámetros
    # ─────────────────────────────────────────────
 
    def _cargar_parametros(self):
        def tarea():
            datos = api_get("/esp32/parametros")
            self.after(0, self._rellenar_parametros, datos)
 
        threading.Thread(target=tarea, daemon=True).start()
 
    def _rellenar_parametros(self, datos):
        if datos is None:
            self.lbl_params_status.config(
                text="❌ No se pudieron cargar los parámetros.", fg=self.C_RED)
            return
        for clave, entry in self.entries_params.items():
            valor = datos.get(clave, "")
            entry.delete(0, tk.END)
            entry.insert(0, str(valor))
        self.lbl_params_status.config(
            text="✅ Parámetros cargados desde el ESP32.", fg=self.C_GREEN)
 
    def _guardar_parametros(self):
        payload = {}
        for clave, entry in self.entries_params.items():
            texto = entry.get().strip()
            if not texto:
                continue
            try:
                payload[clave] = float(texto)
            except ValueError:
                messagebox.showerror(
                    "Error", f"El valor de '{clave}' no es un número válido.")
                return
 
        if not payload:
            messagebox.showwarning("Aviso", "No hay valores para guardar.")
            return
 
        def tarea():
            resultado = api_post("/esp32/parametros", payload)
            if resultado:
                self.after(0, lambda: self.lbl_params_status.config(
                    text="✅ Parámetros guardados en el ESP32.", fg=self.C_GREEN))
            else:
                self.after(0, lambda: self.lbl_params_status.config(
                    text="❌ Error al guardar los parámetros.", fg=self.C_RED))
 
        threading.Thread(target=tarea, daemon=True).start()
 
    # ─────────────────────────────────────────────
    # Lógica — Estadísticas
    # ─────────────────────────────────────────────
 
    def _generar_graficas(self):
        opciones = {
            "Última 1 hora":    1,
            "Últimas 6 horas":  6,
            "Últimas 24 horas": 24,
            "Últimos 3 días":   72,
            "Última semana":    168,
        }
        horas = opciones.get(self.combo_horas.get(), 24)
        self.lbl_graf_status.config(text="⏳ Cargando datos...", fg=self.C_YELLOW)
 
        def tarea():
            datos = api_get(f"/lecturas?horas={horas}&limit=500")
            self.after(0, self._dibujar_graficas, datos, horas)
 
        threading.Thread(target=tarea, daemon=True).start()
 
    def _dibujar_graficas(self, datos, horas):
        if not datos:
            self.lbl_graf_status.config(
                text="❌ Sin datos para el período seleccionado.", fg=self.C_RED)
            return
 
        # Destruir figura anterior
        if self.canvas_graf:
            self.canvas_graf.get_tk_widget().destroy()
 
        tiempos = [d["fecha_hora"] for d in datos]
        dist    = [d["distancia_cm"]  for d in datos]
        vib     = [d["vibracion_g"]   for d in datos]
        temp    = [d["temperatura_c"] for d in datos]
        hum     = [d["humedad_pct"]   for d in datos]
 
        fig, axs = plt.subplots(4, 1, figsize=(9, 7), sharex=True)
        fig.patch.set_facecolor("#1e1e2e")
 
        datasets = [
            (axs[0], dist, "Distancia (cm)",   "#60a5fa"),
            (axs[1], vib,  "Vibración (g)",    "#f97316"),
            (axs[2], temp, "Temperatura (°C)", "#f43f5e"),
            (axs[3], hum,  "Humedad (%)",      "#34d399"),
        ]
 
        for ax, valores, etiqueta, color in datasets:
            ax.plot(tiempos, valores, color=color, linewidth=1.4)
            ax.set_ylabel(etiqueta, color="#94a3b8", fontsize=8)
            ax.set_facecolor("#12122a")
            ax.tick_params(colors="#94a3b8", labelsize=7)
            ax.spines[:].set_color("#2a2a3e")
            for label in ax.get_xticklabels():
                label.set_rotation(30)
                label.set_ha("right")
 
        fig.suptitle(
            f"Historial — últimas {horas} hora(s)",
            color="#e2e8f0", fontsize=11, y=0.995
        )
        fig.tight_layout()
 
        self.canvas_graf = FigureCanvasTkAgg(fig, master=self.frame_graf)
        self.canvas_graf.draw()
        self.canvas_graf.get_tk_widget().pack(fill="both", expand=True)
 
        self.lbl_graf_status.config(
            text=f"✅ {len(datos)} registros cargados.", fg="#22c55e")
 
 
# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────
 
if __name__ == "__main__":
    app = AppSeguridad()
    app.mainloop()
 