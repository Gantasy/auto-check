# codecheck-shield v1.0.0

Batch process CodeCheck defect links from a spreadsheet and update each issue to `忽略问题` with a review comment.

Requires Python 3.10+.

## Recommended Mode

For Windows environments with strict security checks, use `windows-desktop` mode.

This mode:

- opens each `详情链接` in your normal browser environment
- clicks fixed desktop positions instead of attaching to Chrome DevTools
- avoids the security limitations that blocked `Playwright` against the real Chrome profile

## What It Does

- Reads tasks from `CSV` or `XLSX`
- Uses the `详情链接` column as the target defect page
- Uses the optional `屏蔽理由` column as the comment text
- Supports a global fallback reason through `--default-reason`
- Falls back to `评审可屏蔽` when no reason is provided anywhere
- Writes a result CSV with per-row execution status and failure screenshots

## Supported Page Flow

The current automation follows this fixed flow:

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

Reason precedence:

1. use the row's `屏蔽理由` when present and non-empty
2. otherwise use `--default-reason`
3. otherwise fall back to `评审可屏蔽`

All other columns are preserved and copied into the result CSV.

See `examples/sample_tasks.csv` for the expected shape.

### Input Template

Minimum useful header:

```csv
详情链接,屏蔽理由
```

Example:

```csv
详情链接,屏蔽理由,备注
https://example.test/codecheck/defect/1,规则稳定误报,首批
https://example.test/codecheck/defect/2,人工确认可屏蔽,二次复核
https://example.test/codecheck/defect/3,,使用全局默认理由
```

Notes:

- `详情链接` is required
- `屏蔽理由` is optional
- any extra columns are preserved in the output CSV

## Installation

Install the project and desktop automation dependencies:

```bash
python -m pip install --no-build-isolation -e .[automation]
```

`windows-desktop` mode does not require `playwright install chromium`.

On Windows, the equivalent command is:

```powershell
py -3.10 -m pip install --upgrade pip setuptools wheel
py -3.10 -m pip install --no-build-isolation -e .[automation]
```

## Windows Desktop Setup

1. Open your browser normally and log in to the target site.
2. Maximize the browser window and keep its layout stable.
3. Run desktop calibration once:

```bash
codecheck-shield --calibrate-desktop --desktop-calibration-file desktop-calibration.json
```

During calibration, move the mouse to each target and press Enter:

- `修改问题状态`
- `忽略问题`
- comment input field
- `确定`

4. Run the batch task in `windows-desktop` mode:

```bash
codecheck-shield tasks.xlsx --output results.csv --browser-mode windows-desktop --desktop-calibration-file desktop-calibration.json
```

If you want to set a global fallback reason:

```bash
codecheck-shield tasks.xlsx --output results.csv --browser-mode windows-desktop --desktop-calibration-file desktop-calibration.json --default-reason "人工确认可屏蔽"
```

Useful timing flags:

```bash
codecheck-shield tasks.xlsx --browser-mode windows-desktop --desktop-calibration-file desktop-calibration.json --page-load-seconds 4 --action-delay-seconds 0.8
```

Example with both timing and fallback reason:

```bash
codecheck-shield tasks.xlsx --output results.csv --browser-mode windows-desktop --desktop-calibration-file desktop-calibration.json --default-reason "人工确认可屏蔽" --page-load-seconds 4 --action-delay-seconds 0.8
```

## Optional Playwright Modes

Two Playwright-based modes remain available for environments that do not block them:

- `isolated-profile`
- `attach-cdp`

Example:

```bash
codecheck-shield tasks.xlsx --browser-mode attach-cdp --cdp-url http://127.0.0.1:9222
```

## Output

The result CSV keeps the original columns and appends:

- `run_status`
- `run_message`
- `processed_at`
- `used_reason`
- `screenshot_path`

### Output Example

```csv
详情链接,屏蔽理由,run_status,run_message,processed_at,used_reason,screenshot_path
https://example.test/codecheck/defect/1,规则稳定误报,success,,2026-04-27T13:20:00+08:00,规则稳定误报,
https://example.test/codecheck/defect/2,,failed_desktop_step,button not found,2026-04-27T13:21:10+08:00,人工确认可屏蔽,artifacts/screenshots/desktop-failure-20260427-132110.png
```

Field meaning:

- `run_status`: execution result such as `success` or `failed_desktop_step`
- `run_message`: error detail when a row fails
- `processed_at`: processing timestamp
- `used_reason`: the actual reason text used for this row
- `screenshot_path`: failure screenshot path when available

## Development

Run tests:

```bash
pytest -q
```

## Notes

- `windows-desktop` mode depends on stable screen positions, so recalibrate after browser zoom, monitor scaling, or layout changes.
- Keep the target browser window in the foreground while the batch is running.
- Local files like real screenshots or internal spreadsheets should not be pushed to GitHub unless they are sanitized.
