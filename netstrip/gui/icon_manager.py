"""
Icon Manager for Cripper GUI.
Handles app identification, local icon extraction, and online fallback fetching.
"""

import os
import urllib.request
import threading
from PIL import Image
from typing import Optional
import customtkinter as ctk

# Trustworthy generic icon URLs (Wikimedia Commons / public domain vectors)
OS_ICONS = {
    'windows': 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/e6/Windows_logo_-_2012_%28dark_blue%29.svg/240px-Windows_logo_-_2012_%28dark_blue%29.svg.png',
    'linux': 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/35/Tux.svg/240px-Tux.svg.png',
    'macos': 'https://upload.wikimedia.org/wikipedia/commons/thumb/f/fa/Apple_logo_black.svg/240px-Apple_logo_black.svg.png',
    'system': 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/Octicons-gear.svg/240px-Octicons-gear.svg.png'
}

APP_ICONS = {
    'chrome': 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/e1/Google_Chrome_icon_%28February_2022%29.svg/240px-Google_Chrome_icon_%28February_2022%29.svg.png',
    'firefox': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a0/Firefox_logo%2C_2019.svg/240px-Firefox_logo%2C_2019.svg.png',
    'msedge': 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/98/Microsoft_Edge_logo_%282019%29.svg/240px-Microsoft_Edge_logo_%282019%29.svg.png',
    'discord': 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c6/Discord_Color_Text_Logo_%282015-2021%29.svg/240px-Discord_Color_Text_Logo_%282015-2021%29.svg.png',
    'steam': 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/83/Steam_icon_logo.svg/240px-Steam_icon_logo.svg.png',
    'spotify': 'https://upload.wikimedia.org/wikipedia/commons/thumb/1/19/Spotify_logo_without_text.svg/240px-Spotify_logo_without_text.svg.png',
    'code': 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/9a/Visual_Studio_Code_1.35_icon.svg/240px-Visual_Studio_Code_1.35_icon.svg.png',
    'zoom': 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/07/Zoom_Icon.png/240px-Zoom_Icon.png',
    'teams': 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c9/Microsoft_Office_Teams_%282018%E2%80%93present%29.svg/240px-Microsoft_Office_Teams_%282018%E2%80%93present%29.svg.png',
    'brave': 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/51/Brave_icon_lion_face.png/240px-Brave_icon_lion_face.png'
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
"""
Icon Manager for Cripper GUI.
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
    'system': 'https://www.google.com/s2/favicons?domain=microsoft.com&sz=64',
    'user_app': 'https://www.google.com/s2/favicons?domain=github.com&sz=64'
}

APP_ICONS = {
    'chrome': 'https://www.google.com/s2/favicons?domain=google.com&sz=64',
    'firefox': 'https://www.google.com/s2/favicons?domain=mozilla.org&sz=64',
    'msedge': 'https://www.google.com/s2/favicons?domain=microsoft.com&sz=64',
    'discord': 'https://www.google.com/s2/favicons?domain=discord.com&sz=64',
    'steam': 'https://www.google.com/s2/favicons?domain=steampowered.com&sz=64',
    'spotify': 'https://www.google.com/s2/favicons?domain=spotify.com&sz=64',
    'code': 'https://www.google.com/s2/favicons?domain=visualstudio.com&sz=64',
    'zoom': 'https://www.google.com/s2/favicons?domain=zoom.us&sz=64',
    'teams': 'https://www.google.com/s2/favicons?domain=microsoft.com&sz=64',
    'brave': 'https://www.google.com/s2/favicons?domain=brave.com&sz=64'
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
            
        # In-memory cache of PIL.Image
        self._image_cache = {}
        # Prevent multiple threads extracting the same icon
        self._in_progress = set()

    def get_icon(self, process_path: str, process_name: str, callback=None) -> Optional[ctk.CTkImage]:
        """
        Attempts to get the icon. 
        Returns immediately if cached. If a download is needed, returns None and fires callback when done.
        """
        if process_name == "Cripper":
            if "cripper_logo" in self._image_cache:
                img = self._image_cache["cripper_logo"]
                return ctk.CTkImage(light_image=img, dark_image=img, size=(24, 24))
            try:
                logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "assets", "cripper_logo.png")
                if os.path.exists(logo_path):
                    img = Image.open(logo_path)
                    self._image_cache["cripper_logo"] = img
                    return ctk.CTkImage(light_image=img, dark_image=img, size=(24, 24))
            except Exception:
                pass
                
        if not process_path:
            return None
            
        # Check memory cache
        if process_path in self._image_cache:
            img = self._image_cache[process_path]
            return ctk.CTkImage(light_image=img, dark_image=img, size=(24, 24))
            
        app_name_base = process_name.lower().replace('.exe', '')
        cached_exe_icon = os.path.join(self.cache_dir, f"exe_{app_name_base}.png")
        
        # Check disk cache
        if os.path.exists(cached_exe_icon):
            try:
                img = Image.open(cached_exe_icon)
                self._image_cache[process_path] = img
                return ctk.CTkImage(light_image=img, dark_image=img, size=(24, 24))
            except Exception:
                pass
                
        # If not in cache, launch a background thread to extract it via PowerShell
        # We attempt native extraction for ALL .exe files on Windows for maximum accuracy.
        if callback and process_path.endswith('.exe') and os.path.exists(process_path):
            if process_path not in self._in_progress:
                self._in_progress.add(process_path)
                threading.Thread(
                    target=self._extract_icon_native,
                    args=(process_path, cached_exe_icon, callback),
                    daemon=True
                ).start()
            return None

        # Check for popular apps (Fallback)
        if app_name_base in APP_ICONS:
            app_icon_path = os.path.join(self.cache_dir, f"app_{app_name_base}.png")
            if os.path.exists(app_icon_path):
                try:
                    img = Image.open(app_icon_path)
                    self._image_cache[process_path] = img
                    return ctk.CTkImage(light_image=img, dark_image=img, size=(24, 24))
                except Exception:
                    pass
            if callback:
                threading.Thread(target=self._download_icon, args=(APP_ICONS[app_name_base], app_icon_path, process_path, callback), daemon=True).start()
            return None

        # If not found locally and not a popular app, identify OS type
        os_type = AppIdentifier.identify(process_path)
        if os_type in OS_ICONS:
            # We need to download or load cached generic OS icon
            cached_os_icon_path = os.path.join(self.cache_dir, f"{os_type}.png")
            
            if os.path.exists(cached_os_icon_path):
                try:
                    img = Image.open(cached_os_icon_path)
                    self._image_cache[process_path] = img
                    return ctk.CTkImage(light_image=img, dark_image=img, size=(24, 24))
                except Exception:
                    pass
            
            # Download in background
            if callback:
                threading.Thread(
                    target=self._download_icon, 
                    args=(OS_ICONS[os_type], cached_os_icon_path, process_path, callback), 
                    daemon=True
                ).start()
                
        return None

    def _extract_icon_native(self, process_path: str, save_path: str, callback):
        """Uses PowerShell to extract the embedded high-res icon from a Windows executable."""
        import subprocess
        import base64
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
                stderr=subprocess.DEVNULL
            )
            
            if os.path.exists(save_path):
                callback()
            else:
                self._do_fallback(process_path, callback)
        except Exception as e:
            print(f"Failed to extract native icon: {e}")
            self._do_fallback(process_path, callback)
        finally:
            if process_path in self._in_progress:
                self._in_progress.remove(process_path)

    def _do_fallback(self, process_path: str, callback):
        os_type = AppIdentifier.identify(process_path)
        if os_type in OS_ICONS:
            cached_os_icon_path = os.path.join(self.cache_dir, f"{os_type}.png")
            self._download_icon(OS_ICONS[os_type], cached_os_icon_path, process_path, callback)

    def _download_icon(self, url: str, save_path: str, process_path: str, callback):
        if not url:
            return
            
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'NetStrip/1.0'})
            with urllib.request.urlopen(req) as response, open(save_path, 'wb') as out_file:
                out_file.write(response.read())
                
            # Fire callback so UI can refresh
            callback()
        except Exception as e:
            print(f"Failed to download OS icon: {e}")
import PIL.ImageTk
import logging

# Monkey patch PhotoImage.__del__ to prevent it from deleting the image from Tcl
original_del = getattr(PIL.ImageTk.PhotoImage, '__del__', None)

def safe_del(self):
    # Do nothing, intentionally leaking the Tcl image to prevent 'pyimage doesn't exist'
    pass

PIL.ImageTk.PhotoImage.__del__ = safe_del
logging.getLogger(__name__).info("Monkey-patched PIL.ImageTk.PhotoImage.__del__ to prevent Tcl image deletion")
