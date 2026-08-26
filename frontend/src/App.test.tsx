import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import App from './App'

describe('App', () => {
  it('renders the starter page and updates the counter', () => {
    render(<App />)

    const counter = screen.getByRole('button', { name: 'Count is 0' })
    expect(
      screen.getByRole('heading', { name: 'Get started' }),
    ).toBeInTheDocument()

    fireEvent.click(counter)

    expect(
      screen.getByRole('button', { name: 'Count is 1' }),
    ).toBeInTheDocument()
  })
})
