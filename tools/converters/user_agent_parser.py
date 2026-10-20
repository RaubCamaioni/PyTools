# user agent, browser, device, parse, web

import ua_parser


def user_agent_parser(
    user_agent: str = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) Version/17.5 Mobile/15E148 Safari/604.1",
) -> dict:
    """Decode a browser User-Agent string into the browser, its version, the operating
    system and the device, and say whether it looks like a bot or a mobile.
    """
    parsed = ua_parser.parse(user_agent.strip())
    ua, os_, dev = parsed.user_agent, parsed.os, parsed.device

    def version(part) -> str:
        if part is None:
            return ""
        return ".".join(p for p in (part.major, part.minor, part.patch) if p)

    lowered = user_agent.lower()
    return {
        "browser": ua.family if ua else "Other",
        "browser_version": version(ua),
        "os": os_.family if os_ else "Other",
        "os_version": version(os_),
        "device": dev.family if dev else "Other",
        "device_brand": (dev.brand if dev else None) or "",
        "device_model": (dev.model if dev else None) or "",
        "is_mobile": any(k in lowered for k in ("mobile", "android", "iphone", "ipad")),
        "is_bot": any(k in lowered for k in ("bot", "crawler", "spider", "slurp", "curl", "wget", "python-requests")),
    }
