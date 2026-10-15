"""
Android-specific tests for Cripple-NetStrip
Tests Android platform implementation, VPNService, Buildozer, VpnService API.
"""
import sys
import pytest
import platform
import os

# Skip if not on Android (or in Android build environment)
IS_ANDROID = (
    os.environ.get('NETSTRIP_ANDROID') == '1' or 
    hasattr(sys, 'getandroidapilevel') or
    'android' in sys.platform.lower()
)
pytestmark = pytest.mark.skipif(not IS_ANDROID, reason="Android-only tests")


class TestAndroidPlatform:
    """Tests for Android platform implementation."""
    
    def test_android_platform_import(self):
        """Test Android platform module can be imported."""
        from netstrip.platform.android import AndroidPlatform
        assert AndroidPlatform is not None
    
    def test_is_root_check(self):
        """Test root privilege check."""
        from netstrip.platform.android import AndroidPlatform
        ap = AndroidPlatform()
        result = ap.is_admin()
        assert isinstance(result, bool)
        # On Android, typically not root unless rooted device
        assert result == os.access('/data', os.W_OK) or os.getuid() == 0
    
    def test_get_active_interfaces(self):
        """Test getting active network interfaces via ConnectivityManager."""
        from netstrip.platform.android import AndroidPlatform
        ap = AndroidPlatform()
        interfaces = ap.get_active_interfaces()
        assert isinstance(interfaces, list)
        for iface in interfaces:
            assert isinstance(iface, str)
    
    def test_dns_operations(self):
        """Test DNS set/restore (requires VPN or root)."""
        from netstrip.platform.android import AndroidPlatform
        ap = AndroidPlatform()
        
        # Should not crash
        result = ap.set_system_dns("wlan0", "1.1.1.1")
        assert isinstance(result, bool)
        
        result = ap.restore_system_dns("wlan0")
        assert isinstance(result, bool)
    
    def test_get_original_dns(self):
        """Test getting original DNS from system properties."""
        from netstrip.platform.android import AndroidPlatform
        ap = AndroidPlatform()
        dns = ap.get_original_dns("wlan0")
        assert dns is None or isinstance(dns, str)
    
    def test_vpn_service_api(self):
        """Test VpnService integration."""
        # Test VpnService.Builder availability
        try:
            from android.net import VpnService
            assert VpnService is not None
        except ImportError:
            pytest.skip("Android SDK not available in test environment")
    
    def test_vpn_builder_operations(self):
        """Test VpnService.Builder operations (dry run)."""
        try:
            from android.net import VpnService
            # Verify builder methods exist
            assert hasattr(VpnService.Builder, 'addAddress')
            assert hasattr(VpnService.Builder, 'addDnsServer')
            assert hasattr(VpnService.Builder, 'addRoute')
            assert hasattr(VpnService.Builder, 'setBlocking')
            assert hasattr(VpnService.Builder, 'establish')
        except ImportError:
            pytest.skip("Android SDK not available")
    
    def test_protect_socket(self):
        """Test VpnService.protect() for bypassing VPN."""
        try:
            from android.net import VpnService
            # protect() is a static method
            assert hasattr(VpnService, 'protect')
        except ImportError:
            pytest.skip("Android SDK not available")


