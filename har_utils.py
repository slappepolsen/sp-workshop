"""HAR file utilities: extract cookies and m3u8 URLs."""

import json
import re
import sys
from pathlib import Path
from typing import Optional, List, Tuple, Any, Dict
from urllib.parse import unquote


def extract_cookies_from_har(har_file: Path) -> Optional[str]:
    """Extract cookies from a HAR file for use in requests.

    Returns a cookie string in the format "name1=value1; name2=value2" or None.
    """
    if not har_file or not har_file.exists():
        return None

    try:
        with open(har_file, 'r', encoding='utf-8') as f:
            har_data = json.load(f)

        cookies = {}
        for entry in har_data.get('log', {}).get('entries', []):
            request = entry.get('request', {})
            for header in request.get('headers', []):
                if header.get('name', '').lower() == 'cookie':
                    cookie_header = header.get('value', '')
                    for cookie_pair in cookie_header.split(';'):
                        cookie_pair = cookie_pair.strip()
                        if '=' in cookie_pair:
                            name, value = cookie_pair.split('=', 1)
                            name, value = name.strip(), value.strip()
                            if name:
                                cookies[name] = value
            for cookie in request.get('cookies', []):
                name = cookie.get('name', '')
                value = cookie.get('value', '')
                if name:
                    cookies[name] = value
            response = entry.get('response', {})
            for header in response.get('headers', []):
                if header.get('name', '').lower() == 'set-cookie':
                    cookie_value = header.get('value', '')
                    if '=' in cookie_value:
                        cookie_name = cookie_value.split('=')[0].strip()
                        cookie_val = cookie_value.split('=')[1].split(';')[0].strip()
                        if cookie_name:
                            cookies[cookie_name] = cookie_val

        if cookies:
            return '; '.join(f"{k}={v}" for k, v in sorted(cookies.items()))
    except Exception as e:
        print(f"Error extracting cookies from HAR: {e}")
    return None


def extract_m3u8_urls(har_file: Path) -> List[Tuple[str, Dict[str, Any]]]:
    """Extract unique main m3u8 URLs from HAR file with episode metadata.

    Returns list of (video_id, {"url": ..., "title": ...}).
    """
    with open(har_file, 'r', encoding='utf-8') as f:
        har_data = json.load(f)

    episodes = {}
    for entry in har_data.get('log', {}).get('entries', []):
        url = entry.get('request', {}).get('url', '')

        if 'title=' in url and 'mediaResource=' in url:
            resource_match = re.search(r'/(\d+)\.m3u8', url)
            if resource_match:
                video_id = resource_match.group(1)
                title_match = re.search(r'[?&]title=([^&]+)', url)
                if title_match and video_id not in episodes:
                    episodes[video_id] = {"title": unquote(title_match.group(1)), "url": None}

        if '.m3u8' in url:
            match = re.search(r'/(\d+)\.m3u8($|\?)', url)
            if match and '-manifest-' not in url:
                video_id = match.group(1)
                if video_id in episodes:
                    episodes[video_id]["url"] = url
                else:
                    episodes[video_id] = {"url": url, "title": None}

    sorted_ids = sorted(episodes.keys(), key=int)
    return [(vid, episodes[vid]) for vid in sorted_ids]


def main() -> None:
    """CLI entry point for extract_m3u8."""
    if len(sys.argv) < 2:
        print("Usage: python3 -m har_utils <har_file>")
        sys.exit(1)
    har_path = Path(sys.argv[1])
    episodes = extract_m3u8_urls(har_path)
    print(f"Found {len(episodes)} unique episodes:\n")
    print("=" * 80)
    for video_id, data in episodes:
        title = data.get("title") or "Unknown"
        url = data.get("url") or "No URL found"
        print(f"\nVideo ID: {video_id}")
        print(f"Title: {title}")
        print(f'URL: "{url}"')
    print("\n" + "=" * 80)
    print("\nURLs only (ready to paste):\n")
    for video_id, data in episodes:
        if data.get("url"):
            print(f'"{data["url"]}"')
