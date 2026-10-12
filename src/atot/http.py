from __future__ import annotations

from typing import BinaryIO, cast
from urllib.parse import urlparse
from urllib.request import Request, urlopen

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
)


class HttpFetchError(RuntimeError):
    pass


def fetch_bytes(url: str, *, timeout: float = 30.0) -> bytes:
    try:
        with open_url(url, timeout=timeout) as response:
            return response.read()
    except HttpFetchError:
        raise
    except Exception as exc:
        raise HttpFetchError(f"Could not fetch URL: {url}") from exc


def open_url(url: str, *, timeout: float = 30.0) -> BinaryIO:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise HttpFetchError(f"Only HTTP/HTTPS URLs are supported: {url}")
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        return cast(BinaryIO, urlopen(request, timeout=timeout))
    except Exception as exc:
        raise HttpFetchError(f"Could not fetch URL: {url}") from exc
