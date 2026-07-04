from typing import TypedDict, Optional, List, NotRequired

class ManagedVersion(TypedDict):
    name: str
    version: str
    mod_file_id: int
    file_uid: NotRequired[str]
    files: Optional[List[str]]
    latest_version: NotRequired[str]
    latest_file_id: NotRequired[int]

class ManagedPlugin(TypedDict):
    uid: str
    # name: str
    # mod_id: int
    versions: List[ManagedVersion]
    # group_id: int
    latest_version: NotRequired[str]
    latest_file_id: NotRequired[int]