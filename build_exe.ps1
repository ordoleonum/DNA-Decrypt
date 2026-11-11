# Builds the app and the Windows program from the source files:
#   app\page.html (layout), app\styles.css, app\app.js (interface), app\zip.js (zip reader),
#   engine\engine.js and library\markers.json
#   ->  dist\DNA-Health-Report.html  ->  dist\DNA-Decrypt.exe (C# compiler built into Windows)
# Edit the source files, never the files in dist\ (they are rebuilt every time and are not kept in git).
# Run:  powershell -ExecutionPolicy Bypass -File build_exe.ps1
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$csc  = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path $csc)) { $csc = Join-Path $env:WINDIR 'Microsoft.NET\Framework\v4.0.30319\csc.exe' }
if (-not (Test-Path $csc)) { throw 'The .NET Framework C# compiler (csc.exe) was not found.' }

$html = Join-Path $here 'dist\DNA-Health-Report.html'
$src  = Join-Path $here 'launcher\Launcher.cs'
$ico  = Join-Path $here 'launcher\app.ico'
$dist = Join-Path $here 'dist'
New-Item -ItemType Directory -Force $dist | Out-Null

# Assemble the single-file app. Each {{NAME}} placeholder in app\page.html is replaced by a file's contents
# (minus its final newline), so the output is byte-for-byte reproducible.
$utf8 = New-Object System.Text.UTF8Encoding $false
function Read-Part($rel) {
    $s = [System.IO.File]::ReadAllText((Join-Path $here $rel), $utf8).Replace("`r`n", "`n")
    if ($s.EndsWith("`n")) { $s = $s.Substring(0, $s.Length - 1) }
    if ($rel -like '*.js' -and $s -match '</script') { throw "$rel must not contain </script." }
    return $s
}
$page = (Read-Part 'app\page.html') + "`n"
# The library is stored indented (readable diffs); line breaks and indentation are dropped when embedding.
# JSON strings cannot contain raw line breaks, so this never changes the data.
$json = [System.Text.RegularExpressions.Regex]::Replace([System.IO.File]::ReadAllText((Join-Path $here 'library\markers.json'), $utf8).Trim(), '\r?\n *', '').Replace('</', '<\/')
$engine = [System.IO.File]::ReadAllText((Join-Path $here 'engine\engine.js'), $utf8).Replace("`r`n", "`n").Trim()
if ($engine -match '</script') { throw 'engine\engine.js must not contain </script.' }
$parts = [ordered]@{ '{{STYLES}}' = (Read-Part 'app\styles.css'); '{{ZIP}}' = (Read-Part 'app\zip.js'); '{{APP}}' = (Read-Part 'app\app.js');
                     '{{ENGINE}}' = $engine; '{{LIBRARY}}' = $json }
foreach ($k in $parts.Keys) {
    if (-not $page.Contains($k)) { throw "app\page.html is missing the $k placeholder." }
    $page = $page.Replace($k, $parts[$k])
}
[System.IO.File]::WriteAllText($html, $page, $utf8)
Write-Host "Built $html ($([Math]::Round((Get-Item $html).Length / 1KB)) KB)"
$out  = Join-Path $dist 'DNA-Decrypt.exe'

