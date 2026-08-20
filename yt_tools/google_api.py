import json

from googleapiclient.errors import HttpError


def format_http_error(error: HttpError, api_name: str) -> str:
    """Format a Google API HTTP failure without losing actionable details."""
    status = getattr(error.resp, "status", "unknown status")
    try:
        payload = json.loads(error.content.decode("utf-8"))
        detail = payload["error"]
        parts = [detail.get("message")]
        for item in detail.get("errors", []):
            context = "; ".join(
                f"{name}: {item[name]}"
                for name in ("reason", "location")
                if item.get(name)
            )
            item_message = item.get("message")
            if item_message and item_message != parts[0]:
                context = f"{context}; {item_message}" if context else item_message
            if context:
                parts.append(context)
        details = " | ".join(part for part in parts if part)
    except (KeyError, TypeError, ValueError, UnicodeDecodeError):
        details = error._get_reason().strip()
    suffix = f": {details}" if details else ""
    return f"{api_name} request failed ({status}){suffix}"
