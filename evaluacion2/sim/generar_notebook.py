"""Genera guia_montaje.ipynb a partir de sim/resultados.json (correr antes correr_simulaciones.py)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R = json.loads((ROOT / "sim" / "resultados.json").read_text(encoding="utf-8"))
cells = []


def md(s):
    cells.append({"cell_type": "markdown", "id": f"md{len(cells)}", "metadata": {}, "source": s.strip("\n").splitlines(True)})


def code(s):
    cells.append({"cell_type": "code", "id": f"code{len(cells)}", "metadata": {}, "execution_count": None,
                  "outputs": [], "source": s.strip("\n").splitlines(True)})


def img(name, caption):
    return f"![{caption}](graficas/{name}.png)\n\n*Captura de LTspice: {caption}*"


def vout(case, i=0, sig="V(out)"):
    return R[case][i][sig]


def amp_table(case, extra_col=True):
    rows = ["| Entrada | V<sub>max</sub> | V<sub>min</sub> | Vpp | THD |" + (" Vpp medido |" if extra_col else ""),
            "|---|---|---|---|---|" + ("---|" if extra_col else "")]
    for s in R[case]:
        o = s["V(out)"]
        rows.append(f"| {s['step']*1000:g} mVp ({s['step']*2000:g} mVpp) | {o['vmax']:+.2f} V | {o['vmin']:+.2f} V | "
                    f"{o['vpp']:.2f} V | {o['thd']:.0f} % |" + (" |" if extra_col else ""))
    return "\n" + "\n".join(rows)


def logpot(pos, r):   # resistencia cursor-tierra de un pot tipo A (modelo pots.lib)
    return r * (81 ** pos - 1) / 80


def fmt_r(x):
    return f"{x/1e3:.1f} kΩ" if x >= 1e3 else f"{x:.0f} Ω"


bo, bpo, fo, fpo = R["bz_op"], R["bz_pdf_op"], R["ff_op"], R["ff_pdf_op"]
bias = R["ff_bias"]["hfe"]
h = {k: R[k][0]["V(out)"]["harm_db"] for k in ("bz_100mV", "bz_500mV", "ff_100mV", "ff_500mV")}
c2amp = {s["step"]: s["V(c2)"] for s in R["ff_amp"]}
rc2 = {s["step"]: s for s in R["ff_rc2"]}
byp = {s["step"]: s["V(out)"] for s in R["ff_pdf_bypass"]}
bzf = {s["step"]: s["V(out)"] for s in R["bz_fuente"]}
fff = {s["step"]: s["V(out)"] for s in R["ff_fuente"]}

# ======================================================================= portada
md("""
# Pedales fuzz: Bazz Fuss y Fuzz Face (silicio)
### Simulación en LTspice y guía de montaje en protoboard. Electrónica Análoga, UdeA 2026-2

Entrega: **viernes 13 de noviembre** (simulación y montaje). Prueba en el laboratorio con **generador de señales** (senoidal de 1 kHz, amplitud de guitarra), **fuente DC de 9 V** y **osciloscopio**.

**Todas las imágenes de este notebook son capturas de pantalla de LTspice.** El script `sim/correr_simulaciones.py` simula cada caso, lo abre en LTspice y captura la ventana. Las cifras de las tablas (Vpp, THD, armónicos) se calculan a partir de los mismos archivos `.raw` que genera LTspice.

**Contenido**
1. Dos versiones de cada circuito: la del esquema original (PDF) y la de montaje. Qué se quitó o cambió y por qué.
2. Lista de componentes
3. Bazz Fuss: simulaciones
4. Fuzz Face: simulaciones
5. Montaje en protoboard paso a paso
6. Qué medir en el laboratorio (tablas para llenar)
7. Si algo no funciona
8. Volver a correr las simulaciones

| Archivo | Contenido |
|---|---|
| `ltspice/BazzFuss_PDF.asc` | Bazz Fuss **tal cual el esquema original** |
| `ltspice/BazzFuss.asc` | Bazz Fuss **versión de montaje** |
| `ltspice/FuzzFace_PDF.asc` | Fuzz Face **tal cual el PDF** (versión NPN), con el interruptor S1 y los conectores IN/OUT |
| `ltspice/FuzzFace.asc` | Fuzz Face **versión de montaje** (sin S1 y con el trimmer RT1) |
| `ltspice/pot.asy`, `spdt.asy`, `pots.lib` | Símbolos y modelos del potenciómetro y del interruptor. Deben estar en la misma carpeta que los .asc |
| `sim/correr_simulaciones.py` | Corre todas las simulaciones y toma las capturas de LTspice |
| `sim/resultados.json` | Cifras de todas las simulaciones |
| `graficas/` | Capturas de LTspice |

**Cómo leer las capturas**
- En los transitorios se simulan 200 ms, pero solo se guardan los últimos 50 ms, cuando los condensadores ya se cargaron (régimen permanente). Por eso **el eje de tiempo de LTspice empieza en 0 ms en el instante 150 ms**: "47–50 ms" en la captura corresponde a 197–200 ms.
- Cuando hay un barrido (`.step`), LTspice dibuja cada paso con un color distinto. En el panel V(gen) se ve qué amplitud corresponde a cada color.
- En las FFT el eje vertical está en dB respecto a 1 V RMS y el horizontal es logarítmico (100 Hz a 100 kHz).
- Los elementos **VGEN, RG (10 kΩ), RSCOPE y CSCOPE no son parte del pedal.** Representan el equipo del laboratorio: el generador, la impedancia de una pastilla de guitarra y la entrada del osciloscopio.
""")

# ======================================================================= 1
md(f"""
## 1. Versión del esquema original vs. versión de montaje

