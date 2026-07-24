"""
Icon Manager for Cripple GUI.
Handles app identification, local icon extraction, and online fallback fetching.
"""

import os
import urllib.request
import threading
from PIL import Image
from typing import Optional
import customtkinter as ctk

# Trustworthy generic icon URLs using reliable Favicon API
OS_ICONS = {
    'windows': 'https://www.google.com/s2/favicons?domain=microsoft.com&sz=64',
    'linux': 'https://www.google.com/s2/favicons?domain=kernel.org&sz=64',
    'macos': 'https://www.google.com/s2/favicons?domain=apple.com&sz=64',
    'system': 'https://www.google.com/s2/favicons?domain=microsoft.com&sz=64'
}

APP_ICONS = {
    'chrome': 'https://www.google.com/s2/favicons?domain=chrome.com&sz=64',
    'firefox': 'https://www.google.com/s2/favicons?domain=mozilla.org&sz=64',
    'msedge': 'https://www.google.com/s2/favicons?domain=microsoftedge.com&sz=64',
    'discord': 'https://www.google.com/s2/favicons?domain=discord.com&sz=64',
    'steam': 'https://www.google.com/s2/favicons?domain=steampowered.com&sz=64',
    'spotify': 'https://www.google.com/s2/favicons?domain=spotify.com&sz=64',
    'code': 'https://www.google.com/s2/favicons?domain=code.visualstudio.com&sz=64',
    'zoom': 'https://www.google.com/s2/favicons?domain=zoom.us&sz=64',
    'teams': 'https://www.google.com/s2/favicons?domain=teams.microsoft.com&sz=64',
    'brave': 'https://www.google.com/s2/favicons?domain=brave.com&sz=64',
    'dns': 'https://www.google.com/s2/favicons?domain=cloudflare.com&sz=64',
    'unknown (dns)': 'https://www.google.com/s2/favicons?domain=cloudflare.com&sz=64',
    'taskhostw': 'https://www.google.com/s2/favicons?domain=microsoft.com&sz=64',
    'svchost': 'https://www.google.com/s2/favicons?domain=microsoft.com&sz=64',
    'explorer': 'https://www.google.com/s2/favicons?domain=windows.com&sz=64',
    'cmd': 'https://www.google.com/s2/favicons?domain=microsoft.com&sz=64',
    'powershell': 'https://www.google.com/s2/favicons?domain=microsoft.com&sz=64',
    'pwsh': 'https://www.google.com/s2/favicons?domain=microsoft.com&sz=64',
    'services': 'https://www.google.com/s2/favicons?domain=microsoft.com&sz=64',
    'wininit': 'https://www.google.com/s2/favicons?domain=microsoft.com&sz=64',
    'smss': 'https://www.google.com/s2/favicons?domain=microsoft.com&sz=64',
    'conhost': 'https://www.google.com/s2/favicons?domain=microsoft.com&sz=64',
    'csrss': 'https://www.google.com/s2/favicons?domain=microsoft.com&sz=64',
    'lsass': 'https://www.google.com/s2/favicons?domain=microsoft.com&sz=64',
    'spoolsv': 'https://www.google.com/s2/favicons?domain=microsoft.com&sz=64',
    'wermgr': 'https://www.google.com/s2/favicons?domain=microsoft.com&sz=64',
    'system': 'https://www.google.com/s2/favicons?domain=microsoft.com&sz=64'
}

class AppIdentifier:
    @staticmethod
    def identify(process_path: str) -> str:
        """Categorize the process based on its absolute path."""
        if not process_path:
            return 'unknown'
            
        path = process_path.lower()
        
        # Windows System
        if 'windows\\system32' in path or 'windows\\syswow64' in path:
            return 'windows'
        if 'program files\\windowsapps' in path:
            return 'windows'
            
        # Linux System
        if path.startswith('/usr/bin/') or path.startswith('/sbin/') or path.startswith('/usr/sbin/'):
            return 'linux'
            
        # macOS System
        if path.startswith('/system/library/') or path.startswith('/usr/libexec/'):
            return 'macos'
            
        return 'user_app'

