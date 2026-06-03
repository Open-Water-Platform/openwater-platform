import { createBrowserRouter, RouterProvider } from "react-router-dom"

import AppLayout from "@/layouts/app-layout"
import DashboardPage from "@/pages/dashboard/DashboardPage"
import DeviceAnalytics from "@/pages/devices/DeviceAnalytics"
import DevicesIndex from "@/pages/devices/DevicesIndex"
import DevicesPage from "@/pages/devices/DevicesPage"

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
