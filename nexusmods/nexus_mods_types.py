from typing import TypedDict, List, Optional, Literal, Iterable

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
    viewerEndorsed: bool
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
    changelogText: Iterable[str]
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