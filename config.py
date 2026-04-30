"""
Shared configuration for kaiwu-cli-mcp.
Reads from user_config.yaml with environment variable overrides.
"""

import os
import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_FILE = PROJECT_ROOT / "user_config.yaml"
USER_SCRIPT_DIR = PROJECT_ROOT / "user_script"
DOCKER_COMPOSE_FILE = PROJECT_ROOT / "docker-compose.yml"


def load_config() -> dict:
    """Load user configuration from user_config.yaml.

    Returns:
        dict with keys: user_id, sdk_code, container_name, image_name
    """
    config = {
        "user_id": "",
        "sdk_code": "",
        "container_name": "kaiwu-sdk",
        "image_name": "kaiwu-sdk:latest",
    }

    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            file_config = yaml.safe_load(f) or {}
            config.update(file_config)

    # Environment variable overrides
    if os.environ.get("KAIWU_USER_ID"):
        config["user_id"] = os.environ["KAIWU_USER_ID"]
    if os.environ.get("KAIWU_SDK_CODE"):
        config["sdk_code"] = os.environ["KAIWU_SDK_CODE"]
    if os.environ.get("KAIWU_CONTAINER_NAME"):
        config["container_name"] = os.environ["KAIWU_CONTAINER_NAME"]
    if os.environ.get("KAIWU_IMAGE_NAME"):
        config["image_name"] = os.environ["KAIWU_IMAGE_NAME"]

    return config
