"""
Process utility functions for NetStrip.
Provides canonical process name normalization and deep parent tree resolution (handling child processes and console host windows).
"""

import os
import time
import threading
from typing import Tuple, Optional

try:
    import psutil
except ImportError:
    psutil = None

_PID_CACHE = {}
_PID_CACHE_LOCK = threading.Lock()

# Intermediate console windows / shell wrappers
CONSOLE_WRAPPERS = {
    'cmd.exe', 'powershell.exe', 'pwsh.exe', 'conhost.exe', 
    'openconsole.exe', 'windowsterminal.exe', 'bash', 'sh', 'zsh', 
    'wsl.exe', 'wslhost.exe', 'terminal.exe'
}

# True OS desktop shell & service manager roots where application tree terminates
OS_ROOT_LAUNCHERS = {
    'explorer.exe', 'svchost.exe', 'services.exe', 'wininit.exe', 
    'smss.exe', 'systemd', 'init', 'launchd', 'taskhostw.exe',
    'winlogon.exe', 'csrss.exe', 'lsass.exe'
}

# Comprehensive system process identification across all supported operating systems.
# Used by the GUI (Block All red-light), classifier and connection monitor so that
# OS background processes are consistently identified at startup AND during runtime.
SYSTEM_PROCESSES_WINDOWS = {
    'system', 'system idle process', 'system (kernel/driver)', 'registry',
    'memory compression', 'secure system', 'ntoskrnl', 'smss.exe', 'csrss.exe',
    'wininit.exe', 'winlogon.exe', 'services.exe', 'lsass.exe', 'lsaiso.exe',
    'svchost.exe', 'svchost', 'service host', 'dwm.exe', 'fontdrvhost.exe',
    'sihost.exe', 'ctfmon.exe', 'conhost.exe', 'openconsole.exe', 'runtimebroker.exe',
    'dllhost.exe', 'taskhostw.exe', 'taskhost.exe', 'explorer.exe', 'searchapp.exe',
    'searchhost.exe', 'shellexperiencehost.exe', 'startmenuexperiencehost.exe',
    'applicationframehost.exe', 'backgroundtaskhost.exe', 'textinputhost.exe',
    'widgetservice.exe', 'widgets.exe', 'feedsinfobar.exe', 'lockapp.exe',
    'logonui.exe', 'wmiprvse.exe', 'wmiapsrv.exe', 'spoolsv.exe', 'wermgr.exe',
    'werfault.exe', 'werfaultsecure.exe', 'wudfhost.exe', 'audiodg.exe',
    'wlanext.exe', 'dashost.exe', 'sppsvc.exe', 'vssvc.exe', 'castsrv.exe',
    'slui.exe', 'provtool.exe', 'systemsettings.exe', 'systemsettingsbroker.exe',
    'securityhealthsystray.exe', 'securityhealthservice.exe', 'sgrmbroker.exe',
    'smartscreen.exe', 'msmpeng.exe', 'nissrv.exe', 'winrsphost.exe',
    'winrshost.exe', 'wsappx.exe', 'appinstaller.exe', 'mousocoreworker.exe',
    'usoclient.exe', 'wuauclt.exe', 'wuauserv', 'trustedinstaller.exe',
    'tiworker.exe', 'waasmedicagent.exe', 'sedlauncher.exe', 'remsh.exe',
    'compattelrunner.exe', 'devicecensus.exe', 'device-census', 'invagent.exe',
    'diagtrack.exe', 'useroobebroker.exe', 'installagent.exe', 'searchindexer.exe',
    'searchprotocolhost.exe', 'searchfilterhost.exe', 'settingsynchost.exe',
    'phoneexperiencehost.exe', 'yourphone.exe', 'gamebar.exe', 'gamebarftserver.exe',
    'xboxpcapp.exe', 'xboxpcappft.exe', 'gamingservices.exe', 'gamingservicesui.exe',
    'msedgeupdate.exe', 'microsoftedgeupdate.exe', 'onedrive.exe',
    'onedrivestandaloneupdater.exe', 'filecoauth.exe', 'officec2rclient.exe',
    'clicktodisk.exe', 'upfc.exe', 'pnkbstrA.exe', 'pnkbstrB.exe', 'nvcontainer.exe',
    'nvdisplay.container.exe', 'nvvsvc.exe', 'razercentralservice.exe',
    'armsvc.exe', 'adobeupdateservice.exe', 'gaosd.exe', 'gfbgsservice.exe',
    'memcompression', 'cmd.exe', 'powershell.exe', 'pwsh.exe', 'wsl.exe',
    'wslhost.exe', 'wslrelay.exe', 'windowsterminal.exe', 'tabtip.exe',
    'shellexperiencerunner.exe', 'perfmon.exe', 'resmon.exe', 'msdtc.exe',
    'smsts.exe', 'scardsvr.exe', 'keyiso.exe', 'sessionmanager',
    'taskmgr.exe', 'copilot.exe', 'winstore.app', 'microsoft.photos',
}

