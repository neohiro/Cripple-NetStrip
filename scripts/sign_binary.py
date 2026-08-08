"""
FrenzyPenguin Media - Authenticode Code Signing & Packaging Helper
Automatically signs Windows binaries for FrenzyPenguin Media with Authenticode SHA-256.
Supports:
  1. GitHub Secrets CI (via WINDOWS_PFX_BASE64 and WINDOWS_PFX_PASSWORD env vars)
  2. Local PFX certificate file (scripts/frenzy_signing.pfx)
  3. Dynamic Pure-.NET Code-Signing Certificate Generation (zero dependencies, works on any Windows/CI runner)
"""
import os
import sys
import subprocess
import shutil
import base64
import tempfile
from pathlib import Path

def run_powershell(script: str) -> subprocess.CompletedProcess:
    with tempfile.NamedTemporaryFile(suffix=".ps1", delete=False, mode="w", encoding="utf-8") as tf:
        tf.write(script)
        temp_ps1 = tf.name
    try:
        return subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", temp_ps1],
            capture_output=True,
            text=True
        )
    finally:
        try:
            os.remove(temp_ps1)
        except Exception:
            pass

def sign_and_package():
    print("=" * 60)
    print(" FrenzyPenguin Media - Autosign & Packaging Helper")
    print("=" * 60)

    dist_cripple = Path("dist/Cripple")
    exe_path = dist_cripple / "Cripple.exe"
    cer_path = dist_cripple / "FrenzyPenguinMedia.cer"

    if not dist_cripple.exists():
        print(f"Warning: {dist_cripple} not found. Skipping binary signing.")
        return

    # 1. Determine PFX source
    pfx_env = os.environ.get("WINDOWS_PFX_BASE64", "").strip()
    pfx_pass = os.environ.get("WINDOWS_PFX_PASSWORD", "FrenzyPenguin2026").strip()

    temp_pfx_file = None
    if pfx_env:
        print("[+] Found WINDOWS_PFX_BASE64 in environment (GitHub Secrets).")
        temp_pfx = tempfile.NamedTemporaryFile(suffix=".pfx", delete=False)
        temp_pfx.write(base64.b64decode(pfx_env))
        temp_pfx.close()
        pfx_path_str = temp_pfx.name
        temp_pfx_file = temp_pfx.name
    elif Path("scripts/frenzy_signing.pfx").exists():
        print("[+] Found local scripts/frenzy_signing.pfx certificate.")
        pfx_path_str = str(Path("scripts/frenzy_signing.pfx").resolve())
    elif Path("scripts/frenzy_signing_pfx_base64.txt").exists():
        print("[+] Found scripts/frenzy_signing_pfx_base64.txt, restoring official FrenzyPenguin Media certificate.")
        b64_content = Path("scripts/frenzy_signing_pfx_base64.txt").read_text(encoding="utf-8").strip()
        temp_pfx = tempfile.NamedTemporaryFile(suffix=".pfx", delete=False)
        temp_pfx.write(base64.b64decode(b64_content))
        temp_pfx.close()
        pfx_path_str = temp_pfx.name
        temp_pfx_file = temp_pfx.name
    else:
        print("[+] Generating fresh FrenzyPenguin Media Code Signing Certificate via .NET...")
        pfx_temp = Path("scripts/frenzy_signing.pfx").resolve()
        ps_gen_script = f"""
        $rsa = [System.Security.Cryptography.RSA]::Create(2048)
        $req = New-Object System.Security.Cryptography.X509Certificates.CertificateRequest(
            "CN=FrenzyPenguin Media, O=FrenzyPenguin Media, C=US",
            $rsa,
            [System.Security.Cryptography.HashAlgorithmName]::SHA256,
            [System.Security.Cryptography.RSASignaturePadding]::Pkcs1
        )
        $oid = New-Object System.Security.Cryptography.Oid("1.3.6.1.5.5.7.3.3", "Code Signing")
        $oidCollection = New-Object System.Security.Cryptography.OidCollection
        $oidCollection.Add($oid) | Out-Null
        $eku = New-Object System.Security.Cryptography.X509Certificates.X509EnhancedKeyUsageExtension($oidCollection, $false)
        $req.CertificateExtensions.Add($eku)

        $keyUsage = New-Object System.Security.Cryptography.X509Certificates.X509KeyUsageExtension(
            [System.Security.Cryptography.X509Certificates.X509KeyUsageFlags]::DigitalSignature,
            $true
        )
        $req.CertificateExtensions.Add($keyUsage)

        $cert = $req.CreateSelfSigned((Get-Date), (Get-Date).AddYears(5))
        $pfxBytes = $cert.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Pfx, "{pfx_pass}")
        [System.IO.File]::WriteAllBytes('{str(pfx_temp).replace("'", "''")}', $pfxBytes)
        """
        run_powershell(ps_gen_script)
        pfx_path_str = str(pfx_temp)

    pfx_path_escaped = pfx_path_str.replace("'", "''")
    cer_path_escaped = str(cer_path.resolve()).replace("'", "''")

    # 2. Collect all binary files in dist/Cripple (.exe, .dll, .pyd)
    binaries = list(dist_cripple.rglob("*.exe")) + list(dist_cripple.rglob("*.dll")) + list(dist_cripple.rglob("*.pyd"))
    print(f"[+] Found {len(binaries)} binary files to sign in {dist_cripple}")


    # 3. Locate signtool.exe if available in Windows SDK
    import glob
    sdk_signtools = glob.glob("C:/Program Files (x86)/Windows Kits/10/bin/*/x64/signtool.exe")
    signtool_exe = sdk_signtools[-1] if sdk_signtools else None

    if signtool_exe and os.path.exists(signtool_exe):
        print(f"[+] Found Windows SDK signtool: {signtool_exe}")
        signed_count = 0
        ts_urls = ["http://timestamp.digicert.com", "http://timestamp.sectigo.com", "http://timestamp.globalsign.com/scripts/timstamp.dll"]
        for b in binaries:
            signed = False
            for ts in ts_urls:
                cmd = [
                    signtool_exe, "sign",
                    "/f", pfx_path_str,
                    "/p", pfx_pass,
                    "/fd", "SHA256",
                    "/tr", ts,
                    "/td", "SHA256",
                    str(b.resolve())
                ]
                r = subprocess.run(cmd, capture_output=True, text=True)
                if r.returncode == 0:
                    signed = True
                    break
            if not signed:
                cmd_notime = [
                    signtool_exe, "sign",
                    "/f", pfx_path_str,
                    "/p", pfx_pass,
                    "/fd", "SHA256",
                    str(b.resolve())
                ]
                r = subprocess.run(cmd_notime, capture_output=True, text=True)
                if r.returncode == 0:
                    signed = True
            if signed:
                signed_count += 1
        print(f"[+] Successfully signed {signed_count} binaries with signtool Authenticode SHA-256.")

        # Export Public Certificate
        ps_export = f"""
        $pfxPath = '{pfx_path_escaped}'
        $pfxPass = '{pfx_pass}'
        $flags = [System.Security.Cryptography.X509Certificates.X509KeyStorageFlags]::Exportable
        $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($pfxPath, $pfxPass, $flags)
        $cerPath = '{cer_path_escaped}'
        [System.IO.File]::WriteAllBytes($cerPath, $cert.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Cert))
        Write-Output "CERT_THUMBPRINT:$($cert.Thumbprint)"
        Write-Output "EXPORTED_CER:$cerPath"
        """
        res = run_powershell(ps_export)
        for line in res.stdout.splitlines():
            line = line.strip()
            if line.startswith("CERT_THUMBPRINT:"):
                print(f"[+] Certificate Thumbprint: {line.split(':', 1)[1]}")
            elif line.startswith("EXPORTED_CER:"):
                print(f"[+] Exported Public Certificate to {cer_path}")
    else:
        # Fallback: PowerShell Set-AuthenticodeSignature
        escaped_paths = []
        for b in binaries:
            escaped_p = str(b.resolve()).replace("'", "''")
            escaped_paths.append(f"    '{escaped_p}'")
        file_paths_str = "@(\n" + ",\n".join(escaped_paths) + "\n)"

        ps_sign_batch = f"""
        $pfxPath = '{pfx_path_escaped}'
        $pfxPass = '{pfx_pass}'
        $pass = ConvertTo-SecureString $pfxPass -AsPlainText -Force
        $imported = @(Import-PfxCertificate -FilePath $pfxPath -CertStoreLocation Cert:\\CurrentUser\\My -Password $pass -Exportable)
        $cert = $null
        if ($imported.Count -gt 0) {{
            $cert = $imported[0]
        }}
        if (-not $cert -or -not $cert.Thumbprint) {{
            $flags = [System.Security.Cryptography.X509Certificates.X509KeyStorageFlags]::Exportable -bor [System.Security.Cryptography.X509Certificates.X509KeyStorageFlags]::PersistKeySet -bor [System.Security.Cryptography.X509Certificates.X509KeyStorageFlags]::UserKeySet
            $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($pfxPath, $pfxPass, $flags)
        }}
        Write-Output "CERT_THUMBPRINT:$($cert.Thumbprint)"

        $files = {file_paths_str}
        $signed = 0
        $tsUrls = @('http://timestamp.digicert.com', 'http://timestamp.sectigo.com', 'http://timestamp.globalsign.com/scripts/timstamp.dll')

        foreach ($f in $files) {{
            if (Test-Path $f) {{
                $ok = $false
                foreach ($ts in $tsUrls) {{
                    try {{
                        $res = Set-AuthenticodeSignature -FilePath $f -Certificate $cert -HashAlgorithm SHA256 -TimestampServer $ts -ErrorAction Stop
                        if ($res.Status -in @('Valid', 'UnknownError', 'NotTrusted')) {{
                            $ok = $true
                            break
                        }}
                    }} catch {{
                        # Try next timestamp server
                    }}
                }}
                if (-not $ok) {{
                    $res = Set-AuthenticodeSignature -FilePath $f -Certificate $cert -HashAlgorithm SHA256 -ErrorAction SilentlyContinue
                    if ($res.Status -in @('Valid', 'UnknownError', 'NotTrusted')) {{
                        $ok = $true
                    }}
                }}
                if ($ok) {{
                    $signed++
                }}
            }}
        }}
        Write-Output "SIGNED_COUNT:$signed"

        # Export Public .cer Certificate
        $cerPath = '{cer_path_escaped}'
        [System.IO.File]::WriteAllBytes($cerPath, $cert.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Cert))
        Write-Output "EXPORTED_CER:$cerPath"
        """

        res = run_powershell(ps_sign_batch)
        for line in res.stdout.splitlines():
            line = line.strip()
            if line.startswith("CERT_THUMBPRINT:"):
                print(f"[+] Certificate Thumbprint: {line.split(':', 1)[1]}")
            elif line.startswith("SIGNED_COUNT:"):
                print(f"[+] Successfully signed {line.split(':', 1)[1]} binaries with Authenticode SHA-256.")
            elif line.startswith("EXPORTED_CER:"):
                print(f"[+] Exported Public Certificate to {cer_path}")

    if temp_pfx_file and os.path.exists(temp_pfx_file):
        try:
            os.remove(temp_pfx_file)
        except Exception:
            pass

    # 4. Copy Install_Certificate.bat and create Run_Cripple.bat
    cert_installer = Path("scripts/Install_Certificate.bat")
    if cert_installer.exists():
        dest_installer = dist_cripple / "Install_Certificate.bat"
        shutil.copy2(cert_installer, dest_installer)
        print(f"[+] Bundled Certificate Installer to {dest_installer}")

    run_cripple_bat = dist_cripple / "Run_Cripple.bat"
    run_cripple_bat.write_text(
        "@echo off\n"
        "title Starting Cripple NetStrip...\n"
        "powershell -NoProfile -ExecutionPolicy Bypass -Command \"Get-ChildItem -Path '%~dp0' -Recurse -File | Unblock-File -ErrorAction SilentlyContinue\"\n"
        "start \"\" \"%~dp0Cripple.exe\" %*\n",
        encoding="utf-8"
    )
    print(f"[+] Created Smart Unblock Launcher at {run_cripple_bat}")

    print("=" * 60)
    print(" FrenzyPenguin Media Code Signing Complete!")
    print("=" * 60)

if __name__ == "__main__":
    sign_and_package()
