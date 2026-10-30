"""
★ 统一请求封装（requests.Session 二次封装）
- 自动拼接 base_url、自动注入鉴权头 X-Api-Key
- 统一超时、统一异常捕获、统一日志
- 自动把请求 / 响应写入 Allure 步骤与附件（Key 脱敏）
"""
import json
import logging
import requests
import allure


class RequestHandler:
    def __init__(self, base_url: str, api_key: str, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        # 统一请求头：所有接口共用，避免每个用例重复写
        self.session.headers.update({
            "X-Api-Key": api_key,
            "Accept": "application/json",
            "Accept-Language": "zh-Hans",
            "Content-Type": "application/json; charset=utf-8",
        })
        self.log = logging.getLogger("api")

    def _masked_headers(self) -> dict:
        """把 API Key 脱敏后再写入 Allure，避免密钥泄露到报告。"""
        h = dict(self.session.headers)
        key = h.get("X-Api-Key", "")
        if key:
            h["X-Api-Key"] = key[:8] + "****" + key[-2:]
        return h

    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = self.base_url + path
        kwargs.setdefault("timeout", self.timeout)

        # ---- 写入 Allure 步骤：请求 ----
        with allure.step(f"[请求] {method.upper()} {url}"):
            req_attach = {
                "method": method.upper(),
                "url": url,
                "headers": self._masked_headers(),
                "params": kwargs.get("params"),
                "json": kwargs.get("json"),
            }
            allure.attach(
                json.dumps(req_attach, ensure_ascii=False, indent=2),
                name="request.json",
                attachment_type=allure.attachment_type.JSON,
            )
        self.log.info("%s %s params=%s", method.upper(), url, kwargs.get("params"))

        # ---- 发请求（异常不外泄原始堆栈，统一包装到 Allure） ----
        try:
            resp = self.session.request(method, url, **kwargs)
        except requests.RequestException as e:
            allure.attach(str(e), name="request_exception.txt",
                          attachment_type=allure.attachment_type.TEXT)
            raise

        # ---- 写入 Allure 步骤：响应 ----
        with allure.step(f"[响应] HTTP {resp.status_code}"):
            allure.attach(
                resp.text,
                name=f"response_{resp.status_code}.json",
                attachment_type=allure.attachment_type.JSON,
            )
        self.log.info("-> %s (%dB)", resp.status_code, len(resp.content))
        return resp

    # 常用方法快捷封装
    def get(self, path: str, params: dict = None, **kwargs) -> requests.Response:
        return self.request("GET", path, params=params, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        return self.request("POST", path, **kwargs)