Se simularon **las dos versiones** de cada circuito para mostrar que los cambios son necesarios o que no alteran el funcionamiento.

### Bazz Fuss

| Elemento | Esquema original | Versión de montaje | ¿Por qué? |
|---|---|---|---|
| Q1 | "Normal NPN small-signal" | **2N3904** | El esquema no pide un transistor específico. El 2N3904 es el NPN de señal más común en Medellín |
| D1 | 1N4148 | **1N4148** | Igual |
| R2 (1 MΩ en la salida) | **no existe** | **agregada** | Sin ella, la salida después de C2 queda "flotando" si no hay nada conectado. C2 se carga y produce un "pop" al conectar el osciloscopio o el amplificador. **En la simulación no cambia nada** (§3.3), porque el osciloscopio ya pone 1 MΩ a tierra |
| P1 | 50 kΩ log | trimmer de 50 kΩ (o pot A50K) | Encaja directo en la protoboard (ver §2) |
| BuzzBox (2.ª etapa del dibujo) | aparece en la imagen | **no se monta** | El proyecto es solo el Bazz Fuss de un transistor |

### Fuzz Face

El PDF dibuja la versión PNP de germanio. El mismo PDF indica cómo hacer la **versión NPN de silicio**: R de 470 Ω → 330 Ω e invertir la fuente y los electrolíticos. La "versión del esquema original" que se simula es esa versión NPN, **con todos los demás elementos del dibujo**, incluido el interruptor S1 y los conectores IN/OUT. Lo único cambiado son los valores no comerciales.

| Elemento | En el PDF | Versión "original" simulada | Versión de montaje | ¿Por qué? |
|---|---|---|---|---|
| Q1, Q2 | AC128 (Ge) / BC108C (Si) | 2N3904 | 2N3904 | El BC108C y el germanio son difíciles de conseguir. El 2N3904 es común y LTspice trae su modelo |
| R de 470 Ω\\* | 470 Ω | **330 Ω** | 330 Ω | Así lo indica el PDF para la versión NPN |
| C de 20 µF | 20 µF | **22 µF** | 22 µF | 20 µF no es un valor comercial |
| Fuente y electrolíticos | −9 V (PNP) | +9 V, invertidos | +9 V, invertidos | Versión NPN |
| R3 = 8.2 kΩ (colector de Q2) | 8.2 kΩ | **8.2 kΩ** | **trimmer RT1 de 10 kΩ ≈ 6.2 kΩ** | Con silicio y 8.2 kΩ, Q2 queda mal polarizado: V(c2) = {fpo['V(c2)']:.2f} V en lugar de ~4.5 V, y la onda sale recortada de forma asimétrica (§4.2 y §4.3) |
| **S1 (DPDT, bypass)** | sí | **sí** (S1A y S1B) | **se quita** | S1 solo sirve para **saltarse el efecto**: la entrada va directo a la salida. En el laboratorio siempre se mide con el efecto activo. Con S1 en "efecto" el circuito es idéntico al de montaje (§4.4), así que quitarlo no cambia ninguna medición y simplifica la protoboard |
| Conectores IN / OUT | jacks de 1/4" | nodos `in` / `out` | puntas de caimán | En el lab no hay guitarra ni amplificador: la entrada viene del generador y la salida va al osciloscopio |

### Pines de los componentes (¡revisar antes de montar!)
| Componente | Cómo identificar los pines |
|---|---|
| **2N3904** (TO-92) | Cara plana hacia ti y patas hacia abajo: **E – B – C** de izquierda a derecha |
| BC547 / BC548 (si se usa como reemplazo) | Cara plana hacia ti: **C – B – E** (¡al revés del 2N3904!) |
| 1N4148 | La **franja negra es el cátodo** |
| Electrolítico | Pata larga = **+**. La franja del cuerpo marca el **−** |
| Trimmer de 3 patas | Las patas de los extremos son la resistencia total; la del centro es el cursor |
""")

# ======================================================================= 2
md("""
## 2. Lista de componentes (pensada para la protoboard)

Se usan **trimmers de una vuelta** (azules, tipo 3362 o 3386, con patas a 2,54 mm) en vez de potenciómetros, porque entran directo en la protoboard. El circuito es el mismo; solo cambia que se ajustan con destornillador.

### Bazz Fuss
| Ref. | Elemento | Cant. | Reemplazo si no lo encuentras |
|---|---|---|---|
| Q1 | Transistor **2N3904** (TO-92) | 1 | BC547 o BC548 (pines C-B-E) |
| D1 | Diodo **1N4148** | 1 | 1N914 |
| R1 | **10 kΩ** 1/4 W | 1 | — |
| R2 | **1 MΩ** 1/4 W | 1 | 470 kΩ |
| RG | **10 kΩ** 1/4 W (emula la pastilla) | 1 | — |
| C1, C2 | Electrolítico radial **10 µF**, 16–50 V | 2 | 4,7 µF o 22 µF |
| P1 | **Trimmer 50 kΩ** (código 503) | 1 | Trimmer 47 kΩ (473) o pot A50K con cables soldados |

