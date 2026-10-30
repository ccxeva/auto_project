# 实时天气接口自动化（Pytest + Requests + Yaml + Allure）

## 0. 关于真实后端
文档第 1 章的 `api.weather-demo.com` 是契约占位域名，公网不可访问。
本项目内置了 **mock_server.py**，按文档契约返回真实响应（200/400/401/404/405），
开箱即可跑通用例并生成 Allure 报告。如需联调真实第三方（心知/和风/OpenWeatherMap），
修改 `config/config.yaml` 的 `base_url` 和 `api_key` 即可。

## 1. 安装
    pip install -r requirements.txt
    # 可选：安装 Allure 命令行用于生成 HTML 报告
    #   macOS: brew install allure
    #   Windows: scoop install allure
    #   Linux: 从 https://github.com/allure-framework/allure2/releases 下载

## 2. 运行（mock 模式自动启动）
    python run.py
    # conftest.py 会自动在 127.0.0.1:18765 后台起 mock_server.py，跑完自动关闭
    # 也可手动起 mock 再跑 pytest：
    #   python mock_server.py &
    #   pytest testcases --alluredir=report/tmp --clean-alluredir

## 3. 查看报告（重要）
    # 方式 A：allure 命令行（会自动起本地 HTTP 服务）
    allure open report/html

    # 方式 B：手动起静态服务（不能直接双击 index.html，否则报 500 Failed to fetch）
    cd report/html
    python -m http.server 8080
    # 浏览器访问 http://localhost:8080

## 4. 设计要点
- 统一请求封装：common/request_handler.py（Session 复用、Key 脱敏、Allure 附件）
- 请求/数据分离：用例只写在 data/test_weather_now.yaml，新增用例不改 .py
- 依赖注入：conftest.py 的 location_data 先调 /v1/locations 再驱动实时天气
- 断言收敛：common/assert_util.py 按文档错误码统一断言
- Allure 定制：epic/feature/story/severity/tag + environment.properties 环境面板
- 用例隔离：extra_headers 修改 session 头后 try/finally 自动恢复，不污染后续用例

## 5. 已验证
- Python 3.12 / pytest 9.x / allure-pytest 2.16.x：20 passed in 0.75s
