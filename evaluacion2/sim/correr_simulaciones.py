"""Corre TODAS las simulaciones en LTspice y toma las CAPTURAS de pantalla de LTspice.

    python sim/correr_simulaciones.py            # simula + captura (no tocar mouse/teclado ~5 min)
    python sim/correr_simulaciones.py --sin-gui  # solo simula y calcula las cifras

Para cada caso: copia el .asc con las directivas del caso -> simula en batch ->
calcula cifras (Vpp, THD, armonicos) a partir del .raw de LTspice -> abre el .raw
en LTspice con las trazas elegidas (.plt) y captura la ventana.
Resultados: sim/resultados.json   Capturas: graficas/*.png
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ltspice import read_op, read_raw, spectrum
from gui import CAP_DIR, GRAF, batch, capture, make_case, raw_vars, write_plt

GUI = "--sin-gui" not in sys.argv
F0 = 1000.0
AMPS = [0.05, 0.1, 0.2, 0.5, 1.0]
BASE = [".lib pots.lib", ".options plotwinsize=0"]
TRAN = ".tran 0 200m 150m 2u"           # se guardan solo los ultimos 50 ms (regimen permanente)
X3 = (0.047, 0.050)                     # ultimos 3 ciclos (eje de LTspice empieza en 150 ms)
QH = (".model QH NPN(IS=1E-14 VAF=100 Bf={hfe} IKF=0.4 XTB=1.5 BR=4 CJC=4E-12 CJE=8E-12 "
      "RB=20 RC=0.1 RE=0.1 TR=250E-9 TF=350E-12 ITF=1 VTF=2 XTF=3)")


def metrics(t, v):
    f, db, h = spectrum(t, v, F0, ncycles=50)
    thd = float(np.sqrt(np.sum(h[1:] ** 2)) / h[0] * 100)
    m = t >= t[-1] - 20e-3
    return {"vmax": float(v[m].max()), "vmin": float(v[m].min()), "vpp": float(np.ptp(v[m])),
            "vdc": float(v[m].mean()), "thd": thd,
            "harm_db": [float(20 * np.log10(x / h[0])) for x in h]}


def fft_clicks(raw, trace):
    """Clics para View -> FFT -> elegir la traza -> OK -> zoom 100 Hz..100 kHz."""
    idx, _ = raw_vars(raw)
    k = idx[trace] - 1                      # la lista del dialogo no incluye 'time'
    col, row = divmod(k, 13)
    x, y = 520 + 73 * col, 151 + 13 * row
    return f"75,32|w600|100,233|w1500|{x},{y}|831,100|w3000|d393,130,786,420"


RES = {}


def tran_case(key, asc, params, step=None, panes=None, extra=(), sig=("V(out)",), fft=None, subs=None):
    """Transitorio (opcionalmente con .step). Guarda cifras y captura."""
    name, values = key, None
    dirs = BASE + [".param " + params] + list(extra) + [TRAN]
    if step:
        p, values = step
        dirs.append(f".step param {p} list " + " ".join(str(v) for v in values))
    a = make_case(name, asc, dirs, subs)
    raw, log = batch(a)
    steps = read_raw(raw)["steps"]
    labels = re.findall(r"^\.step (\S+)=(\S+)", log, re.M)   # orden real de LTspice
    out = []
    for i, d in enumerate(steps):
        r = {s: metrics(d["time"], d[s]) for s in sig}
        if values:
            r["step"] = float(labels[i][1])
        out.append(r)
    RES[key] = out
    if GUI:
        if not fft:   # en los casos de FFT solo se captura el espectro
            write_plt(raw, panes or [{"traces": ["V(out)"]}, {"traces": ["V(gen)"]}], x=X3)
            capture(raw, GRAF / f"{key}.png")
        else:
            write_plt(raw, [{"traces": [fft]}], x=X3)
            capture(raw, GRAF / f"{key}_fft.png", clicks=fft_clicks(raw, fft), keys_wait=1.0)
    print(" ", key, "ok")


def op_case(key, asc, params):
    a = make_case(key, asc, BASE + [".param " + params, ".op"])
    raw, log = batch(a)
    RES[key] = read_op(a.with_suffix(".op.raw") if a.with_suffix(".op.raw").exists() else raw)
    if GUI:
        capture(a, GRAF / f"{key}.png", run=True, wait=5, dialog=".net")
    print(" ", key, "ok")


def schematic(key, asc):
    if GUI:
        from ltspice import LTSPICE_DIR
        capture(LTSPICE_DIR / asc, GRAF / f"{key}.png")
    print(" ", key, "ok")


def bias_case():
    """Familia de curvas V(c2) vs RT1 para varios hFE: barrido .dc de una fuente que fija
    la resistencia del trimmer (resistencia comportamental R = V(rctl)) + .step de hFE."""
    key = "ff_bias"
    hfes = [100, 200, 300, 400]
    dirs = BASE + [".param A=0 Rg=10k fuzz=1 vol=1", QH, "Vctl rctl 0 6200",
                   ".step param hfe list " + " ".join(map(str, hfes)),
                   ".dc Vctl 2000 10000 100"]
    a = make_case(key, "FuzzFace.asc", dirs, subs={"SYMATTR Value 2N3904": "SYMATTR Value QH",
                                                  "SYMATTR Value {Rc2}": "SYMATTR Value R=V(rctl)"})
    raw, log = batch(a)
    steps = read_raw(raw)["steps"]
    res = {}
    for h, d in zip(hfes, steps):
        r = d["V(rctl)"] if "V(rctl)" in d else d[list(d)[0]]
        vc = d["V(c2)"]
        need = float(np.interp(4.5, vc[::-1], r[::-1]))
        res[h] = {"R_para_4V5": need, "vc2_con_8k2": float(np.interp(8200, r, vc)),
                  "vc2_con_6k2": float(np.interp(6200, r, vc))}
    RES[key] = {"hfe": res}
    if GUI:
        write_plt(raw, [{"traces": ["V(c2)"]}], x=(2000, 10000), xunit="K")
        capture(raw, GRAF / f"{key}.png")
    print(" ", key, "ok")


if __name__ == "__main__":
    GRAF.mkdir(exist_ok=True)
    print("BAZZ FUSS")
    schematic("bz_pdf_esquematico", "BazzFuss_PDF.asc")
    schematic("bz_montaje_esquematico", "BazzFuss.asc")
    op_case("bz_pdf_op", "BazzFuss_PDF.asc", "A=0 Rg=10k vol=1")
    op_case("bz_op", "BazzFuss.asc", "A=0 Rg=10k vol=1")
    tran_case("bz_pdf_amp", "BazzFuss_PDF.asc", "Rg=10k vol=1", step=("A", AMPS))
    tran_case("bz_amp", "BazzFuss.asc", "Rg=10k vol=1", step=("A", AMPS))
    tran_case("bz_100mV", "BazzFuss.asc", "A=0.1 Rg=10k vol=1", fft="V(out)")
    tran_case("bz_500mV", "BazzFuss.asc", "A=0.5 Rg=10k vol=1", fft="V(out)")
    tran_case("bz_pot", "BazzFuss.asc", "A=0.1 Rg=10k", step=("vol", [0.3, 0.6, 0.8, 0.9, 1.0]))
    tran_case("bz_fuente", "BazzFuss.asc", "A=0.2 vol=1", step=("Rg", ["1m", "10k"]))

    print("FUZZ FACE")
    schematic("ff_pdf_esquematico", "FuzzFace_PDF.asc")
    schematic("ff_montaje_esquematico", "FuzzFace.asc")
    op_case("ff_pdf_op", "FuzzFace_PDF.asc", "A=0 Rg=10k fuzz=1 vol=1 byp=0")
    op_case("ff_op", "FuzzFace.asc", "A=0 Rg=10k fuzz=1 vol=1 Rc2=6.2k")
    tran_case("ff_pdf_amp", "FuzzFace_PDF.asc", "Rg=10k fuzz=1 vol=1 byp=0", step=("A", AMPS), sig=("V(out)", "V(c2)"))
    tran_case("ff_pdf_bypass", "FuzzFace_PDF.asc", "A=0.2 Rg=10k fuzz=1 vol=1", step=("byp", [0, 1]))
    tran_case("ff_rc2", "FuzzFace.asc", "A=0.2 Rg=10k fuzz=1 vol=1", step=("Rc2", ["8.2k", "6.2k"]),
              panes=[{"traces": ["V(c2)"]}, {"traces": ["V(out)"]}], sig=("V(out)", "V(c2)"))
    bias_case()
    tran_case("ff_amp", "FuzzFace.asc", "Rg=10k fuzz=1 vol=1 Rc2=6.2k", step=("A", AMPS), sig=("V(out)", "V(c2)"))
    tran_case("ff_100mV", "FuzzFace.asc", "A=0.1 Rg=10k fuzz=1 vol=1 Rc2=6.2k", fft="V(out)")
    tran_case("ff_500mV", "FuzzFace.asc", "A=0.5 Rg=10k fuzz=1 vol=1 Rc2=6.2k", fft="V(out)")
    tran_case("ff_fuzz", "FuzzFace.asc", "A=0.02 Rg=10k vol=1 Rc2=6.2k", step=("fuzz", [0, 0.25, 0.5, 0.75, 1]))
    tran_case("ff_vol", "FuzzFace.asc", "A=0.2 Rg=10k fuzz=1 Rc2=6.2k", step=("vol", [0.2, 0.4, 0.6, 0.8, 1.0]))
    tran_case("ff_fuente", "FuzzFace.asc", "A=0.2 fuzz=1 vol=1 Rc2=6.2k", step=("Rg", ["1m", "10k"]))

    out = Path(__file__).resolve().parent / "resultados.json"
    out.write_text(json.dumps(RES, indent=1, default=str), encoding="utf-8")
    # sim/capturas/ solo guarda archivos intermedios (.asc, .net, .raw, .fft...): se borra al final
    import shutil
    shutil.rmtree(CAP_DIR, ignore_errors=True)
    print("resultados ->", out)
