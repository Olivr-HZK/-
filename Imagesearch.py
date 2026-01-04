# coding=utf-8
"""
ImageSearch: enrich ai_result.json with local images and interactive card payloads.

Changes:
- Uses serper.dev image search (SERPER_API_KEY) instead of Bing.
- Builds high-intent queries (e.g., "<title> official poster" / "promotional background") to fetch promotional-quality assets.
- Stores images locally under ./image for manual QA.
- Outputs ai_result_with_images.json mirroring ai_result.json plus image_path and a Feishu interactive card payload (img_key is a local placeholder; no Feishu upload).

Env vars:
  SERPER_API_KEY           (required)
  AI_RESULT_PATH           (default /app/output/ai_result.json)
  AI_RESULT_WITH_IMAGES_PATH (default /app/output/ai_result_with_images.json)
  IMAGE_DIR                (default ./image)
"""

import base64
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import requests

SERPER_IMAGE_URL = "https://google.serper.dev/images"


def load_ai_results(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: Dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def extract_trends(ai_data: Dict) -> List[Tuple[str, Dict]]:
    if "google_trend_ai" in ai_data and isinstance(ai_data["google_trend_ai"], dict):
        ai_data = ai_data["google_trend_ai"]
    trends = []
    for title, payload in ai_data.items():
        if isinstance(payload, dict):
            trends.append((title, payload))
    return trends


def safe_filename(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "_", text).strip("_")
    return text or "image"


def build_query(title: str) -> str:
    base = title.split("[")[0].strip() or title.strip()
    # Heuristic: entertainment/IP keywords
    entertainment_keywords = ["movie", "film", "episode", "season", "trailer", "show", "series", "poster", "drama"]
    if any(k.lower() in base.lower() for k in entertainment_keywords):
        return f"{base} official poster background"
    return f"{base} promotional background"


def search_image_serper(query: str, api_key: str) -> Optional[str]:
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    payload = {"q": query, "num": 5, "gl": "us"}
    try:
        resp = requests.post(SERPER_IMAGE_URL, headers=headers, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        images = data.get("images") or []
        if not images:
            return None
        return images[0].get("imageUrl") or images[0].get("thumbnailUrl")
    except Exception as exc:
        print(f"[WARN] Serper search failed for '{query}': {exc}")
        return None


def download_image(url: str) -> Optional[bytes]:
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        return resp.content
    except Exception as exc:
        print(f"[WARN] Download image failed: {exc}")
        return None


def save_image(image_bytes: bytes, folder: Path, filename: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{filename}.jpg"
    with open(path, "wb") as f:
        f.write(image_bytes)
    return path


def build_card_payload(title: str, payload: Dict, image_path: Path) -> Dict:
    score = payload.get("usability_score", "")
    rank = payload.get("ranks", [""])[0] if isinstance(payload.get("ranks"), list) else payload.get("ranks", "")
    analysis = payload.get("analysis", {}) if isinstance(payload, dict) else {}

    summary = analysis.get("summary") or ""
    nature = analysis.get("nature") or ""
    ua_inspiration = analysis.get("ua_inspiration") or ""
    suitability = analysis.get("ai_suitability_check") or ""

    # img_key is a local placeholder; Feishu cards need an upload. Left for later wiring.
    return {
        "config": {"wide_screen_mode": True},
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**{title}**\n⭐ 评分: {score}\n🔥 排名: {rank}\n\n📝 {summary}\n🎭 {nature}\n🎯 {ua_inspiration}\n🤖 {suitability}",
                },
            },
            {
                "tag": "img",
                "img_key": f"local://{image_path}",  # placeholder for later upload
                "alt": {"tag": "plain_text", "content": title},
            },
        ],
    }


def main() -> int:
    serper_key = os.environ.get("SERPER_API_KEY")
    if not serper_key:
        print("❌ Missing SERPER_API_KEY")
        return 1

    ai_result_path = os.environ.get("AI_RESULT_PATH", "/app/output/ai_result.json")
    out_path = os.environ.get("AI_RESULT_WITH_IMAGES_PATH", "/app/output/ai_result_with_images.json")
    image_dir = Path(os.environ.get("IMAGE_DIR", "./image"))

    try:
        ai_data = load_ai_results(ai_result_path)
    except Exception as exc:
        print(f"❌ Failed to load ai_result.json: {exc}")
        return 1

    trends = extract_trends(ai_data)
    print(f"Found {len(trends)} topics, start serper image search...")

    for title, payload in trends:
        query = build_query(title)
        img_url = search_image_serper(query, serper_key)
        if not img_url:
            print(f"[WARN] No image found for '{title}'")
            continue

        img_bytes = download_image(img_url)
        if not img_bytes:
            print(f"[WARN] Failed to download image for '{title}'")
            continue

        filename = safe_filename(title)
        img_path = save_image(img_bytes, image_dir, filename)

        if isinstance(payload, dict):
            payload["image_path"] = str(img_path)
            # include base64 for downstream if needed
            payload["image_base64"] = base64.b64encode(img_bytes).decode("utf-8")
            payload["card"] = build_card_payload(title, payload, img_path)

        print(f"[OK] {title} -> saved {img_path}")

    try:
        save_json(out_path, ai_data)
        print(f"✅ Saved enriched JSON to {out_path}")
    except Exception as exc:
        print(f"❌ Failed to save output JSON: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
