from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import fitz


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = BASE_DIR / "notebooks" / "output"
DEFAULT_PDF = BASE_DIR / "Recueil_AMMC_VF_ Mars 2026.pdf"


def link_kind_name(kind: int | None) -> str:
    names = {
        fitz.LINK_GOTO: "goto",
        fitz.LINK_URI: "uri",
        fitz.LINK_LAUNCH: "launch",
        fitz.LINK_GOTOR: "gotor",
        fitz.LINK_NAMED: "named",
    }
    return names.get(kind, str(kind))


def extract_links(pdf_path: str | Path, *, with_source_text: bool = False) -> list[dict[str, Any]]:
    doc = fitz.open(pdf_path)
    links: list[dict[str, Any]] = []
    for page_index, page in enumerate(doc):
        for link in page.get_links():
            rect = link.get("from")
            item: dict[str, Any] = {
                "source_page": page_index + 1,
                "kind": link_kind_name(link.get("kind")),
                "xref": link.get("xref"),
            }
            if with_source_text and rect:
                source_text = page.get_textbox(rect).strip()
                item["source_text"] = " ".join(source_text.split())
            if rect:
                item["source_rect"] = [rect.x0, rect.y0, rect.x1, rect.y1]
            if "page" in link:
                item["target_page"] = int(link["page"]) + 1
            if "to" in link and link["to"]:
                point = link["to"]
                item["target_point"] = [point.x, point.y]
            for key in ("uri", "file", "id", "name"):
                if link.get(key):
                    item[key] = link[key]
            links.append(item)
    return links


def write_jsonl(items: list[dict[str, Any]], output_path: str | Path) -> None:
    with Path(output_path).open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract PDF link annotations as JSONL.")
    parser.add_argument("pdf_path", nargs="?", default=str(DEFAULT_PDF))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_DIR / "pdf_links.jsonl"))
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--with-source-text", action="store_true", help="Also extract text under each link rectangle.")
    args = parser.parse_args()

    links = extract_links(args.pdf_path, with_source_text=args.with_source_text)
    write_jsonl(links, args.output)
    counts: dict[str, int] = {}
    for link in links:
        counts[link["kind"]] = counts.get(link["kind"], 0) + 1
    print(f"wrote_links={args.output}")
    print(f"links={len(links)} " + ", ".join(f"{kind}={count}" for kind, count in sorted(counts.items())))
    for link in links[: args.limit]:
        print(
            f"p{link['source_page']} {link['kind']} -> "
            f"{link.get('target_page') or link.get('uri') or link.get('file') or '?'} | "
            f"{link.get('source_text', '')[:140]}"
        )


if __name__ == "__main__":
    main()
