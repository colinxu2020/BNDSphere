import { createBrowserRouter, RouterProvider, Outlet } from "react-router-dom";
import { RootLayout } from "./components/layout/RootLayout";
import { Home } from "./pages/Home";

function LayoutWrapper() {
  return (
    <RootLayout>
      <Outlet />
    </RootLayout>
  );
}

const router = createBrowserRouter([
  {
    path: "/",
    element: <LayoutWrapper />,
    children: [
      {
        index: true,
        element: <Home />,
      },
      {
        path: "explore",
        lazy: () =>
          import("./pages/ExploreClubs").then(({ ExploreClubs }) => ({
            Component: ExploreClubs,
          })),
      },
      {
        path: "club/:id",
        lazy: () =>
          import("./pages/ClubDetail").then(({ ClubDetail }) => ({ Component: ClubDetail })),
      },
      {
        path: "club/:id/manage",
        lazy: () =>
          import("./pages/ClubWorkspace").then(({ ClubWorkspace }) => ({
            Component: ClubWorkspace,
          })),
      },
      {
        path: "clubs/new",
        lazy: () =>
          import("./pages/CreateClub").then(({ CreateClub }) => ({ Component: CreateClub })),
      },
      {
        path: "activities",
        lazy: () =>
          import("./pages/GeneralActivities").then(({ GeneralActivities }) => ({
            Component: GeneralActivities,
          })),
      },
      {
        path: "activities/:id",
        lazy: () =>
          import("./pages/GeneralActivityDetail").then(({ GeneralActivityDetail }) => ({
            Component: GeneralActivityDetail,
          })),
      },
      {
        path: "users/:id",
        lazy: () =>
          import("./pages/UserProfile").then(({ UserProfile }) => ({ Component: UserProfile })),
      },
      {
        path: "workspace",
        lazy: () => import("./pages/Workspace").then(({ Workspace }) => ({ Component: Workspace })),
      },
      {
        path: "star-level",
        lazy: () =>
          import("./pages/StarLevelApplications").then(({ StarLevelApplications }) => ({
            Component: StarLevelApplications,
          })),
      },
      {
        path: "moderation",
        lazy: () =>
          import("./pages/Moderation").then(({ Moderation }) => ({ Component: Moderation })),
      },
      {
        path: "admin",
        lazy: () => import("./pages/Admin").then(({ Admin }) => ({ Component: Admin })),
      },
      {
        path: "federation",
        lazy: () =>
          import("./pages/Federation").then(({ Federation }) => ({ Component: Federation })),
      },
      {
        path: "profile",
        lazy: () => import("./pages/Profile").then(({ Profile }) => ({ Component: Profile })),
      },
      {
        path: "login",
        lazy: () => import("./pages/Login").then(({ Login }) => ({ Component: Login })),
      },
      {
        path: "register",
        lazy: () => import("./pages/Register").then(({ Register }) => ({ Component: Register })),
      },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
