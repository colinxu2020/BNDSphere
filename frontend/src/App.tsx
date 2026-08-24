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
        path: "club/:id/joint-activities/manage",
        lazy: () =>
          import("./pages/JointActivityWorkspace").then(({ JointActivityWorkspace }) => ({
            Component: JointActivityWorkspace,
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
        path: "joint-activities",
        lazy: () =>
          import("./pages/JointActivities").then(({ JointActivities }) => ({
            Component: JointActivities,
          })),
      },
      {
        path: "joint-activities/:id",
        lazy: () =>
          import("./pages/JointActivityDetail").then(({ JointActivityDetail }) => ({
            Component: JointActivityDetail,
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
        path: "dev",
        lazy: () => import("./pages/DevPanel").then(({ DevPanel }) => ({ Component: DevPanel })),
      },
      {
        path: "federation",
        lazy: () =>
          import("./pages/Federation").then(({ Federation }) => ({ Component: Federation })),
      },
      {
        path: "federation/joint-activities",
        lazy: () =>
          import("./pages/FederationJointActivities").then(({ FederationJointActivities }) => ({
            Component: FederationJointActivities,
          })),
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
