"""Yaml 读取工具：集中管理配置与用例数据的加载。"""
import os
import yaml


def load_yaml(file_path: str) -> dict:
    """读取 yaml 文件为 dict，统一编码 UTF-8。"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"yaml 文件不存在: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def get_project_root() -> str:
    """返回项目根目录（common 上一级），保证相对路径稳定。"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))