SYSTEM_PROCESSES_LINUX = {
    'systemd', 'init', 'kthreadd', 'ksoftirqd', 'kworker', 'migration',
    'rcu_sched', 'rcu_bh', 'watchdogd', 'systemd-journald', 'systemd-logind',
    'systemd-resolved', 'systemd-timesyncd', 'systemd-networkd',
    'systemd-udevd', 'udevd', 'dbus-daemon', 'dbus', 'networkmanager',
    'modemmanager', 'wpa_supplicant', 'dhclient', 'dhcpcd', 'avahi-daemon',
    'cupsd', 'cups-browsed', 'packagekitd', 'snapd', 'fwupd', 'chronyd',
    'ntpd', 'ntp', 'timesyncd', 'rpcbind', 'unattended-upgrades', 'apt',
    'dpkg', 'yum', 'dnf', 'zypper', 'pacman', 'dockerd', 'containerd',
    'kubelet', 'polkitd', 'accounts-daemon', 'rtkit-daemon', 'colord',
    'udisksd', 'gvfsd', 'gnome-shell', 'gsd-', 'Xorg', 'xinit', 'pulseaudio',
    'pipewire', 'wireplumber', 'NetworkManager', 'sshd', 'cron', 'crond',
    'atd', 'rsyslogd', 'syslogd', 'journald', 'login', 'getty', 'agetty',
    'upowerd', 'thermald', 'irqbalance', 'multipathd', 'lxcfs', 'containerd-shim',
}

SYSTEM_PROCESSES_MACOS = {
    'launchd', 'kernel_task', 'mdnsresponder', 'configd', 'syspolicyd',
    'networkd', 'nsurlsessiond', 'apsd', 'softwareupdated', 'trustd',
    'rapportd', 'symptomsd', 'rtcreportingd', 'awdd', 'analyticsd',
    'cloudd', 'touristd', 'locationd', 'identityservicesd', 'securityd',
    'cfprefsd', 'tcc', 'corelocationagent', 'crashreporter',
    'submitdiagnosticinfo', 'submitdiaginfo', 'com.apple.geod',
    'finder', 'dock', 'windowserver', 'loginwindow', 'distnoted',
    'usernoted', 'pbs', 'pboard', 'cfprefsd', 'diagnosticsd', 'powerd',
    'iokit', 'bluetoothd', 'coreaudiod', 'hidd', 'diskarbitrationd',
    'fseventsd', 'notifyd', 'opendirectoryd', 'coreservicesd',
    'launchservicesd', 'spotlight', 'mds', 'mds_stores', 'appleevents',
    'sandboxd', 'amfid', 'syslogd', 'asld', 'tailspind', 'reportmemoryexception',
}

SYSTEM_PROCESSES_ANDROID = {
    'zygote', 'zygote64', 'system_server', 'servicemanager', 'vold',
    'netd', 'netd_agent', 'logd', 'lmkd', 'installd', 'surfaceflinger',
    'audioserver', 'cameraserver', 'mediaserver', 'media.extractor',
    'media.codec', 'drmserver', 'keystore', 'gatekeeperd', 'incidentd',
    'statsd', 'traced', 'traced_probes', 'heapprofd', 'perfetto',
    'adbd', 'debuggerd', 'vndclient', 'radio', 'rild', 'cnd', 'qmuxd',
    'thermal-engine', 'thermal-engine-845', 'sensors', 'sensors-qcom',
    'vendor.', 'com.android.systemui',
    'com.android.phone', 'com.android.providers.telephony',
}

# Flattened lookup set (lowercase, with and without .exe suffix)
SYSTEM_PROCESSES = set()
for _s in (
    SYSTEM_PROCESSES_WINDOWS | SYSTEM_PROCESSES_LINUX |
    SYSTEM_PROCESSES_MACOS | SYSTEM_PROCESSES_ANDROID
):
    _lower = _s.lower()
    SYSTEM_PROCESSES.add(_lower)
    if _lower.endswith('.exe'):
        SYSTEM_PROCESSES.add(_lower[:-4])

