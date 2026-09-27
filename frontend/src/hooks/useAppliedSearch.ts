import { useCallback, useState, type KeyboardEvent } from "react";

export function useAppliedSearch() {
  const [search, setSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");

  const handleSearchKeyDown = useCallback(
    (event: KeyboardEvent<HTMLInputElement>, reload: () => void | Promise<unknown>) => {
      if (event.key !== "Enter") return;
      if (search === appliedSearch) void reload();
      else setAppliedSearch(search);
    },
    [appliedSearch, search],
  );

  return { search, setSearch, appliedSearch, handleSearchKeyDown };
}
