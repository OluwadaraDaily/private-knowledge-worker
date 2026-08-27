import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import App from './App'

describe('App', () => {
  it('reports when the backend is available', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue({ ok: true, json: async () => ({ status: 'ok' }) }),
    )
    render(<App />)

    await waitFor(() =>
      expect(screen.getByText('Backend is available.')).toBeInTheDocument(),
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
    render(<App />)

    expect(await screen.findByText('user@example.com')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Disconnect Google' }))

    await waitFor(() =>
      expect(
        screen.getByRole('link', { name: 'Connect Google' }),
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
    render(<App />)

    await screen.findByText('user@example.com')
    fireEvent.click(screen.getByRole('button', { name: 'Disconnect Google' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Unable to disconnect Google.',
    )
    expect(screen.getByText('user@example.com')).toBeInTheDocument()
  })

  it('reports when the backend is unavailable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
    render(<App />)

    await waitFor(() =>
      expect(screen.getByText(/Backend is unavailable/)).toBeInTheDocument(),
    )
  })
})
