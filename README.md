# codecheck-shield v1.0.0

## TL;DR

推荐默认使用 `requests` 模式。
要求 Python `3.10+`。

```bash
python -m pip install --no-build-isolation -e .
codecheck-shield setup --from-curl-file request.curl
codecheck-shield run tasks.xlsx
```

- 日常主流程只有两个命令：`setup` 和 `run`
- 默认配置文件名：`codecheck-shield.config.json`
- 默认输出目录：`output/`
- 默认输出后缀：`.results.csv`
- 默认会在 `output/` 下同时生成结果文件、运行日志 `.log`，命中 HTTP 429 时额外生成 `.retry429.csv`

## 这是什么

`codecheck-shield` 用于批量读取 `CSV` 或 `XLSX` 中的 CodeCheck 问题详情链接，并将指定问题更新为 `忽略问题`。

它面向操作人员，核心目标是把一次手工成功操作沉淀为本地配置，之后通过表格批量执行。当前推荐路径是 `requests` 模式：直接调用后端接口，不依赖浏览器点击，适合稳定批处理。

## 推荐使用流程

推荐按下面的顺序使用：

1. 安装最小依赖。
2. 手工完成一次成功的 `忽略问题` 操作，并从浏览器开发者工具导出对应请求的 cURL。
3. 执行 `setup`，把认证信息和默认参数保存到本地 `codecheck-shield.config.json`。
4. 准备任务表格。
5. 执行 `run` 批量处理。

主流程说明：

- `setup` 是一次性初始化步骤，读取 cURL 并写入本地配置。
- `run` 是日常执行步骤，默认会自动读取当前工作目录下的 `codecheck-shield.config.json`。
- 如果需要，也可以通过 `--config` 指定其他配置文件路径。

## 快速开始

安装：

```bash
python -m pip install --no-build-isolation -e .
```

要求 Python `3.10+`。

准备好浏览器导出的 cURL 文件后，执行初始化：

```bash
codecheck-shield setup --from-curl-file request.curl
```

准备好任务表格后执行批处理：

```bash
codecheck-shield run tasks.xlsx
```

如果不显式传 `--output`，程序会基于输入文件名自动生成结果文件并写到 `output/` 目录下，默认后缀是 `.results.csv`。例如 `tasks.xlsx` 默认输出 `output/tasks.results.csv`，同时生成 `output/tasks.results.log`；若存在可重试的 HTTP 429 失败，还会生成 `output/tasks.retry429.csv`。

## 输入文件要求

支持格式：

- `CSV`
- `XLSX`

列要求：

- 必填列：`详情链接`
- 可选列：`处理方式（待屏蔽/修改）`
- 可选理由列：`屏蔽理由`、`屏蔽描述`、`reason`

执行规则：

- 如果某行没有 `详情链接`，该行不会进入执行队列。
- 如果表格中不存在 `处理方式（待屏蔽/修改）` 这一列，则所有包含 `详情链接` 的行都会执行。
- 如果表格中存在 `处理方式（待屏蔽/修改）`，则只有值严格等于 `待屏蔽` 的行会执行，其他值会被跳过。

每一行实际使用的理由按以下优先级选择：

1. `屏蔽理由`
2. `屏蔽描述`
3. `reason`
4. `--default-reason`
5. 内置默认值 `评审可屏蔽`

CSV 表头示例：

```csv
详情链接,处理方式（待屏蔽/修改）,屏蔽描述,reason
```

可参考 [examples/sample_tasks.csv](/home/gantasy/work/auto-check/examples/sample_tasks.csv)。

## 输出结果说明

结果文件会保留原始输入列，并在末尾追加以下列：

- `run_status`
- `run_message`
- `processed_at`
- `used_reason`
- `screenshot_path`

默认输出行为：

- 默认输出目录：`output/`
- 结果文件默认后缀：`.results.csv`
- 运行日志文件后缀：`.log`
- HTTP 429 可重试任务文件后缀：`.retry429.csv`

