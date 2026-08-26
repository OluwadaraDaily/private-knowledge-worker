import { render, screen, waitFor } from '@testing-library/react'
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

  it('reports when the backend is unavailable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
    render(<App />)

    await waitFor(() =>
      expect(screen.getByText(/Backend is unavailable/)).toBeInTheDocument(),
    )
  })
})
