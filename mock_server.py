"""
本地 Mock Server：按《天气预报接口 API 详细设计文档》契约返回响应。
零第三方依赖，仅用 Python 标准库。
- 127.0.0.1:18765
- GET /v1/locations           -> 地点搜索（返回厦门）
- GET /v1/weather/now         -> 实时天气（按参数返回 200/400/401/404）
- POST /v1/weather/now        -> 405
- 其他路径                     -> 404 + code=10005
"""
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HOST = "127.0.0.1"
PORT = 18765

VALID_KEY = "wk_test_0123456789abcdef"
FAKE_KEY = "wk_invalid_fake_key"


def _body(code, message, data=None, http_status=200):
    return http_status, {
        "code": code,
        "message": message,
        "requestId": "req-mock-000000000000",
        "timestamp": "2026-10-29T14:30:00+08:00",
        "data": data,
    }


def _now_payload(location_id="101230201", name="厦门", unit="c", lang="zh-Hans"):
    temp = 26 if unit == "c" else round(26 * 9 / 5 + 32, 1)
    feels = 27 if unit == "c" else round(27 * 9 / 5 + 32, 1)
    text = "多云" if lang == "zh-Hans" else "Cloudy"
    return {
        "location": {
            "id": location_id, "name": name, "country": "CN",
            "lat": 24.48, "lon": 118.09, "timezone": "Asia/Shanghai",
        },
        "now": {
            "text": text, "code": "1",
            "temperature": temp, "feelsLike": feels,
            "pressure": 1012, "humidity": 68, "visibility": 18.5,
            "windDirection": "东北风", "windDirectionDegree": 45,
            "windSpeed": 12.3, "windScale": "3", "cloud": 60,
        },
        "lastUpdate": "2026-10-29T14:25:00+08:00",
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # 静默

    def _send(self, http_status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(http_status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _auth(self):
        key = self.headers.get("X-Api-Key")
        if not key:
            return _body(20001, "缺少 API Key", None, 401)
        if key == FAKE_KEY or key != VALID_KEY:
            return _body(20002, "API Key 无效或已过期", None, 401)
        return None

    def do_GET(self):
        parsed = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(parsed.query).items()}

        # ---------- 地点搜索 ----------
        if parsed.path == "/v1/locations":
            err = self._auth()
            if err:
                return self._send(*err)
            if not q.get("keyword"):
                return self._send(*_body(10001, "缺少必填参数 keyword", None, 400))
            return self._send(200, _body(0, "success", [{
                "id": "101230201", "name": "厦门", "nameEn": "Xiamen",
                "adm1": "福建省", "country": "CN",
                "lat": 24.48, "lon": 118.09, "timezone": "Asia/Shanghai",
            }])[1])

        # ---------- 实时天气 ----------
        if parsed.path == "/v1/weather/now":
            err = self._auth()
            if err:
                return self._send(*err)

            location = q.get("location")
            lat = q.get("lat")
            lon = q.get("lon")
            unit = q.get("unit", "c")
            lang = q.get("lang", "zh-Hans")

            # 定位参数：location 与 lat/lon 二选一
            has_loc = bool(location)
            has_latlon = bool(lat) and bool(lon)
            if not has_loc and not has_latlon:
                return self._send(*_body(10001, "缺少必填参数 location 或 lat/lon", None, 400))
            if (bool(lat) ^ bool(lon)):
                return self._send(*_body(10001, "传入 lat 时必须同时传入 lon", None, 400))

            # 枚举校验
            if unit not in ("c", "f"):
                return self._send(*_body(10004, "参数 unit 取值非法，仅支持 c、f", None, 400))
            if lang not in ("zh-Hans", "en"):
                return self._send(*_body(10004, "参数 lang 取值非法", None, 400))

            # location 空串
            if location == "":
                return self._send(*_body(10001, "location 不能为空", None, 400))

            # 无效地点编号
            if location == "999999999":
                return self._send(*_body(10003, "无法识别的地点", None, 404))

            # 坐标越界 / 非数字
            try:
                lat_f = float(lat) if lat is not None else None
                lon_f = float(lon) if lon is not None else None
            except ValueError:
                return self._send(*_body(10002, "参数格式错误：lat/lon 应为数字", None, 400))
            if lat is not None and not (-90 <= lat_f <= 90):
                return self._send(*_body(10003, "坐标越界", None, 404))
            if lon is not None and not (-180 <= lon_f <= 180):
                return self._send(*_body(10003, "坐标越界", None, 404))

            # 海外城市（纽约）
            if lat is not None and abs(lat_f - 40.71) < 0.01:
                payload = _now_payload("69274", "New York", unit, lang)
                payload["location"]["timezone"] = "America/New_York"
                payload["location"]["name"] = "New York"
                return self._send(200, _body(0, "success", payload)[1])

            return self._send(200, _body(0, "success", _now_payload(unit=unit, lang=lang))[1])

        # ---------- 其他路径 ----------
        return self._send(*_body(10005, "请求路径或资源不存在", None, 404))

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/v1/weather/now":
            self.send_response(405)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(_body(0, "method not allowed", None, 405)[1],
                                         ensure_ascii=False).encode("utf-8"))
            return
        return self._send(*_body(10005, "请求路径或资源不存在", None, 404))


def serve():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"[Mock] http://{HOST}:{PORT}  (按 Ctrl+C 退出)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    serve()
