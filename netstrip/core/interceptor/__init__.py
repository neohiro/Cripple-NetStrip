import platform
from typing import Callable
from netstrip.core.interceptor.base import PacketInterceptor

def get_interceptor(callback: Callable[[str, int, str, int, str], bool], engine=None) -> PacketInterceptor:
    import os
    is_android = os.environ.get('NETSTRIP_ANDROID') == '1'
    if is_android:
        from netstrip.core.interceptor.android import AndroidVPNInterceptor
        return AndroidVPNInterceptor(callback, engine=engine)
        
    system = platform.system()
    if system == "Windows":
        from netstrip.core.interceptor.windows import WinDivertInterceptor
        return WinDivertInterceptor(callback, engine=engine)
    elif system == "Linux":
        from netstrip.core.interceptor.linux import LinuxNFQueueInterceptor
        return LinuxNFQueueInterceptor(callback)
    elif system == "Darwin":
        from netstrip.core.interceptor.macos import MacOSPFInterceptor
        return MacOSPFInterceptor(callback)
    else:
        # Fallback dummy
        from netstrip.core.interceptor.base import PacketInterceptor
        class DummyInterceptor(PacketInterceptor):
            def start(self): pass
            def stop(self): pass
        return DummyInterceptor(callback)
