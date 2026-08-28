from typing import cast
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.models.indexed_folder import IndexedFolder
from app.integrations.google.interfaces import GoogleDriveFolder
from app.services.folder_selection import (
    FolderSelectionValidationError,
    list_selected_folders,
    replace_selected_folders,
    validate_selected_folders,
)


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


def test_validate_selected_folders_uses_owned_names_and_rejects_unknown_ids() -> None:
    available = (
        GoogleDriveFolder(id="parent", name="Parent", parents=()),
        GoogleDriveFolder(id="child", name="Child", parents=("parent",)),
    )

    assert validate_selected_folders(available, ["child"]) == [("child", "Child")]
    try:
        validate_selected_folders(available, ["not-owned"])
    except FolderSelectionValidationError as error:
        assert str(error) == "Selected folders must belong to the connected Google Drive account"
    else:
        raise AssertionError("Expected unknown folder validation to fail")


def test_validate_selected_folders_rejects_duplicate_and_ancestor_selections() -> None:
    available = (
        GoogleDriveFolder(id="parent", name="Parent", parents=()),
        GoogleDriveFolder(id="child", name="Child", parents=("parent",)),
    )

    for selected_ids, message in [
        (["parent", "parent"], "Selected folders must be unique"),
        (["parent", "child"], "Select either a folder or one of its descendants, not both"),
    ]:
        try:
            validate_selected_folders(available, selected_ids)
        except FolderSelectionValidationError as error:
            assert str(error) == message
        else:
            raise AssertionError("Expected invalid folder selection to fail")
