from __future__ import annotations

import argparse
from pathlib import Path

from docling_normalizer import blocks_to_jsonl, load_docling_json, normalize_docling
from legal_structure import (
    assign_chunk_ids,
    build_article_chunks,
    merge_footnote_continuations,
    split_fused_article_chunks,
    split_long_annex_chunks,
    structure_blocks,
    write_jsonl,
)
from validate_chunks import format_report, validate_chunks, write_report


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = BASE_DIR / "notebooks" / "output"
DEFAULT_JSON = DEFAULT_OUTPUT_DIR / "docling_raw.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Docling legal parsing pipeline end to end.")
    parser.add_argument(
        "--json-input",
        default=str(DEFAULT_JSON),
        help="Path to Docling JSON.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for generated outputs.",
    )
    parser.add_argument("--skip-normalized-export", action="store_true", help="Do not write normalized_blocks.jsonl.")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    normalized_output = output_dir / "normalized_blocks.jsonl"
    chunks_output = output_dir / "legal_chunks.jsonl"
    validation_output = output_dir / "validation_report.json"

    doc = load_docling_json(args.json_input)
    blocks = normalize_docling(doc)
    if not args.skip_normalized_export:
        blocks_to_jsonl(blocks, normalized_output)
        print(f"wrote_normalized={normalized_output}")

    structured = structure_blocks(blocks)
    chunks = assign_chunk_ids(
        split_long_annex_chunks(
            merge_footnote_continuations(split_fused_article_chunks(build_article_chunks(structured)))
        )
    )
    write_jsonl(chunks, chunks_output)
    print(f"wrote_chunks={chunks_output}")

    report = validate_chunks([chunk.__dict__ for chunk in chunks])
    write_report(report, validation_output)
    print(f"wrote_validation={validation_output}")
    for line in format_report(report):
        print(line)


if __name__ == "__main__":
    main()