class IconManager:
    def __init__(self, cache_dir: str):
        self.cache_dir = os.path.join(cache_dir, 'icons')
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)
            
        self._check_cache_version()
            
        # In-memory cache of PIL.Image
        self._image_cache = {}
        # Prevent multiple threads extracting the same icon
        self._in_progress = set()

    def _check_cache_version(self):
        try:
            from netstrip import __version__
            version_file = os.path.join(self.cache_dir, ".version")
            if os.path.exists(version_file):
                with open(version_file, "r") as f:
                    cached_version = f.read().strip()
                if cached_version == __version__:
                    return
                    
            # Wipe cache
            for fname in os.listdir(self.cache_dir):
                try: os.remove(os.path.join(self.cache_dir, fname))
                except: pass
                
            with open(version_file, "w") as f:
                f.write(__version__)
        except Exception:
            pass

    def get_icon(self, process_path: str, process_name: str, callback=None) -> Optional[ctk.CTkImage]:
        """
        Attempts to get the icon. 
        Returns immediately if cached. If a download is needed, returns None and fires callback when done.
        """
        if process_name and process_name.startswith("Cripple"):
            if "cripple_logo" in self._image_cache:
                img = self._image_cache["cripple_logo"]
                return ctk.CTkImage(light_image=img, dark_image=img, size=(24, 24))
            try:
                logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "assets", "cripple_logo.png")
                if os.path.exists(logo_path):
                    img = Image.open(logo_path)
                    self._image_cache["cripple_logo"] = img
                    return ctk.CTkImage(light_image=img, dark_image=img, size=(24, 24))
            except Exception:
                pass
                
        if process_name and "dns" in process_name.lower():
            if "dns_logo" in self._image_cache:
                img = self._image_cache["dns_logo"]
                return ctk.CTkImage(light_image=img, dark_image=img, size=(24, 24))
            try:
                logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "assets", "dns_logo.png")
                if os.path.exists(logo_path):
                    img = Image.open(logo_path)
                    self._image_cache["dns_logo"] = img
                    return ctk.CTkImage(light_image=img, dark_image=img, size=(24, 24))
            except Exception:
                pass
                
        if not process_path:
            if not process_name or process_name == 'Unknown' or process_name == 'Unknown (DNS)':
                return None
            # Use process_name as a virtual path for caching and fallback logic
            process_path = process_name
            
        # 1. Check memory cache
        if process_path in self._image_cache:
            img = self._image_cache[process_path]
            return ctk.CTkImage(light_image=img, dark_image=img, size=(24, 24))
            
        app_name_base = process_name.lower().replace('.exe', '')
        
        # 2. Check disk cache for native EXE extraction
        cached_exe_icon = os.path.join(self.cache_dir, f"exe_{app_name_base}.png")
        if os.path.exists(cached_exe_icon):
            try:
                img = Image.open(cached_exe_icon)
                img.verify() # Validate it's a real image
                img = Image.open(cached_exe_icon) # Re-open after verify
                self._image_cache[process_path] = img
                return ctk.CTkImage(light_image=img, dark_image=img, size=(24, 24))
            except Exception:
                try: os.remove(cached_exe_icon)
                except Exception: pass

        # 3. Check disk cache for App Fallback
        app_icon_path = os.path.join(self.cache_dir, f"app_{app_name_base}.png")
        if os.path.exists(app_icon_path):
            try:
                img = Image.open(app_icon_path)
                img.verify()
                img = Image.open(app_icon_path)
                self._image_cache[process_path] = img
                return ctk.CTkImage(light_image=img, dark_image=img, size=(24, 24))
            except Exception:
                try: os.remove(app_icon_path)
                except Exception: pass
                
        # 4. Check disk cache for OS Fallback
        os_type = AppIdentifier.identify(process_path)
        cached_os_icon_path = os.path.join(self.cache_dir, f"{os_type}.png")
        if os.path.exists(cached_os_icon_path):
            try:
                img = Image.open(cached_os_icon_path)
                img.verify()
                img = Image.open(cached_os_icon_path)
                self._image_cache[process_path] = img
                return ctk.CTkImage(light_image=img, dark_image=img, size=(24, 24))
            except Exception:
                try: os.remove(cached_os_icon_path)
                except Exception: pass
                
        # If not cached anywhere and we don't have a callback, bail out
        if not callback:
            return None
            
        # Otherwise, initiate background fetch
        if process_path not in self._in_progress:
            self._in_progress.add(process_path)
            
            if process_path.endswith('.exe') and os.path.exists(process_path):
                threading.Thread(
                    target=self._extract_icon_native,
                    args=(process_path, process_name, cached_exe_icon, callback),
                    daemon=True
                ).start()
            else:
                threading.Thread(
                    target=self._do_fallback,
                    args=(process_path, process_name, callback),
                    daemon=True
                ).start()
                
        return None

    def _extract_icon_native(self, process_path: str, process_name: str, save_path: str, callback):
        """Uses PowerShell to extract the embedded high-res icon from a Windows executable."""
        import subprocess
        import base64
        success = False
        try:
            # We use System.Drawing.Icon.ExtractAssociatedIcon to grab the icon
            # Escape single quotes in paths for PowerShell
            safe_process_path = process_path.replace("'", "''")
            safe_save_path = save_path.replace("'", "''")
            
            ps_script = f"""
            Add-Type -AssemblyName System.Drawing
            try {{
                $icon = [System.Drawing.Icon]::ExtractAssociatedIcon('{safe_process_path}')
                $bmp = $icon.ToBitmap()
                $bmp.Save('{safe_save_path}', [System.Drawing.Imaging.ImageFormat]::Png)
            }} catch {{}}
            """
            
            # Encode script to Base64 to prevent any syntax/encoding errors with special characters in paths
            encoded_script = base64.b64encode(ps_script.encode('utf-16-le')).decode('utf-8')
            
            # Run PowerShell silently
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded_script],
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5
            )
            
            # Require at least 200 bytes to filter out corrupt/blank 1x1 PNGs
            if os.path.exists(save_path) and os.path.getsize(save_path) > 200:
                success = True
        except Exception:
            pass
            
        if success:
            if process_path in self._in_progress:
                self._in_progress.remove(process_path)
            callback()
        else:
            try: os.remove(save_path)
            except Exception: pass
            self._do_fallback(process_path, process_name, callback)

    def _do_fallback(self, process_path: str, process_name: str, callback):
        app_name_base = process_name.lower().replace('.exe', '')
        if app_name_base in APP_ICONS:
            app_icon_path = os.path.join(self.cache_dir, f"app_{app_name_base}.png")
            self._download_icon(APP_ICONS[app_name_base], app_icon_path, process_path, callback)
            return
            
        os_type = AppIdentifier.identify(process_path)
        if os_type in OS_ICONS:
            cached_os_icon_path = os.path.join(self.cache_dir, f"{os_type}.png")
            self._download_icon(OS_ICONS[os_type], cached_os_icon_path, process_path, callback)
            return
            
        if process_path in self._in_progress:
            self._in_progress.remove(process_path)

    def _download_icon(self, url: str, save_path: str, process_path: str, callback):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'NetStrip/1.0'})
            with urllib.request.urlopen(req, timeout=5) as response, open(save_path, 'wb') as out_file:
                out_file.write(response.read())
            callback()
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to download icon from {url}: {e}")
        finally:
            if process_path in self._in_progress:
                self._in_progress.remove(process_path)

import PIL.ImageTk
import logging

# Monkey patch PhotoImage.__del__ to prevent it from deleting the image from Tcl
original_del = getattr(PIL.ImageTk.PhotoImage, '__del__', None)

def safe_del(self):
    # Do nothing, intentionally leaking the Tcl image to prevent 'pyimage doesn't exist'
    pass

PIL.ImageTk.PhotoImage.__del__ = safe_del
logging.getLogger(__name__).info("Monkey-patched PIL.ImageTk.PhotoImage.__del__ to prevent Tcl image deletion")
