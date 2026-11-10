"""Corre casos en LTspice y toma CAPTURAS de pantalla de la interfaz grafica.

Cada caso se arma en sim/capturas/<nombre>/ con una copia del .asc (con las
directivas del caso), se simula en batch, se escribe el .plt (que trazas ver)
y luego se abre el .raw en la GUI de LTspice para capturar la ventana.
"""
import re
import shutil
import subprocess
import time
from pathlib import Path

from ltspice import LTSPICE, LTSPICE_DIR, ROOT, _read_text, read_raw

CAP_DIR = ROOT / "sim" / "capturas"
GRAF = ROOT / "graficas"
PS1 = ROOT / "sim" / "captura.ps1"


def make_case(name, asc, directives, subs=None):
    d = CAP_DIR / name
    d.mkdir(parents=True, exist_ok=True)
    for f in ("pot.asy", "spdt.asy", "pots.lib"):
        shutil.copy(LTSPICE_DIR / f, d / f)
    txt = (LTSPICE_DIR / asc).read_text(encoding="latin-1")
    new = "\\n".join(directives)
    txt, n = re.subn(r"^(TEXT -?\d+ -?\d+ Left 2 !)\.lib pots\.lib.*$", lambda m: m.group(1) + new, txt, flags=re.M)
    assert n == 1, "no se encontro el bloque de directivas"
    for k, v in (subs or {}).items():
        txt = txt.replace(k, v)
    a = d / f"{name}.asc"
    a.write_text(txt, encoding="latin-1", newline="\n")
    return a


def batch(asc):
    asc = Path(asc)
    subprocess.run([LTSPICE, "-netlist", asc.name], check=True, cwd=asc.parent)
    subprocess.run([LTSPICE, "-b", asc.with_suffix(".net").name], check=True, cwd=asc.parent)
    return asc.with_suffix(".raw"), _read_text(asc.with_suffix(".log"))


def raw_vars(raw):
    b = Path(raw).read_bytes()
    i = b.find("Binary:\n".encode("utf-16-le"))
    h = b[:i].decode("utf-16-le")
    nv = int(re.search(r"No. Variables:\s*(\d+)", h).group(1))
    lines = h.split("Variables:")[-1].strip().splitlines()[:nv]
    return {ln.split()[1]: int(ln.split()[0]) for ln in lines}, re.search(r"Plotname:\s*(.*)", h).group(1).strip()


def _axis(lo, hi, n=10):
    return f"(' ',0,{lo},{(hi - lo) / n},{hi})"


def write_plt(raw, panes, x=None, xunit="m"):
    """panes: lista (de arriba hacia abajo) de dicts {'traces': [...], 'y': (lo, hi) o None}"""
    idx, plotname = raw_vars(raw)
    out = [f"[{plotname}]", "{", f"   Npanes: {len(panes)}"]
    blocks = []
    for p in reversed(panes):            # LTspice lista los paneles de abajo hacia arriba
        tr = " ".join(f'{{{524288 + idx[t]},0,"{t}"}}' for t in p["traces"])
        b = ["   {", f"      traces: {len(p['traces'])} {tr}"]
        if x:
            b.append(f"      X: ('{xunit}',0,{x[0]},{(x[1] - x[0]) / 8},{x[1]})")
        if p.get("y"):
            lo, hi = p["y"]
            b.append(f"      Y[0]: {_axis(lo, hi)}")
            b.append("      Y[1]: ('_',0,1e+308,0,-1e+308)")
        b += ["      Log: 0 0 0", "      GridStyle: 1", "   }"]
        blocks.append("\n".join(b))
    out.append(",\n".join(blocks))
    out.append("}")
    Path(raw).with_suffix(".plt").write_text("\n".join(out) + "\n", encoding="ascii")


def capture(target, png, wait=4.0, keys=None, keys_wait=3.0, clicks=None, run=False, dialog=None):
    """Abre 'target' (.raw o .asc) en LTspice, opcionalmente envia teclas, captura y cierra."""
    p = subprocess.Popen([LTSPICE] + (["-Run"] if run else []) + [str(target)], cwd=Path(target).parent)
    try:
        time.sleep(wait)
        args = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(PS1),
                "-Out", str(png), "-ProcId", str(p.pid)]
        if dialog:
            args += ["-Dialog", dialog]
        if clicks:
            args += ["-Clicks", clicks, "-KeysWait", str(int(keys_wait * 1000))]
        if keys:
            args += ["-Keys", keys, "-KeysWait", str(int(keys_wait * 1000))]
        r = subprocess.run(args, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(r.stderr)
    finally:
        p.kill()
        time.sleep(1.0)
    return png
