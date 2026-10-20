# url, parse, query, parameters, web

from urllib.parse import parse_qsl, unquote, urlsplit


def url_parser(url: str = "https://user:pw@example.com:8443/path/page.html?a=1&b=two%20words#top") -> dict:
    """Break a URL into scheme, host, port, path, query parameters (decoded) and
    fragment.
    """
    text = url.strip()
    if "://" not in text:
        text = "https://" + text
    parts = urlsplit(text)
    host = parts.hostname or ""
    labels = host.split(".")
    return {
        "scheme": parts.scheme,
        "username": parts.username,
        "password": "(present)" if parts.password else None,
        "host": host,
        "port": parts.port or {"http": 80, "https": 443, "ftp": 21}.get(parts.scheme),
        "domain": ".".join(labels[-2:]) if len(labels) >= 2 else host,
        "subdomain": ".".join(labels[:-2]) if len(labels) > 2 else "",
        "path": unquote(parts.path) or "/",
        "path_segments": [unquote(s) for s in parts.path.split("/") if s],
        "query": dict(parse_qsl(parts.query, keep_blank_values=True)),
        "fragment": parts.fragment,
        "origin": f"{parts.scheme}://{parts.netloc.split('@')[-1]}",
    }
