import re
from pathlib import Path


DEFAULT_MIN_CHUNK_TOKENS = 300
DEFAULT_MAX_CHUNK_TOKENS = 600

# re.compile 会预先创建一个可重复使用的正则规则，避免每次计数都重新解析规则。
# \w+ 匹配连续的文字/数字；[^\w\s] 匹配既不是文字也不是空白的字符，例如标点。
TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]", re.UNICODE)

# 这个规则寻找句号、问号或感叹号后的空白，用它作为句子的切分位置。
# 编译后的 Pattern 可以直接调用 .split(text)，按照规则把文本拆成多个句子。
SENTENCE_BOUNDARY_PATTERN = re.compile(r"(?<=[.!?。！？])(?:[ \t]+|\n+)")


def get_doc_id(doc_Path: Path) -> str:
    #doc_Path: Path doc:Path接收的必须是Path类型的
    # -> str 返回函数提醒 即return出的必须是str
    return doc_Path.stem
    #stem是用来去除文件后缀名的 vpn_set.md 变成vpn_set


def split_markdown_sections(markdown_text: str) -> list[tuple[str, str]]:
    # sections 用来存放切好的段落。
    # 每个元素是一个二元组：(section 标题, section 正文)
    sections: list[tuple[str, str]] = []

    # 如果文档在第一个 ## 标题前有正文，就先归到 Overview。
    current_heading = "Overview"

    # current_lines 暂存当前 section 的所有正文行。
    # 直到遇到下一个 ## 标题，才把这些行合并成一个 section。
    current_lines: list[str] = []

    for line in markdown_text.splitlines():
        # # 是整篇文档的大标题，比如 "# VPN Setup"。
        # 它不适合作为检索 chunk，所以这里跳过。
        if line.startswith("# "):
            continue

        # ## 是我们统一 KB 模板里的 section 标题，
        # 比如 "## Symptoms"、"## Troubleshooting Steps"。
        if line.startswith("## "):
            # 遇到新的 section 前，先把上一个 section 保存下来。
            if current_lines:
                sections.append((current_heading, "\n".join(current_lines).strip()))

            # 去掉开头的 "## "，只保留干净的标题文本。
            current_heading = line.removeprefix("## ").strip()
            current_lines = []
            continue

        # 普通正文行先攒起来，等 section 结束时再统一保存。
        current_lines.append(line)

    # for 循环结束后，最后一个 section 还没有被保存，
    # 所以这里要补一次。
    if current_lines:
        sections.append((current_heading, "\n".join(current_lines).strip()))

    # 过滤掉空 section，避免后面生成没有内容的 chunk。
    return [(heading, text) for heading, text in sections if text]


def estimate_token_count(text: str) -> int:
    """Estimate tokens without requiring a model-specific tokenizer."""
    # findall 会返回文本中所有符合 TOKEN_PATTERN 的单词和标点。
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
    # 使用上面编译好的句子边界规则拆分，优先保留完整句子。
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
    # re.split 会在一个或多个空行处切分文本；\s* 也允许空行中含有空格。
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
                # :03d 表示用 3 位数字补零：
                # 1 -> 001, 2 -> 002, 方便排序和引用。
                "chunk_id": f"{doc_id}#{index:03d}",
                "heading": heading,
                "text": text,
            }
        )

    return chunks


def chunk_file(path: Path) -> list[dict]:
    # 这个函数负责连接“文件系统”和“chunk 逻辑”：
    # 读取某个 .md 文件 -> 根据文件名生成 doc_id -> 返回 chunks。
    markdown_text = path.read_text(encoding="utf-8")
    return chunk_markdown(get_doc_id(path), markdown_text)