### Fuzz Face
| Ref. | Elemento | Cant. | Reemplazo si no lo encuentras |
|---|---|---|---|
| Q1, Q2 | Transistor **2N3904** (TO-92) | **4–5** (para escoger por hFE) | BC547B o BC548B (pines C-B-E) |
| R1 | **33 kΩ** 1/4 W | 1 | 39 kΩ |
| R2 | **100 kΩ** 1/4 W | 1 | — |
| R4 | **330 Ω** 1/4 W | 1 | 470 Ω (valor del original) |
| RT1 | **Trimmer 10 kΩ** (103), en lugar de R3 = 8,2 kΩ | 1 | Trimmer 20 kΩ, o resistencias fijas de 5,6 / 6,2 / 6,8 kΩ para probar |
| RG | **10 kΩ** 1/4 W | 1 | — |
| C1 | Electrolítico radial **2,2 µF**, 16–50 V | 1 | 1 µF o 4,7 µF |
| C2 | Electrolítico radial **22 µF**, 16–50 V | 1 | 10 µF o 47 µF |
| C3 | **100 nF** cerámico o poliéster (104) | 1 | 47 nF (473) |
| P1 FUZZ | **Trimmer 1 kΩ** (102) | 1 | Pot B1K con cables soldados |
| P2 VOLUMEN | **Trimmer 500 kΩ** (504) | 1 | Trimmer 470 kΩ (474) o 1 MΩ (105). Si no hay ninguno: una resistencia de 1 MΩ a tierra (equivale a VOL al 100 %) |

### Compra total
| Elemento | Cantidad |
|---|---|
| 2N3904 | 6 |
| 1N4148 | 2 |
| Resistencias 1/4 W: 10 kΩ ×3, 1 MΩ ×1, 33 kΩ ×1, 100 kΩ ×1, 330 Ω ×1 | 7 (mejor comprar 2 de cada una) |
| Electrolíticos radiales: 10 µF ×2, 2,2 µF ×1, 22 µF ×1 | 4 |
| Cerámico 100 nF (104) | 1 |
| Trimmers de una vuelta: 50 kΩ, 10 kΩ, 1 kΩ, 500 kΩ | 4 |
| Protoboard, cable UTP para puentes, caimanes | — |

**Para que encaje bien:** resistencias de 1/4 W (las de 1/2 W tienen patas gruesas y dañan los contactos), electrolíticos **radiales**, trimmers de patas a 2,54 mm y transistores con las patas completas.
""")

# ======================================================================= 3 Bazz
bp = R["bz_pot"]
md(f"""
## 3. Bazz Fuss

### 3.1 Esquemáticos
{img("bz_pdf_esquematico", "Bazz Fuss, versión del esquema original")}

{img("bz_montaje_esquematico", "Bazz Fuss, versión de montaje (con R2 = 1 MΩ)")}

**Cómo funciona.** Es un amplificador emisor común con R1 = 10 kΩ de colector. **D1 conecta el colector con la base** y hace dos cosas:
- **Polariza Q1.** El colector queda a ≈ V<sub>BE</sub> + V<sub>D</sub> ≈ {bo['V(c)']:.2f} V. Como ese valor está muy cerca de tierra, la señal solo puede bajar ~0,8 V y casi no puede subir.
- **Realimenta en forma no lineal.** La resistencia dinámica del diodo cambia muchísimo con la corriente. El resultado es un recorte duro y **muy asimétrico**: una onda casi cuadrada con picos de ≈ −0,85 V y +0,1 V.

Esa realimentación también hace que la **impedancia de entrada en la base sea muy baja** (decenas de ohmios). Por eso P1 no se comporta como un volumen común. Funciona como una resistencia en serie con una entrada casi en corto: por debajo de ~80 % de giro la señal casi desaparece.

### 3.2 Punto de operación DC
{img("bz_pdf_op", "punto de operación, versión original")}

{img("bz_op", "punto de operación, versión de montaje")}

| Magnitud | Versión original | Versión montaje |
|---|---|---|
| V<sub>B</sub> (base Q1) | {bpo['V(b)']:.3f} V | {bo['V(b)']:.3f} V |
| V<sub>C</sub> (colector Q1) | {bpo['V(c)']:.3f} V | {bo['V(c)']:.3f} V |
| I<sub>C</sub> | {bpo['Ic(Q1)']*1e3:.3f} mA | {bo['Ic(Q1)']*1e3:.3f} mA |
| I<sub>B</sub> = I<sub>D1</sub> | {bpo['Ib(Q1)']*1e6:.2f} µA | {bo['Ib(Q1)']*1e6:.2f} µA |
| Consumo | {-bpo['I(VCC1)']*1e3:.3f} mA | {-bo['I(VCC1)']*1e3:.3f} mA |

R2 está después de un condensador, así que no afecta el punto DC: los dos son idénticos.

