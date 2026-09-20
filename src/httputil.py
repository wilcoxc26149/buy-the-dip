from __future__ import annotations

import json
import urllib.error
import urllib.request

SEC_USER_AGENT = (
    "Leeward/1.0 (https://github.com/wilcoxc26149/buy-the-dip; "
    "wilcoxc26149@users.noreply.github.com)"
)
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def get_json(url: str, *, headers: dict[str, str] | None = None, timeout: int = 25) -> dict:
    payload = get_bytes(url, headers=headers, timeout=timeout)
    return json.loads(payload.decode("utf-8"))


def get_bytes(url: str, *, headers: dict[str, str] | None = None, timeout: int = 25) -> bytes:
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"{exc.code} fetching {url}") from exc
