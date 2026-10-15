"""
Platform test configuration and fixtures.
"""
import pytest
import sys
import os


def pytest_configure(config):
    """Configure pytest for platform tests."""
    # Register platform markers
    config.addinivalue_line("markers", "windows: Windows-only tests")
    config.addinivalue_line("markers", "linux: Linux-only tests")
    config.addinivalue_line("markers", "macos: macOS-only tests")
    config.addinivalue_line("markers", "android: Android-only tests")
    config.addinivalue_line("markers", "requires_root: Tests requiring root/admin")
    config.addinivalue_line("markers", "requires_network: Tests requiring network access")


def pytest_collection_modifyitems(config, items):
    """Auto-skip platform tests based on current platform."""
    current_platform = sys.platform
    
    platform_markers = {
        'win32': 'windows',
        'linux': 'linux', 
        'darwin': 'macos',
    }
    
    # Android detection
    is_android = (
        os.environ.get('NETSTRIP_ANDROID') == '1' or 
        hasattr(sys, 'getandroidapilevel')
    )
    
    for item in items:
        # Skip Windows tests on non-Windows
        if item.get_closest_marker('windows') and current_platform != 'win32':
            item.add_marker(pytest.mark.skip(reason="Windows-only test"))
        
        # Skip Linux tests on non-Linux
        if item.get_closest_marker('linux') and current_platform != 'linux':
            item.add_marker(pytest.mark.skip(reason="Linux-only test"))
        
        # Skip macOS tests on non-macOS
        if item.get_closest_marker('macos') and current_platform != 'darwin':
            item.add_marker(pytest.mark.skip(reason="macOS-only test"))
        
        # Skip Android tests on non-Android
        if item.get_closest_marker('android') and not is_android:
            item.add_marker(pytest.mark.skip(reason="Android-only test"))
        
        # Skip root-required tests if not root
        if item.get_closest_marker('requires_root'):
            if current_platform == 'win32':
                try:
                    import ctypes
                    is_admin = ctypes.windll.shell32.IsUserAnAdmin() == 1
                    if not is_admin:
                        item.add_marker(pytest.mark.skip(reason="Requires admin"))
                except Exception:
                    item.add_marker(pytest.mark.skip(reason="Cannot determine admin status"))
            else:
                if os.getuid() != 0:
                    item.add_marker(pytest.mark.skip(reason="Requires root"))


@pytest.fixture(scope="session")
def platform_info():
    """Provide platform information for tests."""
    return {
        'system': platform.system(),
        'platform': sys.platform,
        'release': platform.release(),
        'version': platform.version(),
        'machine': platform.machine(),
        'processor': platform.processor(),
        'is_64bit': sys.maxsize > 2**32,
    }


@pytest.fixture(scope="session")
def temp_db_path(tmp_path_factory):
    """Provide temporary database path for tests."""
    db_dir = tmp_path_factory.mktemp("db")
    return str(db_dir / "test_netstrip.db")


@pytest.fixture
def mock_db(temp_db_path):
    """Provide a mock database for testing."""
    from netstrip.data.database import Database
    db = Database(temp_db_path)
    yield db
    db.stop()


# Platform detection helpers
def is_windows():
    return sys.platform == "win32"

def is_linux():
    return sys.platform == "linux"

def is_macos():
    return sys.platform == "darwin"

def is_android():
    return (
        os.environ.get('NETSTRIP_ANDROID') == '1' or 
        hasattr(sys, 'getandroidapilevel')
    )


# Export helpers for test modules
pytest.is_windows = is_windows
pytest.is_linux = is_linux
pytest.is_macos = is_macos
pytest.is_android = is_android