import type { CSSProperties } from "react"
import { Outlet, useMatches } from "react-router-dom"

import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
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
      style={
        {
          "--sidebar-width": "calc(var(--spacing) * 72)",
          "--header-height": "calc(var(--spacing) * 12)",
        } as CSSProperties
      }
    >
      {/* Sidebar variant: 'none' (default, straight edge) | 'variant="inset"'(rounded content panel) | 'variant="floating"' (rounded floating sidebar) */}
      <AppSidebar />
      <SidebarInset>
        <SiteHeader title={title?.title ?? "Dashboard"} />
        <div className="flex flex-1 flex-col">
          <Outlet />
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}
