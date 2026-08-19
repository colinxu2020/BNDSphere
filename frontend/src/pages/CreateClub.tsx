import React, { useState } from "react";
import { motion } from "motion/react";
import { Building2, Save } from "@/src/components/ui/Icons";
import { useNavigate } from "react-router-dom";
import { client } from "../api/client";
import { useActionFeedback } from "../lib/useActionFeedback";
import type { components } from "../api/schema";
import { CATEGORY_OPTIONS } from "../lib/labels";
import {
  Field,
  PageHeader,
  PrimaryButton,
  SectionTitle,
  StatusMessage,
  Surface,
  inputClassName,
  selectClassName,
  textareaClassName,
} from "../components/ui/AppPrimitives";
import { FileUploadField } from "../components/ui/FileUploadField";

type Category = components["schemas"]["ClubCategoryEnum"];

export function CreateClub() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [category, setCategory] = useState<Category>("science");
  const [summary, setSummary] = useState("");
  const [description, setDescription] = useState("");
  const [logoUri, setLogoUri] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const feedback = useActionFeedback();

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsSubmitting(true);
    feedback.clear();

    try {
      const { data, error } = await client.POST("/api/v1/clubs/", {
        body: {
          name,
          category,
          summary,
          description,
          logo_uri: logoUri || null,
        },
      });

      if (error) {
        feedback.fail(error);
        return;
      }

      feedback.succeed(data);
      if (data?.id) {
        navigate(`/club/${data.id}`);
      }
    } catch (error) {
      feedback.fail(error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8 flex flex-col gap-8 max-w-3xl mx-auto w-full"
    >
      <PageHeader eyebrow="Club" title="创建社团" />

      <Surface>
        <SectionTitle icon={<Building2 size={20} />} title="基础信息" />

        <form
          onSubmit={submit}
          className="grid grid-cols-1 md:grid-cols-2 gap-5"
        >
          <Field label="社团名称">
            <input
              className={inputClassName}
              value={name}
              onChange={(event) => setName(event.target.value)}
              maxLength={128}
              required
            />
          </Field>

          <Field label="社团类别">
            <select
              className={selectClassName}
              value={category}
              onChange={(event) => setCategory(event.target.value as Category)}
            >
              {CATEGORY_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </Field>

          <div className="md:col-span-2">
            <Field label="一句话简介" hint="最多 50 字。">
              <input
                className={inputClassName}
                value={summary}
                onChange={(event) => setSummary(event.target.value)}
                maxLength={50}
                required
              />
            </Field>
          </div>

          <div className="md:col-span-2">
            <Field label="详细介绍" hint="最多 400 字。">
              <textarea
                className={textareaClassName}
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                maxLength={400}
                required
              />
            </Field>
          </div>

          <div className="md:col-span-2">
            <FileUploadField
              label="社团 Logo"
              scene="club_logo"
              value={logoUri}
              onChange={setLogoUri}
              accept="image/*"
            />
          </div>

          {feedback.message && (
            <div className="md:col-span-2">
              <StatusMessage value={feedback.message} tone={feedback.tone} />
            </div>
          )}

          <div className="md:col-span-2 flex justify-end">
            <PrimaryButton type="submit" loading={isSubmitting}>
              <Save size={18} /> 提交创建
            </PrimaryButton>
          </div>
        </form>
      </Surface>
    </motion.div>
  );
}
