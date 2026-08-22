
def test_version():
    from netstrip import __version__
    import re
    assert re.match(r'^\d+\.\d+\.\d+$', __version__) is not None

def test_engine_import():
    from netstrip.core.engine import NetStripEngine
    assert NetStripEngine is not None

def test_classifier_import():
    from netstrip.core.classifier import TrafficClassifier
    assert TrafficClassifier is not None

def test_dns_proxy_import():
    from netstrip.core.dns_proxy import DOH_PROVIDERS
    assert len(DOH_PROVIDERS) > 0

def test_mac_randomizer_import():
    from netstrip.core.mac_randomizer import MACRandomizer
    assert MACRandomizer.is_supported() in (True, False)

def test_geoip_import():
    from netstrip.core.geoip import GeoIPService
    assert GeoIPService is not None

def test_updater_import():
    from netstrip.core.updater import BlocklistUpdater
    assert BlocklistUpdater is not None

def test_platform_support_map():
    from netstrip.gui.views.settings import SettingsView
    ps = SettingsView.PLATFORM_SUPPORT
    assert 'mac_randomization' in ps
    assert 'force_doh' in ps
    assert 'android' in ps['force_doh']
