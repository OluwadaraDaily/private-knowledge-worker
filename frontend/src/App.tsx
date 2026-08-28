import { RouterProvider } from '@tanstack/react-router'

import { router as defaultRouter } from './router'
import './App.css'

function App({ router = defaultRouter }: { router?: typeof defaultRouter }) {
  return <RouterProvider router={router} />
}

export default App
