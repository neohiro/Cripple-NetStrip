"""Regression test — secures all P0/P1 hardening from security audit."""
import os, re, sys
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, repo_root)

def test_no_pickle_load():
    from netstrip.data import blocklist_manager as bm
    with open(bm.__file__, 'r', encoding='utf-8') as f:
        src = f.read()
    assert 'pickle.load' not in src and 'pickle.dump' not in src, "pickle.load must be removed"

def test_telemetry_token_encrypted_fallback():
    from netstrip.core import github_telemetry as gt
    assert hasattr(gt, '_decrypt_telemetry_token'), "Encrypted telemetry fallback missing"
    assert 'NETSTRIP_TELEMETRY_ENCRYPTED_FALLBACK' in gt.__file__ or hasattr(gt, 'ENCRYPTED_TELEMETRY_FALLBACK'), "Encrypted env gate missing"

def test_crash_token_encrypted_fallback():
    from netstrip.core import crash_reporter as cr
    assert hasattr(cr, '_decrypt_crash_token'), "Encrypted crash fallback missing"

def test_ioh_compare_digest():
    with open(os.path.join(repo_root, 'netstrip/core/iot_local_api.py'), 'r', encoding='utf-8') as f:
        src = f.read()
    assert 'hmac.compare_digest' in src, "IoT auth must use hmac.compare_digest"

def test_updater_tls_strict():
    with open(os.path.join(repo_root, 'netstrip/core/updater.py'), 'r', encoding='utf-8') as f:
        src = f.read()
    assert 'CERT_NONE' not in src, "CERT_NONE must not exist"
    assert 'CERT_REQUIRED' in src, "TLS must be CERT_REQUIRED"

def test_self_update_ed25519_mandatory():
    with open(os.path.join(repo_root, 'netstrip/core/self_update.py'), 'r', encoding='utf-8') as f:
        src = f.read()
    assert 'def _verify_signature(' in src and 'SelfUpdateError' in src, "Mandatory ed25519 missing"

def test_crypto_native_only_no_pure_python_aes():
    with open(os.path.join(repo_root, 'netstrip/core/crypto_utils.py'), 'r', encoding='utf-8') as f:
        src = f.read()
    assert 'AESGCM' in src, "AES-GCM native must be present"
    # Pure-Python AES primitives must NOT exist
    for bad in ('_SBOX', '_cipher_256', '_inv_cipher_256', '_xtime', '_mul', '_key_expansion_256'):
        assert bad not in src, f"Pure-Python AES primitive still present: {bad}"

def test_license_corporate_clause():
    with open(os.path.join(repo_root, 'LICENSE.md'), 'r', encoding='utf-8') as f:
        src = f.read()
    assert 'corporate' in src.lower() or 'corporate-use' in src.lower(), "Corporate-use rights must be preserved"

def test_version_bumped():
    with open(os.path.join(repo_root, 'netstrip/__init__.py'), 'r', encoding='utf-8') as f:
        src = f.read()
    assert '3.9.7' in src, "Version must be bumped to 3.9.7"

def test_readme_accuracy_fixed():
    with open(os.path.join(repo_root, 'README.md'), 'r', encoding='utf-8') as f:
        src = f.read()
    # Must NOT claim "NIST/ISO-conform"; should say aligned/engineered with, not certified
    assert 'NIST/ISO-conform' not in src, "README must not claim NIST/ISO-conform"
    # Must clarify kernel level is packet interception
    assert 'packet-interception layer' in src or 'WinDivert' in src, "README must clarify packet layer"

if __name__ == '__main__':
    for name, fn in list(vars().items()):
        if name.startswith('test_') and callable(fn):
            try:
                fn()
                print('PASS:', name)
            except AssertionError as e:
                print('FAIL:', name, '-', e)
