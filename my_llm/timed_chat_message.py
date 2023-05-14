from langchain.schema import ChatMessage

from typing import Any, Dict
import getpass
import platform
import sys
from datetime import datetime
from pydantic import Field


class TimedChatMessage(ChatMessage):
    """A ChatMessage that has a timestamp and metadata field added to it"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)
    system_string: str = Field(default_factory=str)

    def __init__(self, content, role, timestamp=None, metadata=None, embedding=None, **kwargs):
        kwargs['timestamp'] = timestamp or datetime.utcnow()
        kwargs['metadata'] = metadata if metadata is not None else {}
        kwargs['system_string'] = self._get_system_info()
        kwargs['embedding'] = embedding if embedding is not None else ""
        super().__init__(content=content, role=role, **kwargs)

    def _get_system_info(self):
        user = getpass.getuser()
        os_name = str(platform.uname())
        python_version = sys.version

        info = f"{user} : {os_name} : {python_version}"
        return info

    def to_dict(self) -> Dict[str, Any]:
            base_dict = super().dict()
            base_dict["timestamp"] = self.timestamp.isoformat()
            base_dict["metadata"] = self.metadata
            base_dict["system_string"] = self.system_string
 
            return base_dict

