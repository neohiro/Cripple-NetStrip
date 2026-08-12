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
    'vscodium': 'https://www.google.com/s2/favicons?domain=vscodium.com&sz=64',
    'antigravity': 'https://www.google.com/s2/favicons?domain=google.com&sz=64',
    'cursor': 'https://www.google.com/s2/favicons?domain=cursor.com&sz=64',
    'windsurf': 'https://www.google.com/s2/favicons?domain=codeium.com&sz=64',
    'git': 'https://www.google.com/s2/favicons?domain=github.com&sz=64',
    'python': 'https://www.google.com/s2/favicons?domain=python.org&sz=64',
    'node': 'https://www.google.com/s2/favicons?domain=nodejs.org&sz=64',
    'idea64': 'https://www.google.com/s2/favicons?domain=jetbrains.com&sz=64',
    'pycharm64': 'https://www.google.com/s2/favicons?domain=jetbrains.com&sz=64',
    'webstorm64': 'https://www.google.com/s2/favicons?domain=jetbrains.com&sz=64',
    'zoom': 'https://www.google.com/s2/favicons?domain=zoom.us&sz=64',
    'teams': 'https://www.google.com/s2/favicons?domain=teams.microsoft.com&sz=64',
    'slack': 'https://www.google.com/s2/favicons?domain=slack.com&sz=64',
    'telegram': 'https://www.google.com/s2/favicons?domain=telegram.org&sz=64',
    'whatsapp': 'https://www.google.com/s2/favicons?domain=whatsapp.com&sz=64',
    'signal': 'https://www.google.com/s2/favicons?domain=signal.org&sz=64',
    'dropbox': 'https://www.google.com/s2/favicons?domain=dropbox.com&sz=64',
    'onedrive': 'https://www.google.com/s2/favicons?domain=microsoft.com&sz=64',
    'brave': 'https://www.google.com/s2/favicons?domain=brave.com&sz=64',
    'dns': 'https://www.google.com/s2/favicons?domain=cloudflare.com&sz=64',
    'unknown (dns)': 'https://www.google.com/s2/favicons?domain=cloudflare.com&sz=64',
    'taskhostw': 'https://www.google.com/s2/favicons?domain=microsoft.com&sz=64',
    'svchost': 'https://www.google.com/s2/favicons?domain=microsoft.com&sz=64',
    'explorer': 'https://www.google.com/s2/favicons?domain=windows.com&sz=64',
    'cmd': 'https://www.google.com/s2/favicons?domain=microsoft.com&sz=64',
    'chrome': 'https://www.google.com/s2/favicons?domain=google.com&sz=64',
    'pwsh': 'https://www.google.com/s2/favicons?domain=microsoft.com&sz=64',
    'services': 'https://www.google.com/s2/favicons?domain=microsoft.com&sz=64',
    'wininit': 'https://www.google.com/s2/favicons?domain=microsoft.com&sz=64',
    'smss': 'https://www.google.com/s2/favicons?domain=microsoft.com&sz=64',
    'conhost': 'https://www.google.com/s2/favicons?domain=microsoft.com&sz=64',
    'csrss': 'https://www.google.com/s2/favicons?domain=microsoft.com&sz=64',
    'lsass': 'https://www.google.com/s2/favicons?domain=microsoft.com&sz=64',
    'spoolsv': 'https://www.google.com/s2/favicons?domain=microsoft.com&sz=64',
    'wermgr': 'https://www.google.com/s2/favicons?domain=microsoft.com&sz=64',
    'system': 'https://www.google.com/s2/favicons?domain=microsoft.com&sz=64',
    'system idle process': 'https://www.google.com/s2/favicons?domain=microsoft.com&sz=64'
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

import concurrent.futures

