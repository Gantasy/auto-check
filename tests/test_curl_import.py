from pathlib import Path

CODECHECK_TEST_ORIGIN = "https://codecheck.cn-north-4.example.invalid"


def test_parse_curl_extracts_request_auth_and_defaults(tmp_path: Path) -> None:
    from codecheck_shield.curl_import import parse_curl_text

    curl_text = (
        f'curl "{CODECHECK_TEST_ORIGIN}/codechecknew/report/v1/defect/issue-status?_=1777280163578" '
        '-H "AgencyId: agency-1" '
        '-H "cftk: token-1" '
        '-b "SID=abc; SessionID=xyz" '
        '--data-raw "{\\"platform\\":\\"clouddragon\\",\\"operator\\":\\"Gitee\\"}"'
    )

    imported = parse_curl_text(curl_text)

    assert imported.cookie == "SID=abc; SessionID=xyz"
    assert imported.agency_id == "agency-1"
    assert imported.cftk == "token-1"
    assert imported.platform == "clouddragon"
    assert imported.operator == "Gitee"


def test_parse_curl_falls_back_to_cookie_header_when_b_flag_missing(tmp_path: Path) -> None:
    from codecheck_shield.curl_import import parse_curl_text

    curl_text = (
        f'curl "{CODECHECK_TEST_ORIGIN}/codechecknew/report/v1/defect/issue-status?_=1777280163578" '
        '-H "AgencyId: agency-1" '
        '-H "cftk: token-1" '
        '-H "Cookie: SID=abc; SessionID=xyz" '
        '--data-raw "{\\"platform\\":\\"clouddragon\\",\\"operator\\":\\"Gitee\\"}"'
    )

    imported = parse_curl_text(curl_text)

    assert imported.cookie == "SID=abc; SessionID=xyz"
    assert imported.agency_id == "agency-1"
    assert imported.cftk == "token-1"
    assert imported.platform == "clouddragon"
    assert imported.operator == "Gitee"
