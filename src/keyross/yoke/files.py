"""A folder on disk as the yoke's view of an agent's files — for LangChain agents whose own tools write to disk
(`langchain.agents.create_agent`). Deep Agents is not needed: `Yoke(gauge=..., backend=LocalFiles("out"), write_tools=("save_invoice",))`."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


@dataclass
class Download:
    path: str
    content: bytes | None
    error: str | None = None


class LocalFiles:
    """Paths are relative to `root` ("invoice.xml", "/invoice.xml" and an absolute path inside `root` are the same file);
    a path that leaves `root` is refused. Implements the few backend calls the yoke makes."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()

    def normalize(self, path: str) -> str | None:
        """The virtual path ("/sub/invoice.xml") of a file inside root, or None for a path outside it."""
        candidate = Path(path)
        if candidate.is_absolute() and candidate.drive:
            try:
                path = candidate.resolve().relative_to(self.root).as_posix()
            except ValueError:
                return None
        parts = PurePosixPath(path.replace("\\", "/").lstrip("/")).parts
        if not parts or any(p in ("..", "~") for p in parts):
            return None
        return "/" + "/".join(parts)

    def _file(self, path: str) -> Path:
        virtual = self.normalize(path)
        if virtual is None:
            raise ValueError(f"path outside {self.root}: {path}")
        return self.root / virtual.lstrip("/")

    def download_files(self, paths: list[str]) -> list[Download]:
        out = []
        for p in paths:
            f = self._file(p)
            out.append(Download(p, f.read_bytes()) if f.is_file() else Download(p, None, "file_not_found"))
        return out

    def upload_files(self, files: list[tuple[str, bytes]]) -> list[Download]:
        for p, content in files:
            f = self._file(p)
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(content)
        return [Download(p, None) for p, _ in files]

    def delete(self, path: str) -> None:
        self._file(path).unlink(missing_ok=True)

    async def adownload_files(self, paths: list[str]) -> list[Download]:
        return await asyncio.to_thread(self.download_files, paths)

    async def aupload_files(self, files: list[tuple[str, bytes]]) -> list[Download]:
        return await asyncio.to_thread(self.upload_files, files)

    async def adelete(self, path: str) -> None:
        await asyncio.to_thread(self.delete, path)
