from typing import TypedDict, Optional, List, NotRequired, Dict

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
    versions: Dict[str, ManagedVersion] # ModFile ID keys to version data. Only one version can be active for each mod file. 
    # versions: List[ManagedVersion]
    # group_id: int
    latest_version: NotRequired[str]
    latest_file_id: NotRequired[int]

class AllManagedPlugins: Dict[str, ManagedPlugin]