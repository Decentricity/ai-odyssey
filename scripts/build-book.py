#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TITLE = "The Odyssey"
SUBTITLE = "Retold in English, with Explanations"
AUTHOR = "Robert David Graham"
UPSTREAM_REPO = "https://github.com/robertdavidgraham/ai-odyssey"
UPSTREAM_BOOK = f"{UPSTREAM_REPO}/tree/main/book"
FORK_REPO = "https://github.com/Decentricity/ai-odyssey"


def run(command: list[str], cwd: Path = ROOT) -> None:
    print("+ " + " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def capture(command: list[str], cwd: Path = ROOT) -> str:
    return subprocess.check_output(command, cwd=cwd, text=True).strip()


def require_tool(name: str) -> None:
    if shutil.which(name) is None:
        raise SystemExit(f"Required tool not found on PATH: {name}")


def note_id(book_number: str, label: str) -> str:
    safe_label = re.sub(r"[^A-Za-z0-9_.-]+", "-", label).strip("-")
    return f"book-{book_number}-note-{safe_label}"


def transform_notes(markdown: str, book_number: str) -> str:
    transformed: list[str] = []
    definition = re.compile(r"^\[\^([^\]]+)\]:\s*(.*)$")
    reference = re.compile(r"\[\^([^\]]+)\]")

    for line in markdown.splitlines():
        match = definition.match(line)
        if match:
            label, body = match.groups()
            anchor = note_id(book_number, label)
            transformed.append(f'<a id="{anchor}"></a>')
            transformed.append(f"{label}. {body}")
            continue

        def replace_ref(ref_match: re.Match[str]) -> str:
            label = ref_match.group(1)
            anchor = note_id(book_number, label)
            return f'<sup><a href="#{anchor}">{label}</a></sup>'

        transformed.append(reference.sub(replace_ref, line))

    return "\n".join(transformed).rstrip() + "\n"


def build_combined_markdown(out_dir: Path, source_date: str) -> Path:
    book_files = sorted((ROOT / "book").glob("*.md"))
    if not book_files:
        raise SystemExit("No Markdown files found in book/")

    upstream_commit = capture(["git", "rev-parse", "upstream/main"])
    out_dir.mkdir(parents=True, exist_ok=True)
    combined = out_dir / "ai-odyssey-complete.md"

    parts = [
        "---",
        f'title: "{TITLE}"',
        f'subtitle: "{SUBTITLE}"',
        f'author: "{AUTHOR}"',
        f'date: "{source_date}"',
        'lang: "en-US"',
        'rights: "Original text by Robert David Graham. Source repository had no license file at conversion time."',
        "---",
        "",
        "# Attribution",
        "",
        "This edition compiles the Markdown files in the `book/` directory of",
        f"Robert David Graham's public GitHub repository `{UPSTREAM_REPO}`.",
        "",
        f"- Upstream repository: {UPSTREAM_REPO}",
        f"- Source path: {UPSTREAM_BOOK}",
        f"- Upstream commit used: `{upstream_commit}`",
        f"- Original author/translator: {AUTHOR}",
        f"- Fork: {FORK_REPO}",
        "",
        "No license file was present in the upstream repository at conversion time.",
        "This fork and the generated files preserve attribution and do not add a",
        "separate license claim.",
        "",
        "# Source Text",
        "",
    ]

    for source in book_files:
        book_number = re.search(r"(\d+)(?=\.md$)", source.name)
        if book_number is None:
            raise SystemExit(f"Cannot derive book number from {source}")
        parts.extend(
            [
                '<div class="page-break"></div>',
                "",
                f"<!-- Source: {source.relative_to(ROOT)} -->",
                "",
                transform_notes(source.read_text(encoding="utf-8"), book_number.group(1)),
                "",
            ]
        )

    combined.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")
    return combined


def copy_outputs(paths: list[Path], shared_dir: Path) -> None:
    shared_dir.mkdir(parents=True, exist_ok=True)
    for path in paths:
        shutil.copy2(path, shared_dir / path.name)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build combined PDF and EPUB editions.")
    parser.add_argument("--out-dir", default=str(ROOT / "dist"))
    parser.add_argument(
        "--shared-dir",
        default="/storage/emulated/0/Download/ai-odyssey",
        help="Android-accessible copy destination.",
    )
    parser.add_argument("--date", default=dt.date.today().isoformat())
    args = parser.parse_args()

    require_tool("pandoc")
    require_tool("chromium")

    out_dir = Path(args.out_dir).resolve()
    shared_dir = Path(args.shared_dir).resolve()
    css = ROOT / "assets" / "book.css"
    combined = build_combined_markdown(out_dir, args.date)
    html = out_dir / "ai-odyssey-complete.html"
    epub = out_dir / "ai-odyssey-complete.epub"
    pdf = out_dir / "ai-odyssey-complete.pdf"

    pandoc_base = [
        "pandoc",
        "--from=markdown+raw_html+smart",
        "--standalone",
        "--toc",
        "--toc-depth=3",
        "--wrap=none",
        "--metadata",
        f"title={TITLE}",
        "--metadata",
        f"subtitle={SUBTITLE}",
        "--metadata",
        f"author={AUTHOR}",
        "--css",
        str(css),
    ]

    run([*pandoc_base, "--embed-resources", str(combined), "-o", str(html)])
    run([*pandoc_base, str(combined), "-o", str(epub)])
    run(
        [
            "chromium",
            "--headless",
            "--no-sandbox",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            f"--print-to-pdf={pdf}",
            f"file://{html}",
        ]
    )
    copy_outputs([combined, html, epub, pdf], shared_dir)

    print(f"Built {combined}")
    print(f"Built {html}")
    print(f"Built {epub}")
    print(f"Built {pdf}")
    print(f"Copied outputs to {shared_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
