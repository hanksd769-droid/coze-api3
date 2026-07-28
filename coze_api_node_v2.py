"""
ComfyUI Custom Node: Coze API Caller V2 (通用版)
调用 Coze 工作流 API，支持自定义所有输入参数
使用原生 requests，无需安装 cozepy
"""

import json
import requests


class CozeAPICallerV2:
    """
    ComfyUI 通用节点：调用 Coze 工作流 API
    支持自定义任意输入参数，自动解析流式返回
    """

    CATEGORY = "Coze/API"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("output_text",)
    FUNCTION = "call_coze_api"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "coze_api_token": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "Coze API Token",
                }),
                "workflow_id": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "Coze Workflow ID",
                }),
            },
            "optional": {
                "parameters": ("STRING", {
                    "multiline": True,
                    "default": '{\n  "img": [""],\n  "prompt": ""\n}',
                    "placeholder": '输入 JSON 格式的参数对象，如：\n{"img": ["https://..."], "prompt": "描述图片"}',
                }),
                "api_base_url": ("STRING", {
                    "default": "https://api.coze.cn/v1/workflow/stream_run",
                    "multiline": False,
                    "placeholder": "API 地址",
                }),
                "timeout": ("INT", {
                    "default": 120,
                    "min": 10,
                    "max": 600,
                    "step": 10,
                }),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    def parse_parameters(self, params_str: str) -> dict:
        """
        解析用户输入的参数字符串
        支持 JSON 对象格式
        """
        if not params_str or not params_str.strip():
            return {}

        params_str = params_str.strip()

        try:
            params = json.loads(params_str)
            if isinstance(params, dict):
                result = {}
                for k, v in params.items():
                    if v is not None and v != "" and v != []:
                        result[k] = v
                return result
            else:
                raise ValueError("参数必须是 JSON 对象（dict）")
        except json.JSONDecodeError as e:
            raise ValueError(f"参数 JSON 解析失败: {str(e)}")

    def parse_content(self, content):
        """
        解析 content 字段，支持 dict 和 JSON 字符串两种格式
        """
        if content is None:
            return None

        if isinstance(content, dict):
            return content

        if isinstance(content, str):
            content = content.strip()
            if not content or content == "{}":
                return None
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {"text": content}

        return None

    def extract_text_from_output(self, content):
        """
        从解析后的 content dict 中提取纯文本
        支持多种返回结构
        """
        if not content or not isinstance(content, dict):
            return ""

        # 1. 提取 output 字段
        output = content.get("output")
        if output is not None:
            if isinstance(output, list):
                return "".join(str(item) for item in output)
            else:
                return str(output)

        # 2. 备选：提取 text 字段
        text = content.get("text")
        if text is not None:
            return str(text)

        # 3. 备选：提取 content 字段
        inner_content = content.get("content")
        if inner_content is not None:
            return str(inner_content)

        return ""

    def parse_stream_response(self, response) -> str:
        """
        解析 Coze 流式返回的 SSE 格式数据
        """
        result_text = ""

        for line in response.iter_lines():
            if not line:
                continue

            line_str = line.decode("utf-8")

            if not line_str.startswith("data:"):
                continue

            json_str = line_str[5:].strip()

            if json_str == "[DONE]":
                break

            try:
                event_data = json.loads(json_str)
            except json.JSONDecodeError:
                continue

            # 处理错误事件
            if event_data.get("error_message"):
                raise RuntimeError(f"[Coze Error] {event_data['error_message']}")

            # 解析 content
            content = self.parse_content(event_data.get("content"))

            if not content:
                continue

            # 提取纯文本
            text = self.extract_text_from_output(content)
            if text:
                result_text += text

        return result_text.strip()

    def call_coze_api(self, coze_api_token, workflow_id,
                      parameters='{\n  "img": [""],\n  "prompt": ""\n}',
                      api_base_url="https://api.coze.cn/v1/workflow/stream_run",
                      timeout=120,
                      unique_id=None, extra_pnginfo=None):
        """
        主执行函数：调用 Coze API
        """
        # 参数校验（只检查非空，不限制格式）
        if not coze_api_token or not coze_api_token.strip():
            raise ValueError("[Error] 请提供 Coze API Token")

        if not workflow_id or not workflow_id.strip():
            raise ValueError("[Error] 请提供 Coze Workflow ID")

        # 解析参数
        try:
            params_dict = self.parse_parameters(parameters)
        except ValueError as e:
            raise ValueError(str(e))

        # 构建请求体
        payload = {
            "workflow_id": workflow_id,
        }

        if params_dict:
            payload["parameters"] = params_dict

        # 请求头
        headers = {
            "Authorization": f"Bearer {coze_api_token.strip()}",
            "Content-Type": "application/json",
        }

        print(f"[Coze API V2] 调用工作流: {workflow_id}")
        print(f"[Coze API V2] API 地址: {api_base_url}")
        print(f"[Coze API V2] 参数: {json.dumps(params_dict, ensure_ascii=False)[:300]}")

        try:
            # 发送 POST 请求，流式接收
            response = requests.post(
                api_base_url,
                headers=headers,
                json=payload,
                stream=True,
                timeout=timeout,
            )

            # HTTP 错误直接抛出
            response.raise_for_status()

            # 解析流式返回
            result = self.parse_stream_response(response)

            if not result:
                raise RuntimeError("[Warning] Coze API 返回为空")

            print(f"[Coze API V2] 返回结果: {result[:100]}...")

            return (result,)

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"[Network Error] Coze API 请求失败: {str(e)}")
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            raise RuntimeError(f"[Exception] Coze API 调用失败: {str(e)}")


# ========== 节点注册 ==========

NODE_CLASS_MAPPINGS = {
    "CozeAPICallerV2": CozeAPICallerV2,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CozeAPICallerV2": "Coze API Caller V2 (通用版)",
}