# Draw the app icon (teal tile with a white double helix, matching the report logo) if it is missing.
if (-not (Test-Path $ico)) {
    Add-Type -AssemblyName System.Drawing
    $sizes = 16, 32, 48, 256
    $pngs = foreach ($n in $sizes) {
        $bmp = New-Object System.Drawing.Bitmap $n, $n
        $g = [System.Drawing.Graphics]::FromImage($bmp)
        $g.SmoothingMode = 'AntiAlias'; $g.Clear([System.Drawing.Color]::Transparent)
        $k = $n / 28.0
        $path = New-Object System.Drawing.Drawing2D.GraphicsPath
        $r = 6 * $k * 2
        $path.AddArc(0, 0, $r, $r, 180, 90); $path.AddArc($n - $r - 1, 0, $r, $r, 270, 90)
        $path.AddArc($n - $r - 1, $n - $r - 1, $r, $r, 0, 90); $path.AddArc(0, $n - $r - 1, $r, $r, 90, 90); $path.CloseFigure()
        $g.FillPath((New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(15, 92, 110))), $path)
        $pen = New-Object System.Drawing.Pen ([System.Drawing.Color]::White), ([Math]::Max(1.2, 2.2 * $k))
        $pen.StartCap = 'Round'; $pen.EndCap = 'Round'
        $p = { param($x, $y) New-Object System.Drawing.PointF ($x * $k), ($y * $k) }
        $g.DrawBezier($pen, (& $p 9 5), (& $p 9 11), (& $p 19 11), (& $p 19 14))
        $g.DrawBezier($pen, (& $p 19 14), (& $p 19 17), (& $p 9 17), (& $p 9 23))
        $g.DrawBezier($pen, (& $p 19 5), (& $p 19 11), (& $p 9 11), (& $p 9 14))
        $g.DrawBezier($pen, (& $p 9 14), (& $p 9 17), (& $p 19 17), (& $p 19 23))
        $g.Dispose()
        $ms = New-Object System.IO.MemoryStream
        $bmp.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png); $bmp.Dispose()
        , $ms.ToArray()
    }
    $fs = [System.IO.File]::Create($ico); $w = New-Object System.IO.BinaryWriter $fs
    $w.Write([UInt16]0); $w.Write([UInt16]1); $w.Write([UInt16]$sizes.Count)
    $offset = 6 + 16 * $sizes.Count
    for ($i = 0; $i -lt $sizes.Count; $i++) {
        $d = if ($sizes[$i] -ge 256) { 0 } else { $sizes[$i] }
        $w.Write([byte]$d); $w.Write([byte]$d); $w.Write([byte]0); $w.Write([byte]0)
        $w.Write([UInt16]1); $w.Write([UInt16]32); $w.Write([UInt32]$pngs[$i].Length); $w.Write([UInt32]$offset)
        $offset += $pngs[$i].Length
    }
    foreach ($b in $pngs) { $w.Write($b) }
    $w.Close()
}

& $csc /nologo /target:winexe /optimize+ /platform:anycpu `
    "/out:$out" "/win32icon:$ico" `
    "/resource:$html,DNA-Health-Report.html" `
    /reference:System.Windows.Forms.dll `
    $src
if ($LASTEXITCODE -ne 0) { throw "Compile failed ($LASTEXITCODE)" }
Write-Host "Built $out ($([Math]::Round((Get-Item $out).Length / 1KB)) KB)"

# Optional code signing. Uses a code-signing certificate for "CN=ordoleonum" in the current user's certificate store,
# if there is one (create it once with tools\make_signing_cert.ps1). The signature proves the file has not been changed
# since it was built. It is self-signed, so Windows still shows "Unknown publisher" unless the certificate is trusted.
$cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert -ErrorAction SilentlyContinue |
    Where-Object { $_.Subject -eq 'CN=ordoleonum' -and $_.NotAfter -gt (Get-Date) } | Sort-Object NotAfter -Descending | Select-Object -First 1
if ($cert) {
    $sig = $null
    foreach ($ts in 'http://timestamp.digicert.com', 'http://timestamp.sectigo.com', $null) {
        try {
            $p = @{ FilePath = $out; Certificate = $cert; HashAlgorithm = 'SHA256' }
            if ($ts) { $p.TimestampServer = $ts }
            $sig = Set-AuthenticodeSignature @p -ErrorAction Stop
            if ($sig.SignerCertificate) { break }
        } catch { $sig = $null }
    }
    if (-not $sig -or -not $sig.SignerCertificate) { throw 'Signing failed.' }
    $stamped = if ($sig.TimeStamperCertificate) { 'with timestamp' } else { 'without timestamp' }
    Write-Host "Signed $out as $($cert.Subject) ($stamped; thumbprint $($cert.Thumbprint))"
} else {
    Write-Host 'Not signed: no "CN=ordoleonum" code-signing certificate found (see tools\make_signing_cert.ps1).'
}