### 3.3 Entrada vs. salida a varias amplitudes (1 kHz, P1 al 100 %, con RG = 10 kΩ)
Barrido `.step param A list 0.05 0.1 0.2 0.5 1` (amplitud pico del generador).

{img("bz_pdf_amp", "versión original: V(out) arriba, V(gen) abajo")}

{img("bz_amp", "versión de montaje: V(out) arriba, V(gen) abajo")}

**Versión original**
{amp_table("bz_pdf_amp", False)}

**Versión de montaje**
{amp_table("bz_amp", False)}

Las dos tablas son iguales: **agregar R2 no cambia la señal**, solo evita el "pop". La salida está **invertida** respecto a la entrada (emisor común). Desde 50 mVp ya es casi cuadrada (~0,9 Vpp); subir la amplitud solo endurece los flancos.

### 3.4 FFT de la salida (View → FFT en LTspice)
{img("bz_100mV_fft", "FFT de V(out) con 100 mVp de entrada")}

{img("bz_500mV_fft", "FFT de V(out) con 500 mVp de entrada")}

| Armónico (dB respecto a la fundamental) | 2.º | 3.º | 4.º | 5.º | 6.º |
|---|---|---|---|---|---|
| 100 mVp | {h['bz_100mV'][1]:.0f} | {h['bz_100mV'][2]:.0f} | {h['bz_100mV'][3]:.0f} | {h['bz_100mV'][4]:.0f} | {h['bz_100mV'][5]:.0f} |
| 500 mVp | {h['bz_500mV'][1]:.0f} | {h['bz_500mV'][2]:.0f} | {h['bz_500mV'][3]:.0f} | {h['bz_500mV'][4]:.0f} | {h['bz_500mV'][5]:.0f} |

A 100 mVp el recorte es asimétrico, así que aparecen **pares e impares** parecidos. A 500 mVp la onda se acerca a una cuadrada con ciclo útil del 50 %: los pares caen (2.º en {h['bz_500mV'][1]:.0f} dB) y dominan los impares.

### 3.5 Efecto de P1 (100 mVp)
{img("bz_pot", "V(out) para P1 al 30, 60, 80, 90 y 100 %")}

| Giro de P1 | Resistencia cursor–tierra (trimmer 50 kΩ) | Vpp | THD |
|---|---|---|---|
""" + "\n".join(f"| {s['step']*100:.0f} % | {fmt_r(logpot(s['step'], 50e3))} | {s['V(out)']['vpp']:.2f} V | {s['V(out)']['thd']:.0f} % |" for s in bp) + f"""

### 3.6 Efecto de la impedancia de la fuente (200 mVp)
{img("bz_fuente", "V(out) con RG = 0 (solo generador) y RG = 10 kΩ")}

Sin RG, el generador (50 Ω) mete más corriente a la base: {bzf[0.001]['vpp']:.2f} Vpp y THD de {bzf[0.001]['thd']:.0f} %. Con RG = 10 kΩ: {bzf[10000.0]['vpp']:.2f} Vpp y THD de {bzf[10000.0]['thd']:.0f} %. La traza de mayor amplitud es la que va sin RG.
""")

# ======================================================================= 4 Fuzz
fz = R["ff_fuzz"]
fv = R["ff_vol"]
md(f"""
## 4. Fuzz Face (NPN silicio)

### 4.1 Esquemáticos
{img("ff_pdf_esquematico", "Fuzz Face, versión del esquema original (NPN): S1A/S1B, R3 = 8.2k, IN/OUT")}

{img("ff_montaje_esquematico", "Fuzz Face, versión de montaje: sin S1, RT1 = trimmer")}

Las dos tienen la misma disposición que el PDF. El interruptor S1 (DPDT) aparece como **S1A** (entrada) y **S1B** (salida), unidos por el **cable de bypass** de abajo. El parámetro `byp` elige la posición: 0 = efecto, 1 = bypass.

**Cómo funciona.** Son dos etapas de emisor común con **acople directo** (el colector de Q1 va a la base de Q2).
- **R2 = 100 kΩ** realimenta en DC el emisor de Q2 a la base de Q1 y fija la polarización de las dos etapas.
- **FUZZ (P1 + C2)** decide cuánta resistencia de emisor de Q2 queda puenteada en AC: al 100 %, ganancia y recorte máximos.
- **La salida se toma en el nodo `tap`** (entre la R de 330 Ω y R3/RT1), no en el colector. Por eso la salida es baja (~0,3–0,4 Vpp), mientras que el **colector de Q2 recorre casi toda la fuente** (≈ {c2amp[0.2]['vmin']:.1f} V a {c2amp[0.2]['vmax']:.1f} V).

### 4.2 Punto de operación DC: ¿por qué el trimmer?
{img("ff_pdf_op", "punto de operación, versión original (R3 = 8.2k)")}

{img("ff_op", "punto de operación, versión de montaje (RT1 = 6.2k)")}

