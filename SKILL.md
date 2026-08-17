---
name: imagegen-junliai
description: 通过 img.junliai.org 的 OpenAI 兼容接口生成或编辑位图图片，默认优先使用 firefly-gpt-image-2 模型。适用于文生图、产品原型图、UI 效果图、海报、插画、参考图改图和多图融合；当用户要求使用 Junliai、image2、img.junliai.org 或 firefly-gpt-image-2 画图时使用此技能。
---

# Junliai 图片生成

使用随技能附带的脚本调用 Junliai 图片接口。每位使用者必须提供自己的 API Key，不得在技能文件、命令示例、日志或 Git 提交中写入真实 Key。

## 准备

在执行前确认环境变量存在：

```bash
export JUNLIAI_API_KEY="使用者自己的-key"
```

默认接口地址为 `https://img.junliai.org/v1`。仅在使用者明确要求代理或私有部署时设置 `JUNLIAI_BASE_URL`。

## 工作流程

1. 判断任务是文生图还是参考图编辑。
2. 将用户需求整理为明确提示词，保留用户给出的文字、构图、比例和风格约束。
3. 默认使用 `firefly-gpt-image-2`；只有用户指定其他模型或默认模型不可用时才改用 `--model`。
4. 执行脚本并将最终图片保存到当前项目内。
5. 使用可用的图片查看工具检查主体、构图、文字准确性和明显瑕疵。
6. 如果结果不符合要求，只针对最明显的问题修改提示词并重试。
7. 向用户报告最终图片路径、模型和最终提示词，不得报告或回显 API Key。

## 文生图

```bash
python3 <技能目录>/scripts/junliai_image.py generate \
  --prompt "一张安静专业的邮箱验证码管理后台产品原型图" \
  --size 2048x2048 \
  --output ./output.png
```

## 参考图编辑

单张参考图：

```bash
python3 <技能目录>/scripts/junliai_image.py edit \
  --image ./input.png \
  --prompt "保留布局，将界面改为浅色企业管理后台风格" \
  --output ./edited.png
```

多张参考图时重复传入 `--image`：

```bash
python3 <技能目录>/scripts/junliai_image.py edit \
  --image ./layout.png \
  --image ./style.png \
  --prompt "使用第一张的布局和第二张的视觉风格" \
  --output ./combined.png
```

## 模型与诊断

列出当前账户可用模型：

```bash
python3 <技能目录>/scripts/junliai_image.py models
```

仅检查参数和请求内容，不访问网络：

```bash
python3 <技能目录>/scripts/junliai_image.py generate \
  --prompt "测试提示词" \
  --output ./test.png \
  --dry-run
```

需要了解接口字段、响应格式或故障排查时，读取 [references/api.md](references/api.md)。

## 安全规则

- 只从 `JUNLIAI_API_KEY` 读取 Key，不接受把 Key 写进脚本或仓库。
- 不在输出、异常信息或调试内容中打印 Key。
- 不把返回的临时图片 URL 当作最终交付物；始终下载并保存本地文件。
- 不覆盖已有图片，除非用户明确要求；默认使用新的文件名。
- 不把用户输入图片上传到 Junliai 以外的第三方服务。
- 生成或编辑内容仍需遵守当前运行环境的安全政策。
