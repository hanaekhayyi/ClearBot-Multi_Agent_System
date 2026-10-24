from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import fitz


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = BASE_DIR / "notebooks" / "output"
DEFAULT_PDF = BASE_DIR / "Recueil_AMMC_VF_ Mars 2026.pdf"


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(items: list[dict[str, Any]], output_path: str | Path) -> None:
    with Path(output_path).open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def rect_top_to_bottom(rect: list[float], page_height: float) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = rect
    return x0, page_height - y1, x1, page_height - y0


def point_top_to_bottom(point: list[float], page_height: float) -> tuple[float, float]:
    x, y = point
    return x, page_height - y


def overlap_area(a: tuple[float, float, float, float], b: dict[str, Any]) -> float:
    x0 = max(a[0], float(b["x0"]))
    y0 = max(a[1], float(b["y0"]))
    x1 = min(a[2], float(b["x1"]))
    y1 = min(a[3], float(b["y1"]))
    if x1 <= x0 or y1 <= y0:
        return 0.0
    return (x1 - x0) * (y1 - y0)


def distance_to_rect(point: tuple[float, float], block: dict[str, Any]) -> float:
    x, y = point
    x0, y0, x1, y1 = float(block["x0"]), float(block["y0"]), float(block["x1"]), float(block["y1"])
    dx = max(x0 - x, 0.0, x - x1)
    dy = max(y0 - y, 0.0, y - y1)
    return dx * dx + dy * dy


def best_block_for_rect(blocks: list[dict[str, Any]], rect: tuple[float, float, float, float]) -> dict[str, Any] | None:
    if not blocks:
        return None
    overlaps = [(overlap_area(rect, block), block) for block in blocks]
    overlaps = [item for item in overlaps if item[0] > 0]
    if overlaps:
        return max(overlaps, key=lambda item: item[0])[1]
    center = ((rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2)
    return min(blocks, key=lambda block: distance_to_rect(center, block))


def best_block_for_point(blocks: list[dict[str, Any]], point: tuple[float, float]) -> dict[str, Any] | None:
    if not blocks:
        return None
    return min(blocks, key=lambda block: distance_to_rect(point, block))


def build_indexes(
    blocks: list[dict[str, Any]], chunks: list[dict[str, Any]]
) -> tuple[dict[int, list[dict[str, Any]]], dict[str, dict[str, Any]], dict[int, list[dict[str, Any]]]]:
    blocks_by_page: dict[int, list[dict[str, Any]]] = {}
    for block in blocks:
        blocks_by_page.setdefault(int(block["page"]), []).append(block)

    chunk_by_ref: dict[str, dict[str, Any]] = {}
    chunks_by_page: dict[int, list[dict[str, Any]]] = {}
    for chunk in chunks:
        for ref in chunk.get("block_refs", []):
            chunk_by_ref[ref] = chunk
        for page in range(int(chunk["page_start"]), int(chunk["page_end"]) + 1):
            chunks_by_page.setdefault(page, []).append(chunk)
    return blocks_by_page, chunk_by_ref, chunks_by_page


def chunk_for_block(block: dict[str, Any] | None, chunk_by_ref: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    if not block:
        return None
    return chunk_by_ref.get(block.get("self_ref"))


def fallback_chunk_for_page(page: int, chunks_by_page: dict[int, list[dict[str, Any]]]) -> dict[str, Any] | None:
    chunks = chunks_by_page.get(page, [])
    return chunks[0] if chunks else None


def map_links(
    links: list[dict[str, Any]],
    blocks: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    pdf_path: str | Path,
) -> list[dict[str, Any]]:
    pdf = fitz.open(pdf_path)
    page_heights = {index + 1: page.rect.height for index, page in enumerate(pdf)}
    blocks_by_page, chunk_by_ref, chunks_by_page = build_indexes(blocks, chunks)

    mapped: list[dict[str, Any]] = []
    for link in links:
        item = dict(link)
        source_page = int(link["source_page"])
        source_block = None
        if link.get("source_rect"):
            source_rect = rect_top_to_bottom(link["source_rect"], page_heights[source_page])
            source_block = best_block_for_rect(blocks_by_page.get(source_page, []), source_rect)
        source_chunk = chunk_for_block(source_block, chunk_by_ref)
        if source_block:
            item["source_block_ref"] = source_block.get("self_ref")
        if source_chunk:
            item["source_chunk_id"] = source_chunk.get("chunk_id")
            item["source_chunk_name"] = source_chunk.get("article_id")

        target_chunk = None
        target_page = link.get("target_page")
        if target_page:
            target_page = int(target_page)
            target_block = None
            if link.get("target_point") and target_page in page_heights:
                target_point = point_top_to_bottom(link["target_point"], page_heights[target_page])
                target_block = best_block_for_point(blocks_by_page.get(target_page, []), target_point)
            target_chunk = chunk_for_block(target_block, chunk_by_ref) or fallback_chunk_for_page(target_page, chunks_by_page)
            if target_block:
                item["target_block_ref"] = target_block.get("self_ref")
            if target_chunk:
                item["target_chunk_id"] = target_chunk.get("chunk_id")
                item["target_chunk_name"] = target_chunk.get("article_id")
        mapped.append(item)
    return mapped


def main() -> None:
    parser = argparse.ArgumentParser(description="Map extracted PDF links to normalized blocks and legal chunks.")
    parser.add_argument("--pdf", default=str(DEFAULT_PDF))
    parser.add_argument("--links", default=str(DEFAULT_OUTPUT_DIR / "pdf_links.jsonl"))
    parser.add_argument("--blocks", default=str(DEFAULT_OUTPUT_DIR / "normalized_blocks.jsonl"))
    parser.add_argument("--chunks", default=str(DEFAULT_OUTPUT_DIR / "legal_chunks.jsonl"))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_DIR / "pdf_links_mapped.jsonl"))
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    links = load_jsonl(args.links)
    blocks = load_jsonl(args.blocks)
    chunks = load_jsonl(args.chunks)
    mapped = map_links(links, blocks, chunks, args.pdf)
    write_jsonl(mapped, args.output)

    source_hits = sum(1 for link in mapped if link.get("source_chunk_id"))
    target_hits = sum(1 for link in mapped if link.get("target_chunk_id"))
    both_hits = sum(1 for link in mapped if link.get("source_chunk_id") and link.get("target_chunk_id"))
    print(f"wrote_mapped_links={args.output}")
    print(f"links={len(mapped)} source_chunk={source_hits} target_chunk={target_hits} both={both_hits}")
    for link in mapped[: args.limit]:
        print(
            f"p{link['source_page']} {link['kind']} -> {link.get('target_page') or link.get('uri') or '?'} | "
            f"src={link.get('source_chunk_name') or '-'} | tgt={link.get('target_chunk_name') or '-'}"
        )


if __name__ == "__main__":
    main()