| Nodo | Versión original (8.2k) | Versión montaje (RT1 = 6.2k) |
|---|---|---|
| V(b1), base de Q1 | {fpo['V(b1)']:.3f} V | {fo['V(b1)']:.3f} V |
| V(c1), colector de Q1 = base de Q2 | {fpo['V(c1)']:.3f} V | {fo['V(c1)']:.3f} V |
| V(e2), emisor de Q2 | {fpo['V(e2)']:.3f} V | {fo['V(e2)']:.3f} V |
| **V(c2), colector de Q2** | **{fpo['V(c2)']:.2f} V** | **{fo['V(c2)']:.2f} V** |
| V(tap) | {fpo['V(tap)']:.2f} V | {fo['V(tap)']:.2f} V |
| I<sub>C1</sub> / I<sub>C2</sub> | {fpo['Ic(Q1)']*1e3:.3f} / {fpo['Ic(Q2)']*1e3:.3f} mA | {fo['Ic(Q1)']*1e3:.3f} / {fo['Ic(Q2)']*1e3:.3f} mA |
| Consumo | {-fpo['I(VCC1)']*1e3:.3f} mA | {-fo['I(VCC1)']*1e3:.3f} mA |

La corriente de Q2 la fija el emisor (≈ V<sub>e2</sub>/1 kΩ), así que R3 solo decide **dónde queda el colector**. Con 8.2k queda en {fpo['V(c2)']:.1f} V y la señal tiene mucho espacio para bajar y poco para subir. Con RT1 ≈ 6.2k queda en el centro (~4.5 V).

### 4.3 Polarización según hFE y el trimmer
Barrido DC del valor de RT1 (2 a 10 kΩ) para hFE = 100, 200, 300 y 400. **El eje X es el valor de RT1**; LTspice lo rotula en "V" porque lo barre con una fuente de control (2 KV = 2 kΩ). De abajo hacia arriba las curvas son hFE = 100, 200, 300 y 400.

{img("ff_bias", "V(c2) vs. RT1 para cuatro valores de hFE")}

| hFE (Q1 = Q2) | V(c2) con 8.2k | V(c2) con 6.2k | RT1 necesaria para 4.5 V |
|---|---|---|---|
""" + "\n".join(f"| {k} | {v['vc2_con_8k2']:.2f} V | {v['vc2_con_6k2']:.2f} V | {v['R_para_4V5']/1e3:.2f} kΩ |" for k, v in bias.items()) + f"""

Con cualquier 2N3904 (hFE típico de 100 a 400), un trimmer de 10 kΩ permite llegar a 4.5 V. Con 8.2k fija nunca se llega.

### 4.4 Entrada vs. salida: versión original vs. montaje (FUZZ y VOL al 100 %, RG = 10 kΩ)
{img("ff_pdf_amp", "versión original (8.2k, S1 en efecto): V(out) arriba, V(gen) abajo")}

{img("ff_amp", "versión de montaje (RT1 = 6.2k): V(out) arriba, V(gen) abajo")}

**Versión original (R3 = 8.2k)**
{amp_table("ff_pdf_amp", False)}

**Versión de montaje (RT1 = 6.2k)**
{amp_table("ff_amp", False)}

Comparación directa en el mismo circuito, cambiando solo R3/RT1 (200 mVp):

{img("ff_rc2", "V(c2) arriba y V(out) abajo, con 6.2k y con 8.2k")}

| | 8.2k (original) | 6.2k (trimmer ajustado) |
|---|---|---|
| V(out) | {rc2[8200.0]['V(out)']['vpp']:.2f} Vpp ({rc2[8200.0]['V(out)']['vmax']:+.2f} / {rc2[8200.0]['V(out)']['vmin']:+.2f} V) | {rc2[6200.0]['V(out)']['vpp']:.2f} Vpp ({rc2[6200.0]['V(out)']['vmax']:+.2f} / {rc2[6200.0]['V(out)']['vmin']:+.2f} V) |
| THD | {rc2[8200.0]['V(out)']['thd']:.0f} % | {rc2[6200.0]['V(out)']['thd']:.0f} % |

Con el trimmer la salida es **~30 % más grande** y más simétrica. En V(out), la traza de mayor amplitud es la de 6.2k.

### 4.5 El interruptor S1 (solo en la versión original)
{img("ff_pdf_bypass", "V(out) con S1 en efecto (cuadrada) y en bypass (senoidal); V(gen) abajo")}

| Posición de S1 | V(out) | THD |
|---|---|---|
| byp = 0 (efecto) | {byp[0.0]['vpp']:.2f} Vpp | {byp[0.0]['thd']:.0f} % |
| byp = 1 (bypass) | {byp[1.0]['vpp']:.2f} Vpp | {byp[1.0]['thd']:.1f} % |

En bypass la salida es la misma senoidal de entrada (solo cae un poco por el divisor entre RG = 10 kΩ y el osciloscopio de 1 MΩ). Con S1 en "efecto", los contactos cerrados (≈ 0 Ω) dejan el circuito igual que sin S1. **Por eso se puede quitar S1 del montaje sin cambiar nada de lo que se mide.**

### 4.6 FFT de la salida (versión de montaje)
{img("ff_100mV_fft", "FFT de V(out) con 100 mVp de entrada")}

{img("ff_500mV_fft", "FFT de V(out) con 500 mVp de entrada")}

