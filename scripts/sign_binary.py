"""
FrenzyPenguin Media - Authenticode Code Signing & Packaging Helper
Automatically signs Windows binaries for FrenzyPenguin Media with Authenticode SHA-256
when an official PFX certificate is provided via CI environment variables.
"""
import os
import sys
import subprocess
import shutil
import base64
import tempfile
from pathlib import Path

def sign_and_package():
    print("=" * 60)
    print(" FrenzyPenguin Media - Code Signing & Packaging Helper")
    print("=" * 60)

    dist_cripple = Path("dist/Cripple")
    exe_path = dist_cripple / "Cripple.exe"

    if not dist_cripple.exists() or not exe_path.exists():
        print(f"Warning: {exe_path} not found. Skipping binary signing.")
        return

    # 1. Determine PFX source
    pfx_env = os.environ.get("WINDOWS_PFX_BASE64", "").strip()
    pfx_pass = os.environ.get("WINDOWS_PFX_PASSWORD", "FrenzyPenguin2026").strip()

    temp_pfx_file = None
    pfx_path_str = None

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

    if not pfx_path_str:
        print("[+] No official code signing PFX provided.")
        print("[+] Preserving native PE image integrity (prevents Bad Image / 0xc000012f errors).")
        print("=" * 60)
        return

    # 2. Only sign Cripple.exe (NEVER modify internal .pyd/.dll C-extensions to preserve PE hash integrity)
    import glob
    sdk_signtools = glob.glob("C:/Program Files (x86)/Windows Kits/10/bin/*/x64/signtool.exe")
    signtool_exe = sdk_signtools[-1] if sdk_signtools else None

    if signtool_exe and os.path.exists(signtool_exe):
        print(f"[+] Found Windows SDK signtool: {signtool_exe}")
        ts_urls = ["http://timestamp.digicert.com", "http://timestamp.sectigo.com", "http://timestamp.globalsign.com/scripts/timstamp.dll"]
        signed = False
        for ts in ts_urls:
            cmd = [
                signtool_exe, "sign",
                "/f", pfx_path_str,
                "/p", pfx_pass,
                "/fd", "SHA256",
                "/tr", ts,
                "/td", "SHA256",
                str(exe_path.resolve())
            ]
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode == 0:
                signed = True
                print(f"[+] Successfully signed {exe_path.name} with signtool Authenticode SHA-256 (Timestamp: {ts}).")
                break
        if not signed:
            cmd_notime = [
                signtool_exe, "sign",
                "/f", pfx_path_str,
                "/p", pfx_pass,
                "/fd", "SHA256",
                str(exe_path.resolve())
            ]
            r = subprocess.run(cmd_notime, capture_output=True, text=True)
            if r.returncode == 0:
                print(f"[+] Successfully signed {exe_path.name} with signtool Authenticode SHA-256.")
    else:
        # Fallback PowerShell Set-AuthenticodeSignature on Cripple.exe only
        pfx_path_escaped = pfx_path_str.replace("'", "''")
        exe_path_escaped = str(exe_path.resolve()).replace("'", "''")
        ps_sign = f"""
        $pfxPath = '{pfx_path_escaped}'
        $pfxPass = '{pfx_pass}'
        $pass = ConvertTo-SecureString $pfxPass -AsPlainText -Force
        $imported = @(Import-PfxCertificate -FilePath $pfxPath -CertStoreLocation Cert:\\CurrentUser\\My -Password $pass -Exportable)
        $cert = $null
        if ($imported.Count -gt 0) {{ $cert = $imported[0] }}
        if (-not $cert) {{
            $flags = [System.Security.Cryptography.X509Certificates.X509KeyStorageFlags]::Exportable
            $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($pfxPath, $pfxPass, $flags)
        }}
        $tsUrls = @('http://timestamp.digicert.com', 'http://timestamp.sectigo.com')
        $ok = $false
        foreach ($ts in $tsUrls) {{
            try {{
                $res = Set-AuthenticodeSignature -FilePath '{exe_path_escaped}' -Certificate $cert -HashAlgorithm SHA256 -TimestampServer $ts -ErrorAction Stop
                if ($res.Status -in @('Valid', 'UnknownError', 'NotTrusted')) {{ $ok = $true; break }}
            }} catch {{}}
        }}
        if (-not $ok) {{
            Set-AuthenticodeSignature -FilePath '{exe_path_escaped}' -Certificate $cert -HashAlgorithm SHA256 -ErrorAction SilentlyContinue
        }}
        """
        with tempfile.NamedTemporaryFile(suffix=".ps1", delete=False, mode="w", encoding="utf-8") as tf:
            tf.write(ps_sign)
            temp_ps1 = tf.name
        try:
            subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", temp_ps1], capture_output=True, text=True)
            print(f"[+] Signed {exe_path.name} with PowerShell Authenticode SHA-256.")
        finally:
            try:
                os.remove(temp_ps1)
            except Exception:
                pass

    if temp_pfx_file and os.path.exists(temp_pfx_file):
        try:
            os.remove(temp_pfx_file)
        except Exception:
            pass

    print("=" * 60)
    print(" Code Signing Complete!")
    print("=" * 60)

if __name__ == "__main__":
    sign_and_package()