class IconManager:
    def __init__(self, cache_dir: str):
        self.cache_dir = os.path.join(cache_dir, 'icons')
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)
            
        # In-memory caches
        self._image_cache = {}      # PIL Images
        self._ctk_image_cache = {}  # CTkImage objects
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Prevent multiple threads extracting the same icon
        self._in_progress = set()
        
        # Bounded worker pool to prevent spawning dozens of PowerShell / download threads
        self._worker_pool = concurrent.futures.ThreadPoolExecutor(max_workers=5)

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
                
        if not process_path or not os.path.isabs(process_path):
            if process_name and process_name not in ('Unknown', 'Unknown (DNS)'):
                import shutil
                resolved = shutil.which(process_name)
                if resolved:
                    process_path = resolved
            
        if not process_path:
            if not process_name or process_name == 'Unknown' or process_name == 'Unknown (DNS)':
                return None
            # Use process_name as a virtual path for caching and fallback logic
            process_path = process_name
            
        # 1. Check memory cache
        if process_path in self._ctk_image_cache:
            return self._ctk_image_cache[process_path]
        
        if process_path in self._image_cache:
            img = self._image_cache[process_path]
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(24, 24))
            self._ctk_image_cache[process_path] = ctk_img
            return ctk_img
            
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
        path_base = os.path.basename(process_path).lower().replace('.exe', '') if process_path else ''
        
        possible_app_paths = [os.path.join(self.cache_dir, f"app_{app_name_base}.png")]
        if path_base:
            possible_app_paths.append(os.path.join(self.cache_dir, f"app_{path_base}.png"))
            possible_app_paths.append(os.path.join(self.cache_dir, f"app_guess_{path_base}.png"))
            
        # Add reverse-mapping paths
        display_lower = process_name.lower()
        if "chrome" in display_lower: possible_app_paths.append(os.path.join(self.cache_dir, "app_chrome.png"))
        if "edge" in display_lower: possible_app_paths.append(os.path.join(self.cache_dir, "app_msedge.png"))
        if "service host" in display_lower or "svchost" in display_lower: possible_app_paths.append(os.path.join(self.cache_dir, "app_svchost.png"))
        if "system idle process" in display_lower or "system" == display_lower or "system (kernel" in display_lower or "registry" in display_lower:
            possible_app_paths.append(os.path.join(self.cache_dir, "app_system.png"))
        if "explorer" in display_lower: possible_app_paths.append(os.path.join(self.cache_dir, "app_explorer.png"))
        if "cmd" == display_lower or "command prompt" in display_lower: possible_app_paths.append(os.path.join(self.cache_dir, "app_cmd.png"))
        if "taskhostw" in display_lower or "host process" in display_lower: possible_app_paths.append(os.path.join(self.cache_dir, "app_taskhostw.png"))
        if "services" in display_lower or "services.exe" in display_lower: possible_app_paths.append(os.path.join(self.cache_dir, "app_services.png"))
        if "lsass" in display_lower or "csrss" in display_lower or "wininit" in display_lower or "smss" in display_lower:
            possible_app_paths.append(os.path.join(self.cache_dir, "app_system.png"))
        if "code" in display_lower: possible_app_paths.append(os.path.join(self.cache_dir, "app_code.png"))
            
        possible_app_paths.append(os.path.join(self.cache_dir, "app_default_globe.png"))
        for app_icon_path in possible_app_paths:
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
            
        # Otherwise, initiate background fetch via bounded worker pool
        with self._lock:
            if process_path in self._in_progress or len(self._in_progress) >= 1000:
                return None
            self._in_progress.add(process_path)
            
            if process_path.endswith('.exe') and os.path.exists(process_path):
                try:
                    self._worker_pool.submit(self._extract_icon_native, process_path, process_name, cached_exe_icon, callback)
                except Exception:
                    self._in_progress.discard(process_path)
            else:
                try:
                    self._worker_pool.submit(self._do_fallback, process_path, process_name, callback)
                except Exception:
                    self._in_progress.discard(process_path)
                
        return None

    def _extract_icon_native(self, process_path: str, process_name: str, save_path: str, callback):
        """Native extraction disabled to prevent ML heuristics. Calls fallback immediately."""
        self._do_fallback(process_path, process_name, callback)


    def _do_fallback(self, process_path: str, process_name: str, callback):
        app_name_base = process_name.lower().replace('.exe', '')
        path_base = os.path.basename(process_path).lower().replace('.exe', '') if process_path else ''
        
        # 1. Try matching path base (e.g. chrome)
        if path_base in APP_ICONS:
            app_icon_path = os.path.join(self.cache_dir, f"app_{path_base}.png")
            self._download_icon(APP_ICONS[path_base], app_icon_path, process_path, callback)
            return
            
        # 2. Try matching display name
        if app_name_base in APP_ICONS:
            app_icon_path = os.path.join(self.cache_dir, f"app_{app_name_base}.png")
            self._download_icon(APP_ICONS[app_name_base], app_icon_path, process_path, callback)
            return
            
        # 2.5 Reverse map known display names
        display_lower = process_name.lower()
        if "chrome" in display_lower:
            self._download_icon(APP_ICONS['chrome'], os.path.join(self.cache_dir, "app_chrome.png"), process_path, callback)
            return
        if "edge" in display_lower:
            self._download_icon(APP_ICONS['msedge'], os.path.join(self.cache_dir, "app_msedge.png"), process_path, callback)
            return
        if "service host" in display_lower or "svchost" in display_lower:
            self._download_icon(APP_ICONS['svchost'], os.path.join(self.cache_dir, "app_svchost.png"), process_path, callback)
            return
        if "system idle process" in display_lower or "system" == display_lower or "system (kernel" in display_lower or "registry" in display_lower:
            self._download_icon(APP_ICONS['system'], os.path.join(self.cache_dir, "app_system.png"), process_path, callback)
            return
        if "explorer" in display_lower:
            self._download_icon(APP_ICONS['explorer'], os.path.join(self.cache_dir, "app_explorer.png"), process_path, callback)
            return
        if "cmd" == display_lower or "command prompt" in display_lower:
            self._download_icon(APP_ICONS['cmd'], os.path.join(self.cache_dir, "app_cmd.png"), process_path, callback)
            return
        if "taskhostw" in display_lower or "host process" in display_lower:
            self._download_icon(APP_ICONS['taskhostw'], os.path.join(self.cache_dir, "app_taskhostw.png"), process_path, callback)
            return
        if "services" in display_lower or "services.exe" in display_lower:
            self._download_icon(APP_ICONS['services'], os.path.join(self.cache_dir, "app_services.png"), process_path, callback)
            return
        if "lsass" in display_lower or "csrss" in display_lower or "wininit" in display_lower or "smss" in display_lower:
            self._download_icon(APP_ICONS['system'], os.path.join(self.cache_dir, "app_system.png"), process_path, callback)
            return
        if "code" in display_lower:
            self._download_icon(APP_ICONS['code'], os.path.join(self.cache_dir, "app_code.png"), process_path, callback)
            return
            
        # 3. Try OS icons
        os_type = AppIdentifier.identify(process_path)
        if os_type in OS_ICONS:
            cached_os_icon_path = os.path.join(self.cache_dir, f"{os_type}.png")
            self._download_icon(OS_ICONS[os_type], cached_os_icon_path, process_path, callback)
            return
            
        # 4. Try guessing from a clean domain using the executable name (e.g. 'brave' -> 'brave.com')
        # This catches tons of apps without needing them hardcoded in APP_ICONS
        if path_base and path_base not in ('unknown', 'system', 'svchost', 'explorer') and " " not in path_base:
            guess_url = f"https://www.google.com/s2/favicons?domain={path_base}.com&sz=64"
            app_icon_path = os.path.join(self.cache_dir, f"app_guess_{path_base}.png")
            self._download_icon(guess_url, app_icon_path, process_path, callback)
            return
            
        # 5. Catch-all: default globe icon (using w3.org as a generic globe fallback to prevent 404s)
        guess_url = f"https://www.google.com/s2/favicons?domain=w3.org&sz=64"
        app_icon_path = os.path.join(self.cache_dir, "app_default_globe.png")
        self._download_icon(guess_url, app_icon_path, process_path, callback)
        return

    def _download_icon(self, url: str, save_path: str, process_path: str, callback):
        import random
        temp_path = f"{save_path}.{random.randint(10000, 99999)}.tmp"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'NetStrip/1.0'})
            with urllib.request.urlopen(req, timeout=4) as response, open(temp_path, 'wb') as out_file:
                out_file.write(response.read())
            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                os.replace(temp_path, save_path)
            callback()
        except Exception as e:
            logging.getLogger(__name__).debug(f"Failed to download icon from {url}: {e}")
        finally:
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass
            with self._lock:
                if process_path in self._in_progress:
                    self._in_progress.remove(process_path)

import logging
