import logging
import mobase # type: ignore
from typing import Optional, List
from PyQt6.QtCore import QUrl # type: ignore

from .nexusmods.nexus_mods_client import NexusClient
from .nexusmods.nexus_mods_queries import GET_MO2_EXTENSIONS, GET_MOD_FILES, GET_MODS_BY_UID
from .nexusmods.nexus_mods_types import NexusExtensionsResponse, NexusModsFileListResponse, NexusModsByUidResponse, PluginCategoryType, ModSortType

LOGGER = logging.getLogger("MO2PluginsNexusModsAPI")

class NexusModsAPI(NexusClient):
    def __init__(self, organizer: mobase.IOrganizer):
        super().__init__(organizer)
        self.graph_url = QUrl("https://api.nexusmods.com/v2/graphql")
        self._organizer = organizer

    def get_mo2_extensions(
            self, 
            offset=0, 
            filter_category: PluginCategoryType="All", 
            sort: ModSortType="Endorsements", 
            search_term=None
    ) -> Optional[NexusExtensionsResponse]:
         # Map the sort
        sort_mapping = {
            "Endorsements": [{"endorsements": {"direction": "DESC"}}],
            "Downloads": [{"downloads": {"direction": "DESC"}}],
            "Created At": [{"createdAt": {"direction": "DESC"}}],
            "Updated At": [{"updatedAt": {"direction": "DESC"}}]
        }

        variables = {
            "count": 12,
            "offset": offset,
            "sort": sort_mapping.get(sort, sort_mapping["Endorsements"]),
            "facets": {
                "status": ["published"]
            },
            "filter": {
                "gameDomainName": [{"op": "EQUALS", "value": "site"}]
            }
        }

        if filter_category != "All":
            if filter_category == "Plugins":
                category_filter= { "op": "EQUALS", "value": "Mod Organizer 2 Plugins" }
            elif filter_category == "Themes":
                category_filter= { "op": "EQUALS", "value": "Mod Organizer 2 Themes" }
            else:
                log_msg = f"Unrecognised filter category: {filter_category}"
                LOGGER.info(log_msg)
                category_filter = { "op": "EQUALS", "value": filter_category }
            variables["filter"]["categoryName"] = category_filter
        else:
            variables["filter"]["filter"] = {
                "op": "OR",
                "categoryName": [
                    { "op": "EQUALS", "value": "Mod Organizer 2 Plugins" },
                    { "op": "EQUALS", "value": "Mod Organizer 2 Themes" }
                ]
            }

        if search_term is not None:
            variables["filter"]["name"] = { "op": "WILDCARD", "value": search_term }

        # log_msg = f"Get extensions. Sort: {sort}, Variables {variables}"
        # LOGGER.info(log_msg)
        # Make a graphQL request to fetch the MO2 plugins in the correct category.
        payload = {
            "operationName": "GetMO2Extensions",
            "query": GET_MO2_EXTENSIONS,
            "variables": variables
        }

        # Use the base client to send the request
        response = self.send_request("POST", self.graph_url, body=payload, requires_auth=False)
        return response.get("data") if response else None
    
    def get_mods_by_uid(self, uids: List[str], offset=0) -> Optional[NexusModsByUidResponse]:
        variables = {
            "uids": uids,
            "offset": offset,
            "count": 12
        }

        payload = {
            "operationName": "getMO2PluginsByUid",
            "query": GET_MODS_BY_UID,
            "variables": variables
        }
        LOGGER.debug(f"Requesting mods by UID: {payload}")
        response = self.send_request("POST", self.graph_url, body=payload, requires_auth=False)
        LOGGER.debug(f"Response for mods by UID: {response}")
        return response.get("data") if response else None

    def get_mod_files(self, mod_id: int, game_id: Optional[int] = 2295) -> Optional[NexusModsFileListResponse]:
        variables = {
            "gameId": game_id,
            "modId": mod_id
        }

        payload = {
            "operationName": "getMO2PluginFiles",
            "query": GET_MOD_FILES,
            "variables": variables
        }

        response = self.send_request("POST", self.graph_url, body=payload, requires_auth=False)
        LOGGER.debug(f"Mod Files Response {response}")
        return response.get("data") if response else None
    
    def get_file_download_link(self, mod_id: int, file_id: int, game_domain: str = "site") -> Optional[str]:
        path = f"v1/games/{game_domain}/mods/{mod_id}/files/{file_id}/download_link.json"
        url = QUrl(f"{self.base_url}/{path}")

        # REST call
        reply_data = self.send_request("GET", url, requires_auth=True)
        
        if reply_data and isinstance(reply_data, list) and len(reply_data) > 0:
            return reply_data[0].get("URI")
        return None
    
    def get_mod_update_groups(self, mod_uid: str):
        path = f"v3/mods/{mod_uid}/mods/file-update-groups"
        url = QUrl(f"{self.base_url}/{path}")

        # REST call
        reply_data = self.send_request("GET", url, requires_auth=True)
        if not reply_data: return

        groups = reply_data.get("data", {}).get("groups", None)
        
        return groups