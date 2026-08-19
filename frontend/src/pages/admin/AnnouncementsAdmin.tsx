import React, { useEffect, useState } from "react";
import { Save, Trash2 } from "@/src/components/ui/Icons";
import { client } from "../../api/client";
import type { components } from "../../api/schema";
import {
  formatDate,
  fromDateTimeLocalValue,
  nullableText,
  toDateTimeLocalValue,
} from "../../lib/format";
import {
  Field,
  PrimaryButton,
  SecondaryButton,
  inputClassName,
  textareaClassName,
} from "../../components/ui/AppPrimitives";
import { AdminGrid, ItemList, ListButton, FormHeader } from "./primitives";
import { useAdminContext } from "./context";

type Announcement = components["schemas"]["AnnouncementInfo"];

export function AnnouncementsAdmin() {
  const { isRefreshing, refreshStart, refreshEnd, setResult } = useAdminContext();
  const [items, setItems] = useState<Announcement[]>([]);
  const [selected, setSelected] = useState<Announcement | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [form, setForm] = useState({
    title: "",
    body: "",
    link_url: "",
    starts_at: "",
    ends_at: "",
    is_active: true,
  });

  const loadItems = async () => {
    refreshStart();
    try {
      const { data, error } = await client.GET("/api/v1/admin/announcements/", {
        params: { query: { size: 100, active_only: false } },
      });
      if (error) setResult(error, null);
      setItems(data?.items || []);
    } catch (error) {
      setResult(error, null);
    } finally {
      refreshEnd();
    }
  };

  useEffect(() => {
    loadItems();
  }, []);

  const selectItem = (item: Announcement) => {
    setSelected(item);
    setForm({
      title: item.title || "",
      body: item.body || "",
      link_url: item.link_url || "",
      starts_at: toDateTimeLocalValue(item.starts_at),
      ends_at: toDateTimeLocalValue(item.ends_at),
      is_active: item.is_active,
    });
  };

  const resetCreate = () => {
    setSelected(null);
    setForm({
      title: "",
      body: "",
      link_url: "",
      starts_at: "",
      ends_at: "",
      is_active: true,
    });
  };

  const buildBody = () => ({
    title: form.title,
    body: form.body,
    link_url: nullableText(form.link_url),
    starts_at: form.starts_at ? fromDateTimeLocalValue(form.starts_at) : null,
    ends_at: form.ends_at ? fromDateTimeLocalValue(form.ends_at) : null,
    is_active: form.is_active,
  });

  const saveItem = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsSaving(true);
    try {
      if (selected) {
        const { data, error } = await client.PATCH(
          "/api/v1/admin/announcements/{announcement_id}",
          {
            params: { path: { announcement_id: selected.id } },
            body: buildBody(),
          },
        );
        setResult(error, error ? null : "公告已保存");
        if (data) selectItem(data);
      } else {
        const { data, error } = await client.POST("/api/v1/admin/announcements/", {
          body: buildBody(),
        });
        setResult(error, error ? null : "公告已创建");
        if (data) selectItem(data);
      }
      loadItems();
    } catch (error) {
      setResult(error, null);
    } finally {
      setIsSaving(false);
    }
  };

  const deleteItem = async (item: Announcement) => {
    if (!window.confirm(`确认删除 ${item.title}？`)) return;
    const { error } = await client.DELETE("/api/v1/admin/announcements/{announcement_id}", {
      params: { path: { announcement_id: item.id } },
    });
    setResult(error, error ? null : "公告已删除");
    if (!error) resetCreate();
    loadItems();
  };

  return (
    <AdminGrid
      title="公告管理"
      onRefresh={loadItems}
      refreshing={isRefreshing}
      list={
        <>
          <SecondaryButton type="button" onClick={resetCreate}>
            新建公告
          </SecondaryButton>
          <ItemList>
            {items.map((item) => (
              <ListButton
                key={item.id}
                active={selected?.id === item.id}
                title={item.title}
                meta={formatDate(item.created_at)}
                badge={item.is_active ? "启用" : "停用"}
                onClick={() => selectItem(item)}
              />
            ))}
          </ItemList>
        </>
      }
    >
      <form onSubmit={saveItem} className="grid gap-4">
        <FormHeader
          title={selected ? selected.title : "新建公告"}
          subtitle={selected ? `公告 #${selected.id}` : "显示在首页公告栏"}
        />
        <Field label="标题">
          <input
            className={inputClassName}
            value={form.title}
            onChange={(event) => setForm({ ...form, title: event.target.value })}
            required
          />
        </Field>
        <Field label="正文">
          <textarea
            className={textareaClassName}
            value={form.body}
            onChange={(event) => setForm({ ...form, body: event.target.value })}
            required
          />
        </Field>
        <Field label="链接">
          <input
            className={inputClassName}
            value={form.link_url}
            onChange={(event) => setForm({ ...form, link_url: event.target.value })}
          />
        </Field>
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="开始展示">
            <input
              className={inputClassName}
              type="datetime-local"
              value={form.starts_at}
              onChange={(event) => setForm({ ...form, starts_at: event.target.value })}
            />
          </Field>
          <Field label="结束展示">
            <input
              className={inputClassName}
              type="datetime-local"
              value={form.ends_at}
              onChange={(event) => setForm({ ...form, ends_at: event.target.value })}
            />
          </Field>
        </div>
        <label className="flex items-center gap-2 text-sm font-semibold text-content">
          <input
            type="checkbox"
            checked={form.is_active}
            onChange={(event) => setForm({ ...form, is_active: event.target.checked })}
          />
          启用公告
        </label>
        <div className="flex flex-wrap gap-2">
          <PrimaryButton type="submit" loading={isSaving}>
            <Save size={16} /> {selected ? "保存公告" : "创建公告"}
          </PrimaryButton>
          {selected && (
            <button
              type="button"
              onClick={() => deleteItem(selected)}
              className="inline-flex items-center gap-2 rounded-md border border-tone-danger-edge bg-tone-danger-bg px-4 py-2.5 text-sm font-semibold text-tone-danger-fg hover:bg-tone-danger-bg-hover"
            >
              <Trash2 size={16} /> 删除
            </button>
          )}
        </div>
      </form>
    </AdminGrid>
  );
}
