import re
from pathlib import Path


DEFAULT_MIN_CHUNK_TOKENS = 300
DEFAULT_MAX_CHUNK_TOKENS = 600

# Approximate tokenizer: a run of word characters or a single punctuation mark
# counts as one token. Good enough for sizing chunks without a model tokenizer.
TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]", re.UNICODE)

# Sentence boundary: whitespace after ASCII or CJK terminal punctuation.
SENTENCE_BOUNDARY_PATTERN = re.compile(r"(?<=[.!?。！？])(?:[ \t]+|\n+)")


def get_doc_id(path: Path) -> str:
    return path.stem


def split_markdown_sections(markdown_text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []

    # Text before the first "## " heading is grouped under "Overview".
    current_heading = "Overview"
    current_lines: list[str] = []

    for line in markdown_text.splitlines():
        # The document title ("# VPN Setup") is not useful retrieval content.
        if line.startswith("# "):
            continue

        # "## " headings are the section boundaries of the KB template
        # (Background, Symptoms, Troubleshooting Steps, ...).
        if line.startswith("## "):
            if current_lines:
                sections.append((current_heading, "\n".join(current_lines).strip()))

            current_heading = line.removeprefix("## ").strip()
            current_lines = []
            continue

        current_lines.append(line)

    if current_lines:
        sections.append((current_heading, "\n".join(current_lines).strip()))

    # Drop empty sections so they never become empty chunks.
    return [(heading, text) for heading, text in sections if text]


def estimate_token_count(text: str) -> int:
    """Estimate tokens without requiring a model-specific tokenizer."""
    return len(TOKEN_PATTERN.findall(text))


def _split_by_words(text: str, max_tokens: int) -> list[str]:
    """Fallback for a single sentence that is larger than the chunk limit."""
    pieces: list[str] = []
    current_words: list[str] = []

    for word in text.split():
        if estimate_token_count(word) > max_tokens:
            if current_words:
                pieces.append(" ".join(current_words))
                current_words = []

            # Preserve the original text while handling a pathological unbroken value.
            start = 0
            while start < len(word):
                end = start + 1
                while (
                    end <= len(word)
                    and estimate_token_count(word[start:end]) <= max_tokens
                ):
                    end += 1
                pieces.append(word[start : end - 1])
                start = end - 1
            continue

        candidate = " ".join([*current_words, word])
        if current_words and estimate_token_count(candidate) > max_tokens:
            pieces.append(" ".join(current_words))
            current_words = [word]
        else:
            current_words.append(word)

    if current_words:
        pieces.append(" ".join(current_words))

    return pieces


def _split_oversized_block(text: str, max_tokens: int) -> list[str]:
    """Split a large paragraph at sentence boundaries whenever possible."""
    sentences = [
        sentence.strip()
        for sentence in SENTENCE_BOUNDARY_PATTERN.split(text)
        if sentence.strip()
    ]
    pieces: list[str] = []

    for sentence in sentences:
        if estimate_token_count(sentence) <= max_tokens:
            pieces.append(sentence)
        else:
            pieces.extend(_split_by_words(sentence, max_tokens))

    return pieces


def _build_section_units(text: str, max_tokens: int) -> list[str]:
    """Keep paragraphs intact unless one paragraph exceeds the maximum size."""
    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", text)
        if paragraph.strip()
    ]
    units: list[str] = []

    for paragraph in paragraphs:
        if estimate_token_count(paragraph) <= max_tokens:
            units.append(paragraph)
        else:
            units.extend(_split_oversized_block(paragraph, max_tokens))

    return units


def split_section_text(
    text: str,
    min_tokens: int = DEFAULT_MIN_CHUNK_TOKENS,
    max_tokens: int = DEFAULT_MAX_CHUNK_TOKENS,
) -> list[str]:
    """Split one Markdown section into semantic chunks near the target size."""
    if min_tokens < 1 or max_tokens < min_tokens:
        raise ValueError("chunk token limits must satisfy 1 <= min_tokens <= max_tokens")

    stripped_text = text.strip()
    if not stripped_text:
        return []
    if estimate_token_count(stripped_text) <= max_tokens:
        return [stripped_text]

    units = _build_section_units(stripped_text, max_tokens)
    groups: list[list[str]] = []
    current_group: list[str] = []

    for unit in units:
        candidate = "\n\n".join([*current_group, unit])
        if current_group and estimate_token_count(candidate) > max_tokens:
            groups.append(current_group)
            current_group = [unit]
        else:
            current_group.append(unit)

    if current_group:
        groups.append(current_group)

    # If possible, move one semantic unit so the final chunk is not unnecessarily small.
    if len(groups) > 1 and estimate_token_count("\n\n".join(groups[-1])) < min_tokens:
        previous_group = groups[-2]
        final_group = groups[-1]
        while len(previous_group) > 1:
            moved_unit = previous_group[-1]
            new_previous = "\n\n".join(previous_group[:-1])
            new_final = "\n\n".join([moved_unit, *final_group])
            if (
                estimate_token_count(new_previous) < min_tokens
                or estimate_token_count(new_final) > max_tokens
            ):
                break
            final_group.insert(0, previous_group.pop())

        combined = "\n\n".join([*previous_group, *final_group])
        if estimate_token_count(combined) <= max_tokens:
            groups[-2] = [*previous_group, *final_group]
            groups.pop()

    return ["\n\n".join(group) for group in groups]


def chunk_markdown(
    doc_id: str,
    markdown_text: str,
    min_tokens: int = DEFAULT_MIN_CHUNK_TOKENS,
    max_tokens: int = DEFAULT_MAX_CHUNK_TOKENS,
) -> list[dict]:
    # Keep the section heading on every chunk created from that section.
    chunk_parts: list[tuple[str, str]] = []
    for heading, text in split_markdown_sections(markdown_text):
        for chunk_text in split_section_text(text, min_tokens, max_tokens):
            chunk_parts.append((heading, chunk_text))

    chunks: list[dict] = []
    for index, (heading, text) in enumerate(chunk_parts, start=1):
        chunks.append(
            {
                "doc_id": doc_id,
                # Zero-padded so chunk IDs sort correctly (doc#001, doc#002, ...).
                "chunk_id": f"{doc_id}#{index:03d}",
                "heading": heading,
                "text": text,
            }
        )

    return chunks


def chunk_file(path: Path) -> list[dict]:
    markdown_text = path.read_text(encoding="utf-8")
    return chunk_markdown(get_doc_id(path), markdown_text)
