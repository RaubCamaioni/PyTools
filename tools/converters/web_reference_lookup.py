# http, status, mime, port, reference, lookup

from http import HTTPStatus
from typing import Literal
import mimetypes

PORTS = {
    20: "FTP data",
    21: "FTP",
    22: "SSH",
    23: "Telnet",
    25: "SMTP",
    53: "DNS",
    67: "DHCP",
    80: "HTTP",
    110: "POP3",
    123: "NTP",
    143: "IMAP",
    161: "SNMP",
    194: "IRC",
    389: "LDAP",
    443: "HTTPS",
    445: "SMB",
    465: "SMTPS",
    514: "Syslog",
    587: "SMTP submission",
    636: "LDAPS",
    993: "IMAPS",
    995: "POP3S",
    1433: "MS SQL",
    1521: "Oracle",
    2049: "NFS",
    3000: "dev servers",
    3306: "MySQL",
    3389: "RDP",
    5432: "PostgreSQL",
    5672: "AMQP",
    5900: "VNC",
    6379: "Redis",
    8080: "HTTP alt",
    8443: "HTTPS alt",
    9200: "Elasticsearch",
    27017: "MongoDB",
}


def web_reference_lookup(query: str = "404", kind: Literal["http_status", "mime_type", "port"] = "http_status") -> dict:
    """Look up an HTTP status code (404 → Not Found, with its meaning), a file
    extension's MIME type (or a MIME type's extensions), or what a TCP port number is
    normally used for.
    """
    q = query.strip()
    if kind == "http_status":
        if not q.isdigit():
            matches = [f"{s.value} {s.phrase}" for s in HTTPStatus if q.lower() in s.phrase.lower()]
            return {"matches": matches or ["no status matches that text"]}
        try:
            status = HTTPStatus(int(q))
        except ValueError:
            return {"error": f"{q} is not a standard HTTP status code"}
        classes = {1: "informational", 2: "success", 3: "redirection", 4: "client error", 5: "server error"}
        return {
            "code": status.value,
            "phrase": status.phrase,
            "description": status.description,
            "class": classes.get(status.value // 100),
        }
    if kind == "mime_type":
        if "/" in q:
            return {"mime_type": q, "extensions": mimetypes.guess_all_extensions(q) or ["unknown"]}
        ext = q if q.startswith(".") else "." + q
        mime, encoding = mimetypes.guess_type("file" + ext)
        return {"extension": ext, "mime_type": mime or "unknown", "content_encoding": encoding}
    if not q.isdigit():
        return {"matches": {p: s for p, s in PORTS.items() if q.lower() in s.lower()} or "no known service matches"}
    port = int(q)
    return {
        "port": port,
        "service": PORTS.get(port, "no well-known service in this table"),
        "range": "well-known" if port < 1024 else "registered" if port < 49152 else "dynamic/private",
    }
