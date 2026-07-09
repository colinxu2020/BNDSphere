import { client } from "./client";
import type { components } from "./schema";

export async function adminGetClub(
  clubId: number,
): Promise<components["schemas"]["ClubInfo"]> {
  const { data, error } = await (client.GET as any)(
    "/api/v1/admin/clubs/{club_id}",
    {
      params: { path: { club_id: clubId } },
    },
  );

  if (error) {
    throw error;
  }

  if (!data) {
    throw new Error("Admin club response is empty.");
  }

  return data;
}

export async function adminUpdateClub(
  clubId: number,
  body: components["schemas"]["AdminClubUpdate"],
) {
  return client.PATCH("/api/v1/admin/clubs/{club_id}", {
    params: { path: { club_id: clubId } },
    body,
  });
}
