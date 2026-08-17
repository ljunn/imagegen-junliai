#!/usr/bin/env python3
"""通过 Junliai 的 OpenAI 兼容接口生成或编辑图片。"""

import argparse
import base64
import json
import mimetypes
import os
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path


DEFAULT_BASE_URL = "https://img.junliai.org/v1"
DEFAULT_MODEL = "firefly-gpt-image-2"
DEFAULT_TIMEOUT = 300


class JunliaiError(RuntimeError):
    """表示可安全展示给使用者的接口错误。"""


def normalize_base_url(value):
    """接受带或不带 /v1 的地址，返回规范化 Base URL。"""
    value = (value or DEFAULT_BASE_URL).strip().rstrip("/")
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise JunliaiError("JUNLIAI_BASE_URL 必须是有效的 HTTP 或 HTTPS 地址")
    if not value.endswith("/v1"):
        value += "/v1"
    return value


def get_api_key(required=True):
    """只从环境变量读取密钥，避免进入命令历史。"""
    key = os.environ.get("JUNLIAI_API_KEY", "").strip()
    if required and not key:
        raise JunliaiError("缺少 JUNLIAI_API_KEY，请先设置使用者自己的 API Key")
    return key


def redact(text, key):
    """避免服务端错误意外回显密钥。"""
    text = str(text)
    return text.replace(key, "***") if key else text


def request(req, key, timeout):
    """发送请求并解析 JSON，统一处理错误。"""
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read(8192).decode("utf-8", errors="replace")
        raise JunliaiError(
            "Junliai 接口返回 HTTP {}：{}".format(exc.code, redact(body, key))
        ) from exc
    except urllib.error.URLError as exc:
        raise JunliaiError("无法连接 Junliai 接口：{}".format(redact(exc.reason, key))) from exc

    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise JunliaiError("Junliai 接口没有返回有效 JSON") from exc


def json_request(base_url, path, key, timeout, payload=None):
    """发送 JSON 请求。"""
    headers = {
        "Accept": "application/json",
        "Authorization": "Bearer {}".format(key),
        "User-Agent": "imagegen-junliai/1.0",
    }
    data = None
    method = "GET"
    if payload is not None:
        method = "POST"
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(base_url + path, data=data, headers=headers, method=method)
    return request(req, key, timeout)


def multipart_body(fields, images):
    """创建包含一个或多个 image 字段的 multipart 请求体。"""
    boundary = "----imagegen-junliai-{}".format(uuid.uuid4().hex)
    parts = []

    for name, value in fields.items():
        parts.extend(
            [
                "--{}\r\n".format(boundary).encode("ascii"),
                'Content-Disposition: form-data; name="{}"\r\n\r\n'.format(name).encode("utf-8"),
                str(value).encode("utf-8"),
                b"\r\n",
            ]
        )

    for image_path in images:
        path = Path(image_path)
        if not path.is_file():
            raise JunliaiError("参考图不存在：{}".format(path))
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        safe_name = path.name.replace('"', "")
        parts.extend(
            [
                "--{}\r\n".format(boundary).encode("ascii"),
                (
                    'Content-Disposition: form-data; name="image"; filename="{}"\r\n'.format(
                        safe_name
                    )
                ).encode("utf-8"),
                "Content-Type: {}\r\n\r\n".format(content_type).encode("ascii"),
                path.read_bytes(),
                b"\r\n",
            ]
        )

    parts.append("--{}--\r\n".format(boundary).encode("ascii"))
    return b"".join(parts), boundary


def edit_request(base_url, key, timeout, fields, images):
    """发送参考图编辑请求。"""
    body, boundary = multipart_body(fields, images)
    headers = {
        "Accept": "application/json",
        "Authorization": "Bearer {}".format(key),
        "Content-Type": "multipart/form-data; boundary={}".format(boundary),
        "User-Agent": "imagegen-junliai/1.0",
    }
    req = urllib.request.Request(
        base_url + "/images/edits", data=body, headers=headers, method="POST"
    )
    return request(req, key, timeout)


