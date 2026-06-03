import type { CSSProperties } from "react"
import { Outlet, useMatches } from "react-router-dom"

import { AppSidebar } from "@/components/layout/app-sidebar"
import { SiteHeader } from "@/components/layout/site-header"
import {
  SidebarInset,
  SidebarProvider,
} from "@/components/ui/sidebar"

type RouteHandle = {
  title?: string
}

export default function AppLayout() {
  const matches = useMatches()
  const title =
    [...matches]
      .reverse()
      .find((match) => (match.handle as RouteHandle | undefined)?.title)
      ?.handle as RouteHandle | undefined

  return (
    <SidebarProvider
      className="h-svh overflow-hidden"
      style={
        {
          "--sidebar-width": "15rem",
          "--sidebar-width-icon": "4rem",
          "--header-height": "calc(var(--spacing) * 12)",
        } as CSSProperties
      }
    >
      {/* Sidebar variant: 'none' (default, straight edge) | 'variant="inset"'(rounded content panel) | 'variant="floating"' (rounded floating sidebar) */}
      <AppSidebar />
      <SidebarInset className="min-h-0 overflow-hidden">
        <SiteHeader title={title?.title ?? "Dashboard"} />
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
          <Outlet />
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}
