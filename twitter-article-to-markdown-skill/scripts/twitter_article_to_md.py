from __future__ import annotations

import argparse
import re
import shutil
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}


def clean_filename(value: str, fallback: str = "twitter-article") -> str:
    value = re.sub(r"[\\/:*?\"<>|]", "", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:100] or fallback


def read_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="ignore")


def ensure_dependencies():
    try:
        from bs4 import BeautifulSoup
        from markdownify import markdownify
    except ModuleNotFoundError as exc:
        missing = exc.name or "required package"
        raise SystemExit(
            f"Missing Python package: {missing}\n"
            "Install dependencies with:\n"
            "python -m pip install beautifulsoup4 markdownify"
        )
    return BeautifulSoup, markdownify


def extract_title(soup, html_file: Path) -> str:
    candidates = [
        soup.find("meta", attrs={"property": "og:title"}),
        soup.find("meta", attrs={"name": "twitter:title"}),
    ]
    for item in candidates:
        content = item.get("content") if item else None
        if content:
            return content.strip()

    if soup.title and soup.title.get_text(strip=True):
        return soup.title.get_text(strip=True)

    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(strip=True)

    return html_file.stem


def extract_author(soup) -> str:
    candidates = [
        soup.find("meta", attrs={"name": "author"}),
        soup.find("meta", attrs={"property": "article:author"}),
    ]
    for item in candidates:
        content = item.get("content") if item else None
        if content:
            return content.strip()
    return ""


def normalize_local_src(src: str) -> str:
    parsed = urlparse(src)
    if parsed.scheme in {"http", "https", "data"}:
        return src
    if parsed.scheme == "file":
        return unquote(parsed.path.lstrip("/"))
    return unquote(src)


def article_id_from_html(html_file: Path) -> str:
    match = re.match(r"(\d+)", html_file.stem)
    if match:
        return match.group(1)
    return html_file.stem.split("_")[0]


def related_images(html_file: Path) -> list[Path]:
    article_id = article_id_from_html(html_file)
    images: list[Path] = []
    for path in html_file.parent.iterdir():
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            if path.stem.startswith(article_id):
                images.append(path)
    return sorted(images)


def remove_noise(soup) -> None:
    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()

    for tag in soup.find_all(["button", "input", "textarea", "select"]):
        tag.decompose()


def rewrite_and_copy_images(soup, html_file: Path, assets_dir: Path) -> None:
    assets_dir.mkdir(parents=True, exist_ok=True)

    sibling_images = {image.name: image for image in related_images(html_file)}

    for image in sibling_images.values():
        target = assets_dir / image.name
        if not target.exists():
            shutil.copy2(image, target)

    for img in soup.find_all("img"):
        src = img.get("src")
        if not src:
            continue

        normalized = normalize_local_src(src)
        filename = Path(normalized).name
        if filename in sibling_images:
            img["src"] = f"{assets_dir.name}/{filename}"


def html_to_markdown(html_file: Path, output_dir: Path, source_url: str = "") -> Path:
    BeautifulSoup, markdownify = ensure_dependencies()
    html = read_text(html_file)
    soup = BeautifulSoup(html, "html.parser")
    remove_noise(soup)

    title = extract_title(soup, html_file)
    author = extract_author(soup)
    slug = clean_filename(title, fallback=html_file.stem)
    assets_dir = output_dir / f"{slug}.assets"

    rewrite_and_copy_images(soup, html_file, assets_dir)

    content_root = soup.body or soup
    markdown = markdownify(str(content_root), heading_style="ATX")
    markdown = re.sub(r"\n{3,}", "\n\n", markdown).strip()

    frontmatter = [
        "---",
        f'title: "{title.replace(chr(34), chr(39))}"',
        f'source_url: "{source_url}"',
        f'html_source: "{html_file}"',
        f'converted_at: "{datetime.now().isoformat(timespec="seconds")}"',
    ]
    if author:
        frontmatter.append(f'author: "{author.replace(chr(34), chr(39))}"')
    frontmatter.append("---")

    out_file = output_dir / f"{slug}.md"
    final_text = "\n".join(frontmatter) + f"\n\n# {title}\n\n"
    if source_url:
        final_text += f"原文：{source_url}\n\n"
    final_text += markdown + "\n"

    output_dir.mkdir(parents=True, exist_ok=True)
    out_file.write_text(final_text, encoding="utf-8")
    return out_file


def find_html_files(downloads_dir: Path, latest_only: bool) -> list[Path]:
    files = sorted(
        list(downloads_dir.rglob("*.htm")) + list(downloads_dir.rglob("*.html")),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    return files[:1] if latest_only else files


def parse_args() -> argparse.Namespace:
    default_root = Path.home() / "Desktop" / "twitter-cli"
    parser = argparse.ArgumentParser(description="Convert downloaded X/Twitter article HTML files to Markdown.")
    parser.add_argument("--root", type=Path, default=default_root, help="twitter-cli workspace root.")
    parser.add_argument("--downloads", type=Path, default=None, help="Directory containing gallery-dl downloads.")
    parser.add_argument("--output", type=Path, default=None, help="Directory for Markdown output.")
    parser.add_argument("--source-url", default="", help="Original X/Twitter URL to write into front matter.")
    parser.add_argument("--latest-only", action="store_true", help="Convert only the newest HTML file.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    downloads_dir = args.downloads or args.root / "downloads"
    output_dir = args.output or args.root / "markdown"

    if not downloads_dir.exists():
        print(f"Downloads directory does not exist: {downloads_dir}")
        return 1

    html_files = find_html_files(downloads_dir, latest_only=args.latest_only)
    if not html_files:
        print(f"No HTML files found in: {downloads_dir}")
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    for html_file in html_files:
        out_file = html_to_markdown(html_file, output_dir, source_url=args.source_url)
        print(f"OK: {html_file} -> {out_file}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
