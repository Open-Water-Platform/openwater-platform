import * as React from "react"

import { Link } from "react-router-dom"

import { NavMain } from "@/components/nav-main"
import { NavSecondary } from "@/components/nav-secondary"
import { NavUser } from "@/components/nav-user"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
} from "@/components/ui/sidebar"
import {
  CircleHelpIcon,
  LayoutDashboardIcon,
  MapPinIcon,
  RadioIcon,
  Settings2Icon,
} from "lucide-react"

const data = {
  user: {
    name: "Operator",
    email: "operator@openwater.io",
    avatar: "/avatars/operator.jpg",
  },
  navMain: [
    {
      title: "Dashboard",
      url: "/",
      icon: <LayoutDashboardIcon />,
    },
    {
      title: "Devices",
      url: "/devices",
      icon: <RadioIcon />,
    },
    {
      title: "Sites",
      url: "#",
      icon: <MapPinIcon />,
    },
  ],
  navSecondary: [
    {
      title: "Settings",
      url: "#",
      icon: <Settings2Icon />,
    },
    {
      title: "Get Help",
      url: "#",
      icon: <CircleHelpIcon />,
    },
  ],
}

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader className="px-4 py-3">
        <Link
          to="/"
          className="flex h-10 items-center group-data-[collapsible=icon]:justify-center"
        >
          <img
            src="/logo.svg"
            alt="Open Water Platform"
            className="h-10 w-auto shrink-0 object-contain group-data-[collapsible=icon]:hidden"
          />
          <img
            src="/icon-main.svg"
            alt="Open Water Platform"
            className="hidden h-10 w-10 shrink-0 object-contain group-data-[collapsible=icon]:block"
          />
        </Link>
      </SidebarHeader>
      <SidebarContent>
        <NavMain items={data.navMain} />
        <NavSecondary items={data.navSecondary} className="mt-auto" />
      </SidebarContent>
      <SidebarFooter>
        <NavUser user={data.user} />
      </SidebarFooter>
    </Sidebar>
  )
}
