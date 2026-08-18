import React, { useEffect, useState } from "react";
import { Save } from "@/src/components/ui/Icons";
import { client } from "../../api/client";
import type { components } from "../../api/schema";
import { ROLE_MAP, ROLE_OPTIONS } from "../../lib/labels";
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

type UserInfo = components["schemas"]["UserInfo"];
type Role = components["schemas"]["RoleEnum"];
type AdminUserUpdate = components["schemas"]["AdminUserUpdate"];

export function UsersAdmin() {
  const { isRefreshing, refreshStart, refreshEnd, setResult } =
    useAdminContext();
  const [users, setUsers] = useState<UserInfo[]>([]);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<UserInfo | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [form, setForm] = useState({
    username: "",
    email: "",
    avatar_uri: "",
    description: "",
    role: "" as Role | "",
  });

  const loadUsers = async () => {
    refreshStart();
    try {
      const { data, error } = await client.GET("/api/v1/admin/users/", {
        params: { query: { size: 50, search: search || undefined } },
      });
      if (error) setResult(error, null);
      setUsers(data?.items || []);
      if (selected) {
        const nextSelected =
          data?.items.find((item) => item.id === selected.id) || null;
        if (nextSelected) selectUser(nextSelected);
      }
    } catch (error) {
      setResult(error, null);
    } finally {
      refreshEnd();
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const selectUser = (user: UserInfo) => {
    setSelected(user);
    setForm({
      username: user.username || "",
      email: user.email || "",
      avatar_uri: user.avatar_uri || "",
      description: user.description || "",
      role: user.role,
    });
  };

  const saveUser = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selected) return;
    setIsSaving(true);
    const body: AdminUserUpdate = {
      username: nullableText(form.username),
      email: nullableText(form.email),
      avatar_uri: nullableText(form.avatar_uri),
      description: nullableText(form.description),
      role: form.role || null,
    };
    try {
      const { data, error } = await client.PATCH(
        "/api/v1/admin/users/{user_id}",
        {
          params: { path: { user_id: selected.id } },
          body,
        },
      );
      setResult(error, error ? null : "用户已保存");
      if (data) selectUser(data);
      if (!error) loadUsers();
    } catch (error) {
      setResult(error, null);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <AdminGrid
      title="用户管理"
      onRefresh={loadUsers}
      refreshing={isRefreshing}
      list={
        <>
          <input
            className={inputClassName}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            onKeyDown={(event) => event.key === "Enter" && loadUsers()}
            placeholder="搜索用户名、邮箱或姓名"
          />
          <ItemList>
            {users.map((user) => (
              <ListButton
                key={user.id}
                active={selected?.id === user.id}
                title={user.username}
                meta={`${ROLE_MAP[user.role]} · #${user.id}`}
                onClick={() => selectUser(user)}
              />
            ))}
          </ItemList>
        </>
      }
    >
      {selected ? (
        <form onSubmit={saveUser} className="grid gap-4">
          <FormHeader
            title={selected.username}
            subtitle={`用户 #${selected.id}`}
          />
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="用户名">
              <input
                className={inputClassName}
                value={form.username}
                onChange={(event) =>
                  setForm({ ...form, username: event.target.value })
                }
              />
            </Field>
            <Field label="邮箱">
              <input
                className={inputClassName}
                value={form.email}
                onChange={(event) =>
                  setForm({ ...form, email: event.target.value })
                }
              />
            </Field>
          </div>
          <Field label="头像 URL">
            <input
              className={inputClassName}
              value={form.avatar_uri}
              onChange={(event) =>
                setForm({ ...form, avatar_uri: event.target.value })
              }
            />
          </Field>
          <Field label="角色">
            <select
              className={selectClassName}
              value={form.role}
              onChange={(event) =>
                setForm({ ...form, role: event.target.value as Role })
              }
            >
              {ROLE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </Field>
          <Field label="简介">
            <textarea
              className={textareaClassName}
              value={form.description}
              onChange={(event) =>
                setForm({ ...form, description: event.target.value })
              }
            />
          </Field>
          <PrimaryButton type="submit" loading={isSaving}>
            <Save size={16} /> 保存用户
          </PrimaryButton>
        </form>
      ) : (
        <PickPlaceholder label="从左侧选择用户" />
      )}
    </AdminGrid>
  );
}