# Prefixes treated as system processes (Service Host groupings, kernel workers, vendor daemons)
_SYSTEM_PREFIXES = ('service host', 'svchost (', 'gsd-', 'kworker/', 'com.android.', 'android.')

# Remote endpoints contacted by Cripple's own telemetry / GeoIP / update services.
# Connections to these targets originating from unattributable, system or python
# processes are re-attributed to "Cripple (Internal)" instead of the wrong process.
SELF_SERVICE_TARGETS = {
    'ipwho.is', 'ipinfo.io', 'ipapi.co', 'ip-api.com', 'api.ipify.org',
    'api.github.com', 'raw.githubusercontent.com', 'objects.githubusercontent.com',
    'github.com', 'geoip.jsdelivr.net', 'updates.netstrip.app',
    'cripple.frenzypenguin.media', 'api.telemetry.cripple.media',
}


def is_system_process(name: Optional[str]) -> bool:
    """Return True if the given process name is an OS/system process on any platform."""
    if not name:
        return False
    n = str(name).strip().lower()
    if not n:
        return False
    if n.endswith('.exe'):
        n = n[:-4]
    if n in SYSTEM_PROCESSES:
        return True
    return any(n.startswith(p) for p in _SYSTEM_PREFIXES)


# Canonical display mapping for well-known binaries
CANONICAL_APP_NAMES = {
    'antigravity.exe': 'AntiGravity',
    'antigravity': 'AntiGravity',
    'agy.exe': 'AntiGravity',
    'agy': 'AntiGravity',
    'cripple.exe': 'Cripple (Internal)',
    'cripple': 'Cripple (Internal)',
    'netstrip.exe': 'Cripple (Internal)',
    'netstrip': 'Cripple (Internal)',
    'chrome.exe': 'Google Chrome',
    'chrome': 'Google Chrome',
    'msedge.exe': 'Microsoft Edge',
    'msedge': 'Microsoft Edge',
    'msedgewebview2.exe': 'Microsoft Edge WebView',
    'firefox.exe': 'Firefox',
    'firefox': 'Firefox',
    'brave.exe': 'Brave',
    'brave': 'Brave',
    'discord.exe': 'Discord',
    'discord': 'Discord',
    'spotify.exe': 'Spotify',
    'spotify': 'Spotify',
    'steam.exe': 'Steam',
    'steam': 'Steam',
    'code.exe': 'VS Code',
    'code': 'VS Code',
    'cursor.exe': 'Cursor',
    'cursor': 'Cursor',
    'windsurf.exe': 'Windsurf',
    'windsurf': 'Windsurf',
    'slack.exe': 'Slack',
    'slack': 'Slack',
    'telegram.exe': 'Telegram',
    'telegram': 'Telegram',
    'zoom.exe': 'Zoom',
    'zoom': 'Zoom',
    'teams.exe': 'Microsoft Teams',
    'teams': 'Microsoft Teams',
    'git.exe': 'Git',
    'git': 'Git',
    'curl.exe': 'Curl',
    'curl': 'Curl',
    'dnscrypt-proxy.exe': 'DNSCrypt Proxy',
    'dnscrypt-proxy': 'DNSCrypt Proxy',
    'adguardhome.exe': 'AdGuard Home',
    'adguardhome': 'AdGuard Home',
    'unbound.exe': 'Unbound DNS',
    'unbound': 'Unbound DNS',
    'coredns.exe': 'CoreDNS',
    'coredns': 'CoreDNS',
    'stubby.exe': 'Stubby DoT',
    'stubby': 'Stubby DoT',
    'dns': 'DNS',
    'unknown (dns)': 'DNS',
}


