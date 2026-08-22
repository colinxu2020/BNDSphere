import { createBrowserRouter, RouterProvider, Outlet } from "react-router-dom";
import { RootLayout } from "./components/layout/RootLayout";
import { Home } from "./pages/Home";
import { ExploreClubs } from "./pages/ExploreClubs";
import { ClubDetail } from "./pages/ClubDetail";
import { Profile } from "./pages/Profile";
import { Login } from "./pages/Login";
import { Register } from "./pages/Register";
import { CreateClub } from "./pages/CreateClub";
import { UserProfile } from "./pages/UserProfile";
import { GeneralActivities } from "./pages/GeneralActivities";
import { GeneralActivityDetail } from "./pages/GeneralActivityDetail";
import { ClubWorkspace } from "./pages/ClubWorkspace";
import { Workspace } from "./pages/Workspace";
import { Moderation } from "./pages/Moderation";
import { Admin } from "./pages/Admin";
import { Federation } from "./pages/Federation";
import { StarLevelApplications } from "./pages/StarLevelApplications";
import { JointActivities } from "./pages/JointActivities";
import { JointActivityDetail } from "./pages/JointActivityDetail";
import { JointActivityWorkspace } from "./pages/JointActivityWorkspace";
import { FederationJointActivities } from "./pages/FederationJointActivities";

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
        element: <ExploreClubs />,
      },
      {
        path: "club/:id",
        element: <ClubDetail />,
      },
      {
        path: "club/:id/manage",
        element: <ClubWorkspace />,
      },
      {
        path: "club/:id/joint-activities/manage",
        element: <JointActivityWorkspace />,
      },
      {
        path: "clubs/new",
        element: <CreateClub />,
      },
      {
        path: "activities",
        element: <GeneralActivities />,
      },
      {
        path: "activities/:id",
        element: <GeneralActivityDetail />,
      },
      {
        path: "joint-activities",
        element: <JointActivities />,
      },
      {
        path: "joint-activities/:id",
        element: <JointActivityDetail />,
      },
      {
        path: "users/:id",
        element: <UserProfile />,
      },
      {
        path: "workspace",
        element: <Workspace />,
      },
      {
        path: "star-level",
        element: <StarLevelApplications />,
      },
      {
        path: "moderation",
        element: <Moderation />,
      },
      {
        path: "admin",
        element: <Admin />,
      },
      {
        path: "federation",
        element: <Federation />,
      },
      {
        path: "federation/joint-activities",
        element: <FederationJointActivities />,
      },
      {
        path: "profile",
        element: <Profile />,
      },
      {
        path: "login",
        element: <Login />,
      },
      {
        path: "register",
        element: <Register />,
      },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
