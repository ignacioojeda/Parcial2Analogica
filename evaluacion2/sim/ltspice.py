"""Utilidades minimas para correr LTspice en modo batch y leer archivos .raw.

Uso basico:
    from ltspice import netlist_from_asc, run, read_raw
    net = netlist_from_asc("ltspice/BazzFuss.asc")
    res = run(net, "prueba", extra=[".op"], drop=[".tran", ".four"])
    data = read_raw(res["raw"])
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
LTSPICE_DIR = ROOT / "ltspice"
RUNS_DIR = ROOT / "sim" / "runs"


def find_ltspice():
    cands = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/ADI/LTspice/LTspice.exe",
        Path("C:/Program Files/ADI/LTspice/LTspice.exe"),
        Path("C:/Program Files/LTC/LTspiceXVII/XVIIx64.exe"),
    ]
    for c in cands:
        if c.exists():
            return str(c)
    raise FileNotFoundError("No se encontro LTspice.exe")


LTSPICE = find_ltspice()


def _read_text(path):
    b = Path(path).read_bytes()
    if b[:2] in (b"\xff\xfe", b"\xfe\xff") or (len(b) > 1 and b[1] == 0):
        return b.decode("utf-16-le", errors="replace").lstrip("\ufeff")
    return b.decode("utf-8", errors="replace")


def netlist_from_asc(asc):
    """Pide a LTspice el netlist del esquematico (.asc) y lo devuelve como texto."""
    asc = Path(asc)
    subprocess.run([LTSPICE, "-netlist", str(asc)], check=True, cwd=asc.parent)
    return _read_text(asc.with_suffix(".net"))


def run(net, name, extra=(), drop=(), replace=None, workdir=RUNS_DIR):
    """Corre una simulacion en batch.

    net     : texto del netlist base
    name    : nombre del caso (archivo <name>.net en sim/runs)
    drop    : directivas a eliminar (p.ej. ".tran", ".four", ".param")
    extra   : lineas a agregar antes de .end
    replace : dict {regex: reemplazo} aplicado al netlist
    """
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    lines = []
    for ln in net.splitlines():
        low = ln.strip().lower()
        if low.startswith(".end") and not low.startswith(".ends"):
            continue
        if low.startswith(".backanno"):
            continue
        if any(low.startswith(d) for d in drop):
            continue
        if low.startswith(".lib pots.lib"):
            ln = f".lib {(LTSPICE_DIR / 'pots.lib').as_posix()}"
        lines.append(ln)
    text = "\n".join(lines + list(extra) + [".end", ""])
    for k, v in (replace or {}).items():
        text = re.sub(k, v, text, flags=re.M)
    netf = workdir / f"{name}.net"
    netf.write_text(text, encoding="utf-8")
    for ext in (".raw", ".op.raw", ".log"):
        p = netf.with_suffix(ext)
        if p.exists():
            p.unlink()
    subprocess.run([LTSPICE, "-b", netf.name], check=True, cwd=workdir)
    log = _read_text(netf.with_suffix(".log"))
    if "error" in log.lower() and "fatal" in log.lower():
        raise RuntimeError(log)
    return {"net": netf, "raw": netf.with_suffix(".raw"), "log": log}


def read_raw(path):
    """Lee un .raw binario de LTspice (tran / op / dc). Devuelve dict con
    'vars' (lista de nombres), 'steps' (lista de dicts nombre->array)."""
    b = Path(path).read_bytes()
    marker = "Binary:\n".encode("utf-16-le")
    i = b.find(marker)
    if i < 0:
        raise ValueError("Formato .raw no soportado (se esperaba binario)")
    header = b[:i].decode("utf-16-le")
    data = b[i + len(marker):]
    npts = int(re.search(r"No. Points:\s*(\d+)", header).group(1))
    nvar = int(re.search(r"No. Variables:\s*(\d+)", header).group(1))
    flags = re.search(r"Flags:(.*)", header).group(1)
    varsec = header.split("Variables:")[-1].strip().splitlines()
    names =[ln.strip().split()[1] for ln in varsec[:nvar]]
    if "complex" in flags:
        raise ValueError("AC (complejo) no implementado")
    per_pt = len(data) // npts
    if per_pt == 8 * nvar:
        arr = np.frombuffer(data[: npts * per_pt], dtype="<f8").reshape(npts, nvar)
    elif per_pt == 8 + 4 * (nvar - 1):
        dt = np.dtype([("t", "<f8"), ("v", "<f4", (nvar - 1,))])
        rec = np.frombuffer(data[: npts * per_pt], dtype=dt)
        arr = np.column_stack([rec["t"], rec["v"].astype(float)])
    else:
        raise ValueError(f"Tamano de punto inesperado: {per_pt}")
    x = np.abs(arr[:, 0])
    # separar pasos (.step): el eje x reinicia
    cuts = [0] + list(np.where(np.diff(x) < 0)[0] + 1) + [npts]
    steps = []
    for a, c in zip(cuts, cuts[1:]):
        d = {n: arr[a:c, k] for k, n in enumerate(names)}
        d[names[0]] = x[a:c]
        steps.append(d)
    return {"vars": names, "steps": steps, "header": header}


def read_op(path):
    """Lee el .op.raw (o .raw de .op) y devuelve dict nombre -> valor."""
    r = read_raw(path)
    return {n: float(v[0]) for n, v in r["steps"][0].items()}


def parse_four(log):
    """Extrae THD y armonicos de cada bloque .four del log."""
    out = []
    for blk in re.split(r"Fourier components of", log)[1:]:
        thd = re.search(r"Total Harmonic Distortion:\s*([\d.eE+-]+)%", blk)
        dc = re.search(r"DC component:\s*([\d.eE+-]+)", blk)
        harms = re.findall(r"^\s*(\d+)\s+([\d.eE+]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)", blk, re.M)
        out.append({
            "thd": float(thd.group(1)) if thd else np.nan,
            "dc": float(dc.group(1)) if dc else np.nan,
            "harm": [(int(h[0]), float(h[1]), float(h[2]), float(h[3])) for h in harms],
        })
    return out


def uniform(t, y, fs):
    """Remuestrea una senal a paso uniforme (para FFT)."""
    tu = np.arange(t[0], t[-1], 1 / fs)
    return tu, np.interp(tu, t, y)


def spectrum(t, y, f0=1000.0, ncycles=None, fs=200e3):
    """FFT con ventana de Hann sobre un numero entero de ciclos al final de la senal.
    Devuelve (f, mag_dBV, armonicos_Vpico)."""
    T = 1 / f0
    if ncycles is None:
        ncycles = int(np.floor((t[-1] - t[0]) / T))
    t0 = t[-1] - ncycles * T
    m = t >= t0
    tu, yu = uniform(t[m], y[m], fs)
    yu = yu - yu.mean()
    w = np.hanning(len(yu))
    Y = np.fft.rfft(yu * w) / (w.sum() / 2)
    f = np.fft.rfftfreq(len(yu), 1 / fs)
    mag = np.abs(Y)
    harms = []
    for k in range(1, 11):
        idx = np.argmin(np.abs(f - k * f0))
        harms.append(mag[max(idx - 2, 0): idx + 3].max())
    return f, 20 * np.log10(mag + 1e-12), np.array(harms)
