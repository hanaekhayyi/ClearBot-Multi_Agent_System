from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Iterable

from docling_normalizer import (
    NormalizedBlock,
    load_docling_json,
    normalize_docling,
    page_blocks,
    reconstruct_reading_order,
)


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_JSON = BASE_DIR / "notebooks" / "output" / "docling_raw.json"


LAW_RE = re.compile(
    r"^(?P<kind>Loi|Dahir|Décret|Arrêté|Règlement général|Circulaire)\s+(?P<title>.+)",
    re.IGNORECASE,
)
LIVRE_RE = re.compile(r"^LIVRE\s+(?P<num>[IVXLCDM]+)\b(?P<title>.*)", re.IGNORECASE)
TITRE_RE = re.compile(r"^TITRE\s+(?P<num>PREMIER|[IVXLCDM]+|\d+)\b(?P<title>.*)", re.IGNORECASE)
CHAPITRE_RE = re.compile(r"^Chapitre\s+(?P<num>premier|[IVXLCDM]+|\d+)\b(?P<title>.*)", re.IGNORECASE)
SECTION_RE = re.compile(r"^(?P<prefix>Sous\s*-?\s*section|Section)\s+(?P<num>première|[IVXLCDM]+|\d+)\b(?P<title>.*)", re.IGNORECASE)
ARTICLE_TOKEN = (
    r"Article\s*"
    r"(Premier|premier|[IVXLCDM]+(?:\.\d+)+(?:\s*bis|\s*ter)?|\d+(?:[.-]\d+)*(?:\s*bis|\s*ter)?)"
    r"\s*(\*+)?"
)
ARTICLE_RE = re.compile(rf"^{ARTICLE_TOKEN}", re.IGNORECASE)
STRICT_ARTICLE_RE = re.compile(rf"^{ARTICLE_TOKEN}$", re.IGNORECASE)
TRAILING_ARTICLE_RE = re.compile(rf"\b({ARTICLE_TOKEN})$", re.IGNORECASE)
SIMPLE_ARTICLE_ID = r"Article\s*(?:[IVXLCDM]+(?:\.\d+)+|\d+(?:[.-]\d+)*)(?:\s*(?:bis|ter))?\s*\*?"
DOUBLE_ARTICLE_ID_RE = re.compile(rf"^({SIMPLE_ARTICLE_ID})\s+({SIMPLE_ARTICLE_ID})$", re.IGNORECASE)
FOOTNOTE_NUMBER_RE = re.compile(r"^(?P<num>\d+)\b")
ANNEXE_RE = re.compile(
    r"^ANNEXE\s+(?P<num>(?:n°\s*)?(?:[IVXLCDM]+|\d+)|[«\"“”']?\s*[A-Z]\s*[»\"“”']?)(?P<title>.*)",
    re.IGNORECASE,
)
SOUS_ANNEXE_RE = re.compile(r"^Sous\s*-\s*Annexe\s+(?P<num>[IVXLCDM]+|\d+)\b(?P<title>.*)", re.IGNORECASE)
ANNEXE_SECTION_RE = re.compile(r"^(?P<num>[IVXLCDM]+|\d+)\.\s+(?P<title>.+)")


@dataclass
class LegalContext:
    livre: str | None = None
    document: str | None = None
    titre: str | None = None
    chapitre: str | None = None
    section: str | None = None
    article: str | None = None
    annexe: str | None = None


@dataclass
class StructuredBlock:
    block: NormalizedBlock
    heading_kind: str | None
    context: LegalContext


@dataclass
class ArticleChunk:
    chunk_id: str
    chunk_type: str
    article_id: str
    document: str | None
    livre: str | None
    titre: str | None
    chapitre: str | None
    section: str | None
    annexe: str | None
    page_start: int
    page_end: int
    text: str
    footnotes: list[str]
    block_refs: list[str]


