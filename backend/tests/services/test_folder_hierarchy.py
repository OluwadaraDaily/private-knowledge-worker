import pytest

from app.integrations.google.client import GoogleApiError
from app.integrations.google.interfaces import GoogleDriveFolder
from app.services.folder_hierarchy import GoogleFolderNode, build_google_folder_hierarchy


def test_build_google_folder_hierarchy_handles_nested_and_orphaned_folders() -> None:
    folders = (
        GoogleDriveFolder(id="child", name="Child", parents=("parent",)),
        GoogleDriveFolder(id="parent", name="Parent", parents=("root",)),
        GoogleDriveFolder(id="orphan", name="Alpha", parents=("missing",)),
    )

    tree = build_google_folder_hierarchy(folders)

    assert tree == (
        GoogleFolderNode(id="orphan", name="Alpha", children=()),
        GoogleFolderNode(
            id="parent",
            name="Parent",
            children=(GoogleFolderNode(id="child", name="Child", children=()),),
        ),
    )


def test_build_google_folder_hierarchy_rejects_cycles() -> None:
    folders = (
        GoogleDriveFolder(id="first", name="First", parents=("second",)),
        GoogleDriveFolder(id="second", name="Second", parents=("first",)),
    )

    with pytest.raises(GoogleApiError, match="cyclic"):
        build_google_folder_hierarchy(folders)
