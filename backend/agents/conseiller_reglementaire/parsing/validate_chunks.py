from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ARTICLE_NUM_RE = re.compile(r"^Article\s+(?P<num>\d+)(?:\D|$)", re.IGNORECASE)
ARTICLE_IN_CONTEXT_RE = re.compile(r"\bArticle\s*\d+", re.IGNORECASE)
FOOTNOTE_NUM_RE = re.compile(r"^(?P<num>\d+)\b")


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def article_number(article_id: str) -> int | None:
    match = ARTICLE_NUM_RE.match(article_id or "")
    if not match:
        return None
    return int(match.group("num"))


def validate_chunks(chunks: list[dict[str, Any]]) -> dict[str, Any]:
    report: dict[str, Any] = {
        "total_chunks": len(chunks),
        "counts": {},
        "errors": [],
        "warnings": [],
    }
    counts = Counter(chunk.get("chunk_type") for chunk in chunks)
    report["counts"] = dict(sorted(counts.items()))
    article_chunks = [chunk for chunk in chunks if chunk.get("chunk_type") == "article"]
    annexe_chunks = [chunk for chunk in chunks if str(chunk.get("chunk_type", "")).startswith("annexe")]
    chunk_ids = [chunk.get("chunk_id") for chunk in chunks if chunk.get("chunk_id")]

    report["hierarchy_coverage"] = {
        "chunks_with_chunk_id": len(chunk_ids),
        "unique_chunk_ids": len(set(chunk_ids)),
        "article_chunks": len(article_chunks),
        "articles_with_document": sum(1 for chunk in article_chunks if chunk.get("document")),
        "articles_with_livre": sum(1 for chunk in article_chunks if chunk.get("livre")),
        "articles_with_titre": sum(1 for chunk in article_chunks if chunk.get("titre")),
        "articles_with_chapitre": sum(1 for chunk in article_chunks if chunk.get("chapitre")),
        "articles_with_section": sum(1 for chunk in article_chunks if chunk.get("section")),
        "annexe_chunks": len(annexe_chunks),
        "annexe_chunks_with_annexe": sum(1 for chunk in annexe_chunks if chunk.get("annexe")),
        "unique_documents": len({chunk.get("document") for chunk in chunks if chunk.get("document")}),
        "unique_livres": len({chunk.get("livre") for chunk in chunks if chunk.get("livre")}),
        "unique_titres": len({chunk.get("titre") for chunk in chunks if chunk.get("titre")}),
        "unique_chapitres": len({chunk.get("chapitre") for chunk in chunks if chunk.get("chapitre")}),
        "unique_sections": len({chunk.get("section") for chunk in chunks if chunk.get("section")}),
        "unique_annexes": len({chunk.get("annexe") for chunk in chunks if chunk.get("annexe")}),
    }

    table_chunks = [chunk for chunk in chunks if any(str(ref).startswith("#/tables/") for ref in chunk.get("block_refs", []))]
    table_refs = sorted(
        {ref for chunk in chunks for ref in chunk.get("block_refs", []) if str(ref).startswith("#/tables/")},
        key=lambda ref: int(str(ref).rsplit("/", 1)[-1]),
    )
    report["table_coverage"] = {
        "chunks_with_tables": len(table_chunks),
        "table_refs_in_chunks": len(table_refs),
        "article_chunks_with_tables": sum(1 for chunk in table_chunks if chunk.get("chunk_type") == "article"),
        "annexe_chunks_with_tables": sum(1 for chunk in table_chunks if str(chunk.get("chunk_type", "")).startswith("annexe")),
    }

    footnote_chunks = [chunk for chunk in chunks if chunk.get("footnotes")]
    footnotes = [note for chunk in chunks for note in chunk.get("footnotes", [])]
    numbered_footnotes = [note for note in footnotes if FOOTNOTE_NUM_RE.match(str(note).strip())]
    continuation_footnotes = [note for note in footnotes if not FOOTNOTE_NUM_RE.match(str(note).strip())]
    marker_hits = 0
    for chunk in footnote_chunks:
        text = chunk.get("text", "")
        note_nums = [
            match.group("num")
            for note in chunk.get("footnotes", [])
            for match in [FOOTNOTE_NUM_RE.match(str(note).strip())]
            if match
        ]
        if any(re.search(rf"(?<!\d){re.escape(num)}(?!\d)", text) for num in note_nums):
            marker_hits += 1
    report["footnote_coverage"] = {
        "chunks_with_footnotes": len(footnote_chunks),
        "footnotes": len(footnotes),
        "numbered_footnotes": len(numbered_footnotes),
        "continuation_footnotes": len(continuation_footnotes),
        "chunks_with_numeric_marker_match": marker_hits,
    }

    empty = [chunk for chunk in chunks if not (chunk.get("text") or "").strip()]
    if empty:
        report["errors"].append({"kind": "empty_chunks", "count": len(empty)})

    no_document = [chunk for chunk in chunks if chunk.get("chunk_type") == "article" and not chunk.get("document")]
    if no_document:
        report["errors"].append({"kind": "article_chunks_without_document", "count": len(no_document)})

    missing_chunk_id = [chunk for chunk in chunks if not chunk.get("chunk_id")]
    if missing_chunk_id:
        report["errors"].append({"kind": "chunks_without_chunk_id", "count": len(missing_chunk_id)})

    duplicated_chunk_ids = [chunk_id for chunk_id, count in Counter(chunk_ids).items() if count > 1]
    if duplicated_chunk_ids:
        report["errors"].append(
            {"kind": "duplicate_chunk_ids", "count": len(duplicated_chunk_ids), "sample": duplicated_chunk_ids[:10]}
        )

    no_annexe_parent = [chunk for chunk in annexe_chunks if not chunk.get("annexe")]
    if no_annexe_parent:
        report["errors"].append(
            {
                "kind": "annexe_chunks_without_annexe_context",
                "count": len(no_annexe_parent),
                "sample": [f"{c.get('chunk_type')}:{c.get('article_id')} p{c.get('page_start')}" for c in no_annexe_parent[:8]],
            }
        )

    reversed_pages = [chunk for chunk in chunks if chunk.get("page_start", 0) > chunk.get("page_end", 0)]
    if reversed_pages:
        report["errors"].append({"kind": "chunks_with_invalid_page_range", "count": len(reversed_pages)})

    very_long = [chunk for chunk in chunks if len(chunk.get("text", "")) > 12000]
    if very_long:
        report["warnings"].append(
            {
                "kind": "very_long_chunks",
                "count": len(very_long),
                "sample": [f"{c.get('chunk_type')}:{c.get('article_id')}" for c in very_long[:8]],
            }
        )

    context_fields = ["titre", "chapitre", "section"]
    article_refs_in_context = []
    for field in context_fields:
        article_refs_in_context.extend(
            (field, chunk)
            for chunk in chunks
            if chunk.get(field) and ARTICLE_IN_CONTEXT_RE.search(str(chunk.get(field)))
        )
    if article_refs_in_context:
        report["warnings"].append(
            {
                "kind": "article_references_inside_hierarchy_context",
                "count": len(article_refs_in_context),
                "sample": [
                    f"{field}:{chunk.get(field)} | {chunk.get('article_id')} p{chunk.get('page_start')}"
                    for field, chunk in article_refs_in_context[:10]
                ],
            }
        )

    duplicate_keys: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for chunk in article_chunks:
        duplicate_keys[(chunk.get("document") or "", chunk.get("article_id") or "")].append(chunk)
    duplicate_articles = [(key, values) for key, values in duplicate_keys.items() if key[0] and key[1] and len(values) > 1]
    if duplicate_articles:
        report["warnings"].append(
            {
                "kind": "duplicate_article_ids_within_same_document",
                "count": len(duplicate_articles),
                "sample": [
                    f"{article_id} | {document[:70]} | pages {','.join(str(v.get('page_start')) for v in values[:6])}"
                    for (document, article_id), values in duplicate_articles[:12]
                ],
            }
        )

    by_document: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for chunk in chunks:
        if chunk.get("chunk_type") == "article" and chunk.get("document"):
            by_document[chunk["document"]].append(chunk)

    gap_reports: list[str] = []
    for document, doc_chunks in by_document.items():
        nums = [article_number(chunk.get("article_id", "")) for chunk in doc_chunks]
        nums = [num for num in nums if num is not None]
        if len(nums) < 4:
            continue

        # Article numbering restarts naturally inside many documents. We only
        # report local jumps, not every restart.
        jumps: list[tuple[int, int]] = []
        previous = nums[0]
        for num in nums[1:]:
            if num > previous + 1:
                jumps.append((previous, num))
            previous = num
        if jumps:
            jump_text = ", ".join(f"{a}->{b}" for a, b in jumps[:6])
            gap_reports.append(f"{document[:90]}: {jump_text}")

    if gap_reports:
        report["warnings"].append(
            {
                "kind": "article_number_jumps",
                "count": len(gap_reports),
                "sample": gap_reports[:20],
            }
        )

    return report