def clean_heading(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip(" .")


def clean_article_heading(text: str) -> str:
    text = clean_heading(text)
    return re.sub(
        r"^(Article\s*(?:[IVXLCDM]+(?:\.\d+)+|\d+(?:[.-]\d+)*)(?:\s*(?:bis|ter))?\s*\*?)(?=[A-ZÉÈÀÂÎÔÛÇ])",
        r"\1 ",
        text,
        flags=re.IGNORECASE,
    )


def is_article_heading_block(block: NormalizedBlock, text: str) -> bool:
    if block.label == "section_header":
        return bool(ARTICLE_RE.match(text))
    if not STRICT_ARTICLE_RE.match(text):
        return False
    return block.width <= 170 and block.height <= 26


def classify_heading(block: NormalizedBlock) -> str | None:
    text = clean_heading(block.text)
    if not text:
        return None

    if LIVRE_RE.match(text):
        return "livre"
    if ANNEXE_RE.match(text):
        return "annexe"
    if SOUS_ANNEXE_RE.match(text):
        return "annexe_section"
    if block.label == "section_header" and ANNEXE_SECTION_RE.match(text):
        return "numbered_heading"
    if is_article_heading_block(block, text):
        return "article"
    if SECTION_RE.match(text):
        return "section"
    if CHAPITRE_RE.match(text):
        return "chapitre"
    if TITRE_RE.match(text):
        return "titre"

    # Long legal-document titles often arrive as section_header on first page,
    # but sometimes as body text when Docling sees them as a running header.
    if LAW_RE.match(text) and 690 <= block.y0 and block.y1 < 780 and block.width > 250:
        return "document"
    if block.label == "section_header" and LAW_RE.match(text):
        return "document"

    return None


def reset_below(context: LegalContext, heading_kind: str) -> None:
    if heading_kind == "livre":
        context.document = None
        context.titre = None
        context.chapitre = None
        context.section = None
        context.article = None
        context.annexe = None
    elif heading_kind == "document":
        context.titre = None
        context.chapitre = None
        context.section = None
        context.article = None
        context.annexe = None
    elif heading_kind == "titre":
        context.chapitre = None
        context.section = None
        context.article = None
    elif heading_kind == "chapitre":
        context.section = None
        context.article = None
    elif heading_kind == "section":
        context.article = None
    elif heading_kind == "annexe":
        context.section = None
        context.article = None
    elif heading_kind == "annexe_section":
        context.article = None


def copy_context(context: LegalContext) -> LegalContext:
    return LegalContext(**asdict(context))


def classify_plain_heading(text: str) -> str | None:
    if SECTION_RE.match(text):
        return "section"
    if CHAPITRE_RE.match(text):
        return "chapitre"
    if TITRE_RE.match(text):
        return "titre"
    if ANNEXE_RE.match(text):
        return "annexe"
    return None


def same_running_document_header(text: str, current_document: str | None) -> bool:
    if not current_document:
        return False
    text_norm = clean_heading(text).casefold()
    current_norm = clean_heading(current_document).casefold()
    return current_norm.startswith(text_norm) or text_norm.startswith(current_norm)


def is_collection_livre(text: str) -> bool:
    normalized = clean_heading(text).casefold()
    return normalized in {
        "livre i dahirs et lois",
        "livre ii reglements generaux",
        "livre ii règlements généraux",
        "livre iii decrets et arretes",
        "livre iii décrets et arrêtés",
        "livre iv circulaires",
    }


def iter_ordered_blocks(blocks: Iterable[NormalizedBlock]) -> Iterable[NormalizedBlock]:
    by_page: dict[int, list[NormalizedBlock]] = {}
    for block in blocks:
        by_page.setdefault(block.page, []).append(block)
    for page in sorted(by_page):
        yield from reconstruct_reading_order(by_page[page])


def structure_blocks(blocks: Iterable[NormalizedBlock]) -> list[StructuredBlock]:
    context = LegalContext()
    structured: list[StructuredBlock] = []

    for block in iter_ordered_blocks(blocks):
        heading_kind = classify_heading(block)
        text = clean_heading(block.text)
        if heading_kind == "numbered_heading":
            heading_kind = "annexe_section" if context.annexe else None
        if heading_kind == "document" and block.is_header_candidate and context.document:
            if same_running_document_header(text, context.document) or block.width < 250:
                continue

        if block.label == "section_header" and heading_kind != "article":
            article_match = TRAILING_ARTICLE_RE.search(text)
            if article_match:
                section_text = clean_heading(text[: article_match.start()])
                article_text = clean_article_heading(article_match.group(1))
                leading_kind = classify_plain_heading(section_text)
                if not leading_kind and section_text.startswith("["):
                    note_block = replace(block, text=section_text)
                    structured.append(StructuredBlock(block=note_block, heading_kind=None, context=copy_context(context)))
                else:
                    leading_kind = leading_kind or "section"
                    reset_below(context, leading_kind)
                    if leading_kind == "titre":
                        context.titre = section_text
                    elif leading_kind == "chapitre":
                        context.chapitre = section_text
                    elif leading_kind == "annexe":
                        context.annexe = section_text
                    else:
                        context.section = section_text
                    section_block = replace(block, text=section_text)
                    structured.append(
                        StructuredBlock(block=section_block, heading_kind=leading_kind, context=copy_context(context))
                    )
                reset_below(context, "article")
                context.article = article_text
                article_block = replace(block, text=article_text)
                structured.append(StructuredBlock(block=article_block, heading_kind="article", context=copy_context(context)))
                continue

        if heading_kind:
            if heading_kind == "livre" and context.document and not is_collection_livre(text):
                context.titre = None
                context.chapitre = None
                context.section = None
                context.article = None
                context.annexe = None
                context.livre = text
            else:
                reset_below(context, heading_kind)
                if heading_kind == "livre":
                    context.livre = text
                elif heading_kind == "document":
                    context.document = text
                elif heading_kind == "titre":
                    context.titre = text
                elif heading_kind == "chapitre":
                    context.chapitre = text
                elif heading_kind == "section":
                    context.section = text
                elif heading_kind == "article":
                    context.article = clean_article_heading(text)
                    block = replace(block, text=context.article)
                elif heading_kind == "annexe":
                    context.annexe = text
                elif heading_kind == "annexe_section":
                    context.section = text

        structured.append(StructuredBlock(block=block, heading_kind=heading_kind, context=copy_context(context)))

    return structured


def append_to_chunk(current: ArticleChunk, block: NormalizedBlock) -> None:
    current.page_end = max(current.page_end, block.page)
    current.block_refs.append(block.self_ref)
    if block.label == "footnote":
        text = clean_heading(block.text)
        number_match = FOOTNOTE_NUMBER_RE.match(text)
        previous_match = FOOTNOTE_NUMBER_RE.match(current.footnotes[-1]) if current.footnotes else None
        if current.footnotes and (
            not number_match
            or current.footnotes[-1].rstrip().endswith("-")
            or (previous_match and int(number_match.group("num")) <= int(previous_match.group("num")))
        ):
            current.footnotes[-1] = f"{current.footnotes[-1]} {text}".strip()
        else:
            current.footnotes.append(text)
    elif block.text:
        current.text += "\n" + block.text


def build_article_chunks(structured: Iterable[StructuredBlock]) -> list[ArticleChunk]:
    chunks: list[ArticleChunk] = []
    current: ArticleChunk | None = None

    for item in structured:
        block = item.block
        if item.heading_kind in {"article", "annexe", "annexe_section"}:
            if item.heading_kind == "annexe" and current and current.chunk_type.startswith("annexe"):
                if current.annexe == item.context.annexe:
                    continue
            if current and current.text.strip():
                chunks.append(current)
            ctx = item.context
            chunk_type = item.heading_kind
            chunk_id = ctx.article if chunk_type == "article" else ctx.section or ctx.annexe or block.text
            current = ArticleChunk(
                chunk_id="",
                chunk_type=chunk_type,
                article_id=chunk_id or block.text,
                document=ctx.document,
                livre=ctx.livre,
                titre=ctx.titre,
                chapitre=ctx.chapitre,
                section=ctx.section,
                annexe=ctx.annexe,
                page_start=block.page,
                page_end=block.page,
                text=block.text,
                footnotes=[],
                block_refs=[block.self_ref],
            )
            continue

        if not current:
            continue

        if item.heading_kind in {"livre", "document"}:
            if current.text.strip():
                chunks.append(current)
            current = None
            continue

        if current.chunk_type == "article" and item.heading_kind in {"titre", "chapitre", "section"}:
            continue
        if current.chunk_type.startswith("annexe") and item.heading_kind == "article":
            continue

        append_to_chunk(current, block)

    if current and current.text.strip():
        chunks.append(current)

    return chunks


def merge_footnote_continuations(chunks: Iterable[ArticleChunk]) -> list[ArticleChunk]:
    merged = list(chunks)
    previous_with_note: ArticleChunk | None = None
    for chunk in merged:
        kept: list[str] = []
        for note in chunk.footnotes:
            note_text = clean_heading(note)
            number_match = FOOTNOTE_NUMBER_RE.match(note_text)
            previous_match = (
                FOOTNOTE_NUMBER_RE.match(previous_with_note.footnotes[-1])
                if previous_with_note and previous_with_note.footnotes
                else None
            )
            same_page_as_previous = bool(
                previous_with_note
                and chunk.page_start <= previous_with_note.page_end
                and previous_with_note.page_start <= chunk.page_end
            )
            is_continuation = bool(
                previous_with_note
                and previous_with_note.footnotes
                and same_page_as_previous
                and (
                    not number_match
                    or previous_with_note.footnotes[-1].rstrip().endswith("-")
                    or (previous_match and int(number_match.group("num")) <= int(previous_match.group("num")))
                )
            )
            if is_continuation and previous_with_note:
                previous_with_note.footnotes[-1] = f"{previous_with_note.footnotes[-1]} {note_text}".strip()
            else:
                kept.append(note_text)
                previous_with_note = chunk
        chunk.footnotes = kept
        if chunk.footnotes:
            previous_with_note = chunk
    return merged


def split_fused_article_chunks(chunks: Iterable[ArticleChunk]) -> list[ArticleChunk]:
    split_chunks: list[ArticleChunk] = []
    for chunk in chunks:
        match = DOUBLE_ARTICLE_ID_RE.match(clean_heading(chunk.article_id))
        if chunk.chunk_type != "article" or not match:
            split_chunks.append(chunk)
            continue

        first_article = clean_heading(match.group(1))
        second_article = clean_heading(match.group(2))
        lines = chunk.text.splitlines()
        body_lines = lines[1:] if lines else []

        if body_lines and body_lines[0].lstrip().startswith("[Article abrog"):
            first_body = body_lines[:1]
            second_body = body_lines[1:]
        else:
            first_body = []
            second_body = body_lines

        split_chunks.append(
            replace(
                chunk,
                article_id=first_article,
                text="\n".join([first_article, *first_body]).strip(),
                block_refs=chunk.block_refs[: max(1, 1 + len(first_body))],
            )
        )
        split_chunks.append(
            replace(
                chunk,
                article_id=second_article,
                text="\n".join([second_article, *second_body]).strip(),
                block_refs=chunk.block_refs[max(1, 1 + len(first_body)) :],
            )
        )

    return split_chunks


def split_long_annex_chunks(chunks: Iterable[ArticleChunk], max_chars: int = 10000) -> list[ArticleChunk]:
    split_chunks: list[ArticleChunk] = []
    for chunk in chunks:
        if not chunk.chunk_type.startswith("annexe") or len(chunk.text) <= max_chars:
            split_chunks.append(chunk)
            continue

        lines = chunk.text.splitlines()
        if len(lines) <= 1:
            split_chunks.append(chunk)
            continue

        bucket: list[str] = []
        part = 1
        page_start = chunk.page_start

        def flush() -> None:
            nonlocal bucket, part, page_start
            if not bucket:
                return
            text = "\n".join(bucket).strip()
            split_chunks.append(
                ArticleChunk(
                    chunk_id="",
                    chunk_type=f"{chunk.chunk_type}_part",
                    article_id=f"{chunk.article_id} - partie {part}",
                    document=chunk.document,
                    livre=chunk.livre,
                    titre=chunk.titre,
                    chapitre=chunk.chapitre,
                    section=chunk.section,
                    annexe=chunk.annexe,
                    page_start=page_start,
                    page_end=chunk.page_end,
                    text=text,
                    footnotes=[],
                    block_refs=chunk.block_refs,
                )
            )
            part += 1
            bucket = []
            page_start = chunk.page_start

        for line in lines:
            if bucket and sum(len(item) + 1 for item in bucket) + len(line) > max_chars:
                flush()
            bucket.append(line)
        flush()

    return split_chunks


def slugify(value: str | None, max_length: int = 64) -> str:
    value = value or "none"
    value = value.casefold()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return (value or "none")[:max_length]


def assign_chunk_ids(chunks: Iterable[ArticleChunk]) -> list[ArticleChunk]:
    assigned = list(chunks)
    seen: dict[str, int] = {}
    for chunk in assigned:
        fingerprint = "|".join(
            [
                chunk.chunk_type,
                chunk.article_id or "",
                chunk.document or "",
                chunk.livre or "",
                chunk.titre or "",
                chunk.chapitre or "",
                chunk.section or "",
                chunk.annexe or "",
                str(chunk.page_start),
                str(chunk.page_end),
                ",".join(chunk.block_refs[:8]),
            ]
        )
        digest = hashlib.sha1(fingerprint.encode("utf-8")).hexdigest()[:10]
        base = "__".join(
            [
                slugify(chunk.document, 36),
                slugify(chunk.chunk_type, 20),
                slugify(chunk.article_id, 56),
                f"p{chunk.page_start}-{chunk.page_end}",
                digest,
            ]
        )
        count = seen.get(base, 0) + 1
        seen[base] = count
        chunk.chunk_id = base if count == 1 else f"{base}-{count}"
    return assigned


def write_jsonl(items: Iterable[object], output_path: str | Path) -> None:
    with Path(output_path).open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(asdict(item), ensure_ascii=False) + "\n")


