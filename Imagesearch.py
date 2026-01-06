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
import io
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import requests

try:
    from PIL import Image  # pillow, 用于标准化图片格式
except ImportError:
    Image = None

SERPER_IMAGE_URL = "https://google.serper.dev/images"


def load_ai_results(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: Dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def extract_trends(ai_data) -> List[Tuple[str, Dict]]:
    """兼容 dict / list 包裹的结果"""
    if isinstance(ai_data, list):
        # 兼容 GPT 返回的单元素列表
        if ai_data and isinstance(ai_data[0], dict):
            ai_data = ai_data[0]
        else:
            return []

    if isinstance(ai_data, dict) and "google_trend_ai" in ai_data and isinstance(ai_data["google_trend_ai"], dict):
        ai_data = ai_data["google_trend_ai"]

    if not isinstance(ai_data, dict):
        return []

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


def search_image_serper(query: str, api_key: str) -> List[str]:
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    payload = {"q": query, "num": 5, "gl": "us"}
    try:
        resp = requests.post(SERPER_IMAGE_URL, headers=headers, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        images = data.get("images") or []
        urls: List[str] = []
        for img in images:
            url = img.get("imageUrl") or img.get("thumbnailUrl")
            if not url:
                continue
            lower = url.lower()
            # 仅接受常见的无损/有损可识别格式
            if any(ext in lower for ext in [".jpg", ".jpeg", ".png"]):
                urls.append(url)
        return urls
    except Exception as exc:
        print(f"[WARN] Serper search failed for '{query}': {exc}")
        return []


def download_image(url: str) -> Optional[bytes]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.google.com/",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=20, allow_redirects=True, verify=False)  # 忽略 SSL 校验
        resp.raise_for_status()
        return resp.content
    except Exception as exc:
        print(f"[WARN] Download image failed: {exc}")
        return None


def save_image(image_bytes: bytes, folder: Path, filename: str) -> Optional[Path]:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{filename}.jpg"
    if Image is None:
        try:
            with open(path, "wb") as f:
                f.write(image_bytes)
            return path
        except Exception as exc:
            print(f"❌ 保存图片失败: {exc}")
            return None

    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.save(path, format="JPEG", quality=90)
        return path
    except Exception as exc:
        print(f"❌ 格式转换失败: {exc}")
        return None


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
        candidate_urls = search_image_serper(query, serper_key)
        if not candidate_urls:
            print(f"[WARN] No image found for '{title}'")
            continue
        img_bytes = None
        src_url = ""
        for u in candidate_urls[:5]:
            if "tiktok.com" in u.lower():
                continue  # 避免常见的 SSL/防爬失败域
            img_bytes = download_image(u)
            if img_bytes:
                src_url = u
                break
        if not img_bytes:
            print(f"[WARN] Failed to download image for '{title}' from top results")
            continue

        filename = safe_filename(title)
        img_path = save_image(img_bytes, image_dir, filename)
        if not img_path:
            print(f"[WARN] Failed to save image for '{title}'")
            continue

        if isinstance(payload, dict):
            payload["image_path"] = str(img_path)
            # include base64 for downstream if needed
            payload["image_base64"] = base64.b64encode(img_bytes).decode("utf-8")
            payload["card"] = build_card_payload(title, payload, img_path)
            payload["image_source_url"] = src_url

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
