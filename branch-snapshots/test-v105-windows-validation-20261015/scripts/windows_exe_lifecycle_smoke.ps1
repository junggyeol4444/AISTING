# Actual Windows runner EXE process lifecycle; no real audio, chat, OBS or broadcast.
$ErrorActionPreference = "Stop"
$exe = (Resolve-Path "dist/AISTING.exe").Path
$env:LOCALAPPDATA = Join-Path $env:RUNNER_TEMP "aisting-exe-lifecycle-isolated"
New-Item -ItemType Directory -Force -Path $env:LOCALAPPDATA | Out-Null

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class AistingWindowsMessage {
    [DllImport("user32.dll", SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool PostMessage(IntPtr hwnd, uint msg, IntPtr wParam, IntPtr lParam);
}
'@

function Get-AistingNativeWindow {
    for ($i = 0; $i -lt 50; $i++) {
        foreach ($process in @(Get-Process -Name "AISTING" -ErrorAction SilentlyContinue)) {
            $process.Refresh()
            if ($process.MainWindowHandle -ne 0) { return $process.MainWindowHandle }
        }
        Start-Sleep -Seconds 1
    }
    throw "EXE native GUI was not visible on Windows within 50 seconds"
}

function Assert-No-AistingProcesses {
    for ($i = 0; $i -lt 25; $i++) {
        $remaining = @(Get-Process -Name "AISTING" -ErrorAction SilentlyContinue)
        if ($remaining.Count -eq 0) { return }
        Start-Sleep -Seconds 1
    }
    throw "AISTING.exe or its PyInstaller child remained running after WM_CLOSE"
}

for ($attempt = 1; $attempt -le 2; $attempt++) {
    $parent = Start-Process -FilePath $exe -PassThru
    Write-Host "EXE launch attempt $attempt started root PID $($parent.Id)"
    try {
        $hwnd = Get-AistingNativeWindow
        Write-Host "EXE launch $attempt native HWND $hwnd"
        if (-not [AistingWindowsMessage]::PostMessage($hwnd, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero)) {
            throw "Windows WM_CLOSE was not posted"
        }
        Assert-No-AistingProcesses
        Write-Host "EXE attempt $attempt graceful GUI close: PASS"
    } finally {
        # Cleanup only this isolated test job's processes in case of failure.
        Get-Process -Name "AISTING" -ErrorAction SilentlyContinue |
            Stop-Process -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "WINDOWS EXE USER LIFECYCLE: two launches + GUI window + WM_CLOSE + clean exit PASS"
