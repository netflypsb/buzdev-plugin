#!/usr/bin/env python3
"""
Web & Social Search MCP Server — stdio transport
Part of the BuzDev Plugin.

Wraps Agent-Reach capabilities as an MCP server with stdio transport.
Provides zero-config web reading, search, and social media access.

No external API keys required for core functionality.
Optional: JINA_API_KEY (higher rate limits), platform OAuth tokens (enhanced social access).
"""

import json
import sys
import subprocess
import os
import importlib.util
from typing import Any

# MCP Protocol version
PROTOCOL_VERSION = "2025-11-25"
SERVER_NAME = "web-social-search"
SERVER_VERSION = "1.0.0"

# ─── MCP Protocol Helpers ──────────────────────────────────────

def send_message(msg: dict) -> None:
    """Send a JSON-RPC message to stdout."""
    sys.stdout.write(json.dumps(msg))
    sys.stdout.write("\n")
    sys.stdout.flush()

def create_response(msg_id: Any, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}

def create_error(msg_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}

ERROR_CODES = {
    "PARSE_ERROR": -32700,
    "INVALID_REQUEST": -32600,
    "METHOD_NOT_FOUND": -32601,
    "INVALID_PARAMS": -32602,
    "INTERNAL_ERROR": -32603,
}

# ─── Backend Helpers ───────────────────────────────────────────

JINA_READER_URL = "https://r.jina.ai/"
JINA_SEARCH_URL = "https://s.jina.ai/"
FREESERP_URL = "https://freeserp.ai/api.php"
HN_ALGOLIA_URL = "https://hn.algolia.com/api/v1/search"

def get_jina_key() -> str:
    return os.environ.get("JINA_API_KEY", "")

def get_env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)

# ─── Tool Implementations ──────────────────────────────────────

async def tool_read_webpage(url: str) -> dict:
    """Read any web page and return clean markdown. Uses Jina Reader (free, no API key)."""
    import urllib.request
    import urllib.error

    if not url or not url.startswith("http"):
        return {"error": "url is required and must start with http(s)://"}

    try:
        jina_url = f"{JINA_READER_URL}{url}"
        req = urllib.request.Request(jina_url, headers={
            "Accept": "text/markdown",
            "User-Agent": f"{SERVER_NAME}/{SERVER_VERSION}"
        })

        jina_key = get_jina_key()
        if jina_key:
            req.add_header("Authorization", f"Bearer {jina_key}")

        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            if not text or len(text) < 10:
                return {"error": "Empty response from reader", "url": url}
            # Truncate to 15k chars for MCP response
            return {
                "status": "ok",
                "url": url,
                "markdown": text[:15000],
                "truncated": len(text) > 15000,
                "full_length": len(text)
            }
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "url": url}
    except Exception as e:
        return {"error": str(e), "url": url}

