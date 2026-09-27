import type { components } from "../../api/schema";

type President = components["schemas"]["ClubSummary"]["president"];

export function ClubPresident({ president }: { president: President }) {
  return (
    <span className="inline-flex min-w-0 items-center gap-2 text-sm text-slate-500">
      {president?.avatar_uri && (
        <img
          src={president.avatar_uri}
          alt=""
          className="h-5 w-5 shrink-0 rounded-full object-cover"
        />
      )}
      <span className="truncate">社长：{president?.username ?? "暂无社长"}</span>
    </span>
  );
}
