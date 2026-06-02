import { createBrowserRouter, RouterProvider } from "react-router-dom"

import AppLayout from "@/layouts/app-layout"
import DashboardPage from "@/pages/DashboardPage"
import DevicesPage from "@/pages/DevicesPage"

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
      },
    ],
  },
])

export default function App() {
  return <RouterProvider router={router} />
}
