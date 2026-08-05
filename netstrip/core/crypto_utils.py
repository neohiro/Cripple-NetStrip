"""
Crypto Utilities for NetStrip
Provides 100% pure-Python fallback for Fernet symmetric encryption and key generation.
Guarantees zero crashes on systems with strict Windows Defender Application Control (WDAC),
AppLocker, or missing _cffi_backend DLLs.
"""

import os
import struct
import time
import base64
import hmac
import hashlib
import logging

logger = logging.getLogger(__name__)

# Rijndael S-Box and Inverse S-Box for AES-128
_SBOX = [
    0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5, 0x30, 0x01, 0x67, 0x2b, 0xfe, 0xd7, 0xab, 0x76,
    0xca, 0x82, 0xc9, 0x7d, 0xfa, 0x59, 0x47, 0xf0, 0xad, 0xd4, 0xa2, 0xaf, 0x9c, 0xa4, 0x72, 0xc0,
    0xb7, 0xfd, 0x93, 0x26, 0x36, 0x3f, 0xf7, 0xcc, 0x34, 0xa5, 0xe5, 0xf1, 0x71, 0xd8, 0x31, 0x15,
    0x04, 0xc7, 0x23, 0xc3, 0x18, 0x96, 0x05, 0x9a, 0x07, 0x12, 0x80, 0xe2, 0xeb, 0x27, 0xb2, 0x75,
    0x09, 0x83, 0x2c, 0x1a, 0x1b, 0x6e, 0x5a, 0xa0, 0x52, 0x3b, 0xd6, 0xb3, 0x29, 0xe3, 0x2f, 0x84,
    0x53, 0xd1, 0x00, 0xed, 0x20, 0xfc, 0xb1, 0x5b, 0x6a, 0xcb, 0xbe, 0x39, 0x4a, 0x4c, 0x58, 0xcf,
    0xd0, 0xef, 0xaa, 0xfb, 0x43, 0x4d, 0x33, 0x85, 0x45, 0xf9, 0x02, 0x7f, 0x50, 0x3c, 0x9f, 0xa8,
    0x51, 0xa3, 0x40, 0x8f, 0x92, 0x9d, 0x38, 0xf5, 0xbc, 0xb6, 0xda, 0x21, 0x10, 0xff, 0xf3, 0xd2,
    0xcd, 0x0c, 0x13, 0xec, 0x5f, 0x97, 0x44, 0x17, 0xc4, 0xa7, 0x7e, 0x3d, 0x64, 0x5d, 0x19, 0x73,
    0x60, 0x81, 0x4f, 0xdc, 0x22, 0x2a, 0x90, 0x88, 0x46, 0xee, 0xb8, 0x14, 0xde, 0x5e, 0x0b, 0xdb,
    0xe0, 0x32, 0x3a, 0x0a, 0x49, 0x06, 0x24, 0x5c, 0xc2, 0xd3, 0xac, 0x62, 0x91, 0x95, 0xe4, 0x79,
    0xe7, 0xc8, 0x37, 0x6d, 0x8d, 0xd5, 0x4e, 0xa9, 0x6c, 0x56, 0xf4, 0xea, 0x65, 0x7a, 0xae, 0x08,
    0xba, 0x78, 0x25, 0x2e, 0x1c, 0xa6, 0xb4, 0xc6, 0xe8, 0xdd, 0x74, 0x1f, 0x4b, 0xbd, 0x8b, 0x8a,
    0x70, 0x3e, 0xb5, 0x66, 0x48, 0x03, 0xf6, 0x0e, 0x61, 0x35, 0x57, 0xb9, 0x86, 0xc1, 0x1d, 0x9e,
    0xe1, 0xf8, 0x98, 0x11, 0x69, 0xd9, 0x8e, 0x94, 0x9b, 0x1e, 0x87, 0xe9, 0xce, 0x55, 0x28, 0xdf,
    0x8c, 0xa1, 0x89, 0x0d, 0xbf, 0xe6, 0x42, 0x68, 0x41, 0x99, 0x2d, 0x0f, 0xb0, 0x54, 0xbb, 0x16
]

