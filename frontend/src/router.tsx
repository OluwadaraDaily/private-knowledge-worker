import {
  Outlet,
  createRootRoute,
  createRoute,
  createRouter,
} from '@tanstack/react-router'

import { GoogleConnectionPage } from './pages/GoogleConnectionPage'
import { FolderSelectionPage } from './pages/FolderSelectionPage'
import { LandingPage } from './pages/LandingPage'

const rootRoute = createRootRoute({
  component: () => <Outlet />,
})

const homeRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: LandingPage,
})

const connectRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/connect',
  component: GoogleConnectionPage,
})

const folderSelectionRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/folders',
  component: FolderSelectionPage,
})

const routeTree = rootRoute.addChildren([
  homeRoute,
  connectRoute,
  folderSelectionRoute,
])

export function createAppRouter() {
  return createRouter({
    routeTree,
    defaultPreload: 'intent',
    scrollRestoration: true,
  })
}

export const router = createAppRouter()

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}
