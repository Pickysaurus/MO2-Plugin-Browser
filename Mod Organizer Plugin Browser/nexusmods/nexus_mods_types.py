from typing import TypedDict, List, Optional, Literal

ModSortType = Literal["Endorsements", "Downloads", "Created At", "Updated At"]
PluginCategoryType = Literal["All", "Plugins", "Themes", "Installed"]

class ModCategory(TypedDict):
    categoryId: int
    name: str

class Uploader(TypedDict):
    avatar: Optional[str]
    memberId: int
    name: str

class ModNode(TypedDict):
    adultContent: bool
    createdAt: str
    downloads: int
    endorsements: int
    fileSize: int
    modCategory: ModCategory
    modId: int
    name: str
    status: str
    summary: str
    thumbnailUrl: Optional[str]
    thumbnailBlurredUrl: Optional[str]
    uid: str
    updatedAt: str
    uploader: Uploader
    viewerDownloaded: bool
    viewerEndorsed: bool | None
    viewerTracked: bool
    viewerUpdateAvailable: bool
    viewerIsBlocked: bool

class ModsFacetData(TypedDict):
    count: int
    facet: str
    value: str

class ModsResult(TypedDict):
    nodes: List[ModNode]
    totalCount: int
    nodesCount: int
    facets: List[ModsFacetData]

class NexusExtensionsResponse(TypedDict):
    mods: ModsResult

class NexusModsByUidResponse(TypedDict):
    modsByUid: ModsResult

class ModFilesResult(TypedDict):
    category: str
    changelogText: list[str]
    date: str
    description: str
    fileId: int
    id: int
    groupId: str
    name: str
    primary: bool
    sizeInBytes: int
    version: str
    uid: str
    totalDownloads: int
    uniqueDownloads: int
    uri: str

class NexusModsFileListResponse(TypedDict):
    modFiles: List[ModFilesResult]

class GroupFile(TypedDict):
    id: str
    name: str

class NexusModsFilesInGroup(TypedDict):
    id: str
    position: str
    name: str
    file: GroupFile
    game_scoped_id: str
    version: str
    category: Literal["main", "old_version", "archived", "update"]
    uploaded_at: str

class NexusModsV3ModFile(TypedDict):
    id: str
    name: str
    is_active: bool
    last_file_uploaded_at: str
    versions_count: int
    archived_count: int
    removed_count: int
    versions: Optional[list[ModFilesResult]] # Added later

class NexusModsV3ModFiles(TypedDict):
    mod_files: List[NexusModsV3ModFile]

class NexusModsV3ModFilesResponse(TypedDict):
    data: NexusModsV3ModFiles