def atomic_write(path, content):
    """先写临时文件，再替换目标文件，避免留下半张图片。"""
    output = Path(path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise JunliaiError("目标文件已存在，请使用新的文件名：{}".format(output))

    file_descriptor, temp_name = tempfile.mkstemp(prefix=".junliai-", dir=str(output.parent))
    try:
        with os.fdopen(file_descriptor, "wb") as handle:
            handle.write(content)
        os.replace(temp_name, output)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise
    return output


def download_image(url, timeout):
    """下载接口返回的公开图片 URL，不携带 API Key。"""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise JunliaiError("接口返回了无效的图片 URL")
    req = urllib.request.Request(url, headers={"User-Agent": "imagegen-junliai/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read()
    except urllib.error.URLError as exc:
        raise JunliaiError("图片 URL 下载失败：{}".format(exc.reason)) from exc


def image_bytes(response, timeout):
    """从 OpenAI 风格响应中取得图片字节。"""
    data = response.get("data") if isinstance(response, dict) else None
    if not isinstance(data, list) or not data or not isinstance(data[0], dict):
        raise JunliaiError("响应中缺少 data[0] 图片结果")
    item = data[0]

    if item.get("b64_json"):
        try:
            return base64.b64decode(item["b64_json"], validate=True)
        except (ValueError, TypeError) as exc:
            raise JunliaiError("响应中的 b64_json 无法解码") from exc
    if item.get("url"):
        return download_image(item["url"], timeout)
    raise JunliaiError("响应中既没有 b64_json，也没有 url")


def common_payload(args):
    return {
        "model": args.model,
        "prompt": args.prompt,
        "size": args.size,
        "response_format": args.response_format,
    }


def run_generate(args, base_url):
    payload = common_payload(args)
    if args.dry_run:
        print(json.dumps({"端点": base_url + "/images/generations", "请求": payload}, ensure_ascii=False, indent=2))
        return
    key = get_api_key()
    response = json_request(base_url, "/images/generations", key, args.timeout, payload)
    output = atomic_write(args.output, image_bytes(response, args.timeout))
    print("图片已保存：{}".format(output))


def run_edit(args, base_url):
    fields = common_payload(args)
    if args.dry_run:
        print(
            json.dumps(
                {"端点": base_url + "/images/edits", "表单": fields, "参考图": args.image},
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    key = get_api_key()
    response = edit_request(base_url, key, args.timeout, fields, args.image)
    output = atomic_write(args.output, image_bytes(response, args.timeout))
    print("图片已保存：{}".format(output))


def run_models(args, base_url):
    key = get_api_key()
    response = json_request(base_url, "/models", key, args.timeout)
    models = response.get("data", []) if isinstance(response, dict) else []
    identifiers = [item.get("id") for item in models if isinstance(item, dict) and item.get("id")]
    if identifiers:
        print("\n".join(identifiers))
    else:
        print(json.dumps(response, ensure_ascii=False, indent=2))


def add_image_arguments(parser, include_images=False):
    parser.add_argument("--prompt", required=True, help="图片提示词")
    parser.add_argument("--output", required=True, help="本地输出文件路径")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="模型名，默认：%(default)s")
    parser.add_argument("--size", default="2048x2048", help="图片尺寸，默认：%(default)s")
    parser.add_argument(
        "--response-format",
        choices=("b64_json", "url"),
        default="b64_json",
        help="接口响应格式，默认：%(default)s",
    )
    parser.add_argument("--dry-run", action="store_true", help="只显示请求内容，不访问网络")
    if include_images:
        parser.add_argument("--image", action="append", required=True, help="参考图路径，可重复传入")


def build_parser():
    parser = argparse.ArgumentParser(description="通过 Junliai 生成或编辑图片")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("JUNLIAI_BASE_URL", DEFAULT_BASE_URL),
        help="API Base URL，默认读取 JUNLIAI_BASE_URL",
    )
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="请求超时秒数")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="根据提示词生成图片")
    add_image_arguments(generate)
    generate.set_defaults(handler=run_generate)

    edit = subparsers.add_parser("edit", help="根据参考图编辑图片")
    add_image_arguments(edit, include_images=True)
    edit.set_defaults(handler=run_edit)

    models = subparsers.add_parser("models", help="列出当前账户可用模型")
    models.set_defaults(handler=run_models)
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.timeout <= 0:
            raise JunliaiError("--timeout 必须大于 0")
        base_url = normalize_base_url(args.base_url)
        args.handler(args, base_url)
    except JunliaiError as exc:
        print("错误：{}".format(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