async def tool_search_web(query: str, num_results: int = 10) -> dict:
    """Search the web using FreeSerp (keyless) or Jina Search (optional key)."""
    import urllib.request
    import urllib.error

    if not query:
        return {"error": "query is required"}

    num_results = max(1, min(num_results, 50))

    # Primary: FreeSerp.ai (keyless)
    try:
        url = f"{FREESERP_URL}?q={urllib.parse.quote(query)}&size={num_results}"
        req = urllib.request.Request(url, headers={
            "Accept": "application/json",
            "User-Agent": f"{SERVER_NAME}/{SERVER_VERSION}"
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("results"):
                results = data["results"][:num_results]
                return {
                    "status": "ok",
                    "source": "freeserp",
                    "query": query,
                    "count": len(results),
                    "results": [{
                        "url": f"https://{r.get('domain', '')}" if r.get('domain') else "",
                        "domain": r.get("domain", ""),
                        "title": r.get("title", ""),
                        "description": (r.get("ai_summary") or r.get("title") or "")[:500],
                    } for r in results]
                }
    except Exception:
        pass

    # Fallback: Jina Search (requires key)
    jina_key = get_jina_key()
    if jina_key:
        try:
            url = f"{JINA_SEARCH_URL}{urllib.parse.quote(query)}"
            req = urllib.request.Request(url, headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {jina_key}"
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                results = (data.get("data") or [])[:num_results]
                return {
                    "status": "ok",
                    "source": "jina",
                    "query": query,
                    "count": len(results),
                    "results": [{
                        "url": r.get("url", ""),
                        "title": r.get("title", ""),
                        "description": (r.get("description") or r.get("content") or "")[:500],
                    } for r in results]
                }
        except Exception:
            pass

    return {"status": "ok", "source": "none", "query": query, "count": 0, "results": [], "note": "No search backend available. Set JINA_API_KEY for search capability."}

async def tool_search_hn(query: str, num_results: int = 10) -> dict:
    """Search Hacker News via Algolia API (keyless, no auth)."""
    import urllib.request
    import urllib.parse

    if not query:
        return {"error": "query is required"}

    num_results = max(1, min(num_results, 50))

    try:
        url = f"{HN_ALGOLIA_URL}?query={urllib.parse.quote(query)}&tags=story&hitsPerPage={num_results}"
        req = urllib.request.Request(url, headers={
            "Accept": "application/json",
            "User-Agent": f"{SERVER_NAME}/{SERVER_VERSION}"
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            hits = data.get("hits", [])[:num_results]
            return {
                "status": "ok",
                "source": "hn_algolia",
                "query": query,
                "count": len(hits),
                "results": [{
                    "id": h.get("objectID", ""),
                    "title": h.get("title", ""),
                    "url": h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID', '')}",
                    "points": h.get("points", 0),
                    "author": h.get("author", ""),
                    "comments": h.get("num_comments", 0),
                    "created_at": h.get("created_at", ""),
                } for h in hits]
            }
    except Exception as e:
        return {"error": str(e), "query": query}

async def tool_search_youtube(query: str, num_results: int = 10) -> dict:
    """Search YouTube for videos. Uses yt-dlp if available, falls back to Jina Reader on search results."""
    import urllib.request
    import urllib.parse

    if not query:
        return {"error": "query is required"}

    num_results = max(1, min(num_results, 30))

    # Try yt-dlp search first
    try:
        result = subprocess.run(
            ["yt-dlp", f"ytsearch{num_results}:{query}", "--flat-playlist", "-J", "--no-warnings"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout:
            data = json.loads(result.stdout)
            entries = data.get("entries", [])[:num_results]
            return {
                "status": "ok",
                "source": "yt-dlp",
                "query": query,
                "count": len(entries),
                "results": [{
                    "id": e.get("id", ""),
                    "title": e.get("title", ""),
                    "url": e.get("url") or f"https://youtube.com/watch?v={e.get('id', '')}",
                    "duration": e.get("duration"),
                    "uploader": e.get("uploader", ""),
                    "view_count": e.get("view_count"),
                } for e in entries if e.get("id")]
            }
    except FileNotFoundError:
        pass  # yt-dlp not installed
    except Exception:
        pass

    # Fallback: Jina Reader on YouTube search
    try:
        search_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
        jina_url = f"{JINA_READER_URL}{search_url}"
        req = urllib.request.Request(jina_url, headers={"Accept": "text/markdown"})
        jina_key = get_jina_key()
        if jina_key:
            req.add_header("Authorization", f"Bearer {jina_key}")
        with urllib.request.urlopen(req, timeout=20) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            # Extract video IDs from the markdown
            import re
            video_ids = re.findall(r'youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})', text)
            seen = set()
            results = []
            for vid in video_ids:
                if vid not in seen:
                    seen.add(vid)
                    results.append({
                        "id": vid,
                        "url": f"https://youtube.com/watch?v={vid}",
                    })
                    if len(results) >= num_results:
                        break
            return {
                "status": "ok",
                "source": "jina_reader",
                "query": query,
                "count": len(results),
                "results": results
            }
    except Exception as e:
        return {"error": str(e), "query": query}

    return {"error": "No YouTube search backend available", "query": query}

async def tool_get_youtube_transcript(video_url_or_id: str) -> dict:
    """Extract subtitles/transcript from a YouTube video using yt-dlp (no API key)."""
    if not video_url_or_id:
        return {"error": "video_url_or_id is required"}

    # Normalize to URL
    if not video_url_or_id.startswith("http"):
        video_url = f"https://www.youtube.com/watch?v={video_url_or_id}"
    else:
        video_url = video_url_or_id

    try:
        result = subprocess.run(
            ["yt-dlp", "--write-subs", "--write-auto-subs", "--sub-lang", "en", "--skip-download",
             "--sub-format", "vtt", "-o", "/tmp/yt_transcript", video_url, "--no-warnings"],
            capture_output=True, text=True, timeout=30
        )

        # Find the subtitle file
        import glob
        sub_files = glob.glob("/tmp/yt_transcript*.vtt")
        if not sub_files:
            return {"error": "No English subtitles found for this video", "url": video_url}

        with open(sub_files[0], 'r') as f:
            content = f.read()

        # Clean VTT format — extract just the text
        import re
        # Remove VTT headers and timestamps
        text = re.sub(r'WEBVTT.*?\n\n', '', content, flags=re.DOTALL)
        text = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3}.*?\n', '', text)
        text = re.sub(r'<[^>]+>', '', text)  # Remove HTML-like tags
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()

        # Clean up
        os.remove(sub_files[0])

        return {
            "status": "ok",
            "url": video_url,
            "transcript": text[:15000],
            "truncated": len(text) > 15000,
            "full_length": len(text)
        }
    except FileNotFoundError:
        return {"error": "yt-dlp is not installed. Install with: pip install yt-dlp", "url": video_url}
    except Exception as e:
        return {"error": str(e), "url": video_url}

async def tool_search_reddit(query: str, subreddit: str = "", num_results: int = 10) -> dict:
    """Search Reddit. Uses Jina Reader on Reddit search (keyless)."""
    import urllib.request
    import urllib.parse

    if not query:
        return {"error": "query is required"}

    num_results = max(1, min(num_results, 30))

    if subreddit:
        search_url = f"https://www.reddit.com/r/{subreddit}/search/?q={urllib.parse.quote(query)}&restrict_sr=1&sort=relevance"
    else:
        search_url = f"https://www.reddit.com/search/?q={urllib.parse.quote(query)}&sort=relevance"

    try:
        jina_url = f"{JINA_READER_URL}{search_url}"
        req = urllib.request.Request(jina_url, headers={"Accept": "text/markdown"})
        jina_key = get_jina_key()
        if jina_key:
            req.add_header("Authorization", f"Bearer {jina_key}")
        with urllib.request.urlopen(req, timeout=20) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            return {
                "status": "ok",
                "source": "jina_reader",
                "query": query,
                "subreddit": subreddit or "all",
                "markdown": text[:12000],
                "truncated": len(text) > 12000,
                "note": "Results are page text. Parse titles and links from the markdown."
            }
    except Exception as e:
        return {"error": str(e), "query": query}

async def tool_read_github(repo: str, path: str = "") -> dict:
    """Read a GitHub repo or specific file. Uses gh CLI (authenticated) or Jina Reader (keyless)."""
    if not repo:
        return {"error": "repo is required (format: owner/repo)"}

    # Try gh CLI first
    try:
        if path:
            result = subprocess.run(
                ["gh", "api", f"repos/{repo}/contents/{path}", "--jq", ".content"],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0 and result.stdout:
                import base64
                content = base64.b64decode(result.stdout.strip()).decode("utf-8", errors="replace")
                return {
                    "status": "ok",
                    "source": "gh_cli",
                    "repo": repo,
                    "path": path,
                    "content": content[:15000],
                    "truncated": len(content) > 15000
                }
        else:
            result = subprocess.run(
                ["gh", "repo", "view", repo, "--json", "name,description,url,homepageUrl,stargazerCount,forkCount,primaryLanguage,licenseInfo,repositoryTopics"],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0 and result.stdout:
                data = json.loads(result.stdout)
                return {
                    "status": "ok",
                    "source": "gh_cli",
                    "repo": repo,
                    "info": data
                }
    except FileNotFoundError:
        pass  # gh not installed
    except Exception:
        pass

    # Fallback: Jina Reader
    try:
        github_url = f"https://github.com/{repo}" + (f"/blob/main/{path}" if path else "")
        jina_url = f"{JINA_READER_URL}{github_url}"
        req = urllib.request.Request(jina_url, headers={"Accept": "text/markdown"})
        jina_key = get_jina_key()
        if jina_key:
            req.add_header("Authorization", f"Bearer {jina_key}")
        with urllib.request.urlopen(req, timeout=20) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            return {
                "status": "ok",
                "source": "jina_reader",
                "repo": repo,
                "path": path,
                "markdown": text[:15000],
                "truncated": len(text) > 15000
            }
    except Exception as e:
        return {"error": str(e), "repo": repo}

async def tool_search_github(query: str, num_results: int = 10) -> dict:
    """Search GitHub repositories. Uses gh CLI or Jina Reader."""
    if not query:
        return {"error": "query is required"}

    num_results = max(1, min(num_results, 30))

    # Try gh CLI
    try:
        result = subprocess.run(
            ["gh", "search", "repos", query, "--limit", str(num_results), "--json",
             "fullName,description,url,stargazersCount,forkCount,primaryLanguage,licenseInfo"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0 and result.stdout:
            data = json.loads(result.stdout)
            return {
                "status": "ok",
                "source": "gh_cli",
                "query": query,
                "count": len(data),
                "results": data
            }
    except FileNotFoundError:
        pass
    except Exception:
        pass

    # Fallback: Jina Reader on GitHub search
    try:
        import urllib.parse
        search_url = f"https://github.com/search?q={urllib.parse.quote(query)}&type=repositories"
        jina_url = f"{JINA_READER_URL}{search_url}"
        req = urllib.request.Request(jina_url, headers={"Accept": "text/markdown"})
        jina_key = get_jina_key()
        if jina_key:
            req.add_header("Authorization", f"Bearer {jina_key}")
        with urllib.request.urlopen(req, timeout=20) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            return {
                "status": "ok",
                "source": "jina_reader",
                "query": query,
                "markdown": text[:12000],
                "note": "Parse repo names and descriptions from the markdown."
            }
    except Exception as e:
        return {"error": str(e), "query": query}

async def tool_read_rss(feed_url: str, num_items: int = 10) -> dict:
    """Read an RSS/Atom feed and return structured items. Uses feedparser if available, raw XML otherwise."""
    import urllib.request

    if not feed_url:
        return {"error": "feed_url is required"}

    num_items = max(1, min(num_items, 50))

    # Try feedparser
    try:
        import feedparser
        feed = feedparser.parse(feed_url)
        items = []
        for entry in feed.entries[:num_items]:
            items.append({
                "title": getattr(entry, "title", ""),
                "link": getattr(entry, "link", ""),
                "description": getattr(entry, "summary", getattr(entry, "description", ""))[:500],
                "published": getattr(entry, "published", getattr(entry, "updated", "")),
                "author": getattr(entry, "author", ""),
            })
        return {
            "status": "ok",
            "source": "feedparser",
            "feed_url": feed_url,
            "feed_title": getattr(feed.feed, "title", ""),
            "count": len(items),
            "items": items
        }
    except ImportError:
        pass
    except Exception as e:
        return {"error": str(e), "feed_url": feed_url}

    # Fallback: fetch raw XML via Jina Reader
    try:
        jina_url = f"{JINA_READER_URL}{feed_url}"
        req = urllib.request.Request(jina_url, headers={"Accept": "text/markdown"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            return {
                "status": "ok",
                "source": "jina_reader",
                "feed_url": feed_url,
                "markdown": text[:12000],
                "note": "Install feedparser for structured RSS parsing: pip install feedparser"
            }
    except Exception as e:
        return {"error": str(e), "feed_url": feed_url}

async def tool_get_agent_reach_status() -> dict:
    """Check which Agent-Reach channels are installed and active. Requires agent-reach installed."""
    try:
        result = subprocess.run(
            ["agent-reach", "doctor", "--json"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0 and result.stdout:
            data = json.loads(result.stdout)
            return {"status": "ok", "channels": data}
        else:
            return {
                "status": "warning",
                "message": "agent-reach not installed or doctor failed",
                "stderr": result.stderr[:500] if result.stderr else "",
                "install": "pip install git+https://github.com/Panniantong/Agent-Reach.git"
            }
    except FileNotFoundError:
        return {
            "status": "not_installed",
            "message": "Agent-Reach is not installed. Install for enhanced social media access.",
            "install": "pip install git+https://github.com/Panniantong/Agent-Reach.git"
        }
    except Exception as e:
        return {"error": str(e)}

# ─── Tool Definitions ──────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "name": "read_webpage",
        "description": "Read any web page and return clean markdown text. Uses Jina Reader (free, no API key required). Works on most public web pages including news articles, blog posts, documentation, and landing pages. Optional: set JINA_API_KEY env var for higher rate limits.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The full URL of the web page to read (must start with http:// or https://)"}
            },
            "required": ["url"]
        },
        "handler": tool_read_webpage
    },
    {
        "name": "search_web",
        "description": "Search the web for general results. Uses FreeSerp.ai (keyless, no auth) as primary, Jina Search as fallback (requires JINA_API_KEY). Returns titles, URLs, and descriptions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query string"},
                "num_results": {"type": "integer", "description": "Number of results (1-50, default 10)", "default": 10}
            },
            "required": ["query"]
        },
        "handler": tool_search_web
    },
    {
        "name": "search_hackernews",
        "description": "Search Hacker News stories using the Algolia API (keyless, no auth required). Returns story titles, URLs, points, and comment counts.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "num_results": {"type": "integer", "description": "Number of results (1-50, default 10)", "default": 10}
            },
            "required": ["query"]
        },
        "handler": tool_search_hn
    },
    {
        "name": "search_youtube",
        "description": "Search YouTube for videos. Uses yt-dlp if installed (best results), falls back to Jina Reader. Returns video IDs, titles, and URLs. No API key required.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "num_results": {"type": "integer", "description": "Number of results (1-30, default 10)", "default": 10}
            },
            "required": ["query"]
        },
        "handler": tool_search_youtube
    },
    {
        "name": "get_youtube_transcript",
        "description": "Extract subtitles/transcript from a YouTube video using yt-dlp. No API key required. Requires yt-dlp installed (pip install yt-dlp). Returns the full English transcript text.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "video_url_or_id": {"type": "string", "description": "YouTube video URL or just the video ID (11 characters)"}
            },
            "required": ["video_url_or_id"]
        },
        "handler": tool_get_youtube_transcript
    },
    {
        "name": "search_reddit",
        "description": "Search Reddit for posts and discussions. Uses Jina Reader on Reddit search (keyless). Can search all of Reddit or a specific subreddit. Returns page markdown with post titles and links.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "subreddit": {"type": "string", "description": "Optional: restrict search to a specific subreddit (without the r/ prefix)"},
                "num_results": {"type": "integer", "description": "Number of results (1-30, default 10)", "default": 10}
            },
            "required": ["query"]
        },
        "handler": tool_search_reddit
    },
    {
        "name": "read_github",
        "description": "Read a GitHub repository info or a specific file. Uses gh CLI if authenticated (full API access), falls back to Jina Reader (keyless, public repos only). For repo info, provide owner/repo. For a file, provide owner/repo and the file path.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "description": "Repository in owner/repo format (e.g. 'Panniantong/Agent-Reach')"},
                "path": {"type": "string", "description": "Optional: path to a specific file in the repo (e.g. 'README.md')"}
            },
            "required": ["repo"]
        },
        "handler": tool_read_github
    },
    {
        "name": "search_github",
        "description": "Search GitHub repositories by keyword. Uses gh CLI if available, falls back to Jina Reader. Returns repo names, descriptions, stars, and languages.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "num_results": {"type": "integer", "description": "Number of results (1-30, default 10)", "default": 10}
            },
            "required": ["query"]
        },
        "handler": tool_search_github
    },
    {
        "name": "read_rss",
        "description": "Read an RSS or Atom feed and return structured items. Uses feedparser if installed (best), falls back to Jina Reader. Returns titles, links, descriptions, and publish dates.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "feed_url": {"type": "string", "description": "The full URL of the RSS/Atom feed"},
                "num_items": {"type": "integer", "description": "Number of items to return (1-50, default 10)", "default": 10}
            },
            "required": ["feed_url"]
        },
        "handler": tool_read_rss
    },
    {
        "name": "agent_reach_status",
        "description": "Check which Agent-Reach channels are installed and active. Agent-Reach provides enhanced social media access (Twitter, Instagram, Facebook, Xiaohongshu, Bilibili). Run this to see which platforms are available.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        },
        "handler": tool_get_agent_reach_status
    },
]

