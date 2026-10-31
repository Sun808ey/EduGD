[CmdletBinding()]
param(
    [string]$Adb = "adb",
    [string]$Apk = (Join-Path $PSScriptRoot "..\app\build\outputs\apk\debug\app-debug.apk"),
    [switch]$SkipInstall,
    [switch]$OpenLearnerUi
)

$ErrorActionPreference = "Stop"
$packageName = "io.github.sun808ey.edugd.dpc"
$adminComponent = "$packageName/.admin.AdminReceiver"
$demoComponent = "$packageName/.demo.DpcDemoActivity"
$learnerComponent = "$packageName/.MainActivity"

if (-not (Get-Command $Adb -ErrorAction SilentlyContinue)) {
    throw "adb was not found. Install Android SDK Platform-Tools and add adb to PATH."
}

$devices = @(& $Adb devices | Select-Object -Skip 1 | Where-Object { $_ -match "\tdevice$" })
if ($devices.Count -eq 0) {
    throw "No online emulator/device found. Start a clean API 35 Android Studio emulator first."
}

if (-not $SkipInstall) {
    if (-not (Test-Path -LiteralPath $Apk)) {
        throw "APK not found at $Apk. Run .\gradlew.bat assembleDebug first."
    }
    & $Adb install -r $Apk
    if ($LASTEXITCODE -ne 0) { throw "APK installation failed." }
}

& $Adb shell dpm list-owners
if ($LASTEXITCODE -ne 0) { throw "Could not inspect DevicePolicyManager owners." }

Write-Host "Setting EduGD as the device owner. Use a clean emulator with no account or work profile."
& $Adb shell dpm set-device-owner --user current $adminComponent
if ($LASTEXITCODE -ne 0) {
    throw "Device-owner provisioning failed. Reset the emulator and rerun; do not remove a real device owner during the panel demo."
}

& $Adb shell dpm list-owners
& $Adb shell am start -n $demoComponent
if ($LASTEXITCODE -ne 0) { throw "Could not launch the debug DPC demonstration harness." }

if ($OpenLearnerUi) {
    & $Adb shell am start -n $learnerComponent
    if ($LASTEXITCODE -ne 0) { throw "Could not launch the learner-facing DPC UI." }
}

Write-Host "Demo harness launched. Use 'Queue real backend sync', then 'Refresh read-back'."
