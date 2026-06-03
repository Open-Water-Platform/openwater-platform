import { createBrowserRouter, RouterProvider } from "react-router-dom"

import AppLayout from "@/layouts/app-layout"
import DashboardPage from "@/pages/dashboard/DashboardPage"
import DeviceAnalytics from "@/pages/devices/DeviceAnalytics"
import DevicesIndex from "@/pages/devices/DevicesIndex"
import DevicesPage from "@/pages/devices/DevicesPage"
import GetHelpPage from "@/pages/help/GetHelpPage"
import SettingsPage from "@/pages/settings/SettingsPage"
import SitesPage from "@/pages/sites/SitesPage"

const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      {
        index: true,
        element: <DashboardPage />,
        handle: { title: "Dashboard" },
      },
      {
        path: "sites",
        element: <SitesPage />,
        handle: { title: "Sites" },
      },
      {
        path: "settings",
        element: <SettingsPage />,
        handle: { title: "Settings" },
      },
      {
        path: "get-help",
        element: <GetHelpPage />,
        handle: { title: "Get Help" },
      },
      {
        path: "devices",
        element: <DevicesPage />,
        handle: { title: "Devices" },
        children: [
          {
            index: true,
            element: <DevicesIndex />,
          },
          {
            path: ":deviceId",
            element: <DeviceAnalytics />,
          },
        ],
      },
    ],
  },
])

export default function App() {
  return <RouterProvider router={router} />
}
