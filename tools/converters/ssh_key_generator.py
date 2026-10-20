# ssh, rsa, ed25519, keypair, security, generator

from pathlib import Path
from typing import Literal
import zipfile
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa


def ssh_key_generator(
    key_type: Literal["ed25519", "rsa_4096", "rsa_2048"] = "ed25519",
    comment: str = "user@host",
    passphrase: str = "",
) -> dict:
    """Generate an SSH key pair (Ed25519 or RSA) as OpenSSH files, zipped: the private
    key, optionally passphrase-protected, plus the public key line for
    authorized_keys.
    """
    if key_type == "ed25519":
        private = ed25519.Ed25519PrivateKey.generate()
    else:
        private = rsa.generate_private_key(public_exponent=65537, key_size=4096 if key_type == "rsa_4096" else 2048)
    encryption = (
        serialization.BestAvailableEncryption(passphrase.encode()) if passphrase else serialization.NoEncryption()
    )
    private_pem = private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.OpenSSH, encryption)
    public_line = private.public_key().public_bytes(serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH)
    public_text = public_line.decode() + (f" {comment.strip()}" if comment.strip() else "") + "\n"
    name = "id_ed25519" if key_type == "ed25519" else "id_rsa"
    out = Path(f"{name}_keypair.zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(name, private_pem.decode())
        zf.writestr(f"{name}.pub", public_text)
    return {"file": out, "public_key": public_text.strip(), "note": "chmod 600 the private key after extracting"}