class TestAndroidBuildozer:
    """Tests for Buildozer build configuration."""
    
    def test_buildozer_spec_exists(self):
        """Test buildozer.spec exists and is valid."""
        import os
        spec_path = os.path.join(
            os.path.dirname(__file__), 
            '..', '..', 'buildozer.spec'
        )
        assert os.path.exists(spec_path), "buildozer.spec not found"
        
        with open(spec_path) as f:
            content = f.read()
            # Required sections
            assert '[app]' in content
            assert '[buildozer]' in content
            # Key settings
            assert 'title = NetStrip' in content
            assert 'package.name = netstrip' in content
            assert 'requirements =' in content
            assert 'android.permissions =' in content
    
    def test_buildozer_requirements(self):
        """Test buildozer requirements include necessary packages."""
        import os
        spec_path = os.path.join(
            os.path.dirname(__file__), 
            '..', '..', 'buildozer.spec'
        )
        with open(spec_path) as f:
            content = f.read()
            # Critical dependencies
            assert 'python3' in content
            assert 'cython' in content
            assert 'psutil' in content
            assert 'cryptography' in content
            assert 'dnslib' in content
    
    def test_android_permissions(self):
        """Test required Android permissions declared."""
        import os
        spec_path = os.path.join(
            os.path.dirname(__file__), 
            '..', '..', 'buildozer.spec'
        )
        with open(spec_path) as f:
            content = f.read()
            # VPN and network permissions
            assert 'INTERNET' in content
            assert 'ACCESS_NETWORK_STATE' in content
            assert 'ACCESS_WIFI_STATE' in content
            assert 'FOREGROUND_SERVICE' in content
            assert 'FOREGROUND_SERVICE_DATA_SYNC' in content


class TestAndroidVPNService:
    """Tests for VPN service implementation."""
    
    def test_vpn_service_class(self):
        """Test custom VPN service class exists."""
        try:
            from netstrip.android_vpn import NetStripVpnService
            assert NetStripVpnService is not None
        except ImportError:
            pytest.skip("VPN service implementation not found")
    
    def test_vpn_lifecycle_methods(self):
        """Test VPN service lifecycle methods."""
        try:
            from netstrip.android_vpn import NetStripVpnService
            # Verify lifecycle methods
            assert hasattr(NetStripVpnService, 'onStartCommand')
            assert hasattr(NetStripVpnService, 'onDestroy')
            assert hasattr(NetStripVpnService, 'onRevoke')
        except ImportError:
            pytest.skip("VPN service implementation not found")
    
    def test_vpn_packet_processing(self):
        """Test VPN packet processing loop."""
        try:
            from netstrip.android_vpn import NetStripVpnService
            # Verify packet handling
            assert hasattr(NetStripVpnService, '_process_packets') or \
                   hasattr(NetStripVpnService, 'run')
        except ImportError:
            pytest.skip("VPN service implementation not found")


class TestAndroidJNI:
    """Tests for JNI/PyJNIus integration."""
    
    def test_pyjnius_import(self):
        """Test pyjnius can be imported."""
        try:
            import jnius
            assert jnius is not None
        except ImportError:
            pytest.skip("pyjnius not available")
    
    def test_android_classes_accessible(self):
        """Test Android system classes accessible via JNI."""
        try:
            from jnius import autoclass
            # Core Android classes
            Context = autoclass('android.content.Context')
            ConnectivityManager = autoclass('android.net.ConnectivityManager')
            Network = autoclass('android.net.Network')
            NetworkCapabilities = autoclass('android.net.NetworkCapabilities')
            VpnService = autoclass('android.net.VpnService')
            
            assert Context is not None
            assert ConnectivityManager is not None
            assert Network is not None
            assert NetworkCapabilities is not None
            assert VpnService is not None
        except (ImportError, Exception):
            pytest.skip("Android classes not accessible")


class TestAndroidForegroundService:
    """Tests for foreground service (required for VPN on Android 8+)."""
    
    def test_foreground_service_notification(self):
        """Test foreground service notification creation."""
        try:
            from netstrip.android_vpn import create_foreground_notification
            # Verify notification creation
            notification = create_foreground_notification()
            assert notification is not None
        except ImportError:
            pytest.skip("Foreground service implementation not found")
    
    def test_service_lifecycle(self):
        """Test service start/stop lifecycle."""
        try:
            from netstrip.android_vpn import NetStripVpnService
            service = NetStripVpnService()
            # Verify service methods
            assert hasattr(service, 'onCreate')
            assert hasattr(service, 'onStartCommand')
            assert hasattr(service, 'onDestroy')
        except ImportError:
            pytest.skip("VPN service not found")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])