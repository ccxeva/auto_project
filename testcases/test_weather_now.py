"""
实时天气查询接口测试用例：
- @pytest.mark.parametrize 从 yaml 批量驱动（请求操作与数据分离）
- Allure 定制：epic / feature / story / title / severity / tag
- 运行时把 ${location.xxx} 占位符替换为地点搜索 fixture 的真实值
"""
import os
import pytest
import allure
from common.yaml_util import load_yaml, get_project_root
from common.assert_util import assert_common

ROOT = get_project_root()
DATA = load_yaml(os.path.join(ROOT, "data", "test_weather_now.yaml"))["cases"]


def _resolve(value, location_data):
    """把 ${location.id} / ${location.lat} / ${location.lon} 替换为真实值。"""
    if isinstance(value, str) and value.startswith("${location."):
        key = value[len("${location."):-1]
        return str(location_data[key])
    return value


@allure.epic("天气预报服务")
@allure.feature("I-02 实时天气查询 /v1/weather/now")
class TestWeatherNow:

    @pytest.mark.parametrize("case", DATA, ids=[c["case_id"] for c in DATA])
    def test_weather_now(self, api_client, location_data, case):
        # ---- Allure 动态元数据 ----
        allure.dynamic.title(case["title"])
        allure.dynamic.story(" / ".join(case.get("tags", [])))
        allure.dynamic.severity(case.get("severity", "normal"))
        for t in case.get("tags", []):
            allure.dynamic.tag(t)

        # ---- 解析参数（含占位符替换） ----
        params = {k: _resolve(v, location_data)
                  for k, v in (case.get("params") or {}).items()}
        expected = case.get("expected", {})
        # 同样对 expected.data_field_equals 里的占位符做替换
        if "data_field_equals" in expected:
            expected["data_field_equals"] = {
                k: _resolve(v, location_data)
                for k, v in expected["data_field_equals"].items()
            }

        # ---- 用例级请求头覆盖（用于缺 Key / 伪造 Key 场景），finally 恢复默认 ----
        extra_headers = case.get("extra_headers")
        saved_headers = dict(api_client.session.headers) if extra_headers else None
        try:
            if extra_headers:
                with allure.step(f"覆盖请求头: {extra_headers}"):
                    for k, v in extra_headers.items():
                        if v is None:
                            api_client.session.headers.pop(k, None)
                        else:
                            api_client.session.headers[k] = v

            # ---- 发请求（统一走 RequestHandler） ----
            with allure.step(f"调用 {case['method']} {case['path']}"):
                if case["method"] == "GET":
                    resp = api_client.get(case["path"], params=params)
                elif case["method"] == "POST":
                    resp = api_client.post(case["path"], params=params)
                else:
                    raise ValueError(f"不支持的 method: {case['method']}")

            # ---- 统一断言 ----
            assert_common(resp, expected)
        finally:
            # 恢复 session 级默认 headers，避免污染后续用例
            if saved_headers is not None:
                api_client.session.headers.clear()
                api_client.session.headers.update(saved_headers)