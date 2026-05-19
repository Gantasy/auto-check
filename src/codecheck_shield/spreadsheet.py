from __future__ import annotations

import csv
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from codecheck_shield.models import DEFAULT_REASON, TaskInput

SPREADSHEET_NS = {"ss": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
RELS_NS = {"rel": "http://schemas.openxmlformats.org/package/2006/relationships"}
OFFICE_RELS_NS = {
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
PENDING_ACTION_COLUMN = "处理方式（待屏蔽/修改）"
PENDING_ACTION_VALUE = "待屏蔽"
DETAIL_URL_COLUMN = "详情链接"
LEGACY_REASON_COLUMN = "屏蔽理由"
SHIELD_REASON_COLUMN = "屏蔽描述"
EXPLANATION_REASON_COLUMN = "reason"


def load_tasks(
    path: Path | str,
    default_reason: str = DEFAULT_REASON,
    include_skipped: bool = False,
) -> list[TaskInput] | tuple[list[TaskInput], list[str]]:
    source = Path(path)
    suffix = source.suffix.lower()
    if suffix == ".csv":
        rows = _load_csv_rows(source)
    elif suffix == ".xlsx":
        rows = _load_xlsx_rows(source)
    else:
        raise ValueError(f"Unsupported file format: {source.suffix}")
    tasks, skipped = _build_tasks(rows, default_reason=default_reason)
    if include_skipped:
        return tasks, skipped
    return tasks


def _load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def _load_xlsx_rows(path: Path) -> list[dict[str, str]]:
    with zipfile.ZipFile(path) as archive:
        shared_strings = _read_shared_strings(archive)
        sheet_path = _find_first_sheet_path(archive)
        sheet_xml = ElementTree.fromstring(archive.read(sheet_path))
    rows: list[list[str]] = []
    for row in sheet_xml.findall(".//ss:sheetData/ss:row", SPREADSHEET_NS):
        values: list[str] = []
        last_column = 0
        for cell in row.findall("ss:c", SPREADSHEET_NS):
            reference = cell.attrib.get("r", "")
            column_index = _column_index(reference)
            while last_column + 1 < column_index:
                values.append("")
                last_column += 1
            values.append(_cell_value(cell, shared_strings))
            last_column = column_index
        rows.append(values)
    if not rows:
        return []
    headers = rows[0]
    return [dict(zip(headers, row_values, strict=False)) for row_values in rows[1:]]


def _find_first_sheet_path(archive: zipfile.ZipFile) -> str:
    workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
    first_sheet = workbook.find(".//ss:sheets/ss:sheet", SPREADSHEET_NS)
    if first_sheet is None:
        raise ValueError("Workbook does not contain any sheets")
    rel_id = first_sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
    rels = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    for relationship in rels.findall("rel:Relationship", RELS_NS):
        if relationship.attrib.get("Id") == rel_id:
            target = relationship.attrib['Target']
            # 如果 target 已经以 'xl/' 开头，则直接返回；否则补上 'xl/'
            if target.startswith('xl/'):
                return target
            else:
                return f"xl/{target}"
    raise ValueError("Workbook sheet relationship is missing")

def _read_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    shared = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for item in shared.findall("ss:si", SPREADSHEET_NS):
        text_parts = [node.text or "" for node in item.findall(".//ss:t", SPREADSHEET_NS)]
        values.append("".join(text_parts))
    return values


def _cell_value(cell: ElementTree.Element, shared_strings: list[str]) -> str:
    value = cell.findtext("ss:v", default="", namespaces=SPREADSHEET_NS)
    if cell.attrib.get("t") == "s" and value:
        return shared_strings[int(value)]
    return value


def _column_index(reference: str) -> int:
    letters = "".join(character for character in reference if character.isalpha())
    total = 0
    for character in letters:
        total = (total * 26) + (ord(character.upper()) - ord("A") + 1)
    return total


def _build_tasks(rows: list[dict[str, str]], default_reason: str) -> tuple[list[TaskInput], list[str]]:
    tasks: list[TaskInput] = []
    skipped: list[str] = []
    for offset, row in enumerate(rows, start=2):
        normalized = {str(key): "" if value is None else str(value) for key, value in row.items()}
        url = normalized.get(DETAIL_URL_COLUMN, "").strip()
        if not url:
            continue
        if _has_pending_action_column(normalized) and normalized.get(PENDING_ACTION_COLUMN, "").strip() != PENDING_ACTION_VALUE:
            skipped.append(f"SKIP row={offset} reason={PENDING_ACTION_COLUMN}={normalized.get(PENDING_ACTION_COLUMN, '').strip()}")
            continue
        reason = _resolve_reason(normalized, default_reason)
        tasks.append(TaskInput(row_number=offset, url=url, reason=reason, raw=normalized))
    return tasks, skipped


def _has_pending_action_column(row: dict[str, str]) -> bool:
    return PENDING_ACTION_COLUMN in row


def _resolve_reason(row: dict[str, str], default_reason: str) -> str:
    candidates = [
        row.get(LEGACY_REASON_COLUMN, "").strip(),
        row.get(SHIELD_REASON_COLUMN, "").strip(),
        row.get(EXPLANATION_REASON_COLUMN, "").strip(),
        default_reason,
    ]
    for candidate in candidates:
        if candidate:
            return candidate
    return DEFAULT_REASON
