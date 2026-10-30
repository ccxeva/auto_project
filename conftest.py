"""
pytest 全局 fixture：
- mock_server    : 当 base_url 指向 127.0.0.1 时自动后台启动本地 mock，session 结束后关闭
- api_client     : 统一请求封装实例（session 级）
- location_data  : 先调地点搜索 /v1/locations，拿到厦门的 location 编号与经纬度
                  实时天气用例通过该 fixture 完成"地点搜索 -> 实时天气"的依赖注入
"""
import os
import time
import socket
import subprocess
import sys
import pytest
from common.yaml_util import load_yaml, get_project_root
from common.request_handler import RequestHandler

ROOT = get_project_root()
CFG = load_yaml(os.path.join(ROOT, "config", "config.yaml"))


def _port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex((host, port)) == 0


@pytest.fixture(scope="session", autouse=True)
def mock_server():
    """
    如果 base_url 指向 127.0.0.1:18765 且端口未被占用，自动后台起 mock_server.py。
    切换到真实第三方服务时此 fixture 不会启动任何东西。
    """
    base = CFG["base_url"]
    proc = None
    if "127.0.0.1:18765" in base or "localhost:18765" in base:
        if not _port_in_use("127.0.0.1", 18765):
            proc = subprocess.Popen(
                [sys.executable, os.path.join(ROOT, "mock_server.py")],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            # 等待端口就绪
            for _ in range(30):
                if _port_in_use("127.0.0.1", 18765):
                    break
                time.sleep(0.1)
    yield
    if proc is not None:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture(scope="session")
def api_client() -> RequestHandler:
    return RequestHandler(
        base_url=CFG["base_url"],
        api_key=CFG["api_key"],
        timeout=CFG.get("timeout", 10),
    )


@pytest.fixture(scope="session")
def location_data(api_client) -> dict:
    """
    依赖前置：先调用地点搜索接口，返回厦门的标准编号与经纬度。
    实时天气用例用 ${location.id} / ${location.lat} / ${location.lon} 占位。
    """
    search = CFG["search"]
    resp = api_client.get(search["path"], params={"keyword": search["keyword"]})
    body = resp.json()
    assert body.get("code") == 0, f"地点搜索前置失败: {body}"
    item = body["data"][0]
    return {
        "id": item["id"],       # 如 101230201
        "lat": item["lat"],     # 如 24.48
        "lon": item["lon"],     # 如 118.09
        "name": item["name"],
    }
