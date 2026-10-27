$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$AppRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Build = Join-Path $AppRoot "build"
$Dist = Join-Path $AppRoot "dist"
$UpdaterDist = Join-Path $AppRoot "updater-dist"
$Release = Join-Path $AppRoot "release"

$Version = (& python (Join-Path $PSScriptRoot "generate_version_info.py")).Trim()
if ($LASTEXITCODE -ne 0 -or -not $Version) { throw "Unable to read app version" }
Write-Host "Building Siraj $Version portable for Windows x64"

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
    $Process = Start-Process -FilePath $File -ArgumentList $Arguments -NoNewWindow -Wait -PassThru
    if ($Process.ExitCode -ne 0) { throw "$Label failed with exit code $($Process.ExitCode)" }
}

function Invoke-DoubleClickSmoke([string]$File, [string]$WorkingDirectory) {
    # محاكاة التشغيل من Explorer بلا Console؛ هذا الاختبار كان سيكشف خطأ sys.stderr is None.
    $Process = Start-Process -FilePath $File -WorkingDirectory $WorkingDirectory -PassThru
    try {
        $Title = ""
        for ($Attempt = 0; $Attempt -lt 40; $Attempt++) {
            Start-Sleep -Milliseconds 250
            $Process.Refresh()
            if ($Process.HasExited) { throw "Portable app crashed during double-click startup" }
            $Title = $Process.MainWindowTitle
            if (-not [string]::IsNullOrWhiteSpace($Title)) { break }
        }
        if ($Title -notlike "*سراج*") {
            throw "Expected the Siraj window, got: '$Title'"
        }
        Write-Host "Double-click startup window: $Title"
    }
    finally {
        if (-not $Process.HasExited) {
            Stop-Process -Id $Process.Id -Force
            $Process.WaitForExit()
        }
    }
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
$UpdaterExe = Join-Path $UpdaterDist "SirajPortableUpdater.exe"
if (-not (Test-Path $Exe) -or -not (Test-Path $UpdaterExe)) {
    throw "Portable executables were not created"
}

Write-Host "Running packaged smoke tests"
Invoke-SirajSmoke $Exe @("--selftest") "Packaged self-test"
Invoke-SirajSmoke $Exe @("--audiotest") "Packaged audio test"
Invoke-SirajSign $Exe
Invoke-SirajSign $UpdaterExe

$PortableName = "Siraj-Quran-$Version-windows-portable-x64"
$PortableDir = Join-Path $Release $PortableName
Copy-Item (Join-Path $Dist "Siraj") $PortableDir -Recurse
Copy-Item $UpdaterExe $PortableDir
New-Item -ItemType File -Path (Join-Path $PortableDir "portable.flag") | Out-Null
@"
سراج — قرآن كريم
الإصدار $Version — نسخة Windows محمولة x64

فك الضغط كاملًا، ثم شغّل Siraj.exe مباشرة.
تُحفظ الإعدادات والعلامات والتظليلات والصوتيات داخل UserData بجوار البرنامج.
لا يوجد مثبّت، ولا تكتب هذه النسخة إعداداتها في Registry، ويمكن نقل المجلد كاملًا.
"@ | Set-Content -Path (Join-Path $PortableDir "اقرأني.txt") -Encoding UTF8

Invoke-DoubleClickSmoke (Join-Path $PortableDir "Siraj.exe") $PortableDir
# لا تشحن سجل اختبار التشغيل أو أي إعدادات أنشأها اختبار النقر المزدوج.
Remove-Item (Join-Path $PortableDir "UserData") -Recurse -Force -ErrorAction SilentlyContinue
if (Test-Path (Join-Path $PortableDir "UserData")) { throw "Portable package contains test UserData" }

$SevenZipCommand = Get-Command 7z.exe -ErrorAction SilentlyContinue
if (-not $SevenZipCommand) { $SevenZipCommand = Get-Command 7z -ErrorAction SilentlyContinue }
if (-not $SevenZipCommand) { throw "7-Zip is required to create the portable package" }
$SevenZip = $SevenZipCommand.Source
$PortableZip = Join-Path $Release "$PortableName.zip"
Push-Location $Release
& $SevenZip a -tzip -mx=9 $PortableZip $PortableName | Out-Host
Pop-Location
if ($LASTEXITCODE -ne 0) { throw "Portable ZIP creation failed" }

# اختبر الملف النهائي بعد فكّه في مسار نظيف، ثم لا ترفع المجلد غير المضغوط.
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
Remove-Item $PortableDir -Recurse -Force

$Hash = (Get-FileHash -Algorithm SHA256 $PortableZip).Hash.ToLowerInvariant()
"$Hash  $([IO.Path]::GetFileName($PortableZip))" |
    Set-Content -Path (Join-Path $Release "SHA256SUMS.txt") -Encoding ascii

Write-Host "Portable release artifacts:"
Get-ChildItem $Release -File | Select-Object Name, Length | Format-Table -AutoSize