# ─── MCP Server Loop ───────────────────────────────────────────

def get_tools_list() -> list:
    """Return tool definitions in MCP format."""
    return [{
        "name": t["name"],
        "description": t["description"],
        "inputSchema": t["inputSchema"]
    } for t in TOOL_DEFINITIONS]

def find_tool(name: str):
    """Find a tool definition by name."""
    for t in TOOL_DEFINITIONS:
        if t["name"] == name:
            return t
    return None

async def handle_request(request: dict) -> dict | None:
    """Handle a single JSON-RPC request. Returns response or None for notifications."""
    method = request.get("method")
    msg_id = request.get("id")
    params = request.get("params", {})

    if method == "initialize":
        return create_response(msg_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {
                "name": SERVER_NAME,
                "version": SERVER_VERSION
            }
        })

    elif method == "notifications/initialized":
        return None  # Notification, no response

    elif method == "tools/list":
        return create_response(msg_id, {"tools": get_tools_list()})

    elif method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})

        tool = find_tool(tool_name)
        if not tool:
            return create_error(msg_id, ERROR_CODES["METHOD_NOT_FOUND"], f"Unknown tool: {tool_name}")

        try:
            result = await tool["handler"](**tool_args)
            return create_response(msg_id, {
                "content": [{
                    "type": "text",
                    "text": json.dumps(result, indent=2, default=str)
                }]
            })
        except Exception as e:
            return create_response(msg_id, {
                "content": [{
                    "type": "text",
                    "text": json.dumps({"error": str(e)})
                }],
                "isError": True
            })

    elif method == "ping":
        return create_response(msg_id, {})

    else:
        return create_error(msg_id, ERROR_CODES["METHOD_NOT_FOUND"], f"Unknown method: {method}")

async def main():
    """Main stdio loop — reads JSON-RPC from stdin, writes responses to stdout."""
    import asyncio

    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

    while True:
        try:
            line = await reader.readline()
            if not line:
                break

            line = line.decode("utf-8").strip()
            if not line:
                continue

            request = json.loads(line)
            response = await handle_request(request)

            if response is not None:
                send_message(response)

        except json.JSONDecodeError:
            if msg_id is not None:
                send_message(create_error(None, ERROR_CODES["PARSE_ERROR"], "Invalid JSON"))
        except Exception as e:
            sys.stderr.write(f"Error: {e}\n")
            sys.stderr.flush()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())