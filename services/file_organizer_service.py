import os
import shutil
import hashlib
from utils.logger import logger

class FileOrganizerService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(FileOrganizerService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.pending_duplicates = []
        self._initialized = True

    def organize_folder(self, folder_path: str) -> tuple[bool, str]:
        """
        Organizes files in the specified folder path by grouping them
        into subdirectories based on extension categories.
        """
        path = os.path.expanduser(folder_path)
        if not os.path.exists(path) or not os.path.isdir(path):
            return False, f"Directory '{folder_path}' does not exist or is not a folder."

        categories = {
            "Documents": [".pdf", ".docx", ".doc", ".txt", ".rtf", ".xls", ".xlsx", ".ppt", ".pptx", ".csv"],
            "Images": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".webp", ".ico"],
            "Audio": [".mp3", ".wav", ".m4a", ".flac", ".ogg", ".wma"],
            "Video": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv"],
            "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
            "Installers": [".exe", ".msi", ".dmg", ".pkg"],
            "Scripts": [".py", ".js", ".html", ".css", ".sh", ".bat", ".ps1"]
        }

        moved_count = 0
        try:
            for filename in os.listdir(path):
                file_path = os.path.join(path, filename)
                if os.path.isdir(file_path):
                    continue

                _, ext = os.path.splitext(filename)
                ext = ext.lower()

                # Find destination category
                category = "Other"
                for cat, extensions in categories.items():
                    if ext in extensions:
                        category = cat
                        break

                dest_dir = os.path.join(path, category)
                os.makedirs(dest_dir, exist_ok=True)
                
                shutil.move(file_path, os.path.join(dest_dir, filename))
                moved_count += 1

            return True, f"Successfully organized {moved_count} files in '{folder_path}' into category subfolders."
        except Exception as e:
            logger.log_error(f"Failed to organize folder {folder_path}: {e}")
            return False, f"Failed to organize directory: {e}"

    def calculate_md5(self, file_path: str) -> str:
        """Calculates MD5 hash of a file for duplicate checking."""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""

    def scan_for_duplicates(self, folder_path: str) -> tuple[bool, str]:
        """
        Scans a folder for duplicate files using MD5 hashes.
        Saves duplicates in a pending structure and requests user confirmation.
        """
        path = os.path.expanduser(folder_path)
        if not os.path.exists(path) or not os.path.isdir(path):
            return False, f"Directory '{folder_path}' does not exist."

        hash_map = {} # md5 -> list of file paths
        duplicates = []

        try:
            # Walk directory (non-recursive to prevent accidental deletes of system structures)
            for filename in os.listdir(path):
                file_path = os.path.join(path, filename)
                if os.path.isdir(file_path):
                    continue

                file_hash = self.calculate_md5(file_path)
                if not file_hash:
                    continue

                if file_hash in hash_map:
                    hash_map[file_hash].append(file_path)
                else:
                    hash_map[file_hash] = [file_path]

            # Collect actual duplicates (any hash with > 1 file)
            for f_hash, paths in hash_map.items():
                if len(paths) > 1:
                    # Keep the first, mark the rest as duplicates to delete
                    for dup_path in paths[1:]:
                        duplicates.append(dup_path)

            if not duplicates:
                return True, f"No duplicate files found in '{folder_path}'."

            # Save to pending list
            self.pending_duplicates = duplicates
            count = len(duplicates)
            dup_filenames = [os.path.basename(p) for p in duplicates[:5]]
            list_str = ", ".join(dup_filenames)
            if count > 5:
                list_str += f" and {count - 5} others"
                
            return True, f"Found {count} duplicate files in '{folder_path}' ({list_str}). Are you sure you want to delete them?"
        except Exception as e:
            logger.log_error(f"Failed to scan duplicates: {e}")
            return False, f"Scan failed: {e}"

    def execute_pending_deletion(self) -> tuple[bool, str]:
        """Deletes files in self.pending_duplicates after user confirmation."""
        if not self.pending_duplicates:
            return True, "No pending duplicate deletions."

        deleted_count = 0
        errors = 0
        try:
            for filepath in self.pending_duplicates:
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                        deleted_count += 1
                    except Exception as e:
                        logger.log_error(f"Failed to delete duplicate {filepath}: {e}")
                        errors += 1
                        
            self.pending_duplicates = []
            msg = f"Successfully deleted {deleted_count} duplicate files."
            if errors > 0:
                msg += f" (Encountered errors on {errors} files)."
            return True, msg
        except Exception as e:
            logger.log_error(f"Error executing duplicates deletion: {e}")
            self.pending_duplicates = []
            return False, f"Error deleting files: {e}"

    def cancel_pending_deletion(self) -> str:
        self.pending_duplicates = []
        return "Duplicate file deletion cancelled."
