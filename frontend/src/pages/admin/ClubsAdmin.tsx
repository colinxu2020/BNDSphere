import React, { useEffect, useState } from "react";
import { Save } from "@/src/components/ui/Icons";
import { client } from "../../api/client";
import type { components } from "../../api/schema";
import { CLUB_STATUS_MAP, CLUB_STATUS_OPTIONS, STAR_LEVEL_OPTIONS } from "../../lib/labels";
import { nullableText } from "../../lib/format";
import {
  Field,
  PrimaryButton,
  inputClassName,
  selectClassName,
  textareaClassName,
} from "../../components/ui/AppPrimitives";
import { AdminGrid, ItemList, ListButton, FormHeader, PickPlaceholder } from "./primitives";
import { useAdminContext } from "./context";

type ClubInfo = components["schemas"]["ClubInfo"];
type ClubStarLevel = components["schemas"]["ClubStarLevelEnum"];
type ClubStatus = components["schemas"]["ClubStatusEnum"];
type AdminClubUpdate = components["schemas"]["AdminClubUpdate"];

export function ClubsAdmin() {
  const { isRefreshing, refreshStart, refreshEnd, setResult } =
    useAdminContext();
  const [clubs, setClubs] = useState<ClubInfo[]>([]);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<ClubInfo | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [form, setForm] = useState({
    summary: "",
    description: "",
    logo_uri: "",
    star_level: "" as ClubStarLevel | "",
    status: "" as ClubStatus | "",
  });

  const loadClubs = async () => {
    refreshStart();
    try {
      const { data, error } = await client.GET("/api/v1/admin/clubs/", {
        params: { query: { size: 50, search: search || undefined } },
      });
      if (error) setResult(error, null);
      setClubs(data?.items || []);
    } catch (error) {
      setResult(error, null);
    } finally {
      refreshEnd();
    }
  };

  useEffect(() => {
    loadClubs();
  }, []);

  const selectClub = (club: ClubInfo) => {
    setSelected(club);
    setForm({
      summary: club.summary || "",
      description: club.description || "",
      logo_uri: club.logo_uri || "",
      star_level: club.star_level,
      status: club.status,
    });
  };

  const saveClub = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selected) return;
    setIsSaving(true);
    const body: AdminClubUpdate = {
      summary: nullableText(form.summary),
      description: nullableText(form.description),
      logo_uri: nullableText(form.logo_uri),
      star_level: form.star_level || null,
      status: form.status || null,
    };
    try {
      const { data, error } = await client.PATCH(
        "/api/v1/admin/clubs/{club_id}",
        {
          params: { path: { club_id: selected.id } },
          body,
        },
      );
      setResult(error, error ? null : "社团已保存");
      if (data) selectClub(data);
      if (!error) loadClubs();
    } catch (error) {
      setResult(error, null);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <AdminGrid
      title="社团管理"
      onRefresh={loadClubs}
      refreshing={isRefreshing}
      list={
        <>
          <input
            className={inputClassName}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            onKeyDown={(event) => event.key === "Enter" && loadClubs()}
            placeholder="搜索社团"
          />
          <ItemList>
            {clubs.map((club) => (
              <ListButton
                key={club.id}
                active={selected?.id === club.id}
                title={club.name}
                meta={`${CLUB_STATUS_MAP[club.status]} · #${club.id}`}
                onClick={() => selectClub(club)}
              />
            ))}
          </ItemList>
        </>
      }
    >
      {selected ? (
        <form onSubmit={saveClub} className="grid gap-4">
          <FormHeader title={selected.name} subtitle={`社团 #${selected.id}`} />
          <Field label="简介">
            <input
              className={inputClassName}
              value={form.summary}
              onChange={(event) =>
                setForm({ ...form, summary: event.target.value })
              }
            />
          </Field>
          <Field label="详细介绍">
            <textarea
              className={textareaClassName}
              value={form.description}
              onChange={(event) =>
                setForm({ ...form, description: event.target.value })
              }
            />
          </Field>
          <Field label="Logo URL">
            <input
              className={inputClassName}
              value={form.logo_uri}
              onChange={(event) =>
                setForm({ ...form, logo_uri: event.target.value })
              }
            />
          </Field>
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="星级">
              <select
                className={selectClassName}
                value={form.star_level}
                onChange={(event) =>
                  setForm({
                    ...form,
                    star_level: event.target.value as ClubStarLevel,
                  })
                }
              >
                {STAR_LEVEL_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="状态">
              <select
                className={selectClassName}
                value={form.status}
                onChange={(event) =>
                  setForm({ ...form, status: event.target.value as ClubStatus })
                }
              >
                {CLUB_STATUS_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </Field>
          </div>
          <PrimaryButton type="submit" loading={isSaving}>
            <Save size={16} /> 保存社团
          </PrimaryButton>
        </form>
      ) : (
        <PickPlaceholder label="从左侧选择社团" />
      )}
    </AdminGrid>
  );
}
