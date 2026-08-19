import { createBrowserRouter, RouterProvider, Outlet } from "react-router-dom";
import { MotionConfig } from "motion/react";
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

function LayoutWrapper() {
  return (
    <RootLayout>
      <Outlet />
    </RootLayout>
  );
}

/**
 * The design-system specimen route (Gate 4) exists only in development.
 *
 * `import.meta.env.DEV` is statically replaced with `false` in a production
 * build, so this ternary is dead code there and the dynamic import inside it is
 * unreachable — Rollup drops the module rather than emitting an unused chunk.
 * Guarding the route registration alone would still ship the code.
 */
const devRoutes = import.meta.env.DEV
  ? [
      {
        path: "_dev/specimen",
        lazy: async () => ({
          Component: (await import("./dev/Specimen")).default,
        }),
      },
      {
        path: "_dev/layout/a",
        lazy: async () => ({
          Component: (await import("./dev/layouts/LayoutA")).default,
        }),
      },
      {
        path: "_dev/layout/b",
        lazy: async () => ({
          Component: (await import("./dev/layouts/LayoutB")).default,
        }),
      },
      {
        path: "_dev/layout/c",
        lazy: async () => ({
          Component: (await import("./dev/layouts/LayoutC")).default,
        }),
      },
    ]
  : [];

const router = createBrowserRouter([
  ...devRoutes,
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
  return (
    /**
     * Framer Motion does not honour prefers-reduced-motion on its own. Without
     * this, every page fade and list stagger in the app animated regardless of
     * the setting — the CSS-driven card lifts respected it via motion-reduce:*
     * while the JS-driven ones did not, which is the worst of both.
     *
     * `reducedMotion="user"` makes it follow the media query globally, so
     * transform and layout animations are skipped while opacity changes still
     * run. Motion we drive ourselves uses usePrefersReducedMotion instead.
     */
    <MotionConfig reducedMotion="user">
      <RouterProvider router={router} />
    </MotionConfig>
  );
}
