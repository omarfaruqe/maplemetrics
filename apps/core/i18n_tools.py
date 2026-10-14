"""Compile gettext catalogs without the GNU gettext tools, and check nothing is untranslated.

The compiled ``.mo`` files are committed, so Docker and CI need no extra packages. A test
rebuilds them from the ``.po`` files and fails when a committed ``.mo`` is out of date.
"""

import ast
import re
import struct
from pathlib import Path

from django.conf import settings

CONTEXT_SEPARATOR = "\x04"
_ESCAPES = {"n": "\n", "t": "\t", '"': '"', "\\": "\\", "r": "\r"}
_TRANS_TAG = re.compile(r"""\{%\s*trans\s+(?:"([^"]*)"|'([^']*)')""")
_BLOCKTRANS = re.compile(r"\{%\s*blocktrans\b[^%]*%\}(.*?)\{%\s*endblocktrans\s*%\}", re.S)
_VARIABLE = re.compile(r"\{\{\s*([\w.]+)\s*\}\}")
_GETTEXT_CALLS = {"_", "gettext", "gettext_lazy"}
_CONTEXT_CALLS = {"pgettext", "pgettext_lazy"}


def _unquote(text: str) -> str:
    inner = text.strip()[1:-1]
    return re.sub(r"\\(.)", lambda m: _ESCAPES.get(m.group(1), m.group(1)), inner)


def parse_po(text: str) -> dict[str, str]:
    """Map message keys to translations. A context is joined to its id with EOT, as in .mo."""
    messages: dict[str, str] = {}
    fields: dict[str, list[str]] = {}
    current = ""
    fuzzy = False

    def flush():
        nonlocal fields, fuzzy
        if "msgid" in fields and not fuzzy:
            msgid = "".join(fields["msgid"])
            if "msgctxt" in fields:
                msgid = "".join(fields["msgctxt"]) + CONTEXT_SEPARATOR + msgid
            messages[msgid] = "".join(fields.get("msgstr", []))
        fields, fuzzy = {}, False

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            flush()
        elif line.startswith("#"):
            if line.startswith("#,") and "fuzzy" in line:
                fuzzy = True
        elif line.startswith('"'):
            if current:
                fields[current].append(_unquote(line))
        else:
            keyword, _, rest = line.partition(" ")
            if keyword in ("msgctxt", "msgid") and "msgstr" in fields:
                flush()
            current = keyword
            fields[current] = [_unquote(rest)]
    flush()
    return {key: value for key, value in messages.items() if value or key == ""}


def build_mo(messages: dict[str, str]) -> bytes:
    """Serialize messages in the binary .mo format (no hash table, which readers don't need)."""
    items = sorted((key.encode(), value.encode()) for key, value in messages.items())
    count = len(items)
    keys_offset = 7 * 4 + 16 * count
    values_offset = keys_offset + sum(len(key) + 1 for key, _ in items)
    key_table, value_table = [], []
    key_blob, value_blob = b"", b""
    for key, value in items:
        key_table.append((len(key), keys_offset + len(key_blob)))
        value_table.append((len(value), values_offset + len(value_blob)))
        key_blob += key + b"\0"
        value_blob += value + b"\0"
    header = struct.pack("<7I", 0x950412DE, 0, count, 7 * 4, 7 * 4 + 8 * count, 0, 0)
    tables = b"".join(struct.pack("<2I", *pair) for pair in key_table + value_table)
    return header + tables + key_blob + value_blob


def locale_dir() -> Path:
    return Path(settings.LOCALE_PATHS[0])


def po_files() -> list[Path]:
    return sorted(locale_dir().glob("*/LC_MESSAGES/django.po"))


def compiled_bytes(po_path: Path) -> bytes:
    return build_mo(parse_po(po_path.read_text(encoding="utf-8")))


def compile_all() -> list[Path]:
    written = []
    for po_path in po_files():
        target = po_path.with_suffix(".mo")
        target.write_bytes(compiled_bytes(po_path))
        written.append(target)
    return written


def stale_catalogs() -> list[Path]:
    """The .po files whose committed .mo is missing or differs from a fresh compile."""
    stale = []
    for po_path in po_files():
        target = po_path.with_suffix(".mo")
        if not target.exists() or target.read_bytes() != compiled_bytes(po_path):
            stale.append(po_path)
    return stale


def _template_messages(text: str) -> set[str]:
    found = {a or b for a, b in _TRANS_TAG.findall(text)}
    for body in _BLOCKTRANS.findall(text):
        found.add(_VARIABLE.sub(lambda m: f"%({m.group(1)})s", body.replace("%", "%%")))
    return found


def _constant(node: ast.AST) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _python_messages(source: str) -> set[str]:
    found = set()
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
            continue
        name, args = node.func.id, node.args
        if name in _GETTEXT_CALLS and args and (text := _constant(args[0])) is not None:
            found.add(text)
        elif name in _CONTEXT_CALLS and len(args) >= 2:
            context, text = _constant(args[0]), _constant(args[1])
            if context is not None and text is not None:
                found.add(context + CONTEXT_SEPARATOR + text)
    return found


def source_messages(root: Path | None = None) -> set[str]:
    """Every string the code and templates ask gettext to translate."""
    root = root or Path(settings.BASE_DIR) / "apps"
    found: set[str] = set()
    for path in root.rglob("*.html"):
        found |= _template_messages(path.read_text(encoding="utf-8"))
    for path in root.rglob("*.py"):
        if "tests" not in path.parts and "migrations" not in path.parts:
            found |= _python_messages(path.read_text(encoding="utf-8"))
    return found


def untranslated() -> list[tuple[str, str]]:
    """(language, source string) pairs with no non-empty translation in that language's catalog."""
    missing = []
    sources = sorted(source_messages())
    for po_path in po_files():
        catalog = parse_po(po_path.read_text(encoding="utf-8"))
        language = po_path.parent.parent.name
        missing += [(language, message) for message in sources if not catalog.get(message)]
    return missing
