import re

from app.integrations.google.interfaces import GoogleDocsDocument

_WHITESPACE = re.compile(r"[ \t]+")
_HEADING_LEVELS = {
    "TITLE": 1,
    "HEADING_1": 1,
    "HEADING_2": 2,
    "HEADING_3": 3,
    "HEADING_4": 4,
    "HEADING_5": 5,
    "HEADING_6": 6,
}


def normalize_google_document(document: GoogleDocsDocument) -> str:
    """Convert Google Docs structural elements into deterministic canonical text."""
    lines: list[str] = []
    lists_by_id = {
        list_id: document_list
        for document_list in document.lists
        if isinstance(list_id := document_list.get("listId"), str)
    }

    for element in document.body_content:
        if "paragraph" in element:
            paragraph = element["paragraph"]
            if isinstance(paragraph, dict):
                line = _normalize_paragraph(paragraph, lists_by_id)
                if line:
                    lines.append(line)
            continue
        if "sectionBreak" in element:
            _append_blank_line(lines)

    return "\n".join(lines).strip()


def _normalize_paragraph(
    paragraph: dict[str, object],
    lists_by_id: dict[str, dict[str, object]],
) -> str:
    text = _paragraph_text(paragraph)
    if not text:
        return ""

    style = paragraph.get("paragraphStyle")
    style_name = style.get("namedStyleType") if isinstance(style, dict) else None
    heading_level = _HEADING_LEVELS.get(style_name) if isinstance(style_name, str) else None
    if heading_level is not None:
        return f"{'#' * heading_level} {text}"

    bullet = paragraph.get("bullet")
    if not isinstance(bullet, dict):
        return text

    nesting_level = bullet.get("nestingLevel", 0)
    level = nesting_level if isinstance(nesting_level, int) and nesting_level >= 0 else 0
    list_id = bullet.get("listId")
    list_definition = lists_by_id.get(list_id) if isinstance(list_id, str) else None
    marker = _list_marker(list_definition, level)
    return f"{'  ' * level}{marker} {text}"


def _paragraph_text(paragraph: dict[str, object]) -> str:
    raw_elements = paragraph.get("elements")
    if not isinstance(raw_elements, list):
        return ""
    parts: list[str] = []
    for element in raw_elements:
        if not isinstance(element, dict):
            continue
        text_run = element.get("textRun")
        if isinstance(text_run, dict) and isinstance(content := text_run.get("content"), str):
            parts.append(content.replace("\n", ""))
    return _WHITESPACE.sub(" ", "".join(parts)).strip()


def _list_marker(document_list: dict[str, object] | None, level: int) -> str:
    if document_list is None:
        return "-"
    properties = document_list.get("listProperties")
    levels = properties.get("nestingLevels") if isinstance(properties, dict) else None
    level_properties = levels[level] if isinstance(levels, list) and level < len(levels) else None
    glyph_type = level_properties.get("glyphType") if isinstance(level_properties, dict) else None
    if isinstance(glyph_type, str) and glyph_type.startswith("DECIMAL"):
        return "1."
    return "-"


def _append_blank_line(lines: list[str]) -> None:
    if lines and lines[-1] != "":
        lines.append("")
