# codecheck-shield v1.0.0

批量读取表格中的 CodeCheck 问题链接，并将指定问题更新为 `忽略问题`。

要求 Python 3.10+。

## 推荐使用方式

优先使用 `requests` 模式。

这是当前默认方案，原因是：

- 直接调用 CodeCheck 后端接口，不依赖页面点击
- 不受浏览器焦点、页面布局、分辨率缩放影响
- 更适合大批量执行
- 能根据 `详情链接` 自动构造请求
- POST 之后会追加一次问题详情查询，确认屏蔽理由确实已写入，而不是只信任接口返回

只有在当前站点环境无法稳定导出请求、或者直接请求被限制时，再退回 `windows-desktop` 模式。

## 推荐流程

推荐命令流：

- `codecheck-shield setup`
- `codecheck-shield run <input_file>`

说明：

- `setup`：读取一次手工成功操作对应的 cURL，请求中提取认证信息并保存到本地配置
- `run`：读取本地配置并批量执行，无需每次重复传长串认证参数

默认配置文件路径：

- `./codecheck-shield.config.json`

如果当前工作目录存在这个文件，`codecheck-shield run ...` 会自动读取它。
也可以通过 `--config` 指定其他路径。

## 支持的模式

### 1. `requests` 模式

默认优先模式。

执行逻辑：

1. 根据表格中的 `详情链接` 提取 `project_id / task_id / merge_key / defectIndex`
2. 调用 `POST /codechecknew/report/v1/defect/issue-status`
3. 再调用 `GET /codechecknew/report/v1/defect?...` 做结果校验
4. 只有校验通过，才视为真正成功

### 2. `windows-desktop` 模式

Windows 兜底方案。

执行逻辑：

1. 打开问题详情页
2. 点击 `修改问题状态`
3. 选择 `忽略问题`
4. 填写评论
5. 点击 `确定`
6. 成功后关闭当前标签页

适用于：

- 直接请求无法稳定使用
- 当前登录态只能在真实浏览器环境中通过安全校验

### 3. Playwright 模式

仅保留为可选模式：

- `isolated-profile`
- `attach-cdp`

这两个模式不是主推荐路径，只适用于你的环境确实允许 Playwright 控制浏览器时。

## 输入表格要求

支持 `CSV` 和 `XLSX`。

### 必填列

- `详情链接`

### 可选列

- `处理方式（待屏蔽/修改）`
- `屏蔽理由`
- `屏蔽描述`
- `reason`

## 行筛选规则

如果表格中不存在 `处理方式（待屏蔽/修改）`：

- 只要该行有 `详情链接`，就会进入执行队列

如果表格中存在 `处理方式（待屏蔽/修改）`：

- 只有值为 `待屏蔽` 的行会执行
- 值为 `修改` 的行会自动跳过

## 屏蔽理由取值优先级

每一行实际提交到 CodeCheck 的评论文本，按以下优先级选择：

1. `屏蔽理由`
2. `屏蔽描述`
3. `reason`
4. `--default-reason`
5. 默认值 `评审可屏蔽`

## 表格示例

见 [examples/sample_tasks.csv](/home/gantasy/work/auto-check/examples/sample_tasks.csv)。

推荐表头：

```csv
详情链接,处理方式（待屏蔽/修改）,屏蔽描述,reason
```

示例：

```csv
详情链接,处理方式（待屏蔽/修改）,屏蔽描述,reason,备注
https://codecheck.cn-north-4.example.invalid/codechecknew/project/project-demo/codecheck/task/green/task-demo/defect/defect-demo-1?defectIndex=1,待屏蔽,已经是const,命中函数形参常量性建议,会执行
https://codecheck.cn-north-4.example.invalid/codechecknew/project/project-demo/codecheck/task/green/task-demo/defect/defect-demo-2?defectIndex=1,待屏蔽,,规则稳定误报,会执行
https://codecheck.cn-north-4.example.invalid/codechecknew/project/project-demo/codecheck/task/green/task-demo/defect/defect-demo-3?defectIndex=1,修改,应当修复,按真问题保守处理,会跳过
```

说明：

- `详情链接` 必填
- `处理方式（待屏蔽/修改）` 建议保留，用于自动区分“待屏蔽”和“修改”
- `屏蔽描述` 推荐直接作为屏蔽评论
- `屏蔽理由` 也支持
- 额外列会原样保留到结果文件中

## 安装

### 仅使用 `requests` 模式

Linux / macOS:

```bash
python -m pip install --no-build-isolation -e .
```

Windows:

