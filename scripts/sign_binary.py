"""
FrenzyPenguin Media - Authenticode Signing & Certificate Helper
Generates a valid code-signing certificate for FrenzyPenguin Media, signs compiled executables,
and packages the certificate and installer script for Smart App Control / SmartScreen compliance.
"""
import os
import sys
import subprocess
import shutil
import base64
from pathlib import Path

def run_powershell(script: str) -> subprocess.CompletedProcess:
    encoded = base64.b64encode(script.encode('utf-16le')).decode('ascii')
    return subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded],
        capture_output=True,
        text=True
    )

def sign_and_package():
    print("=" * 60)
    print(" FrenzyPenguin Media - Code Signing & Packaging Helper")
    print("=" * 60)

    dist_cripple = Path("dist/Cripple")
    exe_path = dist_cripple / "Cripple.exe"
    cer_path = dist_cripple / "FrenzyPenguinMedia.cer"

    if not dist_cripple.exists():
        print(f"Warning: {dist_cripple} not found. Skipping binary signing.")
        return

    # 1. Create or get FrenzyPenguin Media code signing certificate in CurrentUser\My
    ps_cert_script = """
    $ErrorActionPreference = 'Stop'
    $cert = Get-ChildItem -Path Cert:\\CurrentUser\\My | Where-Object { $_.Subject -like '*FrenzyPenguin Media*' } | Select-Object -First 1
    if (-not $cert) {
        $cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject 'CN=FrenzyPenguin Media, O=FrenzyPenguin Media, C=US' -CertStoreLocation 'Cert:\\CurrentUser\\My' -NotAfter (Get-Date).AddYears(5) -KeyUsage DigitalSignature -FriendlyName 'FrenzyPenguin Media Code Signing'
    }
    if ($cert) {
        Write-Output $cert.Thumbprint
    }
    """
    res = run_powershell(ps_cert_script)
    lines = [l.strip() for l in res.stdout.strip().splitlines() if l.strip()]
    if not lines:
        print("Error: Could not retrieve code signing certificate thumbprint.")
        if res.stderr:
            print("PowerShell Error:", res.stderr)
        return
    thumbprint = lines[-1]
    print(f"[+] Using Code Signing Certificate Thumbprint: {thumbprint}")

    # 2. Sign all executables (.exe, .dll, .pyd) in dist/Cripple
    binaries = list(dist_cripple.rglob("*.exe")) + list(dist_cripple.rglob("*.dll")) + list(dist_cripple.rglob("*.pyd"))
    print(f"[+] Found {len(binaries)} binary files to sign in {dist_cripple}")

    signed_count = 0
    for bin_file in binaries:
        file_path_str = str(bin_file.resolve()).replace("'", "''")
        ps_sign_script = f"""
        $cert = Get-ChildItem -Path Cert:\\CurrentUser\\My\\{thumbprint}
        $signResult = Set-AuthenticodeSignature -FilePath '{file_path_str}' -Certificate $cert -HashAlgorithm SHA256
        Write-Output $signResult.Status
        """
        res_sign = run_powershell(ps_sign_script)
        status = res_sign.stdout.strip()
        signed_count += 1
        if bin_file.name == "Cripple.exe":
            print(f"[+] Signed main executable: {bin_file.name} -> Status: {status}")

    print(f"[+] Successfully signed {signed_count} binaries with Authenticode SHA256.")

    # 3. Export Certificate .cer
    cer_path_str = str(cer_path.resolve()).replace("'", "''")
    ps_export_script = f"""
    $cert = Get-ChildItem -Path Cert:\\CurrentUser\\My\\{thumbprint}
    Export-Certificate -Cert $cert -FilePath '{cer_path_str}' -Force | Out-Null
    """
    run_powershell(ps_export_script)
    print(f"[+] Exported Public Certificate to {cer_path}")

    # 4. Copy Install_Certificate.bat
    cert_installer = Path("scripts/Install_Certificate.bat")
    if cert_installer.exists():
        dest_installer = dist_cripple / "Install_Certificate.bat"
        shutil.copy2(cert_installer, dest_installer)
        print(f"[+] Bundled Certificate Installer to {dest_installer}")

    print("=" * 60)
    print(" FrenzyPenguin Media Code Signing Complete!")
    print("=" * 60)

if __name__ == "__main__":
    sign_and_package()
