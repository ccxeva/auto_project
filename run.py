"""
123一键执行入口：
1. 跑 pytest，原始结果输出到 report/tmp
2. 复制 environment.properties 到 report/tmp（Allure 环境面板）
3. 用 allure 命令生成 HTML 报告到 report/html（若无 allure 命令则降级提示）
4. 打印正确的查看方式（不能直接双击 index.html，必须起本地 HTTP 服务）
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TMP = os.path.join(ROOT, "report", "tmp")
HTML = os.path.join(ROOT, "report", "html")


def main():
    os.makedirs(TMP, exist_ok=True)

    # 1) 跑 pytest
    cmd = [sys.executable, "-m", "pytest",
           os.path.join(ROOT, "testcases"),
           f"--alluredir={TMP}",
           "--clean-alluredir",
           "-ra"]
    print(">> 执行命令:", " ".join(cmd))
    exit_code = subprocess.call(cmd)

    # 2) 写入 Allure 环境信息
    env_src = os.path.join(ROOT, "config", "environment.properties")
    if os.path.exists(env_src):
        shutil.copy(env_src, os.path.join(TMP, "environment.properties"))

    # 3) 生成 HTML（依赖 allure 命令行；未安装时给出降级提示）
    allure_bin = shutil.which("allure")
    if allure_bin:
        subprocess.call([allure_bin, "generate", TMP, "-o", HTML, "--clean"])
        print(f"\n[OK] HTML 报告已生成: {HTML}")
    else:
        print("\n[WARN] 未检测到 allure 命令行（仅装了 pip 包，没有装 allure CLI）。")
        print("       原始结果已保留在:", TMP)
        print("       安装 allure CLI 后再跑一次即可生成 HTML：")
        print("         macOS : brew install allure")
        print("         Windows: scoop install allure  或  choco install allure")
        print("         Linux:  从 https://github.com/allure-framework/allure2/releases 下载")

    # 4) 明确告知查看方式（关键：不能直接 file:// 打开 index.html）
    print("\n" + "=" * 60)
    print("查看报告（二选一）：")
    print(f"  A) allure open {HTML}")
    print(f"  B) cd {HTML} && python -m http.server 8080")
    print("     然后浏览器访问:  http://localhost:8080")
    print("=" * 60)
    print("注意：直接双击 index.html 会出现 '500 Failed to fetch'，")
    print("      这是浏览器 file:// 协议限制，必须通过 HTTP 访问。")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