| Armónico (dB respecto a la fundamental) | 2.º | 3.º | 4.º | 5.º | 6.º |
|---|---|---|---|---|---|
| 100 mVp | {h['ff_100mV'][1]:.0f} | {h['ff_100mV'][2]:.0f} | {h['ff_100mV'][3]:.0f} | {h['ff_100mV'][4]:.0f} | {h['ff_100mV'][5]:.0f} |
| 500 mVp | {h['ff_500mV'][1]:.0f} | {h['ff_500mV'][2]:.0f} | {h['ff_500mV'][3]:.0f} | {h['ff_500mV'][4]:.0f} | {h['ff_500mV'][5]:.0f} |

Al subir la amplitud, el ciclo útil de la cuadrada se desbalancea (efecto de "compuerta" o gating del Fuzz Face) y el **2.º armónico sube**: de {h['ff_100mV'][1]:.0f} dB a {h['ff_500mV'][1]:.0f} dB.

### 4.7 Potenciómetro FUZZ (P1, 1 kΩ lineal), entrada suave de 20 mVp
{img("ff_fuzz", "V(out) para FUZZ al 0, 25, 50, 75 y 100 %")}

| Giro de FUZZ | Resistencia cursor–tierra (trimmer 1 kΩ) | Vpp | THD | Forma |
|---|---|---|---|---|
""" + "\n".join(f"| {s['step']*100:.0f} % | {fmt_r(s['step']*1e3)} | {s['V(out)']['vpp']:.2f} V | {s['V(out)']['thd']:.2g} % | {'senoidal' if s['V(out)']['thd'] < 5 else ('recorte suave' if s['V(out)']['thd'] < 25 else 'cuadrada')} |" for s in fz) + f"""

Este barrido se hace a 20 mVp porque a amplitudes mayores todas las posiciones saturan. Con FUZZ bajo el THD es mínimo: el emisor de Q2 no queda puenteado y R2 también realimenta en AC, lo que linealiza el amplificador.

### 4.8 Potenciómetro VOLUMEN (P2, 500 kΩ log), 200 mVp
{img("ff_vol", "V(out) para VOL al 20, 40, 60, 80 y 100 %")}

| Giro de VOL | Resistencia cursor–tierra (trimmer 500 kΩ) | Vpp |
|---|---|---|
""" + "\n".join(f"| {s['step']*100:.0f} % | {fmt_r(logpot(s['step'], 500e3))} | {s['V(out)']['vpp']*1000:.0f} mV |" for s in fv) + f"""

VOL es un divisor: solo escala la amplitud, no cambia la forma de la onda.

### 4.9 Efecto de la impedancia de la fuente (200 mVp)
{img("ff_fuente", "V(out) con RG = 0 y RG = 10 kΩ")}

Con el generador directo (RG = 0) los pulsos se angostan mucho y se desplazan (THD {fff[0.001]['thd']:.0f} %). Con 10 kΩ la onda es más pareja (THD {fff[10000.0]['thd']:.0f} %). El Fuzz Face es famoso por cambiar según lo que tenga conectado antes. **En el lab mide los dos casos.**
""")

# ======================================================================= 5 montaje
md(f"""
## 5. Montaje en protoboard (versión de montaje)

**Convención:** las columnas se numeran 1…60, y cada columna (filas a–e) es un nodo. **Riel rojo = +9 V**, **riel azul = GND**.

### Reglas generales
1. **Monta con la fuente apagada.** Configúrala en **9.0 V con límite de 30–50 mA**. Cada circuito consume menos de 1 mA, así que si al encender ves más de 10 mA, apaga y revisa.
2. Conecta primero **todas las tierras**: el negativo de la fuente, el negro del generador y el negro de las dos puntas del osciloscopio al riel GND.
3. Respeta la polaridad de los electrolíticos y los pines del 2N3904 (**E-B-C**).
4. Antes de encender, comprueba con el multímetro que **+9 V y GND no estén en corto**.
5. Puentes cortos: a la entrada hay ganancia muy alta y los cables largos captan ruido de 60 Hz.

### 5.1 Bazz Fuss
| Paso | Componente | Conexión (columnas) |
|---|---|---|
| 1 | Q1 2N3904 | E → col 20, B → col 21, C → col 22 (cara plana hacia ti) |
| 2 | Puente | col 20 → GND |
| 3 | R1 10 kΩ | col 22 → +9 V |
| 4 | D1 1N4148 | ánodo en col 22, **cátodo (franja) en col 21**. Móntalo de pie, con una pata doblada |
| 5 | P1 trimmer 50 kΩ | patas en col 10 (extremo), col 11 (cursor) y col 12 (extremo) |
| 6 | Puente | col 12 → GND |
| 7 | C1 10 µF | **−** en col 11 (cursor de P1), **+** en col 21 |
| 8 | RG 10 kΩ | col 6 → col 10 |
| 9 | C2 10 µF | **+** en col 22, **−** en col 28 |
| 10 | R2 1 MΩ | col 28 → GND |
| 11 | Generador | rojo → col 6 (o col 10 para probar sin RG), negro → GND |
| 12 | Osciloscopio | CH1 → col 6 (entrada), CH2 → col 28 (salida) |

### 5.2 Fuzz Face
**Antes de montar:**
- Si el multímetro mide hFE, mide 4 o 5 transistores. Usa el de **menor hFE como Q1** y uno de hFE medio como Q2.
- Ajusta RT1 a **≈ 6 kΩ** midiendo entre una pata extrema y el cursor antes de insertarlo.

