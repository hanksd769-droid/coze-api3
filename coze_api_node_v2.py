"""
ComfyUI Custom Node: Coze API Caller V2 (通用版) / V3 (参数可视化版) / MultiURLToArray
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
                    "default": '{"img": [""], "prompt": ""}',
                    "placeholder": '输入 JSON 格式的参数对象',
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
        if not content or not isinstance(content, dict):
            return ""
        output = content.get("output")
        if output is not None:
            if isinstance(output, list):
                return "".join(str(item) for item in output)
            return str(output)
        text = content.get("text")
        if text is not None:
            return str(text)
        inner_content = content.get("content")
        if inner_content is not None:
            return str(inner_content)
        return ""

    def parse_stream_response(self, response) -> str:
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
            if event_data.get("error_message"):
                raise RuntimeError(f"[Coze Error] {event_data['error_message']}")
            content = self.parse_content(event_data.get("content"))
            if not content:
                continue
            text = self.extract_text_from_output(content)
            if text:
                result_text += text
        return result_text.strip()

    def call_coze_api(self, coze_api_token, workflow_id,
                      parameters='{"img": [""], "prompt": ""}',
                      api_base_url="https://api.coze.cn/v1/workflow/stream_run",
                      timeout=120,
                      unique_id=None, extra_pnginfo=None):
        if not coze_api_token or not coze_api_token.strip():
            raise ValueError("[Error] 请提供 Coze API Token")
        if not workflow_id or not workflow_id.strip():
            raise ValueError("[Error] 请提供 Coze Workflow ID")
        try:
            params_dict = self.parse_parameters(parameters)
        except ValueError as e:
            raise ValueError(str(e))
        payload = {"workflow_id": workflow_id}
        if params_dict:
            payload["parameters"] = params_dict
        headers = {
            "Authorization": f"Bearer {coze_api_token.strip()}",
            "Content-Type": "application/json",
        }
        print(f"[Coze API V2] 调用工作流: {workflow_id}")
        print(f"[Coze API V2] API 地址: {api_base_url}")
        print(f"[Coze API V2] 参数: {json.dumps(params_dict, ensure_ascii=False)[:300]}")
        try:
            response = requests.post(
                api_base_url,
                headers=headers,
                json=payload,
                stream=True,
                timeout=timeout,
            )
            response.raise_for_status()
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


# ========== V3 节点：参数可视化配置 ==========

class CozeAPICallerV3:
    """
    ComfyUI 节点：调用 Coze 工作流 API（V3 参数可视化版）
    预设 8 组参数槽位，每组支持：变量名、变量类型、变量值
    变量值可连线输入，自动根据类型转换格式
    输出：output_text, debug_url, raw_json
    """

    CATEGORY = "Coze/API"
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("output_text", "debug_url", "raw_json")
    FUNCTION = "call_coze_api"
    OUTPUT_NODE = True

    TYPE_CHOICES = ["String", "Integer", "Number", "Boolean", "Object", "Array<String>", "Array<Object>", "File", "Time"]

    @classmethod
    def INPUT_TYPES(cls):
        inputs = {
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
            "optional": {},
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

        for i in range(1, 9):
            inputs["optional"][f"param_{i}_name"] = ("STRING", {
                "default": "",
                "multiline": False,
                "placeholder": f"参数{i} 变量名（如 img / prompt）",
            })
            inputs["optional"][f"param_{i}_type"] = (cls.TYPE_CHOICES, {"default": "String"})
            inputs["optional"][f"param_{i}_value"] = ("STRING", {
                "default": "",
                "multiline": True,
                "placeholder": f"参数{i} 值\n可手动输入或连线传入",
            })

        inputs["optional"]["api_base_url"] = ("STRING", {
            "default": "https://api.coze.cn/v1/workflow/stream_run",
            "multiline": False,
            "placeholder": "API 地址",
        })
        inputs["optional"]["timeout"] = ("INT", {
            "default": 120,
            "min": 10,
            "max": 600,
            "step": 10,
        })

        return inputs

    def parse_content(self, content):
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
        if not content or not isinstance(content, dict):
            return ""
        output = content.get("output")
        if output is not None:
            if isinstance(output, list):
                return "".join(str(item) for item in output)
            return str(output)
        text = content.get("text")
        if text is not None:
            return str(text)
        inner_content = content.get("content")
        if inner_content is not None:
            return str(inner_content)
        return ""

    def convert_value_by_type(self, name: str, type_str: str, value_str: str):
        if value_str is None:
            value_str = ""
        if isinstance(value_str, str):
            value_str = value_str.strip()
        if type_str != "Boolean" and value_str == "":
            return None
        try:
            if type_str == "String":
                return str(value_str)
            elif type_str == "Integer":
                return int(value_str)
            elif type_str == "Number":
                return float(value_str)
            elif type_str == "Boolean":
                if isinstance(value_str, bool):
                    return value_str
                s = str(value_str).strip().lower()
                return s in ("true", "1", "yes", "on", "是", "真", "开启")
            elif type_str == "Object":
                return json.loads(value_str)
            elif type_str == "Array<String>":
                try:
                    parsed = json.loads(value_str)
                    if isinstance(parsed, list):
                        return [str(v) for v in parsed]
                except (json.JSONDecodeError, TypeError):
                    pass
                lines = [line.strip() for line in str(value_str).splitlines() if line.strip()]
                return lines if lines else None
            elif type_str == "Array<Object>":
                return json.loads(value_str)
            elif type_str == "File":
                return str(value_str)
            elif type_str == "Time":
                return str(value_str)
            else:
                return str(value_str)
        except Exception as e:
            raise ValueError(f'参数 "{name}" 类型转换失败（{type_str}）: {str(e)}')

    def build_parameters(self, **kwargs) -> dict:
        params = {}
        for i in range(1, 9):
            name = kwargs.get(f"param_{i}_name", "")
            type_str = kwargs.get(f"param_{i}_type", "String")
            value = kwargs.get(f"param_{i}_value", "")
            if not name or not str(name).strip():
                continue
            name = str(name).strip()
            converted = self.convert_value_by_type(name, type_str, value)
            if converted is not None:
                params[name] = converted
        return params

    def parse_stream_response_v3(self, response):
        result_text = ""
        debug_url = ""
        raw_events = []
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
            raw_events.append(event_data)
            if event_data.get("error_message"):
                raise RuntimeError(f"[Coze Error] {event_data['error_message']}")
            if event_data.get("debug_url"):
                debug_url = event_data["debug_url"]
            content = self.parse_content(event_data.get("content"))
            if content:
                text = self.extract_text_from_output(content)
                if text:
                    result_text += text
        raw_json = json.dumps(raw_events, ensure_ascii=False, indent=2)
        return result_text.strip(), debug_url, raw_json

    def call_coze_api(self, coze_api_token, workflow_id, **kwargs):
        if not coze_api_token or not str(coze_api_token).strip():
            raise ValueError("[Error] 请提供 Coze API Token")
        if not workflow_id or not str(workflow_id).strip():
            raise ValueError("[Error] 请提供 Coze Workflow ID")

        api_base_url = kwargs.get("api_base_url", "https://api.coze.cn/v1/workflow/stream_run")
        timeout = kwargs.get("timeout", 120)

        try:
            params_dict = self.build_parameters(**kwargs)
        except ValueError as e:
            raise ValueError(str(e))

        payload = {"workflow_id": workflow_id}
        if params_dict:
            payload["parameters"] = params_dict

        headers = {
            "Authorization": f"Bearer {str(coze_api_token).strip()}",
            "Content-Type": "application/json",
        }

        print(f"[Coze API V3] 调用工作流: {workflow_id}")
        print(f"[Coze API V3] API 地址: {api_base_url}")
        print(f"[Coze API V3] 参数: {json.dumps(params_dict, ensure_ascii=False)[:500]}")

        try:
            response = requests.post(
                api_base_url,
                headers=headers,
                json=payload,
                stream=True,
                timeout=timeout,
            )
            response.raise_for_status()
            output_text, debug_url, raw_json = self.parse_stream_response_v3(response)
            if not output_text and not debug_url:
                raise RuntimeError("[Warning] Coze API 返回为空")
            print(f"[Coze API V3] output_text: {output_text[:100]}...")
            print(f"[Coze API V3] debug_url: {debug_url}")
            return (output_text, debug_url, raw_json)
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"[Network Error] Coze API 请求失败: {str(e)}")
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            raise RuntimeError(f"[Exception] Coze API 调用失败: {str(e)}")


# ========== 多 URL 转数组节点 ==========

class MultiURLToArray:
    """
    ComfyUI 工具节点：将最多 15 个 URL 字符串输入合并为一个 JSON 数组字符串
    输出可直接连线到 CozeAPICallerV3 的 Array<String> 类型参数
    """

    CATEGORY = "Coze/Utils"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("url_array",)
    FUNCTION = "convert"
    OUTPUT_NODE = False

    @classmethod
    def INPUT_TYPES(cls):
        optional = {}
        for i in range(1, 16):
            optional[f"url_{i}"] = ("STRING", {
                "default": "",
                "multiline": False,
                "placeholder": f"URL {i}",
            })
        return {
            "required": {},
            "optional": optional,
        }

    def convert(self, **kwargs):
        urls = []
        for i in range(1, 16):
            url = kwargs.get(f"url_{i}", "")
            if url and str(url).strip():
                urls.append(str(url).strip())
        return (json.dumps(urls, ensure_ascii=False),)


# ========== 节点注册 ==========

NODE_CLASS_MAPPINGS = {
    "CozeAPICallerV2": CozeAPICallerV2,
    "CozeAPICallerV3": CozeAPICallerV3,
    "MultiURLToArray": MultiURLToArray,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CozeAPICallerV2": "Coze API Caller V2 (通用版)",
    "CozeAPICallerV3": "Coze API Caller V3 (参数可视化版)",
    "MultiURLToArray": "多 URL 转数组 (MultiURLToArray)",
}
