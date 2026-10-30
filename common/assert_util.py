"""
断言工具：把文档约定的 HTTP 状态码、业务码 code、data 结构校验收敛到一处，
用例里只在 yaml 里写期望值，不重复写断言代码。
"""
import allure


def assert_common(resp, expected: dict):
    """
    expected 支持字段：
      http_code            期望 HTTP 状态码
      code                 期望业务码（响应体 .code）
      data_null            True 表示失败时 data 必须为 null
      data_not_null        True 表示成功时 data 必须非空
      data_field_equals    dict，对 data 下字段做等值断言（支持点路径 a.b.c）
    """
    body = {}
    try:
        body = resp.json()
    except ValueError:
        body = {}

    with allure.step("断言响应"):
        # 1) HTTP 状态码
        if "http_code" in expected:
            assert resp.status_code == expected["http_code"], \
                f"HTTP 状态码不符: 期望 {expected['http_code']}, 实际 {resp.status_code}"

        # 2) 业务码
        if "code" in expected:
            assert body.get("code") == expected["code"], \
                f"业务码 code 不符: 期望 {expected['code']}, 实际 {body.get('code')}"

        # 3) data 存在性
        if expected.get("data_null"):
            assert body.get("data") is None, "期望 data 为 null，但实际非空"
        if expected.get("data_not_null"):
            assert body.get("data") is not None, "期望 data 非空，但实际为 null"

        # 4) 关键字段等值（点路径）
        for dotted, want in (expected.get("data_field_equals") or {}).items():
            node = body.get("data", {})
            for seg in dotted.split("."):
                node = node.get(seg) if isinstance(node, dict) else None
            assert node == want, \
                f"字段 {dotted} 不符: 期望 {want}, 实际 {node}"