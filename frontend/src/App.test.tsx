import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from './App'
import { createAppRouter } from './router'

describe('App', () => {
  async function renderAppAtHome() {
    window.history.replaceState({}, '', '/')
    const appRouter = createAppRouter()
    render(<App router={appRouter} />)
    await appRouter.navigate({ to: '/' })
  }

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('starts on the overview and opens the connection route', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
    await renderAppAtHome()

    expect(
      screen.getByRole('heading', {
        name: 'Ask better questions of the knowledge you already have.',
      }),
    ).toBeInTheDocument()

    fireEvent.click(
      screen.getByRole('link', { name: 'Start with your knowledge' }),
    )

    expect(
      await screen.findByRole('heading', { name: 'Bring your own context.' }),
    ).toBeInTheDocument()
    expect(window.location.pathname).toBe('/connect')
  })

  it('uses the backend OAuth start endpoint from the connection route', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
    await renderAppAtHome()
    fireEvent.click(
      screen.getByRole('link', { name: 'Start with your knowledge' }),
    )

    expect(
      await screen.findByRole('link', { name: 'Continue with Google' }),
    ).toHaveAttribute('href', 'http://127.0.0.1:8000/api/v1/auth/google/start')
  })

  it('reports when the backend is available', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ status: 'ok' }),
      }),
    )
    await renderAppAtHome()
    fireEvent.click(
      screen.getByRole('link', { name: 'Start with your knowledge' }),
    )

    await waitFor(() =>
      expect(screen.getByText('Your workspace is ready.')).toBeInTheDocument(),
    )
  })

  it('shows the connected Google account and can disconnect it', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ status: 'ok' }) })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ connected: true, email: 'user@example.com' }),
      })
      .mockResolvedValueOnce({ ok: true })
    vi.stubGlobal('fetch', fetchMock)
    await renderAppAtHome()
    fireEvent.click(
      screen.getByRole('link', { name: 'Start with your knowledge' }),
    )

    expect(await screen.findByText('user@example.com')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Disconnect Google' }))

    await waitFor(() =>
      expect(
        screen.getByRole('link', { name: 'Continue with Google' }),
      ).toBeInTheDocument(),
    )
    expect(fetchMock).toHaveBeenLastCalledWith(
      'http://127.0.0.1:8000/api/v1/auth/google',
      { method: 'DELETE', credentials: 'include' },
    )
  })

  it('reports a disconnect failure without losing connection state', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ status: 'ok' }) })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ connected: true, email: 'user@example.com' }),
      })
      .mockResolvedValueOnce({ ok: false })
    vi.stubGlobal('fetch', fetchMock)
    await renderAppAtHome()
    fireEvent.click(
      screen.getByRole('link', { name: 'Start with your knowledge' }),
    )

    await screen.findByText('user@example.com')
    fireEvent.click(screen.getByRole('button', { name: 'Disconnect Google' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Unable to disconnect Google.',
    )
    expect(screen.getByText('user@example.com')).toBeInTheDocument()
  })

  it('reports when the backend is unavailable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
    await renderAppAtHome()
    fireEvent.click(
      screen.getByRole('link', { name: 'Start with your knowledge' }),
    )

    await waitFor(() =>
      expect(
        screen.getByText(/workspace service is unavailable/),
      ).toBeInTheDocument(),
    )
  })
})