def normalize_process_name(name: Optional[str], cmdline: Optional[list] = None, pid: Optional[int] = None) -> str:
    """Normalize process name into a canonical, human-friendly application name."""
    if not name or name == "Unknown":
        return "Unknown"
        
    name_clean = name.strip()
    name_lower = name_clean.lower()
    
    # Check NetStrip internal PID
    if pid is not None and pid == os.getpid():
        return "Cripple (Internal)"
        
    # Check canonical dictionary lookup
    if name_lower in CANONICAL_APP_NAMES:
        return CANONICAL_APP_NAMES[name_lower]
        
    # Handle scripting runtimes by inspecting command line
    if name_lower in ('python.exe', 'python3.exe', 'pythonw.exe', 'python', 'python3', 'pythonw', 'node.exe', 'node', 'java.exe', 'javaw.exe', 'ruby.exe'):
        runtime_prefix = "Python" if 'python' in name_lower else "Node.js" if 'node' in name_lower else "Java" if 'java' in name_lower else "Ruby"
        if cmdline:
            try:
                cmd_str = " ".join(cmdline).lower()
                if "antigravity" in cmd_str or "agy" in cmd_str:
                    return "AntiGravity"
                if "netstrip" in cmd_str or "cripple" in cmd_str or "main.py" in cmd_str:
                    return "Cripple (Internal)"
                if len(cmdline) > 1:
                    for arg in cmdline[1:]:
                        if not arg.startswith('-') and '.' in arg:
                            base = os.path.basename(arg)
                            if base.lower().endswith(('.py', '.js', '.jar', '.rb', '.ts', '.mjs')):
                                return f"{runtime_prefix} ({base})"
            except Exception:
                pass
        return runtime_prefix
        
    # General cleanup: strip .exe extension
    if name_lower.endswith('.exe'):
        base_name = name_clean[:-4]
        if base_name.lower() in CANONICAL_APP_NAMES:
            return CANONICAL_APP_NAMES[base_name.lower()]
        # If all lowercase, title-case nicely
        if base_name.islower():
            return base_name.title()
        return base_name
        
    return name_clean


def resolve_process_identity(proc) -> Tuple[str, str, any, str]:
    """
    Ascend the process tree to find the root parent application.
    Bypasses intermediate console windows, shell wrappers (cmd, powershell, conhost),
    and runtime wrappers to correctly attribute connections to the parent application (e.g. AntiGravity).
    
    Returns:
        (canonical_process_name, process_path, root_proc, original_exe_name)
    """
    if not proc or not psutil:
        return "Unknown", "", None, "Unknown"
        
    proc_pid = getattr(proc, 'pid', None)
    now = time.time()
    if proc_pid is not None:
        with _PID_CACHE_LOCK:
            cached = _PID_CACHE.get(proc_pid)
            if cached and (now - cached[4]) < 30.0:
                return cached[0], cached[1], cached[2], cached[3]

    original_exe = "Unknown"
    try:
        original_exe = proc.name()
    except Exception:
        pass
        
    current_proc = proc
    root_proc = proc
    cmdline = None
    
    try:
        depth = 0
        while depth < 10:
            parent = current_proc.parent()
            if not parent:
                break
                
            try:
                parent_name = parent.name().lower()
            except Exception:
                break
                
            # If parent is an OS root launcher (e.g. explorer.exe or init), stop
            if parent_name in OS_ROOT_LAUNCHERS:
                break
                
            # If parent is an intermediate console wrapper (cmd.exe, powershell.exe, conhost.exe)
            if parent_name in CONSOLE_WRAPPERS:
                try:
                    grandparent = parent.parent()
                    if grandparent:
                        gp_name = grandparent.name().lower()
                        # If grandparent is an actual application, continue traversing up!
                        if gp_name not in OS_ROOT_LAUNCHERS:
                            root_proc = grandparent
                            current_proc = grandparent
                            depth += 1
                            continue
                except Exception:
                    pass
                # Grandparent was explorer or unavailable, break here
                break
                
            root_proc = parent
            current_proc = parent
            depth += 1
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
        
    try:
        raw_name = root_proc.name()
    except Exception:
        raw_name = original_exe or "Unknown"
        
    try:
        process_path = root_proc.exe()
    except Exception:
        process_path = ""
        
    try:
        cmdline = root_proc.cmdline()
    except Exception:
        cmdline = None
        
    try:
        pid_val = root_proc.pid
    except Exception:
        pid_val = None
        
    canonical_name = normalize_process_name(raw_name, cmdline=cmdline, pid=pid_val)
    
    if raw_name.lower() == "svchost.exe" and cmdline and len(cmdline) > 2:
        if cmdline[1].lower() == "-k":
            service_group = cmdline[2]
            canonical_name = f"Service Host ({service_group})"
    
    if proc_pid is not None:
        with _PID_CACHE_LOCK:
            # Clean old entries if cache grows beyond 2000
            if len(_PID_CACHE) > 2000:
                _PID_CACHE.clear()
            _PID_CACHE[proc_pid] = (canonical_name, process_path, root_proc, original_exe, now)
            
    return canonical_name, process_path, root_proc, original_exe
