"""Pretask — get a list of files from a source."""

from dataclasses import dataclass
from threading import Event
from typing import Self

from loguru import logger

from platform_input_support.config import scratchpad
from platform_input_support.helpers import google_helper
from platform_input_support.tasks import Pretask, PretaskDefinition, report


@dataclass
class GetFileListDefinition(PretaskDefinition):
    """Configuration fields for the get_file_list pretask.

    This pretask has the following custom configuration fields:
        - source (str): The source to list files from.
        - pattern (str): The pattern to match files against.
        - sentinel (str): The key to store the file list in the scratchpad.
    """

    source: str
    pattern: str
    sentinel: str


class GetFileList(Pretask):
    """Get a list of files from a source.

    This pretask will list files from a source and store the list in the scratchpad.
    """

    def __init__(self, definition: PretaskDefinition):
        super().__init__(definition)
        self.definition: GetFileListDefinition

    @report
    def run(self, *, abort: Event) -> Self:
        source, pattern, sentinel = self.definition.source, self.definition.pattern, self.definition.sentinel
        file_list: list[str] = []

        if pattern.startswith('!'):
            file_list = google_helper().list_blobs(source, exclude=pattern[1:])
        else:
            file_list = google_helper().list_blobs(source, include=pattern)

        if len(file_list):
            scratchpad().store(sentinel, file_list)
            logger.info(f'{len(file_list)} files with pattern {pattern} found in {source}')
            return self
        else:
            raise ValueError(f'no files found in {source} with pattern {pattern}')
