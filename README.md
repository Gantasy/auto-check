# codecheck-shield v1.0.0

Batch process CodeCheck defect links from a spreadsheet and update each issue to `忽略问题` with a review comment.

Requires Python 3.10+.

## What It Does

- Reads tasks from `CSV` or `XLSX`
- Uses the `详情链接` column as the target defect page
- Uses the optional `屏蔽理由` column as the comment text
- Falls back to `评审可屏蔽` when no reason is provided
- Reuses a local Chrome profile instead of automating login
- Writes a result CSV with per-row execution status and failure screenshots

## Supported Page Flow

The current automation is intentionally narrow and follows this fixed flow:

1. Open the defect detail URL
2. Click `修改问题状态`
3. Select `忽略问题`
4. Fill the comment dialog
5. Click `确定`

## Input Contract

Required column:

- `详情链接`

Optional column:

- `屏蔽理由`

All other columns are preserved and copied into the result CSV.

See `examples/sample_tasks.csv` for the expected shape.

## Installation

```bash
python -m pip install --no-build-isolation -e .[automation]
playwright install chromium
```

## Windows Chrome Usage

This project is optimized for Windows Chrome because the target browser profile is usually there.

If you do not pass `--user-data-dir`, the tool will default to:

```text
%LOCALAPPDATA%\Google\Chrome\User Data
```

If your logged-in Chrome account is not in the default profile, pass `--profile-directory`.

Example:

```bash
codecheck-shield tasks.xlsx --output results.csv --profile-directory "Profile 2"
```

For Edge:

```bash
codecheck-shield tasks.xlsx --browser-channel msedge --profile-directory "Default"
```

## Output

The result CSV keeps the original columns and appends:

- `run_status`
- `run_message`
- `processed_at`
- `used_reason`
- `screenshot_path`

## Development

Run tests:

```bash
pytest -q
```

## Notes

- Close Chrome before running if Playwright cannot attach to the selected user data directory.
- The current automation targets one known CodeCheck page flow. If the site UI changes, selectors may need to be updated.
- Local files like real screenshots or internal spreadsheets should not be pushed to GitHub unless they are sanitized.
