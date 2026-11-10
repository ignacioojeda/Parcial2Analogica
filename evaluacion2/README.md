# Pedales fuzz: Bazz Fuss y Fuzz Face (silicio)

Proyecto de Electrónica Análoga (UdeA, 2026-2). Se eligieron dos circuitos de la lista de pedales fuzz de [Experimentalists Anonymous](https://experimentalistsanonymous.com/diy/Schematics/Fuzz%20and%20Fuzzy%20Noisemakers/), aprobados por el profesor: **Bazz Fuss** y **Fuzz Face**. Cada uno se simula en LTspice y se monta en protoboard.

- **Entrega:** viernes 13 de noviembre, con simulación y montaje.
- **Prueba en el laboratorio:** fuente DC de 9 V, generador de señales (senoidal de 1 kHz con amplitud de guitarra, de 20 mVp a 1 Vp) y osciloscopio. No se usa guitarra ni amplificador.
- **Componentes:** solo de silicio y de valores comerciales que se consiguen en Medellín. Los controles se montan con trimmers, que encajan directo en la protoboard.

**El documento principal es [`guia_montaje.ipynb`](guia_montaje.ipynb).** Todas sus imágenes son capturas de pantalla de LTspice.

---

## Estructura de la carpeta

```
evaluacion2/
├── README.md                     este archivo
├── .gitignore                    excluye los archivos temporales de LTspice (.raw, .net, .log, .fft...)
├── guia_montaje.ipynb            guía completa: versiones, componentes, simulaciones, montaje y mediciones
├── Fuzzface.pdf                  esquema original del Fuzz Face (Dallas Arbiter)
├── BazzFuss&BuzzBox.png          esquema original del Bazz Fuss (y el BuzzBox, que no se monta)
├── Diseño e Implementación ... Clase D.docx   enunciado general del curso (la parte del clase D no aplica)
├── ltspice/                      esquemáticos de LTspice (se abren con doble clic)
├── sim/                          scripts que simulan, toman las capturas y generan el notebook
└── graficas/                     capturas de LTspice que usa el notebook
```

### `ltspice/`: esquemáticos

| Archivo | Qué es |
|---|---|
| `BazzFuss_PDF.asc` | Bazz Fuss **igual al esquema original**, sin resistencia a tierra en la salida |
| `BazzFuss.asc` | Bazz Fuss **versión de montaje**: igual al original más R2 = 1 MΩ en la salida |
| `FuzzFace_PDF.asc` | Fuzz Face **igual al PDF**, en la versión NPN que el PDF describe: R3 = 8.2k fija, interruptor **S1** (DPDT, dibujado como S1A y S1B con su cable de bypass) y nodos IN/OUT. Con el parámetro `byp` se elige la posición: 0 = efecto, 1 = bypass |
| `FuzzFace.asc` | Fuzz Face **versión de montaje**: sin S1 y con el **trimmer RT1** en lugar de R3 (`Rc2` = 6.2k) |
| `pot.asy` | Símbolo del potenciómetro, con tres pines: 1, cursor W y 3 |
| `spdt.asy` | Símbolo del interruptor de un polo y dos tiros (cada mitad de S1) |
| `pots.lib` | Modelos `potlog` (curva A, logarítmica), `potlin` (curva B, lineal) y `spdt`. El parámetro `pos` va de 0 a 1 e indica el giro del eje |

`pot.asy`, `spdt.asy` y `pots.lib` **deben quedar en la misma carpeta que los .asc**; si no, LTspice no abre los esquemáticos.

**Convenciones de los esquemáticos:**
- Los Fuzz Face respetan la disposición de los elementos del PDF.
- **VGEN, RG, RSCOPE y CSCOPE no son parte del pedal.** Representan el equipo del laboratorio:
  - VGEN: el generador, con 50 Ω de salida.
  - RG: 10 kΩ que emulan la impedancia de la pastilla de una guitarra. Con `Rg=1m` se quita.
  - RSCOPE y CSCOPE: la entrada del osciloscopio, 1 MΩ en paralelo con 20 pF.
- **Parámetros** que se cambian en la directiva `.param`:

  | Parámetro | Qué controla |
  |---|---|
  | `A` | Amplitud pico de la entrada |
  | `Rg` | Resistencia que emula la pastilla |
  | `vol` | Giro de P1 en el Bazz Fuss; giro de VOLUMEN en el Fuzz Face |
  | `fuzz` | Giro de FUZZ |
  | `Rc2` | Valor del trimmer RT1 |
  | `byp` | Posición de S1 |

- Al abrir un `.asc` y darle Run se simula el transitorio por defecto. Para barrer un parámetro, agrega por ejemplo `.step param A list 0.05 0.1 0.2 0.5 1`.

### `sim/`: scripts

| Archivo | Qué hace |
|---|---|
| `correr_simulaciones.py` | **Script principal.** Para cada caso: copia el `.asc` con las directivas del caso, lo simula en LTspice en modo batch, calcula las cifras a partir del `.raw` de LTspice, abre el resultado en LTspice y captura la ventana. Genera `graficas/*.png` y `sim/resultados.json` |
| `ltspice.py` | Funciones básicas: localiza LTspice, corre netlists en batch, lee archivos `.raw` binarios y `.op.raw`, y calcula el espectro (FFT con un número entero de ciclos) para el Vpp, el THD y los armónicos |
| `gui.py` | Arma la carpeta de cada caso, escribe el `.plt` (qué trazas mostrar y con qué zoom) y llama a la captura |
| `captura.ps1` | PowerShell que maximiza la ventana de LTspice abierta por el script, **verifica que esté al frente**, hace los clics necesarios (por ejemplo, View → FFT y el zoom) y guarda la captura. Si otra ventana tiene el foco, cancela la captura en vez de hacer clic |
| `volver_vscode.ps1` | Devuelve el foco a VS Code al terminar |
| `generar_notebook.py` | Escribe `guia_montaje.ipynb` con las tablas tomadas de `resultados.json` |
| `resultados.json` | Cifras de todas las simulaciones: punto de operación DC; Vmax, Vmin, Vpp, THD y armónicos por cada paso; polarización según hFE |
| `capturas/<caso>/` | Carpeta **temporal** que se crea mientras corre `correr_simulaciones.py` (copias de los `.asc`, `.net`, `.raw`, `.fft`). Se borra sola al terminar y está en `.gitignore`, así que no se sube a GitHub |

### `graficas/`: capturas de LTspice

Los nombres empiezan por `bz_` (Bazz Fuss) o `ff_` (Fuzz Face). El sufijo `_pdf` indica la versión del esquema original.

| Captura | Contenido |
|---|---|
| `*_esquematico` | Esquemático abierto en LTspice |
| `*_op` | Ventana "Operating Point" (punto de operación DC) |
| `*_amp` | Transitorio con barrido de amplitud (50 mVp a 1 Vp): V(out) arriba y V(gen) abajo |
| `*_100mV_fft`, `*_500mV_fft` | FFT de V(out) hecha con View → FFT de LTspice |
| `bz_pot`, `ff_fuzz`, `ff_vol` | Barrido de un potenciómetro |
| `*_fuente` | Con y sin la resistencia de 10 kΩ que emula la pastilla |
| `ff_pdf_bypass` | S1 en efecto vs. en bypass |
| `ff_rc2` | R3 = 8.2k vs. trimmer de 6.2k: V(c2) y V(out) |
| `ff_bias` | V(c2) en función del trimmer RT1, una curva por cada hFE (100, 200, 300 y 400) |

---

## Contenido de `guia_montaje.ipynb`, sección por sección

**Portada.** Presenta los objetivos, la tabla de archivos e indica cómo leer las capturas:
- El eje de tiempo empieza en 150 ms, porque se descarta el arranque mientras se cargan los condensadores. Así, "47–50 ms" en la captura corresponde a 197–200 ms.
- En un barrido (`.step`), cada paso sale de un color distinto.
- Las FFT están en dB y con el eje de frecuencia logarítmico.
- Qué elementos de los esquemáticos son equipo de laboratorio y no parte del pedal.

**1. Versión del esquema original vs. versión de montaje.** Tabla por circuito con cada elemento: cómo está en el original, cómo se monta y por qué cambia.
- **Bazz Fuss:**
  - Q1 = 2N3904, porque el esquema solo pide un "NPN de señal".
  - Se agrega R2 = 1 MΩ, que evita el "pop" y no cambia la señal.
  - P1 se monta con un trimmer.
  - El BuzzBox no se monta.
- **Fuzz Face:**
  - BC108C/AC128 → 2N3904.
  - 470 Ω → 330 Ω y polaridad invertida, como indica el PDF para la versión NPN.
  - 20 µF → 22 µF, que es el valor comercial.
  - R3 = 8.2k → trimmer, porque con silicio el colector de Q2 queda en 3,1 V en vez de 4,5 V.
  - **S1 se quita**, porque solo sirve para el bypass y en el laboratorio siempre se mide con el efecto activo. La simulación muestra que en la posición "efecto" el circuito es idéntico sin S1.
  - Los jacks IN/OUT se reemplazan por caimanes al generador y al osciloscopio.
- Tabla de pines del 2N3904 (E-B-C), del BC547 (C-B-E), del 1N4148, de los electrolíticos y de los trimmers.

**2. Lista de componentes.** Por circuito, con referencia, valor, cantidad y un reemplazo para lo que sea difícil de conseguir. Incluye la compra total de los dos circuitos y consejos para que todo encaje en la protoboard: resistencias de 1/4 W, electrolíticos radiales y trimmers de patas a 2,54 mm.

**3. Bazz Fuss.**
- 3.1 Capturas de los dos esquemáticos y explicación del funcionamiento: emisor común, polarización por diodo (Vc ≈ 1 V), recorte asimétrico y por qué P1 actúa casi como un interruptor.
- 3.2 Punto de operación de las dos versiones, en capturas y en tabla. Son idénticos.
- 3.3 Transitorio a 5 amplitudes en las dos versiones, con tablas de Vmax, Vmin, Vpp y THD. Son idénticas, lo que demuestra que R2 no altera la señal.
- 3.4 FFT a 100 y 500 mVp, con la tabla de armónicos 2.º a 6.º.
- 3.5 Barrido de P1, con la resistencia cursor–tierra que equivale a cada posición.
- 3.6 Efecto de la impedancia de la fuente (con y sin RG).

**4. Fuzz Face.**
- 4.1 Capturas de los dos esquemáticos y explicación: acople directo, realimentación DC por R2, el control FUZZ y la salida tomada en el nodo `tap`.
- 4.2 Punto de operación de las dos versiones: 8.2k da 3,10 V y el trimmer da 4,49 V en el colector de Q2.
- 4.3 Polarización según hFE: curvas de V(c2) vs. RT1 y tabla con la RT1 necesaria para 4,5 V (5,1 a 6,4 kΩ).
- 4.4 Transitorio a 5 amplitudes en las dos versiones, más la comparación directa 8.2k vs. 6.2k (0,32 contra 0,42 Vpp).
- 4.5 S1 en efecto vs. en bypass: justifica que S1 se puede quitar.
- 4.6 FFT a 100 y 500 mVp, con la tabla de armónicos.
- 4.7 Barrido de FUZZ a 20 mVp, de senoidal limpia a cuadrada.
- 4.8 Barrido de VOLUMEN.
- 4.9 Efecto de la impedancia de la fuente.

**5. Montaje en protoboard.**
- Reglas generales: fuente de 9 V con límite de 30–50 mA, tierras primero, revisar que no haya corto antes de encender.
- Tabla paso a paso, columna por columna, para cada circuito.
- Cómo escoger los transistores midiendo el hFE.
- Cómo ajustar RT1 hasta 4,5 V.
- Cómo fijar la posición de los trimmers midiendo la resistencia entre el cursor y tierra.

**6. Qué medir en el laboratorio.**
- Configuración del generador (High-Z; diferencia entre Vp y Vpp) y del osciloscopio (escalas, acople, FFT).
- **Tablas para llenar**, cada una con su columna "Medido":
  - voltajes DC con rango aceptable;
  - formas de onda a cada amplitud;
  - posiciones de los trimmers;
  - con y sin la resistencia de la pastilla.
- Por qué pueden diferir medición y simulación.

**7. Si algo no funciona.** Tabla de síntomas, causas probables y qué revisar.

**8. Volver a correr las simulaciones.** Instrucciones y precauciones, más una celda de código que corre todo y regenera el notebook.

---

## Resultados principales

| | Bazz Fuss | Fuzz Face (montaje) |
|---|---|---|
| Punto DC | V<sub>B</sub> = 0,65 V; V<sub>C</sub> = 0,97 V; I<sub>C</sub> = 0,80 mA | V(b1) = 0,62 V; V(c1) = 1,34 V; V(e2) = 0,69 V; **V(c2) = 4,49 V** |
| Consumo | 0,80 mA | 0,92 mA |
| Salida (control al máximo, 100 mVp) | cuadrada asimétrica, 0,94 Vpp, invertida | cuadrada, 0,42 Vpp; el colector de Q2 va de ≈0,8 a 9 V |
| Versión del PDF vs. montaje | idénticas (R2 no cambia la señal) | 8.2k: V(c2) = 3,10 V y 0,32 Vpp. Trimmer: 4,49 V y 0,42 Vpp |

---

## Cómo volver a correr todo

Requisitos:
- Windows con **LTspice** instalado, en `%LOCALAPPDATA%\Programs\ADI\LTspice`.
- **Python 3** con `numpy`.
- Para ejecutar las celdas del notebook: un kernel de Jupyter (`pip install ipykernel`). Para solo leerlo en VS Code no hace falta.

```bash
python sim/correr_simulaciones.py            # simula + capturas de LTspice (~6 min)
python sim/correr_simulaciones.py --sin-gui  # solo simula y recalcula las cifras (~1,5 min)
python sim/generar_notebook.py               # regenera guia_montaje.ipynb con las cifras nuevas
```

**Precauciones al tomar capturas:**
- **Cierra todas las ventanas de LTspice antes de empezar.** El script abre y cierra LTspice muchas veces y hace clics automáticos para la FFT. Una ventana de LTspice abierta por ti puede quedarse con el foco.
- **No toques el mouse ni el teclado mientras corre.**
- Si cambias un `.asc`, guárdalo, cierra LTspice y vuelve a correr los dos comandos.
- Las capturas dependen del tamaño de la pantalla. Los clics de la FFT están calibrados para la ventana maximizada de este equipo (1374 × 728). En otra pantalla podría ser necesario ajustar las coordenadas en `fft_clicks()` (`correr_simulaciones.py`).
