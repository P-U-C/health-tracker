from __future__ import annotations

import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from core.contracts import REPO_ROOT


def push_line(message: str) -> dict[str, str]:
    sent: dict[str, str] = {}
    ntfy_url = os.getenv("HEALTH_NTFY_URL")
    telegram_token = os.getenv("HEALTH_TELEGRAM_BOT_TOKEN")
    telegram_chat = os.getenv("HEALTH_TELEGRAM_CHAT_ID")

    if ntfy_url:
        request = urllib.request.Request(ntfy_url, data=message.encode("utf-8"), method="POST")
        with urllib.request.urlopen(request, timeout=10) as response:
            sent["ntfy"] = str(response.status)

    if telegram_token and telegram_chat:
        url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        data = urllib.parse.urlencode({"chat_id": telegram_chat, "text": message}).encode("utf-8")
        with urllib.request.urlopen(url, data=data, timeout=10) as response:
            sent["telegram"] = str(response.status)

    if not sent:
        path = REPO_ROOT / "data" / "exports" / "alerts.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(f"{datetime.now(timezone.utc).isoformat()} {message}\n")
        sent["file"] = str(path)
    return sent
