"""
Free artifact signing via ed25519 (no purchase required).

Usage:
  python scripts/release_sign.py gen     -- generate keypair (once, keep secret safe)
  python scripts/release_sign.py sign    -- sign SHA256SUMS.txt -> SHA256SUMS.txt.sig
  python scripts/release_sign.py verify  -- verify signature against embedded pubkey

Secret key goes into the GitHub secret NETSTRIP_UPDATE_SIGNING_KEY (base64).
Public key is committed below so every install self-verifies for free.
"""

import base64
import os
import sys
from pathlib import Path

# ed25519 public key — replace after running `gen` once with your own.
PUBLIC_KEY_B64 = os.environ.get("NETSTRIP_UPDATE_PUBKEY", "<paste-pubkey-after-gen>")


def _keys():
    from cryptography.hazmat.primitives.asymmetric import ed25519
    if len(sys.argv) > 2 and sys.argv[1] == "gen":
        pass  # handled by caller
    priv_b64 = os.environ.get("NETSTRIP_UPDATE_SIGNING_KEY")
    if not priv_b64 or priv_b64.startswith("<"):
        print("Set NETSTRIP_UPDATE_SIGNING_KEY (base64 ed25519 private key)")
        sys.exit(1)
    priv = ed25519.Ed25519PrivateKey.from_private_bytes(base64.b64decode(priv_b64))
    pub = priv.public_key().public_bytes_raw()
    return priv, pub


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    manifest = Path("SHA256SUMS.txt")

    if cmd == "gen":
        from cryptography.hazmat.primitives.asymmetric import ed25519
        import base64 as b64
        priv = ed25519.Ed25519PrivateKey.generate()
        print("PRIVATE (GitHub secret NETSTRIP_UPDATE_SIGNING_KEY):")
        print(b64.b64encode(priv.private_bytes_raw()).decode())
        print("PUBLIC (commit to scripts/release_sign.py PUBLIC_KEY_B64):")
        print(b64.b64encode(priv.public_key().public_bytes_raw()).decode())

    elif cmd == "sign":
        priv, pub = _keys()
        sig = priv.sign(manifest.read_bytes())
        manifest.with_suffix(".txt.sig").write_bytes(sig)
        print(f"Signed → {manifest}.sig ({len(sig)} bytes)")

    elif cmd == "verify":
        from cryptography.hazmat.primitives.asymmetric import ed25519
        pub = ed25519.Ed25519PublicKey.from_public_bytes(base64.b64decode(PUBLIC_KEY_B64))
        sig = manifest.with_suffix(".txt.sig").read_bytes()
        try:
            pub.verify(sig, manifest.read_bytes())
            print("VERIFIED ✅")
        except Exception:
            print("SIGNATURE INVALID ❌")
            sys.exit(1)

    else:
        print(__doc__)


if __name__ == "__main__":
    main()

