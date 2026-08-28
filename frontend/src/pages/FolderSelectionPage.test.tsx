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
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => folderTree,
      }),
    )
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
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => folderTree,
      }),
    )
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
      .mockResolvedValueOnce({
        ok: true,
        json: async () => folderTree,
      })
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
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('reuses the cached hierarchy when returning to the route', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => folderTree,
    })
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
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('refetches the hierarchy only when manually requested', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => folderTree,
    })
    vi.stubGlobal('fetch', fetchMock)
    await renderFoldersPage()

    await screen.findByRole('checkbox', { name: 'Projects' })
    fireEvent.click(screen.getByRole('button', { name: 'refresh' }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
  })
})