def preview_articles(chunks: list[ArticleChunk], limit: int) -> str:
    counts: dict[str, int] = {}
    for chunk in chunks:
        counts[chunk.chunk_type] = counts.get(chunk.chunk_type, 0) + 1
    counts_text = ", ".join(f"{kind}:{count}" for kind, count in sorted(counts.items()))
    lines = [f"legal_chunks={len(chunks)} ({counts_text})"]
    for chunk in chunks[:limit]:
        text = re.sub(r"\s+", " ", chunk.text)
        if len(text) > 220:
            text = text[:217] + "..."
        lines.append(
            f"{chunk.chunk_type}:{chunk.article_id} | pages={chunk.page_start}-{chunk.page_end} | "
            f"doc={chunk.document or '?'} | {text}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build legal structure and article chunks from Docling JSON.")
    parser.add_argument(
        "json_path",
        nargs="?",
        default=str(DEFAULT_JSON),
        help="Path to docling_raw.json.",
    )
    parser.add_argument("--limit", type=int, default=20, help="Number of chunks to preview.")
    parser.add_argument("--chunks-output", help="Optional path to write article chunks as JSONL.")
    args = parser.parse_args()

    doc = load_docling_json(args.json_path)
    blocks = normalize_docling(doc)
    structured = structure_blocks(blocks)
    chunks = assign_chunk_ids(
        split_long_annex_chunks(
        merge_footnote_continuations(split_fused_article_chunks(build_article_chunks(structured)))
        )
    )

    if args.chunks_output:
        write_jsonl(chunks, args.chunks_output)
        print(f"wrote_chunks={args.chunks_output}")

    print(preview_articles(chunks, args.limit))


if __name__ == "__main__":
    main()
