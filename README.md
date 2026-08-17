# imagegen-junliai

通过 [Junliai 图片接口](https://img.junliai.org/) 生成和编辑图片的 Agent Skill，默认优先使用 `firefly-gpt-image-2`。

支持 Codex、Claude Code、Cursor、OpenCode 等兼容 Agent Skills 标准的工具。

## 功能

- 根据中文提示词生成图片
- 使用一张或多张参考图进行编辑
- 默认调用 `firefly-gpt-image-2`
- 支持 `b64_json` 和图片 URL 响应
- 自动将结果下载到本地文件
- 支持查询当前账号可用模型
- 支持通过 `JUNLIAI_BASE_URL` 使用兼容的私有地址
- 不在代码、日志或 Git 历史中保存 API Key

## 安装

### 使用 `npx skills` 安装

`npx skills` 是 Vercel Labs 的跨 Agent 技能安装工具。它支持从 GitHub 仓库根目录发现 `SKILL.md`，因此可以直接安装本仓库。

当前版本的 `skills` CLI 要求 Node.js `>=22.20.0`。安装到所有已识别的 Agent：

```bash
npx skills add ljunn/imagegen-junliai -g -a '*' -y
```

其中 `-g` 表示全局安装，`-a '*'` 表示安装到 CLI 支持并检测到的所有 Agent。只安装到 Codex 时才使用 `-a codex`：

```bash
npx skills add ljunn/imagegen-junliai -g -a codex -y
```

查看仓库中发现的技能：

```bash
npx skills add ljunn/imagegen-junliai --list
```

更新已安装版本：

```bash
npx skills update imagegen-junliai -g -y
```

关闭匿名遥测：

```bash
DISABLE_TELEMETRY=1 npx skills add ljunn/imagegen-junliai -g -a '*' -y
```

### 手动安装到 Codex

不使用 Node.js 时，可以直接把仓库放入 Codex 用户技能目录：

```bash
git clone https://github.com/ljunn/imagegen-junliai.git \
  "$HOME/.agents/skills/imagegen-junliai"
```

也可以安装到当前项目，使团队成员共享：

```bash
mkdir -p .agents/skills
git clone https://github.com/ljunn/imagegen-junliai.git \
  .agents/skills/imagegen-junliai
```

安装后重新启动 Codex，或在提示词中显式输入：

```text
$imagegen-junliai 帮我生成一张邮箱验证码管理后台产品原型图
```

## 配置 API Key

每个使用者必须使用自己的 Key。建议通过环境变量配置，不要把 Key 写入项目文件：

```bash
export JUNLIAI_API_KEY="使用者自己的-key"
```

可选地覆盖接口地址：

```bash
export JUNLIAI_BASE_URL="https://img.junliai.org/v1"
```

## 使用脚本

文生图：

```bash
python3 scripts/junliai_image.py generate \
  --prompt "一张专业、简洁的邮箱验证码管理后台产品原型图" \
  --size 2048x2048 \
  --output ./output.png
```

参考图编辑：

```bash
python3 scripts/junliai_image.py edit \
  --image ./input.png \
  --prompt "保留页面布局，改成浅色企业管理后台风格" \
  --output ./edited.png
```

查询模型：

```bash
python3 scripts/junliai_image.py models
```

查看全部参数：

```bash
python3 scripts/junliai_image.py --help
```

## 目录结构

```text
SKILL.md                         技能说明和执行流程
agents/openai.yaml               Codex/ChatGPT 界面元数据
scripts/junliai_image.py         图片生成和编辑脚本
references/api.md                 Junliai 接口参考
```

## 安全说明

- 本仓库不包含任何可用 API Key。
- 图片请求会将提示词和参考图发送到 Junliai 服务。
- 默认使用 Base64 响应并保存到本地，避免依赖临时 URL。
- 请不要把第三方账号、私密文件或未获授权的内容上传到接口。

## 相关文档

- [Codex 官方技能文档](https://developers.openai.com/codex/skills)
- [`npx skills` CLI 文档](https://github.com/vercel-labs/skills)
- [Junliai 图片接口](https://img.junliai.org/)

## 许可证

[MIT License](LICENSE)
