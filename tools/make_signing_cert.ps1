# Creates a free, self-signed code-signing certificate for "CN=ordoleonum" in the current user's certificate store
# (Cert:\CurrentUser\My) and exports its public part to dist\ordoleonum-codesign.cer. Run once; build_exe.ps1 then
# signs DNA-Decrypt.exe with it automatically. The private key never leaves this Windows account.
#
# What a self-signed signature does: anyone can check that the .exe has not been altered since it was signed, and
# that it was signed by this certificate (compare the thumbprint). What it does not do: it does not make Windows
# SmartScreen trust the file. That needs a certificate from a paid certificate authority.
# Usage: powershell -ExecutionPolicy Bypass -File tools\make_signing_cert.ps1
$ErrorActionPreference = 'Stop'
$existing = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert | Where-Object { $_.Subject -eq 'CN=ordoleonum' -and $_.NotAfter -gt (Get-Date) }
if ($existing) { $cert = $existing | Sort-Object NotAfter -Descending | Select-Object -First 1; Write-Host "Already exists: $($cert.Thumbprint)" }
else {
    $cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject 'CN=ordoleonum' -CertStoreLocation Cert:\CurrentUser\My `
        -KeyAlgorithm RSA -KeyLength 3072 -HashAlgorithm SHA256 -KeyExportPolicy NonExportable -NotAfter (Get-Date).AddYears(5)
    Write-Host "Created: $($cert.Thumbprint) (valid until $($cert.NotAfter.ToString('yyyy-MM-dd')))"
}
$dist = Join-Path (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)) 'dist'
New-Item -ItemType Directory -Force $dist | Out-Null
Export-Certificate -Cert $cert -FilePath (Join-Path $dist 'ordoleonum-codesign.cer') | Out-Null
Write-Host "Public certificate: $(Join-Path $dist 'ordoleonum-codesign.cer')"
