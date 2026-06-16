"""
* SettingsStore class
* 用户配置持久化 - 存储LLM API Key等配置到用户目录JSON文件
* create by 林文光
* copyright USTC
* 2026.06.13
"""
import os
import json
import logging

logger = logging.getLogger(__name__)

# 用户目录下的配置文件路径
_SETTINGS_DIR = os.path.join(os.path.expanduser('~'), '.homework_grader')
_SETTINGS_FILE = os.path.join(_SETTINGS_DIR, 'settings.json')

# 默认配置（缺省值）
_DEFAULTS = {
    'api_key': '',
    'base_url': '',
    'model': 'gpt-4o-mini',
    'timeout': 30,
}


def _ensure_dir():
    """确保配置目录存在"""
    if not os.path.exists(_SETTINGS_DIR):
        os.makedirs(_SETTINGS_DIR, exist_ok=True)


def load_settings() -> dict:
    """读取配置文件，合并默认值。读取失败返回默认值。"""
    settings = dict(_DEFAULTS)
    try:
        if os.path.exists(_SETTINGS_FILE):
            with open(_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
            if isinstance(saved, dict):
                settings.update(saved)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning('读取配置失败: %s', e)
    return settings


def save_settings(settings: dict) -> None:
    """保存配置到文件。只保存已知字段。"""
    _ensure_dir()
    data = {k: settings.get(k, _DEFAULTS.get(k)) for k in _DEFAULTS}
    try:
        with open(_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError as e:
        logger.error('保存配置失败: %s', e)
        raise