def format_report(report: dict[str, Any]) -> list[str]:
    lines = [
        "counts: " + ", ".join(f"{kind}={count}" for kind, count in report["counts"].items()),
        "hierarchy: "
        + ", ".join(f"{kind}={count}" for kind, count in report.get("hierarchy_coverage", {}).items()),
        "tables: " + ", ".join(f"{kind}={count}" for kind, count in report.get("table_coverage", {}).items()),
        "footnotes: " + ", ".join(f"{kind}={count}" for kind, count in report.get("footnote_coverage", {}).items()),
        f"errors={len(report['errors'])}",
        f"warnings={len(report['warnings'])}",
    ]
    for error in report["errors"]:
        lines.append(f"ERROR {error['kind']}={error['count']}")
        for sample in error.get("sample", [])[:20]:
            lines.append(f"  {sample}")
    for warning in report["warnings"]:
        lines.append(f"WARNING {warning['kind']}={warning['count']}")
        for sample in warning.get("sample", [])[:20]:
            lines.append(f"  {sample}")
    return lines


def write_report(report: dict[str, Any], output_path: str | Path) -> None:
    with Path(output_path).open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate legal chunks generated from Docling.")
    parser.add_argument(
        "chunks_path",
        nargs="?",
        default="parsing/notebooks/output/legal_chunks.jsonl",
        help="Path to legal_chunks.jsonl.",
    )
    parser.add_argument("--json-output", help="Optional path to write a JSON validation report.")
    args = parser.parse_args()

    chunks = load_jsonl(args.chunks_path)
    report = validate_chunks(chunks)
    if args.json_output:
        write_report(report, args.json_output)
        print(f"wrote_report={args.json_output}")
    for line in format_report(report):
        print(line)


if __name__ == "__main__":
    main()
