from typing import TypedDict, Optional, List, NotRequired

class ManagedPlugin(TypedDict):
    uid: str
    name: str
    mod_id: int
    version: str
    group_id: int
    files: Optional[List[str]]
    latest_version: NotRequired[str]
    latest_file_id: NotRequired[int]