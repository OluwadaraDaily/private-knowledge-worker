from typing import cast
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.models.indexed_folder import IndexedFolder
from app.services.folder_selection import list_selected_folders, replace_selected_folders


class ScalarResult:
    def __init__(self, values: list[IndexedFolder]) -> None:
        self.values = values

    def all(self) -> list[IndexedFolder]:
        return self.values


class SelectionSession:
    def __init__(self, folders: list[IndexedFolder]) -> None:
        self.folders = folders
        self.added: list[IndexedFolder] = []
        self.deleted: list[IndexedFolder] = []
        self.commits = 0

    def scalars(self, _statement: object) -> ScalarResult:
        return ScalarResult(self.folders)

    def add(self, folder: IndexedFolder) -> None:
        self.folders.append(folder)
        self.added.append(folder)

    def delete(self, folder: IndexedFolder) -> None:
        self.folders.remove(folder)
        self.deleted.append(folder)

    def commit(self) -> None:
        self.commits += 1


def test_replace_selected_folders_updates_adds_and_removes_sources() -> None:
    user_id = uuid4()
    existing = IndexedFolder(user_id=user_id, google_folder_id="keep", name="Old name")
    remove = IndexedFolder(user_id=user_id, google_folder_id="remove", name="Remove me")
    session = SelectionSession([existing, remove])

    selected = replace_selected_folders(
        cast(Session, session),
        user_id,
        [("keep", "New name"), ("new", "New folder")],
    )

    assert [(folder.google_folder_id, folder.name) for folder in selected] == [
        ("keep", "New name"),
        ("new", "New folder"),
    ]
    assert session.deleted == [remove]
    assert [folder.google_folder_id for folder in session.added] == ["new"]
    assert session.commits == 1


def test_list_selected_folders_uses_the_session_query() -> None:
    user_id = uuid4()
    folder = IndexedFolder(user_id=user_id, google_folder_id="folder", name="Folder")
    session = SelectionSession([folder])

    assert list_selected_folders(cast(Session, session), user_id) == [folder]
