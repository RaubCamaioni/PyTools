# text, encoding, url, converter

from typing import Literal
from urllib.parse import quote, quote_plus, unquote, unquote_plus


def url_encoder(
    input: str,
    mode: Literal["encode", "decode"],
    space: Literal["percent20", "plus"],
    keep_reserved: Literal["yes", "no"],
) -> str:
    """Percent-encode text for URLs, or decode it back.

    keep_reserved=yes leaves / ? & = : characters untouched (encode a whole URL);
    keep_reserved=no encodes everything except unreserved characters (encode a value).
    """
    if mode == "decode":
        return unquote_plus(input) if space == "plus" else unquote(input)

    safe = "/?&=:#@+;,$!*'()" if keep_reserved == "yes" else ""
    if space == "plus":
        return quote_plus(input, safe=safe)
    return quote(input, safe=safe)
