"""
Linux-specific tests for Cripple-NetStrip
Tests Linux platform implementation, eBPF, iptables/nftables, systemd.
"""
import sys
import pytest
import platform

# Skip if not on Linux
pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="Linux-only tests")


class TestLinuxPlatform:
    """Tests for Linux platform implementation."""
    
    def test_linux_platform_import(self):
        """Test Linux platform module can be imported."""
        from netstrip.platform.linux import LinuxPlatform
        assert LinuxPlatform is not None
    
    def test_is_root_check(self):
        """Test root privilege check."""
        from netstrip.platform.linux import LinuxPlatform
        lp = LinuxPlatform()
        result = lp.is_admin()
        assert isinstance(result, bool)
        # Should match os.getuid() == 0
        assert result == (os.getuid() == 0)
    
    def test_get_active_interfaces(self):
        """Test getting active network interfaces."""
        from netstrip.platform.linux import LinuxPlatform
        lp = LinuxPlatform()
        interfaces = lp.get_active_interfaces()
        assert isinstance(interfaces, list)
        # Should return interface names
        for iface in interfaces:
            assert isinstance(iface, str)
            assert len(iface) > 0
    
    def test_dns_operations(self):
        """Test DNS set/restore operations."""
        from netstrip.platform.linux import LinuxPlatform
        lp = LinuxPlatform()
        
        # Test with a dummy interface
        # Should not crash even if interface doesn't exist
        result = lp.set_system_dns("dummy0", "1.1.1.1")
        assert isinstance(result, bool)
        
        result = lp.restore_system_dns("dummy0")
        assert isinstance(result, bool)
    
    def test_get_original_dns(self):
        """Test getting original DNS from systemd-resolved or resolv.conf."""
        from netstrip.platform.linux import LinuxPlatform
        lp = LinuxPlatform()
        
        # Get DNS for a common interface
        dns = lp.get_original_dns("eth0")
        assert dns is None or isinstance(dns, str)
    
    def test_disable_ipv6(self):
        """Test IPv6 disable/enable."""
        from netstrip.platform.linux import LinuxPlatform
        lp = LinuxPlatform()
        
        # These may fail without proper permissions but shouldn't crash
        result = lp.disable_ipv6()
        assert isinstance(result, bool)
        
        result = lp.enable_ipv6()
        assert isinstance(result, bool)
    
    def test_harden_network_adapters(self):
        """Test network adapter hardening (sysctl/proc)."""
        from netstrip.platform.linux import LinuxPlatform
        lp = LinuxPlatform()
        
        # Should not crash
        result = lp.harden_network_adapters(enable_hardening=True)
        assert isinstance(result, bool)
        
        result = lp.harden_network_adapters(enable_hardening=False)
        assert isinstance(result, bool)


class TestLinuxEBPF:
    """Tests for eBPF/XDP integration."""
    
    def test_ebpf_manager_import(self):
        """Test eBPF manager can be imported."""
        try:
            from netstrip.platform.linux_ebpf import EBPFManager
            assert EBPFManager is not None
        except ImportError:
            pytest.skip("eBPF dependencies not available")
    
    def test_ebpf_monitor_import(self):
        """Test eBPF monitor can be imported."""
        try:
            from netstrip.core.linux_ebpf_monitor import EBPFMonitor
            assert EBPFMonitor is not None
        except ImportError:
            pytest.skip("eBPF dependencies not available")
    
    def test_ebpf_program_compilation(self):
        """Test eBPF C program syntax (if clang available)."""
        import subprocess
        import os
        
        ebpf_path = os.path.join(
            os.path.dirname(__file__), 
            '..', '..', 'netstrip', 'core', 'ebpf', 'xdp_filter.c'
        )
        
        if not os.path.exists(ebpf_path):
            pytest.skip("eBPF source not found")
        
        # Check if clang is available for compilation test
        try:
            result = subprocess.run(
                ['clang', '--version'], 
                capture_output=True, timeout=5
            )
            if result.returncode != 0:
                pytest.skip("clang not available")
        except FileNotFoundError:
            pytest.skip("clang not available")
        
        # Try to compile (syntax check only)
        result = subprocess.run(
            ['clang', '-target', 'bpf', '-O2', '-c', ebpf_path, '-o', '/dev/null'],
            capture_output=True, timeout=30
        )
        # Should compile without errors
        assert result.returncode == 0, f"eBPF compilation failed: {result.stderr.decode()}"


class TestLinuxSystemd:
    """Tests for systemd integration."""
    
    def test_service_file_generation(self):
        """Test systemd service file can be generated."""
        # This would test the service template
        # For now just verify the template exists
        import os
        service_path = os.path.join(
            os.path.dirname(__file__), 
            '..', '..', 'netstrip', 'data', 'netstrip.service'
        )
        # Service file might not exist yet - skip if missing
        if not os.path.exists(service_path):
            pytest.skip("systemd service template not found")
        
        with open(service_path) as f:
            content = f.read()
            assert '[Unit]' in content
            assert '[Service]' in content
            assert '[Install]' in content
            assert 'ExecStart=' in content
    
    def test_sysctl_configuration(self):
        """Test sysctl hardening values."""
        from netstrip.platform.linux import LinuxPlatform
        lp = LinuxPlatform()
        
        # Test that hardening applies sysctl settings
        # We can't easily test actual sysctl changes without root
        # but we can verify the method exists
        assert hasattr(lp, 'harden_network_adapters')


class TestLinuxNftables:
    """Tests for nftables/iptables integration."""
    
    def test_firewall_controller_linux(self):
        """Test firewall controller on Linux."""
        from netstrip.core.firewall import FirewallController
        fc = FirewallController()
        
        # Verify Linux-specific methods
        assert hasattr(fc, 'block_ip')
        assert hasattr(fc, 'unblock_ip')
        assert hasattr(fc, 'sync_ip_blocklist')
        assert hasattr(fc, 'apply_paranoid_mode')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])