含义说明：

- `run_status`：该行执行状态
- `run_message`：执行结果或错误信息
- `processed_at`：处理时间
- `used_reason`：该行最终实际提交的理由
- `screenshot_path`：失败截图路径；无截图时通常为空

## 模式选择

支持的 `--browser-mode` 取值如下：

- `requests`
- `isolated-profile`
- `attach-cdp`
- `windows-desktop`

推荐顺序：

1. `requests`：默认推荐，也是未显式指定时的默认模式。
2. `windows-desktop`：Windows 环境下的桌面自动化兜底方案。
3. `isolated-profile` / `attach-cdp`：Playwright 可选模式，仅在你的环境适合浏览器自动化时再使用。

## requests 模式配置

`requests` 是默认主路径，`setup` 也会把配置中的 `mode` 写成 `requests`。

典型步骤：

1. 在浏览器里手工完成一次成功的 `忽略问题`。
2. 在开发者工具的 Network 面板中找到对应请求，导出为 cURL 并保存为 `request.curl`。
3. 执行下面的初始化命令：

```bash
codecheck-shield setup --from-curl-file request.curl
```

4. 日常运行时直接执行：

```bash
codecheck-shield run tasks.xlsx
```

补充说明：

- `setup` 默认写入当前目录下的 `codecheck-shield.config.json`
- `run` 在未传 `--config` 时，会优先查找当前目录下的 `codecheck-shield.config.json`
- `setup` 会同时写入默认输出后缀、默认理由以及 `windows-desktop` 的基础参数

## windows-desktop 模式

这是兜底方案，不是首选。只有在 `requests` 模式无法稳定使用时再切换。

先执行桌面坐标校准：

```bash
codecheck-shield --calibrate-desktop --desktop-calibration-file desktop-calibration.json
```

然后使用桌面自动化运行：

```bash
codecheck-shield run tasks.xlsx --browser-mode windows-desktop --desktop-calibration-file desktop-calibration.json
```

适用场景：

- 直接请求无法通过当前环境校验
- 认证链路只能在真实桌面浏览器中稳定完成

执行前请注意：

- 执行期间必须保持目标浏览器窗口位于前台，否则固定坐标点击会落到错误位置
- 屏幕分辨率、系统缩放、浏览器缩放或页面布局发生变化后，应重新执行桌面坐标校准
- 成功处理一行后程序会发送 `Ctrl+W` 关闭当前标签页，不要在同一个浏览器窗口中混用无关标签页

## Playwright 可选模式

以下模式保留为可选方案，不属于推荐主路径：

- `isolated-profile`
- `attach-cdp`

说明：

- `isolated-profile` 会启动独立浏览器用户目录，适合隔离自动化环境。
- `attach-cdp` 会连接已启动并开启 CDP 的 Chrome/Edge。
- 这两种模式都需要先安装自动化依赖，并额外执行 `playwright install chromium`。
- 这两种模式只应放在 `requests` 主流程之后考虑。

## 安装说明

最小安装只覆盖推荐主路径 `requests`：

```bash
python -m pip install --no-build-isolation -e .
```

如果需要 `windows-desktop` 或 Playwright 相关能力，再安装自动化依赖：

```bash
python -m pip install --no-build-isolation -e .[automation]
```

如果要使用 Playwright 相关模式 `isolated-profile` 或 `attach-cdp`，还必须继续执行：

```bash
playwright install chromium
```

## 注意事项

- README 中的主流程以 `requests` 为准；兜底和可选模式都放在快速开始之后。
- 默认配置文件名固定为 `codecheck-shield.config.json`。
- 默认输出命名规则依赖输入文件名，默认写入 `output/` 目录，结果为 `.results.csv`，日志为 `.log`，429 重试文件为 `.retry429.csv`。
- 输入文件的执行规则以 `详情链接` 和 `处理方式（待屏蔽/修改）` 为准。
- 结果文件只是在原始列后追加运行结果列，不会丢弃原始输入字段。
