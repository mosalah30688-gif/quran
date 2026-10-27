$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$AppRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$RepoRoot = (Resolve-Path (Join-Path $AppRoot "..")).Path
$Build = Join-Path $AppRoot "build"
$Dist = Join-Path $AppRoot "dist"
$UpdaterDist = Join-Path $AppRoot "updater-dist"
$Release = Join-Path $AppRoot "release"

$Version = (& python (Join-Path $PSScriptRoot "generate_version_info.py")).Trim()
if ($LASTEXITCODE -ne 0 -or -not $Version) { throw "Unable to read app version" }
Write-Host "Building Siraj $Version for Windows x64"

$SigningEnabled = -not [string]::IsNullOrWhiteSpace($env:SIRAJ_SIGN_CERT_PATH)
$SignTool = $null
if ($SigningEnabled) {
    if (-not (Test-Path $env:SIRAJ_SIGN_CERT_PATH)) { throw "Signing certificate does not exist" }
    $SignCommand = Get-Command signtool.exe -ErrorAction SilentlyContinue
    if ($SignCommand) { $SignTool = $SignCommand.Source }
    if (-not $SignTool) {
        $Kits = "${env:ProgramFiles(x86)}\Windows Kits\10\bin"
        $SignTool = Get-ChildItem $Kits -Filter signtool.exe -Recurse -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match '\\x64\\signtool\.exe$' } |
            Sort-Object FullName -Descending |
            Select-Object -First 1 -ExpandProperty FullName
    }
    if (-not $SignTool) { throw "signtool.exe was not found" }
}

function Invoke-SirajSign([string]$File) {
    if (-not $SigningEnabled) { return }
    & $SignTool sign /fd SHA256 /td SHA256 /tr "http://timestamp.digicert.com" `
        /f $env:SIRAJ_SIGN_CERT_PATH /p $env:SIRAJ_SIGN_CERT_PASSWORD $File | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Signing failed: $File" }
    & $SignTool verify /pa /v $File | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Signature verification failed: $File" }
}

function Invoke-SirajSmoke([string]$File, [string[]]$Arguments, [string]$Label) {
    # GUI executables may return control to PowerShell before exiting unless Start-Process -Wait is used.
    $Process = Start-Process -FilePath $File -ArgumentList $Arguments -NoNewWindow -Wait -PassThru
    if ($Process.ExitCode -ne 0) { throw "$Label failed with exit code $($Process.ExitCode)" }
}

foreach ($Path in @($Build, $Dist, $UpdaterDist, $Release)) {
    if (Test-Path $Path) { Remove-Item $Path -Recurse -Force }
    New-Item -ItemType Directory -Path $Path | Out-Null
}

& python -m PyInstaller --clean --noconfirm `
    --workpath (Join-Path $Build "app") `
    --distpath $Dist `
    (Join-Path $PSScriptRoot "siraj.spec")
if ($LASTEXITCODE -ne 0) { throw "Siraj PyInstaller build failed" }

& python -m PyInstaller --clean --noconfirm `
    --workpath (Join-Path $Build "updater") `
    --distpath $UpdaterDist `
    (Join-Path $PSScriptRoot "portable_updater.spec")
if ($LASTEXITCODE -ne 0) { throw "Portable updater build failed" }

$Exe = Join-Path $Dist "Siraj\Siraj.exe"
if (-not (Test-Path $Exe)) { throw "Siraj.exe was not created" }

Write-Host "Running packaged smoke tests"
Invoke-SirajSmoke $Exe @("--selftest") "Packaged self-test"
Invoke-SirajSmoke $Exe @("--audiotest") "Packaged audio test"

$UpdaterExe = Join-Path $UpdaterDist "SirajPortableUpdater.exe"
Invoke-SirajSign $Exe
Invoke-SirajSign $UpdaterExe

# النسخة المحمولة الحقيقية: إعداداتها وصوتياتها داخل UserData بجوار البرنامج.
$PortableName = "Siraj-Quran-$Version-windows-portable-x64"
$PortableDir = Join-Path $Release $PortableName
Copy-Item (Join-Path $Dist "Siraj") $PortableDir -Recurse
Copy-Item (Join-Path $UpdaterDist "SirajPortableUpdater.exe") $PortableDir
New-Item -ItemType File -Path (Join-Path $PortableDir "portable.flag") | Out-Null
@"
سراج — قرآن كريم
الإصدار $Version — نسخة Windows محمولة x64

شغّل Siraj.exe مباشرة. تُحفظ الإعدادات والعلامات والتظليلات والصوتيات داخل UserData.
لن تكتب هذه النسخة إعداداتها في Registry، ويمكن نقل المجلد كاملًا إلى أي مكان.
"@ | Set-Content -Path (Join-Path $PortableDir "اقرأني.txt") -Encoding UTF8

$SevenZip = $null
$SevenZipCommand = Get-Command 7z.exe -ErrorAction SilentlyContinue
if (-not $SevenZipCommand) { $SevenZipCommand = Get-Command 7z -ErrorAction SilentlyContinue }
if ($SevenZipCommand) { $SevenZip = $SevenZipCommand.Source }
if (-not $SevenZip) { throw "7-Zip is required to create the portable package" }
$PortableZip = Join-Path $Release "$PortableName.zip"
Push-Location $Release
& $SevenZip a -tzip -mx=9 $PortableZip $PortableName | Out-Host
Pop-Location
if ($LASTEXITCODE -ne 0) { throw "Portable ZIP creation failed" }

# اختبر الملف المضغوط نفسه في مجلد نظيف، لا مجلد PyInstaller الأصلي فقط.
$PortableSmoke = Join-Path $Build "portable-zip-smoke"
New-Item -ItemType Directory -Path $PortableSmoke -Force | Out-Null
& $SevenZip x -y "-o$PortableSmoke" $PortableZip | Out-Host
if ($LASTEXITCODE -ne 0) { throw "Portable ZIP extraction smoke test failed" }
$PortableSmokeExe = Join-Path $PortableSmoke "$PortableName\Siraj.exe"
$PortableSmokeFlag = Join-Path $PortableSmoke "$PortableName\portable.flag"
if (-not (Test-Path $PortableSmokeExe) -or -not (Test-Path $PortableSmokeFlag)) {
    throw "Portable ZIP is missing Siraj.exe or portable.flag"
}
Invoke-SirajSmoke $PortableSmokeExe @("--selftest") "Portable ZIP self-test"
Remove-Item $PortableSmoke -Recurse -Force
# لا نرفع المجلد غير المضغوط كأثر إضافي ولا نمرره خطأً إلى GitHub Release.
Remove-Item $PortableDir -Recurse -Force

$IsccCandidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
)
$Iscc = $IsccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Iscc) { throw "Inno Setup 6 (ISCC.exe) was not found" }
$InstallerScript = Join-Path $PSScriptRoot "installer\siraj.iss"
$InnoArgs = @(
    "/DMyAppVersion=$Version",
    "/DMySourceDir=$(Join-Path $Dist 'Siraj')",
    "/DMyOutputDir=$Release"
)
if ($SigningEnabled) {
    $InnoSignCommand = "`"$SignTool`" sign /fd SHA256 /td SHA256 /tr http://timestamp.digicert.com /f `"$env:SIRAJ_SIGN_CERT_PATH`" /p `"$env:SIRAJ_SIGN_CERT_PASSWORD`" `$f"
    $InnoArgs += "/Ssirajsign=$InnoSignCommand"
    $InnoArgs += "/DSignToolName=sirajsign"
}
$InnoArgs += $InstallerScript
& $Iscc $InnoArgs | Out-Host
if ($LASTEXITCODE -ne 0) { throw "Inno Setup build failed" }

