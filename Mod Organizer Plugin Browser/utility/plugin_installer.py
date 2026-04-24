import os
import zipfile
import subprocess
import shutil
import tempfile
import logging
from pathlib import Path
import mobase # type: ignore
from typing import List, Literal, Optional
from PyQt6.QtCore import QObject, pyqtSignal, QCoreApplication # type: ignore
from ..messenger import BUS
from ..nexusmods_api import NexusModsAPI
from .managed_plugins import ManagedPlugins
from ..nexusmods.nexus_mods_types import ModFilesResult, ModNode
from ..nexusmods.nexus_mods_errors import NexusModsAPIKeyMissingError

LOGGER = logging.getLogger("MO2PluginsInstaller")

class PluginInstaller(QObject):
    # Signals to communicate back to the UI
    download_started = pyqtSignal(int) # download_id
    install_complete = pyqtSignal(str) # mod_uid
    error_occurred = pyqtSignal(str, object)

    def __init__(self, organizer: mobase.IOrganizer, api, installed_manager):
        super().__init__()
        self._organizer: mobase.IOrganizer = organizer
        self.api: NexusModsAPI = api
        self.installed_manager: ManagedPlugins = installed_manager
        
        # Internal state
        self._active_downloads = {} # download_id -> metadata
        
        # Connect to MO2's global download signal once
        self._organizer.downloadManager().onDownloadComplete(self._on_mo2_download_finished)
        self._organizer.downloadManager().onDownloadFailed(self._on_mo2_download_failed)
        self._organizer.downloadManager().onDownloadRemoved(self._on_mo2_download_removed)

    def start_install(self, mod_node: ModNode, type: Literal['install', 'update'], newId: Optional[int]):
        """High-level entry point with local file check, called by the UI."""
        mod_id = mod_node.get("modId")
        try:
            files_resp = self.api.get_mod_files(mod_id)
            if not files_resp or not files_resp.get("modFiles"):
                self.error_occurred.emit("No files found for this mod.", Exception("No files found"))
                return

            mod_files = files_resp.get("modFiles")
            if newId:
                primary_file = next((f for f in mod_files if f.get("fileId") == newId), None)
                # Optional: Fallback to best file if the specific ID isn't found in the list
                if not primary_file:
                    primary_file = self._select_best_file(mod_files)
            else:
                primary_file = self._select_best_file(mod_files)
            file_name = primary_file.get("uri", None) if primary_file else None
            
            if not primary_file or not file_name:
                raise Exception(f"Primary file is missing or has no file name {primary_file}")
            

            # Check if we already have the file
            downloads_dir = self._organizer.downloadsPath()
            local_path = os.path.join(downloads_dir, file_name)

            if os.path.exists(local_path):
                LOGGER.info(f"Found existing file: {file_name}. Skipping download step.")
                self._finish_installation(local_path, mod_node, primary_file, type)
                return
            
            download_url = self.api.get_file_download_link(mod_id, primary_file["fileId"])
            
            if download_url:
                dl_id = self._organizer.downloadManager().startDownloadURLs([download_url])
                self._active_downloads[dl_id] = {
                    "uid": mod_node.get("uid"),
                    "mod_id": mod_id,
                    "metadata": primary_file,
                    "type": type,
                    "mod": mod_node
                }
                self.download_started.emit(dl_id)
        except NexusModsAPIKeyMissingError as e:
            LOGGER.warning("API key is missing when trying to download")
            self.error_occurred.emit("API key not provided", e)
        except Exception as e:
            LOGGER.error(e)
            self.error_occurred.emit(str(e), e)

    def _select_best_file(self, mod_files: List[ModFilesResult]) -> ModFilesResult | None:
        """
        Finds the best file to download based on priority:
        1. Explicitly marked as 'primary'.
        2. Newest file in the 'MAIN' category.
        3. Fallback to the first available file.
        """
        if not mod_files:
            return None

        # 1. Look for the Primary file
        primary = next((f for f in mod_files if f.get("primary")), None)
        if primary:
            return primary

        # 2. Filter for 'Main' category files
        # Note: Depending on the API version, this is usually "MAIN" or category 1.
        main_files = [
            f for f in mod_files 
            if str(f.get("category", "")).upper() == "MAIN"
        ]

        if main_files:
            # Sort by uploadedTimestamp descending (newest first)
            # If timestamp is missing, it falls back to 0.
            return sorted(
                main_files, 
                key=lambda x: x.get("date", 0), 
                reverse=True
            )[0]

        # 3. Ultimate Fallback
        return mod_files[0]

    def _on_mo2_download_finished(self, download_id):
        if download_id not in self._active_downloads:
            return

        data = self._active_downloads.pop(download_id)
        archive_path = self._organizer.downloadManager().downloadPath(download_id)
        self._finish_installation(archive_path, data["mod"], data["metadata"], data["type"])
    
    def _on_mo2_download_failed(self, download_id):
        if download_id not in self._active_downloads:
            return
        self.error_occurred.emit("Download failed.", Exception("MO2 reported download failure"))
    
    def _on_mo2_download_removed(self, download_id):
        if download_id not in self._active_downloads:
            return
        self.error_occurred.emit("Download removed.", Exception("MO2 reported download removed"))
    
    def _get_update_staging_dir(self) -> str:
        """Creates a persistent staging area for updates that survives MO2 restart."""
        staging_path = Path(QCoreApplication.applicationDirPath()) / "web_cache" / "plugin_browser_updates"
        if staging_path.exists():
            shutil.rmtree(staging_path) # Clean up old failed attempts
        staging_path.mkdir(parents=True, exist_ok=True)
        LOGGER.info(f"Temporary update staging at {str(staging_path)}")
        return str(staging_path)

    def _finish_installation(self, archive_path: str, mod_node: ModNode, metadata, type: Literal['install', 'update']):
        """Shared logic for both local and newly downloaded files."""
        try:
            if type == 'install':
                tmp_dir_context = tempfile.TemporaryDirectory()
                staging_dir = tmp_dir_context.name
            else:
                staging_dir = self._get_update_staging_dir()

            # --- EDGE CASE 2: Handle 7z/RAR/ZIP ---
            self._extract_archive(archive_path, staging_dir)

            # Move files logic
            plugins_path = os.path.join(QCoreApplication.applicationDirPath(), "plugins")
            source = os.path.join(staging_dir, "plugins") if os.path.exists(os.path.join(staging_dir, "plugins")) else staging_dir

            file_list: List[str] = []
            
            if type == 'install':
                file_list = self._install_plugin(source, plugins_path)
                self.installed_manager.add_managed_plugin({
                    "uid": mod_node.get("uid"),
                    "mod_id": mod_node.get("modId"),
                    "version": metadata["version"],
                    "name": metadata["name"],
                    "group_id": metadata["groupId"],
                    "files": file_list
                })
            elif type == 'update':
                LOGGER.info("Updating existing plugin")
                current = self.installed_manager.get_managed_plugin(mod_node.get("uid"))
                if not current: raise Exception(f"Could not update {mod_node.get("name", "Unknown plugin")} as it is not managed")
                for file in current["files"] if current["files"] else []:
                    BUS.queue_delete_on_restart_op.emit(file)
                
                for item in os.listdir(source):
                    s, d = os.path.join(source, item), os.path.join(plugins_path, item)
                    BUS.queue_move_on_restart_op.emit(s, d)
                    file_list.append(d)

                del current["latest_file_id"]
                del current["latest_version"]
                current["version"] = metadata["version"]
                current["files"] = file_list
                self.installed_manager.add_managed_plugin(current)  
                
            BUS.focus_plugin_browser.emit()
            BUS.relaunch_required.emit(True)
            self.install_complete.emit(mod_node.get("uid"))
        except Exception as e:
            self.error_occurred.emit(str(e), e)

    def _install_plugin(self, plugin_folder: str, destination: str) -> List[str]:
        """
        Merges plugin files into the destination.
        Skips existing files, and queues locked files for a restart operation.
        """
        installed_files: List[str] = []

        # os.walk handles nested directories without needing rmtree
        for root, dirs, files in os.walk(plugin_folder):
            # Calculate the corresponding path in the MO2 plugins folder
            rel_path = os.path.relpath(root, plugin_folder)

            target_dir = os.path.join(destination, rel_path) if rel_path != "." else destination

            # 1. Ensure the sub-directory exists in destination
            if not os.path.exists(target_dir):
                try:
                    os.makedirs(target_dir, exist_ok=True)
                except PermissionError:
                    # If we can't even make the directory, queue it for restart
                    BUS.queue_move_on_restart_op.emit(root, target_dir)
                    continue

            # 2. Process individual files
            for file_name in files:
                s_file = os.path.join(root, file_name)
                d_file = os.path.join(target_dir, file_name)

                # Requirement: If they already exist, do nothing
                if os.path.exists(d_file):
                    LOGGER.debug(f"File already exists, skipping: {file_name}")
                    installed_files.append(d_file)
                    continue

                try:
                    # Attempt immediate copy
                    shutil.copy2(s_file, d_file)
                    installed_files.append(d_file)
                except PermissionError:
                    # Requirement: Record permission errors to queue for later
                    LOGGER.info(f"Access denied to {file_name}, queuing for restart.")
                    # Using the MaintenanceManager bus created earlier
                    BUS.queue_move_on_restart_op.emit(s_file, d_file)
                    installed_files.append(d_file)
                except Exception as e:
                    LOGGER.error(f"Unexpected error installing {file_name}: {e}")

        return installed_files        
    
    def _extract_archive(self, archive_path, dest_dir):
        """Universal extractor supporting ZIP, 7Z, and RAR."""
        ext = os.path.splitext(archive_path)[1].lower()
        
        if ext == ".zip" or not ext:
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(dest_dir)
        else:
            # For 7z and RAR, we use the 7z.exe bundled with MO2 or the system
            seven_zip_path = self._find_7z_executable()
            if not seven_zip_path:
                raise Exception("Could not find 7z.exe to extract non-ZIP archive.")
            
            # 'x' means extract with full paths, '-y' means assume yes to all prompts
            cmd = [seven_zip_path, "x", archive_path, f"-o{dest_dir}", "-y"]
            subprocess.run(cmd, check=True, creationflags=subprocess.CREATE_NO_WINDOW)

    def _find_7z_executable(self):
        """Search for 7z.exe in MO2 folder and common paths."""
        # 1. Check MO2 directory
        mo2_dir = QCoreApplication.applicationDirPath()
        local_7z = os.path.join(mo2_dir, "7z.exe")
        if os.path.exists(local_7z): return local_7z
        
        # 2. Check standard install path
        standard_path = r"C:\Program Files\7-Zip\7z.exe"
        if os.path.exists(standard_path): return standard_path
        
        # 3. Check system PATH
        return shutil.which("7z")