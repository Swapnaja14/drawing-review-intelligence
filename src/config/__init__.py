"""
src/config/__init__.py
Centralized Configuration Package for UCC AI Drawing Review Comment Analyzer.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from src.config.app_config import (
    PROJECT_ROOT,
    DEFAULT_CONFIG_PATH,
    AppConfig,
    DatabaseConfig,
    LoggingConfig,
    PDFConfig,
    OCRConfig,
    AIConfig,
    UIConfig,
    ExportConfig,
)

_ACTIVE_CONFIG: Optional[AppConfig] = None


def get_config(config_path: Optional[Path | str] = None) -> AppConfig:
    """
    Get or initialize the global singleton AppConfig instance.
    Loads from `config/config.yaml` if it exists, otherwise initializes defaults.
    """
    global _ACTIVE_CONFIG
    if _ACTIVE_CONFIG is None:
        target_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        if target_path.exists():
            _ACTIVE_CONFIG = AppConfig.load_from_yaml(target_path)
        else:
            _ACTIVE_CONFIG = AppConfig()
            _ACTIVE_CONFIG.apply_env_overrides()
            # Write default configuration file if missing
            try:
                _ACTIVE_CONFIG.save_to_yaml(target_path)
            except Exception:
                pass
    return _ACTIVE_CONFIG


def reload_config(config_path: Optional[Path | str] = None) -> AppConfig:
    """
    Force reload configuration from file and update singleton.
    """
    global _ACTIVE_CONFIG
    target_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    if target_path.suffix.lower() in (".json",):
        _ACTIVE_CONFIG = AppConfig.load_from_json(target_path)
    else:
        _ACTIVE_CONFIG = AppConfig.load_from_yaml(target_path)
    return _ACTIVE_CONFIG


def save_config(config: Optional[AppConfig] = None, config_path: Optional[Path | str] = None) -> Path:
    """
    Persist configuration to YAML file.
    """
    cfg = config or get_config()
    target_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    return cfg.save_to_yaml(target_path)


def set_config(config: AppConfig) -> None:
    """
    Explicitly set the active configuration singleton (useful for testing).
    """
    global _ACTIVE_CONFIG
    _ACTIVE_CONFIG = config


__all__ = [
    "PROJECT_ROOT",
    "DEFAULT_CONFIG_PATH",
    "AppConfig",
    "DatabaseConfig",
    "LoggingConfig",
    "PDFConfig",
    "OCRConfig",
    "AIConfig",
    "UIConfig",
    "ExportConfig",
    "get_config",
    "reload_config",
    "save_config",
    "set_config",
]
