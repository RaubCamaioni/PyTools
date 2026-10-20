# uuid, guid, generator

from typing import Literal
import uuid


def uuid_generator(
    count: int = 5,
    version: Literal["v4_random", "v1_time", "v5_sha1_name", "v3_md5_name"] = "v4_random",
    name: str = "example.com",
    format: Literal["lowercase", "UPPERCASE", "no_dashes", "braces", "urn"] = "lowercase",
) -> str:
    """Generate UUIDs (GUIDs). v4 is random; v5/v3 hash the given name in the DNS
    namespace.
    """
    count = max(1, min(count, 200))
    out = []
    for _ in range(count):
        if version == "v1_time":
            u = uuid.uuid1()
        elif version == "v5_sha1_name":
            u = uuid.uuid5(uuid.NAMESPACE_DNS, name)
        elif version == "v3_md5_name":
            u = uuid.uuid3(uuid.NAMESPACE_DNS, name)
        else:
            u = uuid.uuid4()
        s = str(u)
        if format == "UPPERCASE":
            s = s.upper()
        elif format == "no_dashes":
            s = u.hex
        elif format == "braces":
            s = "{" + s + "}"
        elif format == "urn":
            s = u.urn
        out.append(s)
    return "\n".join(out)
