import { Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'

import { LogoMark } from '../components/LogoMark'

type FolderNode = {
  id: string
  name: string
  children: FolderNode[]
}

type FolderMeta = {
  node: FolderNode
  parentId: string | null
  path: string[]
}

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1'
const RECONNECT_ERROR = 'Reconnect Google to see your folders.'
const GENERIC_LOAD_ERROR = 'We could not load your folders. Try again.'

async function requestFolderTree() {
  const response = await fetch(API_BASE + '/drive/folders/tree', {
    credentials: 'include',
  })

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error(RECONNECT_ERROR)
    }
    throw new Error(GENERIC_LOAD_ERROR)
  }

  return (await response.json()) as FolderNode[]
}

function getFolderLoadError(error: unknown) {
  return error instanceof Error && error.message === RECONNECT_ERROR
    ? RECONNECT_ERROR
    : GENERIC_LOAD_ERROR
}

export function FolderSelectionPage() {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set())
  const folderTreeQuery = useQuery<FolderNode[], Error>({
    queryKey: ['google-drive', 'folders', 'tree'],
    queryFn: requestFolderTree,
    staleTime: Infinity,
    gcTime: 30 * 60 * 1000,
    retry: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  })
  const folders = folderTreeQuery.data ?? null
  const error = folderTreeQuery.error
    ? getFolderLoadError(folderTreeQuery.error)
    : null
  const isLoading = folderTreeQuery.isPending
  const isRefreshing = folderTreeQuery.isFetching && !isLoading

  const folderMetadata = useMemo(() => {
    const metadata = new Map<string, FolderMeta>()

    function collect(
      nodes: FolderNode[],
      parentId: string | null,
      parentPath: string[],
    ) {
      for (const node of nodes) {
        const path = [...parentPath, node.name]
        metadata.set(node.id, { node, parentId, path })
        collect(node.children, node.id, path)
      }
    }

    if (folders) {
      collect(folders, null, [])
    }

    return metadata
  }, [folders])

  function isIncludedBySelection(folderId: string) {
    let parentId = folderMetadata.get(folderId)?.parentId ?? null

    while (parentId) {
      if (selectedIds.has(parentId)) {
        return true
      }
      parentId = folderMetadata.get(parentId)?.parentId ?? null
    }

    return false
  }

  function toggleFolder(folderId: string) {
    if (isIncludedBySelection(folderId)) {
      return
    }

    setSelectedIds((currentSelectedIds) => {
      const nextSelectedIds = new Set(currentSelectedIds)

      if (nextSelectedIds.has(folderId)) {
        nextSelectedIds.delete(folderId)
        return nextSelectedIds
      }

      for (const selectedId of currentSelectedIds) {
        let parentId = folderMetadata.get(selectedId)?.parentId ?? null
        while (parentId) {
          if (parentId === folderId) {
            nextSelectedIds.delete(selectedId)
            break
          }
          parentId = folderMetadata.get(parentId)?.parentId ?? null
        }
      }

      nextSelectedIds.add(folderId)
      return nextSelectedIds
    })
  }

  const selectedFolders = [...selectedIds]
    .map((id) => folderMetadata.get(id))
    .filter((folder): folder is FolderMeta => folder !== undefined)
    .sort((first, second) =>
      first.path.join('/').localeCompare(second.path.join('/')),
    )

  const hasFolders = folders !== null && folders.length > 0

  return (
    <div className="setup-shell folder-selection-shell">
      <header className="site-header setup-header">
        <Link className="brand" to="/">
          <LogoMark />
          <span>private knowledge worker</span>
        </Link>
        <span className="setup-progress">setup / 02</span>
      </header>

      <main className="setup-main folder-selection-main">
        <Link className="back-link" to="/connect">
          <span aria-hidden="true">←</span>
          Back to connection
        </Link>

        <div className="folder-selection-heading">
          <div>
            <p className="eyebrow">Second, define your source</p>
            <h1>Choose what stays in context.</h1>
            <p className="setup-description">
              Pick one or more folders from Google Drive. Everything inside a
              selected folder comes with it.
            </p>
          </div>

          <div className="selection-counter" aria-live="polite">
            <span className="selection-counter-label">Source scope</span>
            <strong>{selectedIds.size.toString().padStart(2, '0')}</strong>
            <span>
              {selectedIds.size === 1 ? 'folder selected' : 'folders selected'}
            </span>
          </div>
        </div>

        <div className="folder-selection-layout">
          <section
            className="folder-tree-card"
            aria-labelledby="folder-tree-title"
          >
            <div className="folder-tree-card-header">
              <div>
                <p className="card-kicker">Your Google Drive</p>
                <h2 id="folder-tree-title">Owned folders</h2>
              </div>
              <span className="read-only-label">
                <span className="status-dot" aria-hidden="true" />
                read only
                <button
                  className="tree-refresh-button"
                  type="button"
                  onClick={() => void folderTreeQuery.refetch()}
                  disabled={isRefreshing}
                >
                  {isRefreshing ? 'refreshing…' : 'refresh'}
                </button>
              </span>
            </div>

            {isLoading && (
              <div className="folder-tree-state" role="status">
                <span
                  className="state-mark state-mark-loading"
                  aria-hidden="true"
                />
                <strong>Looking through your folders…</strong>
                <p>Google Drive is sending back your owned folder structure.</p>
              </div>
            )}

            {!isLoading && error && (
              <div
                className="folder-tree-state folder-tree-state-error"
                role="alert"
              >
                <span className="state-mark" aria-hidden="true">
                  !
                </span>
                <strong>{error}</strong>
                <p>Your selection has not changed.</p>
                <div className="folder-tree-state-actions">
                  {error.startsWith('Reconnect') && (
                    <Link className="text-button" to="/connect">
                      Reconnect Google
                    </Link>
                  )}
                  <button
                    className="text-button"
                    type="button"
                    onClick={() => void folderTreeQuery.refetch()}
                  >
                    Try again
                  </button>
                </div>
              </div>
            )}

            {!isLoading && !error && !hasFolders && (
              <div className="folder-tree-state" role="status">
                <span className="state-mark" aria-hidden="true">
                  ∅
                </span>
                <strong>No owned folders found.</strong>
                <p>
                  Create a folder in Google Drive, then try loading this list
                  again.
                </p>
                <button
                  className="text-button"
                  type="button"
                  onClick={() => void folderTreeQuery.refetch()}
                >
                  Refresh folders
                </button>
              </div>
            )}

            {!isLoading && !error && hasFolders && folders && (
              <ul className="folder-tree" aria-label="Google Drive folders">
                {folders.map((folder) => (
                  <FolderTreeNode
                    key={folder.id}
                    node={folder}
                    depth={0}
                    selectedIds={selectedIds}
                    isIncludedBySelection={isIncludedBySelection}
                    onToggle={toggleFolder}
                  />
                ))}
              </ul>
            )}

            {!isLoading && !error && hasFolders && (
              <p className="folder-tree-footnote">
                Selecting a parent includes all of its descendants.
              </p>
            )}
          </section>

          <aside
            className="selection-summary"
            aria-labelledby="selection-summary-title"
          >
            <p className="card-kicker">Selection preview</p>
            <h2 id="selection-summary-title">Your source trail.</h2>
            {selectedFolders.length > 0 ? (
              <ul className="selected-folder-list">
                {selectedFolders.map(({ node, path }) => (
                  <li key={node.id}>
                    <span className="folder-icon" aria-hidden="true" />
                    <span>
                      <strong>{node.name}</strong>
                      <small>{path.join(' / ')}</small>
                    </span>
                    <button
                      className="remove-folder-button"
                      type="button"
                      onClick={() => toggleFolder(node.id)}
                      aria-label={`Remove ${node.name}`}
                    >
                      ×
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="selection-empty">
                <span className="selection-empty-line" aria-hidden="true" />
                <p>
                  Choose a folder to start building your private source set.
                </p>
              </div>
            )}
            <div className="selection-summary-note">
              <span className="lock-icon" aria-hidden="true" />
              <p>Only your owned Google Drive folders are shown.</p>
            </div>
          </aside>
        </div>
      </main>
    </div>
  )
}

type FolderTreeNodeProps = {
  node: FolderNode
  depth: number
  selectedIds: Set<string>
  isIncludedBySelection: (folderId: string) => boolean
  onToggle: (folderId: string) => void
}

function FolderTreeNode({
  node,
  depth,
  selectedIds,
  isIncludedBySelection,
  onToggle,
}: FolderTreeNodeProps) {
  const [isExpanded, setIsExpanded] = useState(depth < 1)
  const hasChildren = node.children.length > 0
  const selected = selectedIds.has(node.id)
  const includedByParent = isIncludedBySelection(node.id)

  return (
    <li className="folder-tree-node">
      <div
        className="folder-tree-row"
        style={{ paddingLeft: `${depth * 1.35 + 0.65}rem` }}
      >
        {hasChildren ? (
          <button
            className="folder-tree-toggle"
            type="button"
            aria-label={`${isExpanded ? 'Collapse' : 'Expand'} ${node.name}`}
            aria-expanded={isExpanded}
            onClick={() => setIsExpanded((expanded) => !expanded)}
          >
            <span aria-hidden="true">{isExpanded ? '⌄' : '›'}</span>
          </button>
        ) : (
          <span className="folder-tree-spacer" aria-hidden="true" />
        )}
        <label
          className={`folder-choice${includedByParent ? ' folder-choice-included' : ''}`}
        >
          <input
            type="checkbox"
            aria-label={node.name}
            checked={selected}
            disabled={includedByParent}
            onChange={() => onToggle(node.id)}
          />
          <span className="folder-checkmark" aria-hidden="true" />
          <span className="folder-choice-name">{node.name}</span>
          {includedByParent && (
            <span className="folder-included-label">included</span>
          )}
        </label>
      </div>
      {hasChildren && isExpanded && (
        <ul className="folder-tree-children">
          {node.children.map((child) => (
            <FolderTreeNode
              key={child.id}
              node={child}
              depth={depth + 1}
              selectedIds={selectedIds}
              isIncludedBySelection={isIncludedBySelection}
              onToggle={onToggle}
            />
          ))}
        </ul>
      )}
    </li>
  )
}
