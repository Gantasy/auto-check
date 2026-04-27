from pathlib import Path


def test_load_csv_uses_detail_link_and_default_reason(tmp_path: Path) -> None:
    source = tmp_path / "issues.csv"
    source.write_text("详情链接,负责人\nhttps://example.test/1,alice\n", encoding="utf-8")

    from codecheck_shield.spreadsheet import load_tasks

    rows = load_tasks(source)

    assert [row.url for row in rows] == ["https://example.test/1"]
    assert rows[0].reason == "评审可屏蔽"
    assert rows[0].raw["负责人"] == "alice"


def test_load_xlsx_uses_reason_column_when_present(tmp_path: Path) -> None:
    source = tmp_path / "issues.xlsx"
    create_simple_xlsx(
        source,
        headers=["详情链接", "屏蔽理由"],
        rows=[["https://example.test/2", "规则稳定误报"]],
    )

    from codecheck_shield.spreadsheet import load_tasks

    rows = load_tasks(source)

    assert [row.reason for row in rows] == ["规则稳定误报"]


def create_simple_xlsx(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    import zipfile

    shared_strings = headers + [cell for row in rows for cell in row]
    string_indexes = {value: index for index, value in enumerate(shared_strings)}

    def row_xml(row_number: int, values: list[str]) -> str:
        cells = []
        for column_index, value in enumerate(values, start=1):
            column_name = chr(ord("A") + column_index - 1)
            cells.append(
                f'<c r="{column_name}{row_number}" t="s"><v>{string_indexes[value]}</v></c>'
            )
        return f'<row r="{row_number}">{"".join(cells)}</row>'

    worksheet_rows = [row_xml(1, headers)]
    worksheet_rows.extend(row_xml(index + 2, row) for index, row in enumerate(rows))

    shared_strings_xml = "".join(f"<si><t>{value}</t></si>" for value in shared_strings)
    sheet_dimension = f"A1:B{len(rows) + 1}"
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="{sheet_dimension}"/>'
        f'<sheetData>{"".join(worksheet_rows)}</sheetData>'
        "</worksheet>"
    )

    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/sharedStrings.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
            "</Types>",
        )
        archive.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="xl/workbook.xml"/>'
            "</Relationships>",
        )
        archive.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>'
            "</workbook>",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            'Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" '
            'Target="sharedStrings.xml"/>'
            "</Relationships>",
        )
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)
        archive.writestr(
            "xl/sharedStrings.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f"{shared_strings_xml}</sst>",
        )