| Paso | Componente | Conexión (columnas) |
|---|---|---|
| 1 | Q1 2N3904 | E → col 20, B → col 21, C → col 22 |
| 2 | Puente | col 20 → GND |
| 3 | R1 33 kΩ | col 22 → +9 V |
| 4 | Q2 2N3904 | E → col 30, B → col 31, C → col 32 |
| 5 | Puente | col 22 → col 31 (colector Q1 → base Q2) |
| 6 | R2 100 kΩ | col 30 → col 21 (emisor Q2 → base Q1) |
| 7 | P1 FUZZ trimmer 1 kΩ | patas en col 24 (extremo), col 25 (cursor) y col 26 (extremo) |
| 8 | Puentes | col 24 → GND; col 26 → col 30 (emisor Q2) |
| 9 | C2 22 µF | **+** en col 25 (cursor de FUZZ), **−** a GND |
| 10 | RT1 trimmer 10 kΩ | patas en col 32 (extremo, colector Q2), col 33 (cursor) y col 34 (extremo) |
| 11 | Puentes | col 33 → col 34 y col 34 → col 36 |
| 12 | R4 330 Ω | col 36 → +9 V (col 36 = nodo `tap`) |
| 13 | C3 100 nF | col 36 → col 40 |
| 14 | P2 VOL trimmer 500 kΩ | patas en col 40 (extremo), col 41 (cursor = **salida**) y col 42 (extremo) |
| 15 | Puente | col 42 → GND |
| 16 | C1 2.2 µF | **−** en col 10, **+** en col 21 |
| 17 | RG 10 kΩ | col 6 → col 10 |
| 18 | Generador | rojo → col 6 (o col 10 sin RG), negro → GND |
| 19 | Osciloscopio | CH1 → col 6, CH2 → col 41 (salida). Úsalo también para ver col 32 (colector Q2) |

**Ajuste de RT1 (encendido y sin señal):** mide V(col 32) contra GND y gira RT1 hasta leer **4.5 V**.

**Posición de los trimmers:** con un trimmer no hay "% de giro". Para comparar con las tablas, mide con el circuito **apagado y el generador desconectado** la resistencia entre el **cursor y la pata que va a GND**. Las tablas de §3.5, §4.7 y §4.8 dan el valor que corresponde a cada posición simulada.
""")

# ======================================================================= 6 mediciones
md(f"""
## 6. Qué medir en el laboratorio

### Configuración de los equipos
- **Generador:** senoidal de 1 kHz, offset 0. Si tiene la opción "Load / Output impedance", ponla en **High-Z**; si queda en 50 Ω, la amplitud real sale el doble de la que muestra la pantalla. Revisa si muestra **Vpp o Vp** (100 mVp = 200 mVpp) y confirma siempre la amplitud en CH1.
- **Osciloscopio:** trigger en CH1. Base de tiempo de **0.2–0.5 ms/div**. CH1 en 20–200 mV/div; CH2 en 100 mV/div para la salida y en 2 V/div para el colector de Q2. Usa acople **DC** para voltajes de nodo.
  - Con 20 mVp de entrada usa la punta en **x1**.
  - Si tiene **FFT** (Math → FFT, ventana Hanning, en dBV), compárala con las FFT de LTspice de §3.4 y §4.6.

### 6.1 Voltajes DC (multímetro, sin señal)
**Bazz Fuss**

| Punto | Simulación | Rango aceptable | Medido |
|---|---|---|---|
| VCC | {bo['V(vcc)']:.2f} V | 8.9 – 9.1 V | |
| Base Q1 (col 21) | {bo['V(b)']:.2f} V | 0.55 – 0.72 V | |
| Colector Q1 (col 22) | {bo['V(c)']:.2f} V | 0.85 – 1.3 V | |
| Salida (col 28) | 0.00 V | ≈ 0 V | |
| Corriente de la fuente | {-bo['I(VCC1)']*1e3:.2f} mA | 0.6 – 1.0 mA | |

**Fuzz Face**

| Punto | Simulación | Rango aceptable | Medido |
|---|---|---|---|
| VCC | {fo['V(vcc)']:.2f} V | 8.9 – 9.1 V | |
| Base Q1 (col 21) | {fo['V(b1)']:.2f} V | 0.55 – 0.70 V | |
| Colector Q1 = base Q2 (col 22) | {fo['V(c1)']:.2f} V | 1.2 – 1.6 V | |
| Emisor Q2 (col 30) | {fo['V(e2)']:.2f} V | 0.6 – 0.9 V | |
| **Colector Q2 (col 32)** | **{fo['V(c2)']:.2f} V** | **ajustar a 4.5 V con RT1** | |
| Tap (col 36) | {fo['V(tap)']:.2f} V | 8.6 – 8.85 V | |
| Corriente de la fuente | {-fo['I(VCC1)']*1e3:.2f} mA | 0.7 – 1.2 mA | |
| RT1 final (apagado, cursor–extremo) | 6.2 kΩ | 5 – 6.5 kΩ | |

*Opcional, para comparar con la versión original:* pon una resistencia fija de 8.2 kΩ en lugar de RT1 y mide V(col 32). Según la simulación debe dar ≈ {fpo['V(c2)']:.1f} V.

