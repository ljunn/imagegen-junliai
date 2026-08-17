# Junliai 图片 API 参考

本文档记录 `https://img.junliai.org/` 在 2026-08-17 公开展示的 OpenAI 兼容图片接口。服务方可能调整模型、尺寸、价格和限额；遇到服务端拒绝时，先调用模型列表确认当前能力。

## 基础信息

- 默认 Base URL：`https://img.junliai.org/v1`
- 鉴权请求头：`Authorization: Bearer <使用者自己的 Key>`
- 推荐模型：`firefly-gpt-image-2`
- 环境变量：`JUNLIAI_API_KEY`
- 可选地址覆盖：`JUNLIAI_BASE_URL`

## 端点

| 方法 | 端点 | 用途 |
|---|---|---|
| `GET` | `/v1/models` | 查询当前 Key 可用模型 |
| `POST` | `/v1/images/generations` | 文生图 |
| `POST` | `/v1/images/edits` | 参考图编辑，使用 multipart |
| `POST` | `/v1/responses` | 提交异步图片任务 |
| `GET` | `/v1/responses/{id}` | 查询异步任务 |
| `POST` | `/v1/responses/{id}/cancel` | 取消异步任务 |

## 文生图请求

```json
{
  "model": "firefly-gpt-image-2",
  "prompt": "一张专业的邮箱管理后台产品原型图",
  "size": "2048x2048",
  "response_format": "b64_json"
}
```

脚本默认请求 `b64_json`，这样可以立即保存本地文件。也可使用 `url`，但站点说明公开 URL 最长只保留 24 小时。

## 参考图编辑

向 `/v1/images/edits` 提交 multipart 表单：

- `model`：模型名
- `prompt`：编辑要求
- `size`：输出尺寸
- `response_format`：`b64_json` 或 `url`
- `image`：图片文件；多图时重复该字段

## 响应

OpenAI 风格响应通常包含以下任一结构：

```json
{"data":[{"b64_json":"..."}]}
```

```json
{"data":[{"url":"https://..."}]}
```

技能脚本会自动解码 Base64 或下载 URL，并以原子方式写入目标文件。

## 常见故障

- `401`：Key 缺失、无效或已过期。
- `403`：Key 没有模型权限，或账户受到限制。
- `429`：额度不足或请求过快，等待后重试。
- `5xx`：服务端或上游模型异常，保留错误摘要后稍后重试。
- 模型不存在：执行 `models` 子命令确认模型名，再显式设置 `--model`。
- 返回 URL 下载失败：重新生成并使用默认的 `b64_json` 响应格式。
