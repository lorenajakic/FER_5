from __future__ import annotations

import os
from typing import Optional


def web_search(
    query: str,
    max_results: int = 5,
    include_domains: Optional[list[str]] = None,
) -> list[dict[str, str]]:
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        return []
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        kwargs: dict = {
            "query": query,
            "search_depth": "basic",
            "max_results": max_results,
            "include_answer": False,
        }
        if include_domains:
            kwargs["include_domains"] = include_domains
        response = client.search(**kwargs)
        return [
            {
                "title": r.get("title", ""),
                "body": r.get("content", ""),
                "href": r.get("url", ""),
            }
            for r in response.get("results", [])
        ]
    except Exception as e:
        import sys
        print(f"[web_search] Tavily error: {e}", file=sys.stderr)
        return []
