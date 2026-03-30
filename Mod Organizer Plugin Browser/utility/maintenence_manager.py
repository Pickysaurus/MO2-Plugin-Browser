import logging
import os
import subprocess
from pathlib import Path
from PyQt6.QtCore import QCoreApplication # type: ignore
from ..messenger import BUS

LOGGER = logging.getLogger("MO2PluginsMaintenance")

class MaintenanceManager:
    def __init__(self):
        self._task_queue = []
        BUS.queue_move_on_restart_op.connect(self.add_move_task)
        BUS.queue_delete_on_restart_op.connect(self.add_delete_task)
        BUS.relaunch_mo2.connect(self.execute_smart_restart)

    def add_delete_task(self, path: str):
        """Queues a file or directory for deletion."""
        path_type = Path(path)
        self._task_queue.append({'type': 'delete', 'path': str(path_type)})
        LOGGER.info(f"Queued for deletion: {path_type.name}")

    def add_move_task(self, src: str, dst: str):
        """Queues a file or directory to be moved/overwritten."""
        src_path = Path(src)
        dst_path = Path(dst)
        self._task_queue.append({'type': 'move', 'src': str(src_path), 'dst': str(dst_path)})
        LOGGER.info(f"Queued for move: {src_path.name} -> {dst_path.name}")

    def has_tasks(self) -> bool:
        return len(self._task_queue) > 0

    def get_and_clear_tasks(self) -> list:
        """Returns the queue and wipes it for the next run."""
        tasks = self._task_queue.copy()
        self._task_queue = []
        return tasks

    def execute_smart_restart(self):
        """The final command that builds the script from the queue."""
        tasks = self.get_and_clear_tasks()
        
        app_dir = Path(QCoreApplication.applicationDirPath())
        mo_exe = app_dir / "ModOrganizer.exe"
        script_path = Path(os.environ["TEMP"]) / "mo2_restart_worker.bat"

        # Start building the batch lines
        lines = [
            "@echo off",
            "echo [Project Pluto] Waiting for MO2 to exit...",
            ":loop",
            'tasklist /fi "IMAGENAME eq ModOrganizer.exe" | find /i "ModOrganizer.exe" >nul',
            "if %errorlevel% equ 0 (timeout /t 1 /nobreak >nul & goto loop)",
            "echo [Project Pluto] Running queued file operations..."
        ]

        # Convert the queue into Batch commands
        for task in tasks:
            if task['type'] == 'delete':
                p = task['path']
                lines.append(f'if exist "{p}" (rd /s /q "{p}" 2>nul || del /f /q "{p}" 2>nul)')
            elif task['type'] == 'move':
                s, d = task['src'], task['dst']
                # Ensure destination is clear before moving
                lines.append(f'if exist "{d}" (rd /s /q "{d}" 2>nul || del /f /q "{d}" 2>nul)')
                lines.append(f'move /y "{s}" "{d}"')

        lines.append(f'start "" "{mo_exe}"')
        lines.append(f'del "{script_path}"')
        
        script_path.write_text("\n".join(lines))
        subprocess.Popen([str(script_path)], shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
        
        QCoreApplication.quit()