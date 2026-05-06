from __future__ import annotations

import json
import re
import shlex
from dataclasses import dataclass

from codecheck_shield.config import DEFAULT_REQUEST_OPERATOR, DEFAULT_REQUEST_PLATFORM


@dataclass(slots=True)
class ImportedCurlRequest:
    cookie: str
    agency_id: str
    cftk: str
    operator: str
    platform: str


def parse_curl_text(text: str) -> ImportedCurlRequest:
    normalized = _normalize_windows_curl(text)
    tokens = shlex.split(normalized, posix=True)

    headers: dict[str, str] = {}
    cookie = ""
    data_raw = ""

    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in {"-H", "--header"} and index + 1 < len(tokens):
            name, value = _split_header(tokens[index + 1])
            headers[name.lower()] = value
            index += 2
            continue
        if token in {"-b", "--cookie"} and index + 1 < len(tokens):
            cookie = tokens[index + 1].strip()
            index += 2
            continue
        if token == "--data-raw" and index + 1 < len(tokens):
            data_raw = tokens[index + 1]
            index += 2
            continue
        index += 1

    payload: dict[str, str] = {}
    if data_raw:
        try:
            parsed_payload = json.loads(data_raw)
        except json.JSONDecodeError:
            parsed_payload = {}
        if isinstance(parsed_payload, dict):
            payload = {str(key): str(value) for key, value in parsed_payload.items()}

    return ImportedCurlRequest(
        cookie=cookie or headers.get("cookie", ""),
        agency_id=headers.get("agencyid", ""),
        cftk=headers.get("cftk", ""),
        operator=payload.get("operator", DEFAULT_REQUEST_OPERATOR),
        platform=payload.get("platform", DEFAULT_REQUEST_PLATFORM),
    )


def _normalize_windows_curl(text: str) -> str:
    normalized = re.sub(r"\^\s*[\r\n]+", " ", text)
    normalized = normalized.replace('\\"', '"')
    normalized = re.sub(r"\^(?=[\"^&|<>])", "", normalized)
    return normalized.strip()


def _split_header(header: str) -> tuple[str, str]:
    if ":" not in header:
        return header.strip(), ""
    name, value = header.split(":", 1)
    return name.strip(), value.strip()
