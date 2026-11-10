# Trae la ventana de VS Code al frente (se usa al terminar las capturas).
Add-Type @"
using System; using System.Runtime.InteropServices;
public class F {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern void keybd_event(byte k, byte s, int f, int e);
}
"@
$c = Get-Process Code -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if ($c) {
  [F]::keybd_event(0x12, 0, 0, 0); [F]::keybd_event(0x12, 0, 2, 0)
  [F]::ShowWindow($c.MainWindowHandle, 9) | Out-Null
  [F]::SetForegroundWindow($c.MainWindowHandle) | Out-Null
}
