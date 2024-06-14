from dataclasses import dataclass
from typing import Any

from platform_input_support.action import Action, ActionConfigMapping
from platform_input_support.helpers.download import download
from platform_input_support.helpers.google import google
from platform_input_support.manifest.manifest import report_to_manifest
from platform_input_support.scratch_pad import scratch_pad


@dataclass
class GetFileListConfigMapping(ActionConfigMapping):
    source: str
    pattern: str
    scratch_pad_key: str


class GetFileList(Action):
    def __init__(self, config: ActionConfigMapping):
        self.config: GetFileListConfigMapping
        super().__init__(config)

    @report_to_manifest
    def run(self):
        file_list: list[str] = []

        if self.config.pattern.startswith('!'):
            file_list = google.list(self.config.source, exclude=self.config.pattern[1:])
        else:
            file_list = google.list(self.config.source, include=self.config.pattern)

        if len(file_list):
            self.append_log(f'{len(file_list)} files with pattern {self.config.pattern} found in {self.config.source}')
            scratch_pad.store(self.config.scratch_pad_key, file_list)
        else:
            raise ValueError(f'no files found in {self.config.source} with pattern {self.config.pattern}')