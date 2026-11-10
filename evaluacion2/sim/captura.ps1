param([string]$Out, [int]$ProcId, [int]$Wait = 0, [string]$Keys = "", [int]$KeysWait = 3000, [string]$Clicks = "", [string]$Dialog = "")
# Captura la ventana principal de LTspice (maximizada) a un PNG.
# -Keys: teclas a enviar antes de capturar (formato SendKeys), separadas por '|'
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class W {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void keybd_event(byte k, byte s, int f, int e);
  [DllImport("user32.dll")] public static extern void mouse_event(int f, int dx, int dy, int d, int e);
  public struct RECT { public int L, T, R, B; }
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc f, IntPtr l);
  [DllImport("user32.dll")] public static extern int GetWindowThreadProcessId(IntPtr h, out int pid);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, System.Text.StringBuilder s, int n);
  public static IntPtr Find(int pid, string endsWith) {
    IntPtr found = IntPtr.Zero;
    EnumWindows(delegate(IntPtr h, IntPtr l) {
      int p; GetWindowThreadProcessId(h, out p);
      if (p == pid && IsWindowVisible(h)) {
        var sb = new System.Text.StringBuilder(512); GetWindowText(h, sb, 512);
        if (sb.ToString().EndsWith(endsWith)) { found = h; return false; }
      }
      return true; }, IntPtr.Zero);
    return found;
  }
}
"@
[W]::SetProcessDPIAware() | Out-Null
if ($Wait -gt 0) { Start-Sleep -Milliseconds $Wait }
$p = Get-Process -Id $ProcId -ErrorAction Stop
$h = $p.MainWindowHandle
[W]::ShowWindow($h, 3) | Out-Null      # maximizar
# traer al frente (la tecla ALT desbloquea SetForegroundWindow) y VERIFICAR que es nuestra ventana
for ($i = 0; $i -lt 5; $i++) {
  [W]::keybd_event(0x12, 0, 0, 0); [W]::keybd_event(0x12, 0, 2, 0)
  [W]::SetForegroundWindow($h) | Out-Null
  Start-Sleep -Milliseconds 500
  $fg = [W]::GetForegroundWindow(); $fp = 0; [W]::GetWindowThreadProcessId($fg, [ref]$fp) | Out-Null
  if ($fp -eq $ProcId) { break }
}
if ($fp -ne $ProcId) { Write-Error "La ventana de LTspice no quedo al frente; se cancela la captura"; exit 2 }
Start-Sleep -Milliseconds 600
if ($Keys -ne "") {
  foreach ($k in $Keys.Split('|')) {
    [System.Windows.Forms.SendKeys]::SendWait($k)
    Start-Sleep -Milliseconds 700
  }
  Start-Sleep -Milliseconds $KeysWait
}
if ($Clicks -ne "") {
  # clics relativos a la esquina de la ventana: "x,y|x,y|..." ; "wNNN" = esperar NNN ms
  $r0 = New-Object W+RECT; [W]::GetWindowRect($h, [ref]$r0) | Out-Null
  foreach ($c in $Clicks.Split('|')) {
    if ($c.StartsWith("w")) { Start-Sleep -Milliseconds ([int]$c.Substring(1)); continue }
    if ($c.StartsWith("d")) {   # arrastre: dx1,y1,x2,y2
      $fg = [W]::GetForegroundWindow(); $fp = 0; [W]::GetWindowThreadProcessId($fg, [ref]$fp) | Out-Null
      if ($fp -ne $ProcId) { Write-Error "Otra ventana tomo el foco; se cancela el arrastre"; exit 3 }
      $q = $c.Substring(1).Split(','); $ox = [Math]::Max($r0.L,0); $oy = [Math]::Max($r0.T,0)
      [W]::SetCursorPos($ox + [int]$q[0], $oy + [int]$q[1]) | Out-Null; Start-Sleep -Milliseconds 200
      [W]::mouse_event(2, 0, 0, 0, 0); Start-Sleep -Milliseconds 200
      for ($i = 1; $i -le 10; $i++) {
        $mx = [int]$q[0] + ([int]$q[2] - [int]$q[0]) * $i / 10; $my = [int]$q[1] + ([int]$q[3] - [int]$q[1]) * $i / 10
        [W]::SetCursorPos($ox + $mx, $oy + $my) | Out-Null; Start-Sleep -Milliseconds 40
      }
      [W]::mouse_event(4, 0, 0, 0, 0); Start-Sleep -Milliseconds 900
      continue
    }
    $fg = [W]::GetForegroundWindow(); $fp = 0; [W]::GetWindowThreadProcessId($fg, [ref]$fp) | Out-Null
    if ($fp -ne $ProcId) { Write-Error "Otra ventana tomo el foco; se cancelan los clics"; exit 3 }
    $xy = $c.Split(','); [W]::SetCursorPos([Math]::Max($r0.L,0) + [int]$xy[0], [Math]::Max($r0.T,0) + [int]$xy[1]) | Out-Null
    Start-Sleep -Milliseconds 200
    [W]::mouse_event(2, 0, 0, 0, 0); [W]::mouse_event(4, 0, 0, 0, 0)
    Start-Sleep -Milliseconds 800
  }
  [W]::SetCursorPos(1300, 700) | Out-Null
  Start-Sleep -Milliseconds $KeysWait
}
if ($Dialog -ne "") {
  $dh = [W]::Find($ProcId, $Dialog)
  if ($dh -ne [IntPtr]::Zero) { $h = $dh; [W]::SetForegroundWindow($h) | Out-Null; Start-Sleep -Milliseconds 700 }
}
$r = New-Object W+RECT
[W]::GetWindowRect($h, [ref]$r) | Out-Null
$x = [Math]::Max($r.L, 0); $y = [Math]::Max($r.T, 0)
$w = $r.R - $x; $hh = $r.B - $y
$bmp = New-Object System.Drawing.Bitmap $w, $hh
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($x, $y, 0, 0, $bmp.Size)
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()
Write-Output "$Out $w x $hh  ($($p.MainWindowTitle))"