```powershell
py -3.10 -m pip install --upgrade pip setuptools wheel
py -3.10 -m pip install --no-build-isolation -e .
```

### 使用桌面自动化或 Playwright 模式

Linux / macOS:

```bash
python -m pip install --no-build-isolation -e .[automation]
```

Windows:

```powershell
py -3.10 -m pip install --upgrade pip setuptools wheel
py -3.10 -m pip install --no-build-isolation -e .[automation]
```

补充说明：

- `requests` 模式不需要安装 `playwright`
- `windows-desktop` 模式也不需要执行 `playwright install chromium`

## `requests` 模式配置

### 第一步：手工完成一次成功屏蔽

在浏览器中手工完成一次 `忽略问题` 操作。

### 第二步：导出 cURL

在浏览器 DevTools 的 Network 面板中，找到对应的 `issue-status` 请求，复制为 cURL。

将内容保存到本地文件，例如：

- `request.curl`

### 第三步：生成本地配置

```bash
codecheck-shield setup --from-curl-file request.curl
```

如果要同时设置默认理由：

```bash
codecheck-shield setup --from-curl-file request.curl --default-reason "人工确认可屏蔽"
```

如果要指定配置文件路径：

```bash
codecheck-shield setup --from-curl-file request.curl --config ./my-config.json
```

### 第四步：执行批处理

```bash
codecheck-shield run tasks.xlsx --output results.csv
```

如果配置文件不是默认路径：

```bash
codecheck-shield run tasks.xlsx --config ./my-config.json --output results.csv
```

## `windows-desktop` 模式使用方式

### 1. 先做一次桌面校准

```bash
codecheck-shield --calibrate-desktop --desktop-calibration-file desktop-calibration.json
```

校准时会依次要求你把鼠标移动到以下位置并回车：

- `修改问题状态`
- `忽略问题`
- 评论输入框
- `确定`

### 2. 执行批处理

```bash
codecheck-shield run tasks.xlsx --output results.csv --browser-mode windows-desktop --desktop-calibration-file desktop-calibration.json
```

如果要指定默认理由：

```bash
codecheck-shield run tasks.xlsx --output results.csv --browser-mode windows-desktop --desktop-calibration-file desktop-calibration.json --default-reason "人工确认可屏蔽"
```

如果页面切换较慢，可以调大等待时间：

```bash
codecheck-shield run tasks.xlsx --browser-mode windows-desktop --desktop-calibration-file desktop-calibration.json --page-load-seconds 4 --action-delay-seconds 0.8
```

## 可选 Playwright 命令示例

例如：

```bash
codecheck-shield run tasks.xlsx --browser-mode attach-cdp --cdp-url http://127.0.0.1:9222
```

注意：这不是主推荐路径。

## 兼容旧命令

旧的直接传认证参数方式仍然可用，例如：

```bash
codecheck-shield tasks.xlsx --output results.csv --request-cookie-file cookie.txt --agency-id "<agency id>" --cftk "<token>"
```

## 输出结果

输出 CSV 会保留原始列，并追加以下字段：

- `run_status`
- `run_message`
- `processed_at`
- `used_reason`
- `screenshot_path`

示例：

```csv
详情链接,处理方式（待屏蔽/修改）,屏蔽描述,run_status,run_message,processed_at,used_reason,screenshot_path
https://example.test/codecheck/defect/1,待屏蔽,规则稳定误报,success,,2026-04-27T13:20:00+08:00,规则稳定误报,
https://example.test/codecheck/defect/2,待屏蔽,,failed_request,CodeCheck API rejected the request...,2026-04-27T13:21:10+08:00,人工确认可屏蔽,
```

字段含义：

- `run_status`：执行状态，例如 `success`、`failed_request`、`failed_desktop_step`
- `run_message`：失败原因
- `processed_at`：执行时间
- `used_reason`：本行实际提交的屏蔽理由
- `screenshot_path`：失败截图路径；通常只在桌面或浏览器自动化失败时存在

## 开发

运行测试：

```bash
pytest -q
```

## 注意事项

- 优先使用 `requests` 模式，不要默认上桌面自动化
- `windows-desktop` 模式依赖固定屏幕坐标，浏览器缩放、分辨率、显示器缩放变化后要重新校准
- 使用 `windows-desktop` 模式时，执行期间请保持目标浏览器窗口在前台
- `windows-desktop` 模式成功处理一行后会关闭当前标签页，建议使用独立浏览器窗口执行
- 不要把真实 cookie、截图、内部表格等敏感数据直接提交到 GitHub
