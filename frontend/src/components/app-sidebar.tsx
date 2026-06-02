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
  LineChartIcon,
  MapPinIcon,
  RadioIcon,
  SearchIcon,
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
      title: "Readings",
      url: "#",
      icon: <LineChartIcon />,
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
    {
      title: "Search",
      url: "#",
      icon: <SearchIcon />,
    },
  ],
}

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader className="px-4 py-3 group-data-[collapsible=icon]:px-2 group-data-[collapsible=icon]:py-2">
        <Link to="/" className="block">
          <img
            src="/logo.svg"
            alt="Open Water Platform"
            className="h-10 w-auto max-w-full object-contain object-left group-data-[collapsible=icon]:hidden"
          />
          <img
            src="/icon-main.svg"
            alt="Open Water Platform"
            className="mx-auto hidden size-8 object-contain group-data-[collapsible=icon]:block"
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
