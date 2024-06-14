import sys
from pathlib import Path
from typing import Any

import yaml
from loguru import logger


class ParseYAML:
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.data: dict[str, Any] = {}

    def parse(self):
        logger.debug(f'reading config file {self.file_path}')
        yaml_str: str
        try:
            yaml_str = Path.read_text(self.file_path)
        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.critical(f'error reading config file: {e}')
            sys.exit(1)

        logger.debug('parsing config file')
        try:
            self.data = yaml.safe_load(yaml_str)
        except yaml.YAMLError as e:
            logger.critical(f'error parsing config file: {e}')
            sys.exit(1)