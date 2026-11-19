import re

_VALID_UNQUOTED_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*\Z")
_RESERVED_KEYS = frozenset(("true", "false", "null"))
_INLINE_MAX_BYTES = 80
_ESCAPE_RE = re.compile(r'["\\\x00-\x1f]')
_ESCAPE_MAP = {
    '"': '\\"',
    "\\": "\\\\",
    "\b": "\\b",
    "\f": "\\f",
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
}


def _escape_char(m):
    ch = m.group(0)
    return _ESCAPE_MAP.get(ch) or f"\\u{ord(ch):04x}"


def _escape_string(s):
    return '"' + _ESCAPE_RE.sub(_escape_char, s) + '"'


def _format_key(key):
    if not isinstance(key, str):
        raise TypeError(f"keys must be str, not {type(key).__name__}")
    if key not in _RESERVED_KEYS and _VALID_UNQUOTED_KEY_RE.match(key):
        return key
    return _escape_string(key)


def _try_format_inline(val):
    if val is None:
        return "null"
    if val is True:
        return "true"
    if val is False:
        return "false"
    if isinstance(val, str):
        return _escape_string(val)
    if isinstance(val, (int, float)):
        return repr(val)
    if isinstance(val, dict):
        return "{}" if len(val) == 0 else None
    if isinstance(val, (list, tuple)):
        if len(val) == 0:
            return "[]"
        parts = []
        byte_len = 2
        for idx, item in enumerate(val):
            rendered = _try_format_inline(item)
            if rendered is None:
                return None
            if idx > 0:
                byte_len += 2
            byte_len += len(rendered.encode("utf-8"))
            if byte_len > _INLINE_MAX_BYTES:
                return None
            parts.append(rendered)
        return "[" + ", ".join(parts) + "]"
    raise TypeError(f"Object of type {type(val).__name__} is not LMON serializable")


def _normalize_indent(indent):
    if isinstance(indent, int) and not isinstance(indent, bool) and indent >= 1:
        return " " * indent
    if isinstance(indent, str) and len(indent) >= 1:
        if indent.strip(" ") == "" or indent.strip("\t") == "":
            return indent
    raise ValueError("indent must be a positive integer or a non-empty string of spaces or tabs")


def _emit_block(val, depth, unit, lines):
    prefix = unit * depth
    if isinstance(val, dict):
        for k, v in val.items():
            fkey = _format_key(k)
            inline = _try_format_inline(v)
            if inline is not None:
                lines.append(f"{prefix}{fkey}: {inline}")
            else:
                lines.append(f"{prefix}{fkey}:")
                child_depth = depth if isinstance(v, (list, tuple)) else depth + 1
                _emit_block(v, child_depth, unit, lines)
    elif isinstance(val, (list, tuple)):
        for item in val:
            inline = _try_format_inline(item)
            if inline is not None:
                lines.append(f"{prefix}- {inline}")
            else:
                lines.append(f"{prefix}-")
                _emit_block(item, depth + 1, unit, lines)
    else:
        raise TypeError(f"Object of type {type(val).__name__} is not LMON serializable")


def dumps(obj, indent=4):
    unit = _normalize_indent(indent)
    inline = _try_format_inline(obj)
    if inline is not None:
        return inline + "\n"
    lines = []
    _emit_block(obj, 0, unit, lines)
    return "\n".join(lines) + "\n"
