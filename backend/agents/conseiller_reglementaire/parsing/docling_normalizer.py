from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


REF_RE = re.compile(r"^#/(?P<collection>[a-z_]+)/(?P<index>\d+)$")


@dataclass(frozen=True)
class NormalizedBlock:
    id: str
    self_ref: str
    parent_ref: str | None
    page: int
    text: str
    label: str
    content_layer: str
    x0: float
    y0: float
    x1: float
    y1: float
    width: float
    height: float
    x_center: float
    y_center: float
    is_table: bool
    is_picture: bool
    is_group_child: bool
    is_header_candidate: bool
    is_footer_candidate: bool


def load_docling_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def build_ref_index(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    refs: dict[str, dict[str, Any]] = {}
    for collection in ("texts", "groups", "tables", "pictures"):
        for item in doc.get(collection, []):
            self_ref = item.get("self_ref")
            if self_ref:
                refs[self_ref] = item
    refs["#/body"] = doc.get("body", {})
    refs["#/furniture"] = doc.get("furniture", {})
    return refs


def ref_parent(item: dict[str, Any], inherited_parent: str | None = None) -> str | None:
    parent = item.get("parent")
    if isinstance(parent, dict) and "$ref" in parent:
        return parent["$ref"]
    return inherited_parent


def first_prov(item: dict[str, Any]) -> dict[str, Any] | None:
    prov = item.get("prov")
    if isinstance(prov, list) and prov:
        return prov[0]
    return None


def bbox_from_item(item: dict[str, Any]) -> tuple[int, float, float, float, float] | None:
    prov = first_prov(item)
    if not prov:
        return None
    bbox = prov.get("bbox") or {}
    try:
        return (
            int(prov["page_no"]),
            float(bbox["l"]),
            float(bbox["b"]),
            float(bbox["r"]),
            float(bbox["t"]),
        )
    except (KeyError, TypeError, ValueError):
        return None


def table_text(table: dict[str, Any]) -> str:
    cells = table.get("data", {}).get("table_cells", [])
    if not cells:
        return ""

    max_row = 0
    max_col = 0
    for cell in cells:
        max_row = max(max_row, int(cell.get("end_row_offset_idx", cell.get("start_row_offset_idx", 0) + 1)))
        max_col = max(max_col, int(cell.get("end_col_offset_idx", cell.get("start_col_offset_idx", 0) + 1)))

    grid = [["" for _ in range(max_col)] for _ in range(max_row)]
    for cell in cells:
        row = int(cell.get("start_row_offset_idx", 0))
        col = int(cell.get("start_col_offset_idx", 0))
        text = normalize_space(cell.get("text", "")).replace("|", "/")
        if not (0 <= row < max_row and 0 <= col < max_col):
            continue
        if grid[row][col]:
            grid[row][col] = f"{grid[row][col]} {text}".strip()
        else:
            grid[row][col] = text

    lines: list[str] = []
    for values in grid:
        if any(values):
            lines.append(" | ".join(values))
    return "\n".join(lines)


def normalize_space(text: str) -> str:
    text = text or ""
    text = text.translate(
        str.maketrans(
            {
                "\uf02d": "-",
                "\uf0b7": "-",
                "\uf0ac": "",
                "\uf0e0": "",
            }
        )
    )
    return re.sub(r"\s+", " ", text).strip()


def iter_body_leaf_refs(
    doc: dict[str, Any],
    refs: dict[str, dict[str, Any]],
) -> Iterable[tuple[str, dict[str, Any], str | None, bool]]:
    def visit(ref: str, inherited_parent: str | None, is_group_child: bool):
        item = refs.get(ref)
        if not item:
            return

        label = item.get("label", "")
        children = item.get("children") or []
        if children and label in {"list", "form_area", "key_value_area"}:
            for child in children:
                child_ref = child.get("$ref")
                if child_ref:
                    yield from visit(child_ref, ref, True)
            return

        yield ref, item, ref_parent(item, inherited_parent), is_group_child

    for child in doc.get("body", {}).get("children", []):
        child_ref = child.get("$ref")
        if child_ref:
            yield from visit(child_ref, "#/body", False)


def normalize_docling(doc: dict[str, Any]) -> list[NormalizedBlock]:
    refs = build_ref_index(doc)
    blocks: list[NormalizedBlock] = []

    for ref, item, parent_ref, is_group_child in iter_body_leaf_refs(doc, refs):
        bbox = bbox_from_item(item)
        if not bbox:
            continue

        page, x0, y0, x1, y1 = bbox
        label = item.get("label", "")
        content_layer = item.get("content_layer", "")
        text = table_text(item) if label in {"table", "document_index"} else normalize_space(item.get("text", ""))

        width = x1 - x0
        height = y1 - y0
        blocks.append(
            NormalizedBlock(
                id=f"p{page}:{ref}",
                self_ref=ref,
                parent_ref=parent_ref,
                page=page,
                text=text,
                label=label,
                content_layer=content_layer,
                x0=x0,
                y0=y0,
                x1=x1,
                y1=y1,
                width=width,
                height=height,
                x_center=x0 + width / 2,
                y_center=y0 + height / 2,
                is_table=label in {"table", "document_index"},
                is_picture=label == "picture",
                is_group_child=is_group_child,
                is_header_candidate=label == "page_header" or y1 >= 780,
                is_footer_candidate=label == "page_footer" or y0 <= 60,
            )
        )

    return blocks


def page_blocks(blocks: Iterable[NormalizedBlock], page: int) -> list[NormalizedBlock]:
    return [block for block in blocks if block.page == page]


def is_full_width(block: NormalizedBlock, page_width: float = 595.32) -> bool:
    return block.width >= page_width * 0.58 or block.x0 < 95 and block.x1 > 500


def reading_order_key(block: NormalizedBlock) -> tuple[int, int, float, float]:
    if block.is_header_candidate and block.label == "page_header":
        return (0, 0, -block.y1, block.x0)
    if block.is_footer_candidate and block.label == "page_footer":
        return (9, 0, -block.y1, block.x0)

    # Centered legal titles are not always wide enough to pass a pure width test.
    # They still need to stay above the two-column body.
    is_top_title = block.label == "section_header" and block.y0 >= 700 and block.x0 < 210 and block.x1 > 380
    if is_top_title:
        return (1, 0, -block.y1, block.x0)
    if is_full_width(block) and block.y0 >= 640:
        return (1, 1, -block.y1, block.x0)

    column = 0 if block.x_center < 300 else 1
    return (2, column, -block.y1, block.x0)


def reconstruct_reading_order(
    blocks: Iterable[NormalizedBlock],
    *,
    keep_furniture: bool = False,
    keep_footnotes: bool = True,
) -> list[NormalizedBlock]:
    selected = []
    for block in blocks:
        if not keep_furniture and (
            block.content_layer == "furniture"
            or block.label in {"page_header", "page_footer"}
        ):
            continue
        if not keep_footnotes and block.label == "footnote":
            continue
        selected.append(block)
    return sorted(selected, key=reading_order_key)


def blocks_to_jsonl(blocks: Iterable[NormalizedBlock], output_path: str | Path) -> None:
    with Path(output_path).open("w", encoding="utf-8") as f:
        for block in blocks:
            f.write(json.dumps(asdict(block), ensure_ascii=False) + "\n")


def preview_page(
    blocks: Iterable[NormalizedBlock],
    page: int,
    *,
    keep_furniture: bool = False,
    limit: int | None = None,
) -> str:
    ordered = reconstruct_reading_order(
        page_blocks(blocks, page),
        keep_furniture=keep_furniture,
    )
    if limit is not None:
        ordered = ordered[:limit]

    lines = [f"=== PAGE {page} ({len(ordered)} blocks) ==="]
    for block in ordered:
        text = block.text.replace("\n", " / ")
        if len(text) > 180:
            text = text[:177] + "..."
        lines.append(
            f"{block.self_ref:>15} {block.label:<15} "
            f"x={block.x0:5.1f}-{block.x1:5.1f} "
            f"y={block.y0:5.1f}-{block.y1:5.1f} | {text}"
        )
    return "\n".join(lines)


def parse_pages(value: str) -> list[int]:
    pages: list[int] = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            pages.extend(range(int(start), int(end) + 1))
        else:
            pages.append(int(part))
    return pages


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize and inspect a Docling JSON document.")
    parser.add_argument(
        "json_path",
        nargs="?",
        default="parsing/notebooks/output/docling_raw.json",
        help="Path to docling_raw.json.",
    )
    parser.add_argument("--pages", default="15,33,41,670,763", help="Pages to preview, e.g. 15,33,41 or 15-17.")
    parser.add_argument("--limit", type=int, default=None, help="Max blocks per page preview.")
    parser.add_argument("--keep-furniture", action="store_true", help="Keep page headers and footers in previews.")
    parser.add_argument("--jsonl-output", help="Optional path to write all normalized blocks as JSONL.")
    args = parser.parse_args()

    doc = load_docling_json(args.json_path)
    blocks = normalize_docling(doc)

    print(f"normalized_blocks={len(blocks)}")
    print(
        "labels="
        + ", ".join(
            f"{label}:{count}"
            for label, count in sorted(
                ((label, sum(1 for block in blocks if block.label == label)) for label in {b.label for b in blocks}),
                key=lambda item: (-item[1], item[0]),
            )
        )
    )

    if args.jsonl_output:
        blocks_to_jsonl(blocks, args.jsonl_output)
        print(f"wrote_jsonl={args.jsonl_output}")

    for page in parse_pages(args.pages):
        print()
        print(preview_page(blocks, page, keep_furniture=args.keep_furniture, limit=args.limit))


if __name__ == "__main__":
    main()
