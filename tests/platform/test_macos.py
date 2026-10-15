"""
macOS-specific tests for Cripple-NetStrip
Tests macOS platform implementation, pfctl, NetworkExtension, launchd.
"""
import sys
import pytest
import platform

# Skip if not on macOS
pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="macOS-only tests")


class TestMacOSPlatform:
    """Tests for macOS platform implementation."""
    
    def test_macos_platform_import(self):
        """Test macOS platform module can be imported."""
        from netstrip.platform.macos import MacOSPlatform
        assert MacOSPlatform is not None
    
    def test_is_admin_check(self):
        """Test admin/root privilege check."""
        from netstrip.platform.macos import MacOSPlatform
        mp = MacOSPlatform()
        result = mp.is_admin()
        assert isinstance(result, bool)
        import os
        assert result == (os.getuid() == 0)
    
    def test_get_active_interfaces(self):
        """Test getting active network interfaces via networksetup."""
        from netstrip.platform.macos import MacOSPlatform
        mp = MacOSPlatform()
        interfaces = mp.get_active_interfaces()
        assert isinstance(interfaces, list)
        for iface in interfaces:
            assert isinstance(iface, str)
    
    def test_dns_operations(self):
        """Test DNS set/restore via networksetup."""
        from netstrip.platform.macos import MacOSPlatform
        mp = MacOSPlatform()
        
        # Test with dummy interface
        result = mp.set_system_dns("Wi-Fi", "1.1.1.1")
        assert isinstance(result, bool)
        
        result = mp.restore_system_dns("Wi-Fi")
        assert isinstance(result, bool)
    
    def test_get_original_dns(self):
        """Test getting original DNS."""
        from netstrip.platform.macos import MacOSPlatform
        mp = MacOSPlatform()
        dns = mp.get_original_dns("Wi-Fi")
        assert dns is None or isinstance(dns, str)
    
    def test_disable_ipv6(self):
        """Test IPv6 disable/enable via networksetup."""
        from netstrip.platform.macos import MacOSPlatform
        mp = MacOSPlatform()
        
        result = mp.disable_ipv6()
        assert isinstance(result, bool)
        
        result = mp.enable_ipv6()
        assert isinstance(result, bool)
    
    def test_harden_network_adapters(self):
        """Test network adapter protocol hardening."""
        from netstrip.platform.macos import MacOSPlatform
        mp = MacOSPlatform()
        
        # Should not crash
        result = mp.harden_network_adapters(enable_hardening=True)
        assert isinstance(result, bool)
        
        result = mp.harden_network_adapters(enable_hardening=False)
        assert isinstance(result, bool)


class TestMacOSPfctl:
    """Tests for pfctl (packet filter) integration."""
    
    def test_pfctl_available(self):
        """Test pfctl is available on macOS."""
        import subprocess
        result = subprocess.run(['pfctl', '-v'], capture_output=True)
        # pfctl exists but may require root for -v
        assert result.returncode in (0, 1)  # 1 = permission denied, OK
    
    def test_pf_anchor_operations(self):
        """Test pf anchor operations (dry run)."""
        from netstrip.platform.macos import MacOSPlatform
        mp = MacOSPlatform()
        
        # Verify pfctl methods exist
        assert hasattr(mp, '_run_pfctl') or hasattr(mp, '_pfctl')
    
    def test_pf_rules_syntax(self):
        """Test PF rules syntax generation."""
        # This would test the PF rules template
        import os
        pf_path = os.path.join(
            os.path.dirname(__file__), 
            '..', '..', 'netstrip', 'data', 'netstrip.pf.conf'
        )
        if not os.path.exists(pf_path):
            pytest.skip("PF config template not found")
        
        with open(pf_path) as f:
            content = f.read()
            # Basic PF syntax checks
            assert 'block' in content.lower() or 'pass' in content.lower()
            assert 'anchor' in content.lower() or 'rdr' in content.lower()


class TestMacOSNetworkExtension:
    """Tests for NetworkExtension framework (if available)."""
    
    def test_networkextension_import(self):
        """Test NetworkExtension can be imported (PyObjC)."""
        try:
            import NetworkExtension
            assert NetworkExtension is not None
        except ImportError:
            pytest.skip("PyObjC/NetworkExtension not available")
    
    def test_neutron_agent_import(self):
        """Test NEAgent/NEFilterManager availability."""
        try:
            from NetworkExtension import NEFilterManager
            assert NEFilterManager is not None
        except ImportError:
            pytest.skip("NetworkExtension NEFilterManager not available")


class TestMacOSLaunchd:
    """Tests for launchd service integration."""
    
    def test_plist_generation(self):
        """Test launchd plist generation."""
        import os
        plist_path = os.path.join(
            os.path.dirname(__file__), 
            '..', '..', 'netstrip', 'data', 'com.cripple.netstrip.plist'
        )
        if not os.path.exists(plist_path):
            pytest.skip("launchd plist template not found")
        
        import plistlib
        with open(plist_path, 'rb') as f:
            plist = plistlib.load(f)
            assert 'Label' in plist
            assert 'ProgramArguments' in plist
            assert 'RunAtLoad' in plist
            assert plist['Label'] == 'com.cripple.netstrip'
    
    def test_launchctl_operations(self):
        """Test launchctl load/unload (dry run)."""
        from netstrip.platform.macos import MacOSPlatform
        mp = MacOSPlatform()
        
        # Verify methods exist
        assert hasattr(mp, 'install_autostart') or hasattr(mp, '_install_launchd')
        assert hasattr(mp, 'uninstall_autostart') or hasattr(mp, '_uninstall_launchd')


class TestMacOSFirewall:
    """Tests for macOS firewall integration."""
    
    def test_firewall_controller_macos(self):
        """Test firewall controller on macOS."""
        from netstrip.core.firewall import FirewallController
        fc = FirewallController()
        
        # Verify macOS-specific methods
        assert hasattr(fc, 'block_ip')
        assert hasattr(fc, 'unblock_ip')
        assert hasattr(fc, 'block_process')
        assert hasattr(fc, 'allow_process')
    
    def test_application_firewall(self):
        """Test Application Firewall (socketfilterfw) integration."""
        import subprocess
        result = subprocess.run(
            ['/usr/libexec/ApplicationFirewall/socketfilterfw', '--getglobalstate'],
            capture_output=True
        )
        # Command exists but may require root
        assert result.returncode in (0, 1, 2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])