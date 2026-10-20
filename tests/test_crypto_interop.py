"""
Crypto backend interoperability + correctness tests.

Guarantees that tokens produced by the vetted native backend (cryptography
lib / OpenSSL) and the pure-Python WDAC-fallback backend are fully
interchangeable — peers never need to agree on a backend.
"""

import time

import pytest

from netstrip.core.crypto_utils import (
    _NATIVE_AVAILABLE,
    InvalidToken,
    QuantumFernet,
)

MSG = b'LAN_KILLSWITCH_TRIGGER {"nonce":"abc","ts":1690000000}'


@pytest.fixture()
def keys():
    return {
        "native64": QuantumFernet.generate_key(),                 # 64-byte key
        "legacy32": QuantumFernet.generate_key(native_pq=False),  # 32-byte key
    }


def test_native_backend_present_or_skipped():
    # Informational: on dev/CI machines cryptography is installed; the
    # pure-python fallback path is still exercised via prefer_native=False.
    print("native available:", _NATIVE_AVAILABLE)


def test_roundtrip_both_backends(keys):
    qn = QuantumFernet(keys["native64"])                       # native preferred
    qp = QuantumFernet(keys["native64"], prefer_native=False)  # forced fallback
    assert qp.decrypt(qn.encrypt(MSG)) == MSG
    assert qn.decrypt(qp.encrypt(MSG)) == MSG


def test_cross_backend_legacy_32byte_keys(keys):
    l_native = QuantumFernet(keys["legacy32"])
    l_pure = QuantumFernet(keys["legacy32"], prefer_native=False)
    token = l_pure.encrypt("hello")
    assert l_native.decrypt(token) == b"hello"
    assert l_pure.decrypt(l_native.encrypt(b"hello")) == b"hello"


def test_tamper_detected_on_both_backends(keys):
    for fernet in (
        QuantumFernet(keys["native64"]),
        QuantumFernet(keys["native64"], prefer_native=False),
    ):
        raw = bytearray(fernet.encrypt(MSG))
        raw[-3] ^= 0xFF
        with pytest.raises(InvalidToken):
            fernet.decrypt(bytes(raw))


def test_ttl_expiry_enforced(keys):
    f = QuantumFernet(keys["native64"])
    tok = f.encrypt(MSG)
    time.sleep(1.1)
    with pytest.raises(InvalidToken):
        f.decrypt(tok, ttl=1)


def test_str_payload_and_unicode_roundtrip(keys):
    f = QuantumFernet(keys["native64"])
    payload = "thréat 🚨 ünicode"
    assert f.decrypt(f.encrypt(payload)).decode("utf-8") == payload


def test_invalid_key_lengths_rejected():
    import base64
    for bad_len in (16, 48, 96):
        with pytest.raises(ValueError):
            QuantumFernet(base64.urlsafe_b64encode(b"\x01" * bad_len))


def test_native_path_is_actually_used_when_available(keys):
    """Guard against prefer_native silently becoming a no-op.

    The flag advertises a native (OpenSSL) fast path. If that wiring is ever
    lost, tokens still round-trip (pure Python is a correct fallback), so no
    behavioural test would notice — only this one. It asserts the native
    primitives are invoked when the backend is present and requested.
    """
    from netstrip.core import crypto_utils

    if not crypto_utils._NATIVE_AVAILABLE:
        pytest.skip("cryptography backend not installed")
    native = QuantumFernet(keys["native64"])
    assert native.prefer_native is True
    # Route through the class hook and confirm the native implementation ran.
    calls = {"n": 0}
    real = native._native_cbc_encrypt
    native._native_cbc_encrypt = lambda d, iv: (calls.__setitem__("n", calls["n"] + 1), real(d, iv))[1]
    native.encrypt(MSG)
    assert calls["n"] == 1
    # And that a forced-fallback instance never reaches it.
    forced = QuantumFernet(keys["native64"], prefer_native=False)
    assert forced.prefer_native is False
    forced_calls = {"n": 0}
    forced._native_cbc_encrypt = lambda d, iv: (forced_calls.__setitem__("n", forced_calls["n"] + 1), None)[1]
    token = forced.encrypt(MSG)
    assert forced_calls["n"] == 0
    assert native.decrypt(token) == MSG


def test_native_and_pure_ciphertexts_are_byte_identical(keys):
    """Same key+IV must yield identical AES-CBC output on both backends.

    This is the property that makes peers backend-agnostic; it is checked
    directly on the primitives so a future divergence fails loudly here.
    """
    from netstrip.core import crypto_utils

    if not crypto_utils._NATIVE_AVAILABLE:
        pytest.skip("cryptography backend not installed")
    key = QuantumFernet(keys["native64"])._encryption_key
    iv = bytes(range(16))
    native = QuantumFernet(keys["native64"])
    for sample in (b"", b"a", b"x" * 15, b"y" * 16, bytes(range(256))):
        assert native._native_cbc_encrypt(sample, iv) == crypto_utils.aes_256_cbc_encrypt(sample, key, iv)
        ct = crypto_utils.aes_256_cbc_encrypt(sample, key, iv)
        assert native._native_cbc_decrypt(ct, iv) == sample
