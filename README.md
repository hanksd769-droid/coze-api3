# ComfyUI Coze API Plugin V2 (通用版)

在 ComfyUI 中调用 Coze（扣子）工作流 API 的通用自定义节点插件。支持自定义任意输入参数，自动解析流式返回。

## 特点

- **零额外依赖**：使用 ComfyUI 自带的 `requests` 库
- **通用参数**：通过 JSON 字符串自定义任意输入参数，不限定字段名
- **灵活配置**：可自定义 API 地址、超时时间
- **自动解析**：支持多种 Coze 返回结构（output/text/content/message/data）
- **错误中断**：Coze 返回错误时抛出异常，中断后续工作流

## 安装

将文件夹复制到 `ComfyUI/custom_nodes/comfyui-coze-api-v2/`，重启 ComfyUI 即可。

**无需安装任何依赖。**

## 使用方法

在 ComfyUI 的节点菜单中找到：

> **Coze/API → Coze API Caller V2 (通用版)**

### 节点参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `coze_api_token` | STRING | ✅ | Coze API Token（`cztei_` 或 `pat_` 开头） |
| `workflow_id` | STRING | ✅ | Coze 工作流 ID |
| `parameters` | STRING | ❌ | JSON 格式的参数字符串，自定义任意输入参数 |
| `api_base_url` | STRING | ❌ | API 地址，默认 `https://api.coze.cn/v1/workflow/stream_run` |
| `timeout` | INT | ❌ | 请求超时时间（秒），默认 120 |

### 输出

| 输出 | 类型 | 说明 |
|------|------|------|
| `output_text` | STRING | Coze 工作流返回的文本内容 |

### parameters 参数示例

**基础用法（图片+提示词）：**
```json
{
  "img": ["https://example.com/image.png"],
  "prompt": "请描述这张图片"
}
```

**多参数自定义：**
```json
{
  "image_url": "https://example.com/1.png",
  "query": "描述图片内容",
  "style": "photorealistic",
  "language": "chinese"
}
```

**空参数（不传 parameters）：**
```json
{}
```
或留空

### 参数注意事项

1. **必须是 JSON 对象**（dict），不是数组
2. **空值会自动过滤**：`""`、`[]`、`null` 不会传入
3. **字段名完全自定义**：根据你的 Coze 工作流输入参数名填写
4. **图片 URL 数组**：如果你的工作流接收 `img` 参数，用 `["url1", "url2"]` 格式

## 获取 Coze API Token

1. 登录 [Coze 平台](https://www.coze.cn/)
2. 进入 **个人设置 → 开发者令牌**
3. 创建 Personal Access Token（PAT）
4. 复制 Token（`pat_xxxx` 或 `cztei_xxxx`）

## 获取 Workflow ID

1. 在 Coze 平台创建并发布工作流
2. 从浏览器地址栏复制工作流 ID（URL 最后一段数字）

## 文件结构

```
comfyui-coze-api-v2/
├── __init__.py              # 插件入口
├── coze_api_node_v2.py      # 通用节点实现
├── requirements.txt         # 依赖说明（无额外依赖）
└── README.md                # 本文件
```

## 常见问题

### Q: 如何知道我的 Coze 工作流需要什么参数？
A: 在 Coze 平台查看工作流的「输入参数」配置，字段名必须完全匹配。

### Q: 参数 JSON 解析失败怎么办？
A: 检查 JSON 格式是否正确，注意引号、逗号、括号匹配。可用在线 JSON 校验工具检查。

### Q: 支持哪些 API 地址？
A: 默认中国节点 `https://api.coze.cn/v1/workflow/stream_run`，国际节点 `https://api.coze.com/v1/workflow/stream_run`，也支持自定义地址。

### Q: 返回结构不匹配怎么办？
A: 当前版本支持提取 `output`、`text`、`content`、`message`、`data` 字段。如果结构不同，可修改代码中的 `extract_text_from_content` 方法。

## License

MIT License

## 致谢

- [Coze](https://www.coze.cn/) — 扣子 AI 平台
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) — 强大的 Stable Diffusion 图形界面
