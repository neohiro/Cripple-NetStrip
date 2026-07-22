"""
Auto-Updater for NetStrip
Downloads updates for offline blocklists on the first internet connection after boot.
"""

import json
import os
import urllib.request
import threading
import logging
import time
from typing import Dict, Any

logger = logging.getLogger(__name__)

class BlocklistUpdater:
    def __init__(self, lists_dir: str):
        self.lists_dir = lists_dir
        self.sources_file = os.path.join(lists_dir, '..', 'updater_sources.json')
        self.is_updating = False

    def check_and_update(self):
        """Run the update in a background thread."""
        if self.is_updating:
            return
            
        threading.Thread(target=self._perform_update, daemon=True).start()

    def _perform_update(self):
        self.is_updating = True
        try:
            if not os.path.exists(self.sources_file):
                logger.warning(f"Updater sources file not found: {self.sources_file}")
                return

            with open(self.sources_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            sources = data.get('sources', [])
            
            # Load state
            state_file = os.path.join(self.lists_dir, 'updater_state.json')
            state_data = {}
            if os.path.exists(state_file):
                try:
                    with open(state_file, 'r', encoding='utf-8') as f:
                        state_data = json.load(f)
                except Exception:
                    pass

            sources_modified = False
            
            for source in sources:
                if not source.get('enabled', False):
                    continue
                    
                url = source.get('url')
                category = source.get('category')
                name = source.get('name')
                
                if not url or not category:
                    continue
                    
                safe_name = name.replace(' ', '_').replace('/', '_').replace(':', '')
                temp_file = os.path.join(self.lists_dir, f"temp_{category}_{safe_name}.txt")
                target_file = os.path.join(self.lists_dir, f"{category}_{safe_name}.txt")
                
                # Check file age (skip if updated within the last 24 hours)
                if os.path.exists(target_file):
                    file_age_seconds = time.time() - os.path.getmtime(target_file)
                    if file_age_seconds < 86400: # 24 hours
                        continue

                # Check if it's been attempted recently (throttle to 1 hour even on failures)
                last_attempt = state_data.get(name, {}).get('last_attempt', 0)
                if time.time() - last_attempt < 3600:
                    continue
                    
                logger.info(f"Updating blocklist '{name}' for category '{category}' from {url}")
                
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) NetStrip/1.0'})
                    with urllib.request.urlopen(req, timeout=15) as response:
                        with open(temp_file, 'wb') as out_file:
                            out_file.write(response.read())
                    
                    if os.path.exists(target_file):
                        os.remove(target_file)
                    os.rename(temp_file, target_file)
                        
                    logger.info(f"Successfully updated '{name}'")
                    state_data[name] = {'last_attempt': time.time(), 'consecutive_failures': 0}
                    
                    # Prevent network/CPU spike by delaying between downloads
                    time.sleep(3)

                    
                except Exception as e:
                    logger.error(f"Failed to update blocklist '{name}': {e}")
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                        
                    # Track failure
                    failures = state_data.get(name, {}).get('consecutive_failures', 0) + 1
                    state_data[name] = {'last_attempt': time.time(), 'consecutive_failures': failures}
                    
                    if failures >= 3:
                        logger.warning(f"Auto-disabling dead blocklist '{name}' after {failures} consecutive failures.")
                        source['enabled'] = False
                        sources_modified = True
                        
                    # Prevent network spike even if host rejected connection
                    time.sleep(3)
                        
            # Save state
            try:
                with open(state_file, 'w', encoding='utf-8') as f:
                    json.dump(state_data, f, indent=2)
            except Exception:
                pass
                
            # Save modified sources if any were disabled
            if sources_modified:
                try:
                    with open(self.sources_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2)
                except Exception as e:
                    logger.error(f"Failed to save updated sources: {e}")
                    
            # Fetch DNSCrypt resolvers to build dynamic upstream options
            self._fetch_dnscrypt_resolvers()
                        
        finally:
            self.is_updating = False

    def _decode_stamp(self, stamp_str):
        import base64
        b64_str = stamp_str.replace('sdns://', '')
        b64_str += '=' * (-len(b64_str) % 4)
        try:
            data = base64.urlsafe_b64decode(b64_str)
        except Exception:
            return None
        if len(data) < 1: return None
        proto = data[0]
        if proto not in (0x02, 0x03): return None
        
        idx = 9
        def read_pascal(buf, i):
            if i >= len(buf): return None, i
            length = buf[i]
            i += 1
            if i + length > len(buf): return None, i
            return buf[i:i+length].decode('utf-8', errors='ignore'), i + length
            
        ip, idx = read_pascal(data, idx)
        if not ip: return None
        ip_clean = ip.split(':')[0]
        if '[' in ip_clean or ':' in ip_clean: return None # Skip IPv6 for simplicity in UI
        
        pk, idx = read_pascal(data, idx)
        provider_name, idx = read_pascal(data, idx)
        if not provider_name: return None
        
        path = "/dns-query"
        if proto == 0x02:
            path_parsed, idx = read_pascal(data, idx)
            if path_parsed: path = path_parsed
            
        return {
            "type": "DoH" if proto == 0x02 else "DoT",
            "ip": ip_clean,
            "hostname": provider_name,
            "path": path
        }

    def _fetch_dnscrypt_resolvers(self):
        target_file = os.path.join(self.lists_dir, "doh_providers_online.json")
        
        # Check file age (skip if updated within the last 24 hours)
        if os.path.exists(target_file):
            file_age_seconds = time.time() - os.path.getmtime(target_file)
            if file_age_seconds < 86400: # 24 hours
                return
                
        try:
            logger.info("Fetching dynamic DNSCrypt resolvers list...")
            req = urllib.request.Request('https://raw.githubusercontent.com/DNSCrypt/dnscrypt-resolvers/master/v3/public-resolvers.md', headers={'User-Agent':'NetStrip/1.0'})
            with urllib.request.urlopen(req, timeout=15) as response:
                content = response.read().decode('utf-8')
                
            providers = []
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('sdns://'):
                    parsed = self._decode_stamp(line)
                    if parsed and parsed['ip'] and parsed['hostname']:
                        providers.append(parsed)
                        
            if providers:
                # Group by IP in case of duplicates, prioritizing DoH over DoT
                unique_providers = {}
                for p in providers:
                    ip = p['ip']
                    if ip not in unique_providers or p['type'] == 'DoH':
                        unique_providers[ip] = p
                        
                with open(target_file, 'w', encoding='utf-8') as f:
                    json.dump(list(unique_providers.values()), f, indent=2)
                logger.info(f"Saved {len(unique_providers)} dynamic DoH/DoT upstream providers.")
        except Exception as e:
            logger.error(f"Failed to fetch DNSCrypt resolvers: {e}")
