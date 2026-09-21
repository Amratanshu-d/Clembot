import os
from pathlib import Path
from typing import List, Optional
from app.filesystem.paths import WindowsPathResolver
from app.logging.logger import logger


class FileSearchService:
    """
    Intelligent bounded file and directory search across standard Windows user locations.
    """

    def __init__(self):
        self.resolver = WindowsPathResolver()

    def get_search_roots(self, scope: Optional[str] = None) -> List[Path]:
        """Determines search roots based on user scope or defaults to primary user folders."""
        if scope:
            target = self.resolver.resolve_path(scope)
            if target.is_dir():
                return [target]

        standard = self.resolver.get_standard_folders()
        roots = [
            standard["Downloads"],
            standard["Desktop"],
            standard["Documents"],
        ]
        if "OneDrive" in standard:
            roots.append(standard["OneDrive"])

        # Also check common code/project folders under user home if they exist
        home = self.resolver.get_user_home()
        for name in ["Projects", "Developer", "Code", "source", "repos"]:
            custom = home / name
            if custom.is_dir():
                roots.append(custom)

        return roots

    def find_files(
        self,
        query: str,
        scope: Optional[str] = None,
        max_results: int = 5,
        max_visited: int = 25000
    ) -> List[Path]:
        """
        Searches for files matching query (fuzzy/substring match) within search roots.
        Bounded by max_visited to maintain low latency.
        """
        q = query.strip().lower()
        if not q:
            return []

        roots = self.get_search_roots(scope)
        matches: List[Path] = []
        visited = 0

        # Skip noisy system/cache directories
        ignored_names = {
            "node_modules", ".git", ".vscode", "__pycache__", "appdata",
            "local", "roaming", "$recycle.bin", "system volume information"
        }

        for root in roots:
            if not root.exists():
                continue

            for dirpath, dirnames, filenames in os.walk(str(root)):
                # Filter out noisy directories in place
                dirnames[:] = [d for d in dirnames if d.lower() not in ignored_names and not d.startswith(".")]

                visited += len(filenames)
                if visited > max_visited:
                    logger.debug(f"Search reached visit limit ({max_visited})")
                    break

                for filename in filenames:
                    fn_lower = filename.lower()
                    if q in fn_lower:
                        full_path = Path(dirpath) / filename
                        matches.append(full_path)
                        if len(matches) >= max_results:
                            return matches

                if visited > max_visited:
                    break

        return matches

    def find_first(self, query: str, scope: Optional[str] = None) -> Optional[Path]:
        """Returns the first matching file, prioritizing exact matches or latest modified."""
        results = self.find_files(query, scope=scope, max_results=10)
        if not results:
            return None

        # Sort matches: prioritize exact name match, then newest modification time
        q = query.strip().lower()

        def _sort_key(p: Path):
            is_exact = 1 if p.name.lower() == q or p.stem.lower() == q else 0
            try:
                mtime = p.stat().st_mtime
            except Exception:
                mtime = 0
            return (is_exact, mtime)

        results.sort(key=_sort_key, reverse=True)
        return results[0]
