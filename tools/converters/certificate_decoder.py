# certificate, x509, ssl, tls, pem, csr, decode

from pathlib import Path
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization


def certificate_decoder(certificate: Path) -> dict:
    """Decode an X.509 certificate or CSR (PEM or DER): subject, issuer, validity, SANs,
    key type, signature algorithm and fingerprints. Only public data is read.
    """
    raw = certificate.read_bytes()
    loaders = [
        ("certificate", lambda b: x509.load_pem_x509_certificate(b)),
        ("certificate", lambda b: x509.load_der_x509_certificate(b)),
        ("csr", lambda b: x509.load_pem_x509_csr(b)),
        ("csr", lambda b: x509.load_der_x509_csr(b)),
    ]
    kind, obj = None, None
    for name, load in loaders:
        try:
            obj = load(raw)
            kind = name
            break
        except Exception:  # noqa: BLE001 - try the next format
            continue
    if obj is None:
        return {"error": "Not a PEM or DER certificate or certificate request"}

    key = obj.public_key()
    key_type = type(key).__name__.replace("_", "").replace("PublicKey", "")
    key_size = getattr(key, "key_size", None)
    try:
        sans = obj.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(
            x509.DNSName
        )
    except x509.ExtensionNotFound:
        sans = []
    info = {
        "type": kind,
        "subject": obj.subject.rfc4514_string(),
        "public_key": f"{key_type} {key_size or ''}".strip(),
        "signature_algorithm": obj.signature_hash_algorithm.name if obj.signature_hash_algorithm else "unknown",
        "subject_alternative_names": sans,
    }
    if kind == "certificate":
        info.update(
            {
                "issuer": obj.issuer.rfc4514_string(),
                "serial_number": format(obj.serial_number, "x"),
                "not_before": obj.not_valid_before_utc.isoformat(),
                "not_after": obj.not_valid_after_utc.isoformat(),
                "self_signed": obj.issuer == obj.subject,
                "fingerprint_sha256": obj.fingerprint(hashes.SHA256()).hex(":"),
                "fingerprint_sha1": obj.fingerprint(hashes.SHA1()).hex(":"),
                "extensions": [e.oid._name or e.oid.dotted_string for e in obj.extensions],
            }
        )
    info["public_key_pem"] = key.public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()
    return info
