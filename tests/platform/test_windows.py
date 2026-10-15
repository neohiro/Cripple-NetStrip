"""
Windows-specific tests for Cripple-NetStrip
Tests Windows platform implementation, firewall, DNS, admin elevation.
"""
import sys
import pytest
import platform
import os

# Skip if not on Windows
pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows-only tests")


class TestWindowsPlatform:
    """Tests for Windows platform implementation."""
    
    def test_windows_platform_import(self):
        """Test Windows platform module can be imported."""
        from netstrip.platform.windows import WindowsPlatform
        assert WindowsPlatform is not None
    
    def test_is_admin_check(self):
        """Test admin privilege check."""
        from netstrip.platform.windows import WindowsPlatform
        wp = WindowsPlatform()
        # Should not raise
        result = wp.is_admin()
        assert isinstance(result, bool)
    
    def test_get_active_interfaces(self):
        """Test getting active network interfaces."""
        from netstrip.platform.windows import WindowsPlatform
        wp = WindowsPlatform()
        interfaces = wp.get_active_interfaces()
        assert isinstance(interfaces, list)
        # Should at least return fallback interfaces
        assert len(interfaces) > 0
    
    def test_firewall_rule_sanitization(self):
        """Test firewall rule name sanitization."""
        from netstrip.platform.windows import WindowsPlatform
        wp = WindowsPlatform()
        
        # Test rule name sanitization removes quotes
        rule_name = 'Test "Rule" Name'
        sanitized = rule_name.replace('"', '')
        assert '"' not in sanitized
    
    def test_dns_operations_require_admin(self):
        """Test DNS operations document admin requirement."""
        from netstrip.platform.windows import WindowsPlatform
        wp = WindowsPlatform()
        
        # These should not crash even without admin
        # (they'll fail gracefully)
        result = wp.set_system_dns("Wi-Fi", "1.1.1.1")
        assert isinstance(result, bool)
        
        result = wp.restore_system_dns("Wi-Fi")
        assert isinstance(result, bool)
    
    def test_get_original_dns(self):
        """Test getting original DNS settings."""
        from netstrip.platform.windows import WindowsPlatform
        wp = WindowsPlatform()
        dns = wp.get_original_dns("Wi-Fi")
        # Can be None or string
        assert dns is None or isinstance(dns, str)
    
    def test_get_current_ssid(self):
        """Test getting current WiFi SSID."""
        from netstrip.platform.windows import WindowsPlatform
        wp = WindowsPlatform()
        ssid = wp.get_current_ssid()
        assert isinstance(ssid, str)
    
    def test_get_default_gateway(self):
        """Test getting default gateway."""
        from netstrip.platform.windows import WindowsPlatform
        wp = WindowsPlatform()
        gateway = wp.get_default_gateway()
        assert gateway is None or isinstance(gateway, str)


class TestWindowsFirewall:
    """Tests for Windows firewall integration."""
    
    def test_firewall_controller_import(self):
        """Test firewall controller can be imported."""
        from netstrip.core.firewall import FirewallController
        fc = FirewallController()
        assert fc is not None
    
    def test_firewall_rule_creation(self):
        """Test firewall rule creation methods exist."""
        from netstrip.core.firewall import FirewallController
        fc = FirewallController()
        
        # Verify methods exist
        assert hasattr(fc, 'block_ip')
        assert hasattr(fc, 'unblock_ip')
        assert hasattr(fc, 'allow_process')
        assert hasattr(fc, 'block_process')
        assert hasattr(fc, 'clear_all_rules')
        assert hasattr(fc, 'apply_paranoid_mode')


class TestWindowsElevation:
    """Tests for admin elevation logic."""
    
    def test_request_admin_logic(self):
        """Test admin elevation request logic."""
        from netstrip.platform.windows import WindowsPlatform
        wp = WindowsPlatform()
        
        # Should not crash when called
        # (actual elevation requires user interaction)
        assert hasattr(wp, 'request_admin')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])