# Tiny local-only web server for running the tests in a browser when Node is not installed.
# Listens on 127.0.0.1 only. Serves the project folder, plus (optionally) one raw data file at /real.
# Usage: powershell -ExecutionPolicy Bypass -File tools\test_server.ps1 [-RealFile C:\path\AncestryDNA.txt] [-Port 8765]
# Then open http://127.0.0.1:8765/engine/tests/run_tests.html   (or ...run_tests.html?real=/real)
# -SaveTo <file.html>: accept one POST /save (used by engine/tests/print_harness.html to save a static report copy).
param([string]$RealFile = '', [int]$Port = 8765, [string]$SaveTo = '')
$root = (Resolve-Path (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) '..')).Path
$types = @{ '.html' = 'text/html; charset=utf-8'; '.js' = 'text/javascript; charset=utf-8'; '.json' = 'application/json; charset=utf-8';
            '.css' = 'text/css; charset=utf-8'; '.txt' = 'text/plain; charset=utf-8'; '.csv' = 'text/csv; charset=utf-8'; '.zip' = 'application/zip' }
$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://127.0.0.1:$Port/")
$listener.Start()
Write-Host "Serving $root at http://127.0.0.1:$Port/  (Ctrl+C to stop)"
try {
    while ($listener.IsListening) {
        $ctx = $listener.GetContext()
        $res = $ctx.Response
        try {
            $rel = [Uri]::UnescapeDataString($ctx.Request.Url.AbsolutePath).TrimStart('/')
            if ($rel -eq 'save' -and $SaveTo -and $ctx.Request.HttpMethod -eq 'POST') {
                $reader = New-Object IO.StreamReader($ctx.Request.InputStream, [Text.Encoding]::UTF8)
                [IO.File]::WriteAllText($SaveTo, $reader.ReadToEnd(), (New-Object Text.UTF8Encoding($false)))
                $res.StatusCode = 204; continue
            }
            if ($rel -eq 'real' -and $RealFile) { $file = $RealFile }
            else {
                $file = [IO.Path]::GetFullPath((Join-Path $root $rel))
                if (-not $file.StartsWith($root, [StringComparison]::OrdinalIgnoreCase)) { $file = $null }
            }
            if ($file -and (Test-Path -LiteralPath $file -PathType Leaf)) {
                $bytes = [IO.File]::ReadAllBytes($file)
                $ext = [IO.Path]::GetExtension($file).ToLower()
                $res.ContentType = if ($types.ContainsKey($ext)) { $types[$ext] } else { 'application/octet-stream' }
                $res.Headers.Add('Cache-Control', 'no-store')
                $res.ContentLength64 = $bytes.Length
                $res.OutputStream.Write($bytes, 0, $bytes.Length)
            } else { $res.StatusCode = 404 }
        } catch { $res.StatusCode = 500 }
        finally { $res.Close() }
    }
} finally { $listener.Stop() }
