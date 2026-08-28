import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from '../App'
import { createAppRouter } from '../router'

const folderTree = [
  {
    id: 'research',
    name: 'Research',
    children: [
      {
        id: 'interviews',
        name: 'Interviews',
        children: [],
      },
      {
        id: 'notes',
        name: 'Notes',
        children: [],
      },
    ],
  },
  {
    id: 'projects',
    name: 'Projects',
    children: [],
  },
]

function mockFolderRequests() {
  return vi.fn().mockImplementation((input: RequestInfo | URL) =>
    Promise.resolve({
      ok: true,
      json: async () => (String(input).endsWith('/selected') ? [] : folderTree),
    }),
  )
}

describe('FolderSelectionPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  async function renderFoldersPage() {
    window.history.replaceState({}, '', '/folders')
    const appRouter = createAppRouter()
    render(<App router={appRouter} />)
    await act(async () => {
      await appRouter.navigate({ to: '/folders' })
    })
    return appRouter
  }

  it('loads the owned hierarchy and selects a folder with its descendants', async () => {
    vi.stubGlobal('fetch', mockFolderRequests())
    await renderFoldersPage()

    expect(
      await screen.findByRole('heading', {
        name: 'Choose what stays in context.',
      }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('checkbox', { name: 'Research' }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('checkbox', { name: 'Interviews' }),
    ).toBeInTheDocument()

    fireEvent.click(screen.getByRole('checkbox', { name: 'Research' }))

    expect(screen.getByRole('checkbox', { name: 'Research' })).toBeChecked()
    expect(screen.getByRole('checkbox', { name: 'Interviews' })).toBeDisabled()
    expect(screen.getByText('folder selected')).toBeInTheDocument()
  })

  it('replaces selected descendants when their parent is selected', async () => {
    vi.stubGlobal('fetch', mockFolderRequests())
    await renderFoldersPage()

    await screen.findByRole('checkbox', { name: 'Interviews' })
    fireEvent.click(screen.getByRole('checkbox', { name: 'Interviews' }))
    fireEvent.click(screen.getByRole('checkbox', { name: 'Research' }))

    expect(screen.getByRole('checkbox', { name: 'Research' })).toBeChecked()
    expect(
      screen.getByRole('checkbox', { name: 'Interviews' }),
    ).not.toBeChecked()
    expect(screen.getByRole('checkbox', { name: 'Interviews' })).toBeDisabled()
    expect(screen.getByText('folder selected')).toBeInTheDocument()
  })

  it('offers recovery when loading the hierarchy fails', async () => {
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new Error('offline'))
      .mockImplementation((input: RequestInfo | URL) =>
        Promise.resolve({
          ok: true,
          json: async () =>
            String(input).endsWith('/selected') ? [] : folderTree,
        }),
      )
    vi.stubGlobal('fetch', fetchMock)
    await renderFoldersPage()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'We could not load your folders. Try again.',
    )

    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))

    await waitFor(() =>
      expect(
        screen.getByRole('checkbox', { name: 'Projects' }),
      ).toBeInTheDocument(),
    )
    expect(fetchMock).toHaveBeenCalledTimes(3)
  })

  it('reuses the cached hierarchy when returning to the route', async () => {
    const fetchMock = mockFolderRequests()
    vi.stubGlobal('fetch', fetchMock)
    const appRouter = await renderFoldersPage()

    await screen.findByRole('checkbox', { name: 'Projects' })
    await act(async () => {
      await appRouter.navigate({ to: '/' })
      await appRouter.navigate({ to: '/folders' })
    })

    expect(
      await screen.findByRole('checkbox', { name: 'Projects' }),
    ).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('refetches the hierarchy only when manually requested', async () => {
    const fetchMock = mockFolderRequests()
    vi.stubGlobal('fetch', fetchMock)
    await renderFoldersPage()

    await screen.findByRole('checkbox', { name: 'Projects' })
    fireEvent.click(screen.getByRole('button', { name: 'refresh' }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3))
  })

  it('reloads saved folders and persists a changed selection', async () => {
    const fetchMock = vi
      .fn()
      .mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
        if (init?.method === 'PUT') {
          return Promise.resolve({
            ok: true,
            json: async () => [
              { id: 'projects', name: 'Projects' },
              { id: 'research', name: 'Research' },
            ],
          })
        }

        return Promise.resolve({
          ok: true,
          json: async () =>
            String(input).endsWith('/selected')
              ? [{ id: 'projects', name: 'Projects' }]
              : folderTree,
        })
      })
    vi.stubGlobal('fetch', fetchMock)
    await renderFoldersPage()

    await waitFor(() =>
      expect(screen.getByRole('checkbox', { name: 'Projects' })).toBeChecked(),
    )
    fireEvent.click(screen.getByRole('checkbox', { name: 'Research' }))
    fireEvent.click(screen.getByRole('button', { name: 'Save selection' }))

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/drive/folders/selected'),
        expect.objectContaining({
          method: 'PUT',
          body: JSON.stringify({
            folders: [
              { id: 'projects', name: 'Projects' },
              { id: 'research', name: 'Research' },
            ],
          }),
        }),
      ),
    )
    expect(
      screen.getByRole('button', { name: 'Save selection' }),
    ).toBeDisabled()
  })

  it('keeps the changed selection and shows an error when saving fails', async () => {
    const fetchMock = vi
      .fn()
      .mockImplementation((input: RequestInfo | URL, init?: RequestInit) =>
        Promise.resolve({
          ok: init?.method !== 'PUT',
          json: async () =>
            String(input).endsWith('/selected') ? [] : folderTree,
        }),
      )
    vi.stubGlobal('fetch', fetchMock)
    await renderFoldersPage()

    await screen.findByRole('checkbox', { name: 'Projects' })
    fireEvent.click(screen.getByRole('checkbox', { name: 'Projects' }))
    fireEvent.click(screen.getByRole('button', { name: 'Save selection' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'We could not save your folders. Try again.',
    )
    expect(screen.getByRole('checkbox', { name: 'Projects' })).toBeChecked()
  })
})