$Installer = Join-Path $Release "Siraj-Quran-Setup-$Version-x64.exe"
if (-not (Test-Path $Installer)) { throw "Installer was not created" }
if ($SigningEnabled) {
    & $SignTool verify /pa /v $Installer | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Installer signature verification failed" }
}

# تثبيت صامت فعلي في مسار مؤقت ثم تشغيل النسخة المثبّتة وإلغاء تثبيتها.
$InstallerSmoke = Join-Path $Build "installer-smoke"
Invoke-SirajSmoke $Installer @(
    "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-", "/NOICONS", "/DIR=$InstallerSmoke"
) "Installer smoke installation"
$InstalledExe = Join-Path $InstallerSmoke "Siraj.exe"
if (-not (Test-Path $InstalledExe)) { throw "Installer did not install Siraj.exe" }
Invoke-SirajSmoke $InstalledExe @("--selftest") "Installed application self-test"
$Uninstaller = Join-Path $InstallerSmoke "unins000.exe"
if (-not (Test-Path $Uninstaller)) { throw "Installer did not create an uninstaller" }
Invoke-SirajSmoke $Uninstaller @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART") "Uninstaller smoke test"
for ($Attempt = 0; $Attempt -lt 20 -and (Test-Path $InstalledExe); $Attempt++) {
    Start-Sleep -Milliseconds 250
}
if (Test-Path $InstalledExe) { throw "Uninstaller left Siraj.exe behind" }

$Artifacts = @($Installer, $PortableZip)
$Lines = foreach ($Artifact in $Artifacts) {
    $Hash = (Get-FileHash -Algorithm SHA256 $Artifact).Hash.ToLowerInvariant()
    "$Hash  $([IO.Path]::GetFileName($Artifact))"
}
$Lines | Set-Content -Path (Join-Path $Release "SHA256SUMS.txt") -Encoding ascii

Write-Host "Release artifacts:"
Get-ChildItem $Release -File | Select-Object Name, Length | Format-Table -AutoSize
