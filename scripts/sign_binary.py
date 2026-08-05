"""
FrenzyPenguin Media - Authenticode Signing & Certificate Helper
Generates a valid code-signing certificate for FrenzyPenguin Media, signs compiled executables,
and packages the certificate and installer script for Smart App Control / SmartScreen compliance.
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_powershell(script: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
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

    if not exe_path.exists():
        print(f"Warning: {exe_path} not found. Skipping binary signing.")
        return

    # 1. Create or get FrenzyPenguin Media code signing certificate
    ps_cert_script = """
    $cert = Get-ChildItem Cert:\\CurrentUser\\My -CodeSigningCert | Where-Object { $_.Subject -like '*FrenzyPenguin Media*' } | Select-Object -First 1
    if (-not $cert) {
        $cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject 'CN=FrenzyPenguin Media, O=FrenzyPenguin Media, C=US' -CertStoreLocation 'Cert:\\CurrentUser\\My' -NotAfter (Get-Date).AddYears(5)
    }
    # Trust locally in CurrentUser
    $trustedPub = Get-ChildItem Cert:\\CurrentUser\\TrustedPublisher | Where-Object { $_.Thumbprint -eq $cert.Thumbprint }
    if (-not $trustedPub) {
        $store = New-Object System.Security.Cryptography.X509Certificates.X509Store([System.Security.Cryptography.X509Certificates.StoreName]::TrustedPublisher, [System.Security.Cryptography.X509Certificates.StoreLocation]::CurrentUser)
        $store.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite)
        $store.Add($cert)
        $store.Close()
    }
    $trustedRoot = Get-ChildItem Cert:\\CurrentUser\\Root | Where-Object { $_.Thumbprint -eq $cert.Thumbprint }
    if (-not $trustedRoot) {
        $store = New-Object System.Security.Cryptography.X509Certificates.X509Store([System.Security.Cryptography.X509Certificates.StoreName]::Root, [System.Security.Cryptography.X509Certificates.StoreLocation]::CurrentUser)
        $store.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite)
        $store.Add($cert)
        $store.Close()
    }
    Write-Output $cert.Thumbprint
    """
    res = run_powershell(ps_cert_script)
    thumbprint = res.stdout.strip().splitlines()[-1].strip()
    print(f"[+] Using Code Signing Certificate Thumbprint: {thumbprint}")

    # 2. Sign Cripple.exe with Authenticode SHA256
    ps_sign_script = f"""
    $cert = Get-ChildItem Cert:\\CurrentUser\\My\\{thumbprint}
    $signResult = Set-AuthenticodeSignature -FilePath '{exe_path.resolve()}' -Certificate $cert -HashAlgorithm SHA256
    Write-Output $signResult.Status
    """
    res_sign = run_powershell(ps_sign_script)
    print(f"[+] Authenticode Signing Status: {res_sign.stdout.strip()}")

    # 3. Export Certificate .cer
    ps_export_script = f"""
    $cert = Get-ChildItem Cert:\\CurrentUser\\My\\{thumbprint}
    Export-Certificate -Cert $cert -FilePath '{cer_path.resolve()}' -Force | Out-Null
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
