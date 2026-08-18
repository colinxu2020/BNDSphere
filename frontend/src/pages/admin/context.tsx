import React from "react";

/**
 * Shared state for the admin sections: a refresh indicator and one way to report
 * the result of an action. Lives here rather than in Admin.tsx so the five
 * section modules can consume it without importing their own parent.
 */
const RefreshContext = React.createContext<{
  isRefreshing: boolean;
  refreshStart: () => void;
  refreshEnd: () => void;
  setResult: (error: unknown, data: unknown) => void;
}>({
  isRefreshing: false,
  refreshStart: () => {},
  refreshEnd: () => {},
  setResult: () => {},
});

export { RefreshContext };
export function useAdminContext() {
  return React.useContext(RefreshContext);
}