### 6.2 Formas de onda: salida vs. amplitud (1 kHz, con RG de 10 kΩ)
Guarda una captura del osciloscopio para cada caso y compárala con §3.3 y §4.4.

**Bazz Fuss (P1 al máximo)**, salida en col 28:

{amp_table("bz_amp")}

**Fuzz Face (FUZZ y VOL al máximo)**, salida en col 41:

{amp_table("ff_amp")}

En el Fuzz Face mide también el **colector de Q2 (col 32)**: según la simulación oscila entre ≈ {c2amp[0.2]['vmin']:.1f} V y {c2amp[0.2]['vmax']:.1f} V.

### 6.3 Trimmers / potenciómetros
**Bazz Fuss, P1 (100 mVp)**

| Resistencia cursor–tierra | Vpp sim | Vpp medido |
|---|---|---|
""" + "\n".join(f"| {fmt_r(logpot(s['step'], 50e3))} | {s['V(out)']['vpp']:.2f} V | |" for s in bp) + """

**Fuzz Face, FUZZ (20 mVp, VOL al máximo)**

| Resistencia cursor–tierra | Vpp sim | Forma esperada | Vpp medido |
|---|---|---|---|
""" + "\n".join(f"| {fmt_r(s['step']*1e3)} | {s['V(out)']['vpp']:.2f} V | {'senoidal' if s['V(out)']['thd'] < 5 else ('recorte suave' if s['V(out)']['thd'] < 25 else 'cuadrada')} | |" for s in fz) + """

**Fuzz Face, VOLUMEN (200 mVp, FUZZ al máximo)**

| Resistencia cursor–tierra | Vpp sim | Vpp medido |
|---|---|---|
""" + "\n".join(f"| {fmt_r(logpot(s['step'], 500e3))} | {s['V(out)']['vpp']*1000:.0f} mV | |" for s in fv) + f"""

### 6.4 Con pastilla emulada vs. generador directo (200 mVp)
Mueve el cable rojo del generador de la col 6 a la col 10 para quitar RG.

| Circuito | Vpp con 10 kΩ (sim) | Vpp sin RG (sim) | Medido con 10 kΩ | Medido sin RG |
|---|---|---|---|---|
| Bazz Fuss | {bzf[10000.0]['vpp']:.2f} V | {bzf[0.001]['vpp']:.2f} V | | |
| Fuzz Face | {fff[10000.0]['vpp']:.2f} V | {fff[0.001]['vpp']:.2f} V | | |

### ¿Por qué pueden diferir medición y simulación?
- El hFE y el V<sub>BE</sub> reales son distintos a los del modelo de LTspice (2N3904 con hFE = 300). En el Fuzz Face eso se corrige con RT1.
- Tolerancias: resistencias 5 %, trimmers 20 %, electrolíticos 20 %.
- La caída real del 1N4148 a pocos µA es distinta a la del modelo, así que V<sub>C</sub> del Bazz Fuss puede salir entre 0.9 y 1.2 V.
""")

# ======================================================================= 7
md("""
## 7. Si algo no funciona

| Síntoma | Causa probable | Qué revisar |
|---|---|---|
| La fuente marca > 10 mA | Corto o transistor al revés | Pines E-B-C y polaridad de los electrolíticos |
| Bazz Fuss: V<sub>C</sub> ≈ 9 V | D1 al revés o Q1 sin base | Franja de D1 hacia la base (col 21) |
| Bazz Fuss: V<sub>C</sub> ≈ 0.1 V | Q1 saturado | Que no haya un puente uniendo col 21 y col 22 |
| Fuzz Face: no se llega a 4.5 V en el colector de Q2 | RT1 mal conectado o Q2 al revés | RT1 entre col 32 y col 36. Prueba otro transistor |
| Fuzz Face: V<sub>c1</sub> ≈ 9 V | Q1 cortado o R2 suelta | R2 entre col 30 y col 21 |
| Zumbido de 60 Hz | Tierras mal unidas o cables largos | Todas las tierras al mismo riel. Cables de entrada cortos |
| Oscilación de alta frecuencia | Ganancia alta + cables largos | Acortar cables. Opcional: 100 pF entre colector y base de Q2 |
| Salida nula | Trimmer mal colocado (cursor a tierra) | Medir resistencia cursor–tierra |
""")

# ======================================================================= 8
md("""
## 8. Volver a correr las simulaciones

`sim/correr_simulaciones.py` simula todos los casos en LTspice, calcula las cifras y toma las capturas (~6 minutos).

**Antes de correrlo cierra todas las ventanas de LTspice y no toques el mouse ni el teclado mientras corre.** El script abre y cierra LTspice y hace clics para la FFT. Si alguna ventana le quita el foco, cancela esa captura en lugar de hacer clic en otro lado.

Para recalcular solo las cifras, sin abrir LTspice: `python sim/correr_simulaciones.py --sin-gui`.
""")
code("""
import subprocess, sys
subprocess.run([sys.executable, "sim/correr_simulaciones.py"], check=True)   # simula + capturas de LTspice (~6 min)
subprocess.run([sys.executable, "sim/generar_notebook.py"], check=True)      # actualiza este notebook
""")

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                   "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 5}
out = ROOT / "guia_montaje.ipynb"
out.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print("notebook ->", out)
