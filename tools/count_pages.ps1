# Prints a saved static report (made by engine/tests/print_harness.html with test_server.ps1 -SaveTo) to PDF with
# headless Edge and counts the pages.
# Usage: powershell -ExecutionPolicy Bypass -File tools\count_pages.ps1 -Html C:\path\report.html -Out C:\path\report.pdf
param([Parameter(Mandatory = $true)][string]$Html, [Parameter(Mandatory = $true)][string]$Out)
$edge = @("${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe", "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $edge) { throw 'Microsoft Edge not found' }
$profile = Join-Path ([IO.Path]::GetDirectoryName($Out)) 'edge-print-profile'
if (Test-Path $Out) { Remove-Item $Out -Force }
$url = ([Uri](Resolve-Path $Html).Path).AbsoluteUri
Start-Process -FilePath $edge -ArgumentList @('--headless', '--disable-gpu', '--no-first-run', "--user-data-dir=$profile", "--print-to-pdf=$Out", '--no-pdf-header-footer', $url) -Wait -WindowStyle Hidden
if (-not (Test-Path $Out)) { throw 'PDF was not created' }
$text = [IO.File]::ReadAllText($Out, [Text.Encoding]::GetEncoding(28591))
$pages = ([regex]::Matches($text, '/Type\s*/Page[^s]')).Count
"Pages: $pages  ($([math]::Round((Get-Item $Out).Length / 1KB)) KB)"