_INV_SBOX = [0] * 256
for _i, _v in enumerate(_SBOX):
    _INV_SBOX[_v] = _i

_RCON = [0x00, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36]

def _xtime(a):
    return ((a << 1) ^ 0x1b) & 0xff if (a & 0x80) else (a << 1)

def _mul(a, b):
    p = 0
    for _ in range(8):
        if b & 1:
            p ^= a
        a = _xtime(a)
        b >>= 1
    return p

def _key_expansion(key):
    w = list(key)
    for i in range(4, 44):
        tmp = w[(i-1)*4 : i*4]
        if i % 4 == 0:
            tmp = [_SBOX[tmp[1]], _SBOX[tmp[2]], _SBOX[tmp[3]], _SBOX[tmp[0]]]
            tmp[0] ^= _RCON[i // 4]
        for j in range(4):
            w.append(w[(i-4)*4 + j] ^ tmp[j])
    return w

def _cipher(block, w):
    state = list(block)
    for i in range(16):
        state[i] ^= w[i]
    for r in range(1, 10):
        state = [_SBOX[b] for b in state]
        state = [
            state[0], state[5], state[10], state[15],
            state[4], state[9], state[14], state[3],
            state[8], state[13], state[2], state[7],
            state[12], state[1], state[6], state[11]
        ]
        ns = [0] * 16
        for c in range(4):
            c0, c1, c2, c3 = state[c*4 : c*4+4]
            ns[c*4]   = _mul(2, c0) ^ _mul(3, c1) ^ c2 ^ c3
            ns[c*4+1] = c0 ^ _mul(2, c1) ^ _mul(3, c2) ^ c3
            ns[c*4+2] = c0 ^ c1 ^ _mul(2, c2) ^ _mul(3, c3)
            ns[c*4+3] = _mul(3, c0) ^ c1 ^ c2 ^ _mul(2, c3)
        state = ns
        rw = w[r*16 : (r+1)*16]
        for i in range(16):
            state[i] ^= rw[i]
    state = [_SBOX[b] for b in state]
    state = [
        state[0], state[5], state[10], state[15],
        state[4], state[9], state[14], state[3],
        state[8], state[13], state[2], state[7],
        state[12], state[1], state[6], state[11]
    ]
    for i in range(16):
        state[i] ^= w[160 + i]
    return bytes(state)

def _inv_cipher(block, w):
    state = list(block)
    for i in range(16):
        state[i] ^= w[160 + i]
    for r in range(9, 0, -1):
        state = [
            state[0], state[13], state[10], state[7],
            state[4], state[1], state[14], state[11],
            state[8], state[5], state[2], state[15],
            state[12], state[9], state[6], state[3]
        ]
        state = [_INV_SBOX[b] for b in state]
        rw = w[r*16 : (r+1)*16]
        for i in range(16):
            state[i] ^= rw[i]
        ns = [0] * 16
        for c in range(4):
            c0, c1, c2, c3 = state[c*4 : c*4+4]
            ns[c*4]   = _mul(14, c0) ^ _mul(11, c1) ^ _mul(13, c2) ^ _mul(9, c3)
            ns[c*4+1] = _mul(9, c0)  ^ _mul(14, c1) ^ _mul(11, c2) ^ _mul(13, c3)
            ns[c*4+2] = _mul(13, c0) ^ _mul(9, c1)  ^ _mul(14, c2) ^ _mul(11, c3)
            ns[c*4+3] = _mul(11, c0) ^ _mul(13, c1) ^ _mul(9, c2)  ^ _mul(14, c3)
        state = ns
    state = [
        state[0], state[13], state[10], state[7],
        state[4], state[1], state[14], state[11],
        state[8], state[5], state[2], state[15],
        state[12], state[9], state[6], state[3]
    ]
    state = [_INV_SBOX[b] for b in state]
    for i in range(16):
        state[i] ^= w[i]
    return bytes(state)

def _aes_cbc_encrypt(data: bytes, key: bytes, iv: bytes) -> bytes:
    pad_len = 16 - (len(data) % 16)
    padded = data + bytes([pad_len] * pad_len)
    w = _key_expansion(key)
    out = bytearray()
    prev = iv
    for i in range(0, len(padded), 16):
        blk = bytes(a ^ b for a, b in zip(padded[i:i+16], prev))
        enc = _cipher(blk, w)
        out.extend(enc)
        prev = enc
    return bytes(out)

def _aes_cbc_decrypt(data: bytes, key: bytes, iv: bytes) -> bytes:
    if len(data) % 16 != 0:
        raise ValueError("Ciphertext length must be a multiple of 16")
    w = _key_expansion(key)
    out = bytearray()
    prev = iv
    for i in range(0, len(data), 16):
        blk = data[i:i+16]
        dec = _inv_cipher(blk, w)
        out.extend(bytes(a ^ b for a, b in zip(dec, prev)))
        prev = blk
    if not out:
        raise ValueError("Decrypted output is empty")
    pad_len = out[-1]
    if pad_len < 1 or pad_len > 16:
        raise ValueError("Invalid PKCS7 padding")
    if out[-pad_len:] != bytes([pad_len] * pad_len):
        raise ValueError("Invalid PKCS7 padding")
    return bytes(out[:-pad_len])

class InvalidToken(Exception):
    """Raised when a Fernet token is invalid, corrupted, or expired."""
    pass

class PureFernet:
    """Pure-Python implementation of the Fernet symmetric encryption standard.
    Requires zero external C binaries or DLLs, preventing AppLocker/WDAC blocking.
    """
    def __init__(self, key):
        if isinstance(key, str):
            key = key.encode('utf-8')
        try:
            key_bytes = base64.urlsafe_b64decode(key)
        except Exception as e:
            raise ValueError(f"Invalid Fernet key encoding: {e}")
        if len(key_bytes) != 32:
            raise ValueError(f"Fernet key must be 32 url-safe base64 decoded bytes, got {len(key_bytes)}")
        self._signing_key = key_bytes[:16]
        self._encryption_key = key_bytes[16:]

    @classmethod
    def generate_key(cls) -> bytes:
        return base64.urlsafe_b64encode(os.urandom(32))

    def encrypt(self, data) -> bytes:
        if isinstance(data, str):
            data = data.encode('utf-8')
        current_time = int(time.time())
        iv = os.urandom(16)
        ciphertext = _aes_cbc_encrypt(data, self._encryption_key, iv)
        basic_parts = b'\x80' + struct.pack('>Q', current_time) + iv + ciphertext
        mac = hmac.new(self._signing_key, basic_parts, hashlib.sha256).digest()
        return base64.urlsafe_b64encode(basic_parts + mac)

    def decrypt(self, token, ttl: int = None) -> bytes:
        if isinstance(token, str):
            token = token.encode('utf-8')
        try:
            raw = base64.urlsafe_b64decode(token)
        except Exception:
            raise InvalidToken("Malformed base64 token")
        if len(raw) < 57 or raw[0] != 0x80:
            raise InvalidToken("Invalid token prefix or length")
        
        timestamp = struct.unpack('>Q', raw[1:9])[0]
        iv = raw[9:25]
        ciphertext = raw[25:-32]
        received_hmac = raw[-32:]
        
        expected_hmac = hmac.new(self._signing_key, raw[:-32], hashlib.sha256).digest()
        if not hmac.compare_digest(received_hmac, expected_hmac):
            raise InvalidToken("HMAC verification failed")
            
        if ttl is not None:
            now = int(time.time())
            if timestamp + ttl < now or timestamp > now + 60:
                raise InvalidToken("Token expired")
                
        try:
            return _aes_cbc_decrypt(ciphertext, self._encryption_key, iv)
        except Exception as e:
            raise InvalidToken(f"Decryption failed: {e}")

# Attempt to load cryptography.fernet if permitted by OS policy, otherwise fallback cleanly
try:
    from cryptography.fernet import Fernet as _LibFernet, InvalidToken as _LibInvalidToken
    Fernet = _LibFernet
    InvalidToken = _LibInvalidToken
except Exception as _err:
    logger.info(f"Using pure-Python Fernet engine (cryptography backend unavailable: {_err})")
    Fernet = PureFernet
