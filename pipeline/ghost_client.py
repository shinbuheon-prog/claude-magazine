"""Ghost Admin API client."""

from __future__ import annotations

import argparse
import os
import time
from typing import Any
from urllib.parse import urlencode

import jwt
import requests
from dotenv import load_dotenv

load_dotenv()


def _admin_api_base() -> str:
    api_url = os.environ["GHOST_ADMIN_API_URL"].rstrip("/")
    if api_url.endswith("/ghost/api/admin"):
        return api_url
    return f"{api_url}/ghost/api/admin"


def _get_token() -> str:
    key = os.environ["GHOST_ADMIN_API_KEY"]
    kid, secret = key.split(":", 1)
    issued_at = int(time.time())
    return jwt.encode(
        {"iat": issued_at, "exp": issued_at + 300, "aud": "/admin/"},
        bytes.fromhex(secret),
        algorithm="HS256",
        headers={"alg": "HS256", "kid": kid, "typ": "JWT"},
    )


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Ghost {_get_token()}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _request(
    method: str,
    path: str,
    *,
    params: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    query = f"?{urlencode(params)}" if params else ""
    response = requests.request(
        method=method,
        url=f"{_admin_api_base()}{path}{query}",
        headers=_headers(),
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def _get_default_newsletter_slug() -> str:
    configured = os.getenv("GHOST_NEWSLETTER_SLUG")
    if configured:
        return configured

    response = _request("GET", "/newsletters/")
    newsletters = response.get("newsletters", [])
    for newsletter in newsletters:
        if newsletter.get("status") == "active" and newsletter.get("slug"):
            return newsletter["slug"]
    raise RuntimeError("No active Ghost newsletter was found.")


def create_post(title: str, html: str, status: str = "draft") -> dict[str, str]:
    """
    Create a Ghost post.

    Returns: {"post_id": str, "url": str, "status": str}
    """
    if status not in {"draft", "published"}:
        raise ValueError("status must be 'draft' or 'published'")

    payload = {
        "posts": [
            {
                "title": title,
                "html": html,
                "status": status,
                "visibility": "public",
            }
        ]
    }
    response = _request("POST", "/posts/", params={"source": "html"}, payload=payload)
    post = response["posts"][0]
    return {"post_id": post["id"], "url": post["url"], "status": post["status"]}


def send_newsletter(post_id: str) -> dict[str, int | str]:
    """
    Publish a post and trigger newsletter delivery.

    Returns: {"newsletter_id": str, "recipient_count": int}
    """
    post_response = _request("GET", f"/posts/{post_id}/")
    post = post_response["posts"][0]
    newsletter_slug = _get_default_newsletter_slug()
    payload = {"posts": [{"updated_at": post["updated_at"], "status": "published"}]}
    response = _request(
        "PUT",
        f"/posts/{post_id}/",
        params={"newsletter": newsletter_slug, "email_segment": "all"},
        payload=payload,
    )
    updated_post = response["posts"][0]
    email = updated_post.get("email") or {}
    return {
        "newsletter_id": email.get("id", ""),
        "recipient_count": int(email.get("email_count", 0)),
    }


def _has_required_env() -> bool:
    return bool(os.getenv("GHOST_ADMIN_API_URL") and os.getenv("GHOST_ADMIN_API_KEY"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Ghost Admin API smoke test")
    parser.add_argument("--title", default="Ghost API Test Post", help="Post title")
    parser.add_argument("--html", default="<p>Ghost Admin API test body.</p>", help="HTML body")
    parser.add_argument("--status", choices=("draft", "published"), default="draft", help="Initial post status")
    parser.add_argument("--send-newsletter", action="store_true", help="Publish the created post via Ghost newsletter")
    parser.add_argument("--dry-run", action="store_true", help="Print the request that would be sent without calling Ghost")
    args = parser.parse_args()

    if args.dry_run or not _has_required_env():
        result = {
            "mode": "dry-run",
            "title": args.title,
            "status": args.status,
            "send_newsletter": args.send_newsletter,
            "api_url_configured": bool(os.getenv("GHOST_ADMIN_API_URL")),
            "api_key_configured": bool(os.getenv("GHOST_ADMIN_API_KEY")),
        }
        print(result)
        if not args.dry_run and not _has_required_env():
            print("Set GHOST_ADMIN_API_URL and GHOST_ADMIN_API_KEY to run the live Ghost smoke test.")
        return 0

    result = create_post(args.title, args.html, status=args.status)
    print(result)

    if args.send_newsletter:
        newsletter_result = send_newsletter(result["post_id"])
        print(newsletter_result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
