import React, { useState } from "react";
import { motion } from "motion/react";
import {
  Bell,
  CalendarDays,
  RefreshCw,
  Shield,
  Users,
} from "@/src/components/ui/Icons";
import { client } from "../api/client";
import { useActionFeedback } from "../lib/useActionFeedback";
import {
  PageHeader,
  SecondaryButton,
  StatusMessage,
} from "../components/ui/AppPrimitives";
import { cn } from "../lib/utils";
import { RefreshContext } from "./admin/context";
import { UsersAdmin } from "./admin/UsersAdmin";
import { ClubsAdmin } from "./admin/ClubsAdmin";
import { TermsAdmin } from "./admin/TermsAdmin";
import { ActivitiesAdmin } from "./admin/ActivitiesAdmin";
import { AnnouncementsAdmin } from "./admin/AnnouncementsAdmin";

type SectionId = "users" | "clubs" | "terms" | "activities" | "announcements";

const sections: { id: SectionId; label: string; icon: React.ReactNode }[] = [
  { id: "users", label: "用户", icon: <Users size={16} /> },
  { id: "clubs", label: "社团", icon: <Shield size={16} /> },
  { id: "terms", label: "学期", icon: <CalendarDays size={16} /> },
  { id: "activities", label: "大型活动", icon: <CalendarDays size={16} /> },
  { id: "announcements", label: "公告", icon: <Bell size={16} /> },
];

export function Admin() {
  const [activeSection, setActiveSection] = useState<SectionId>("users");
  const feedback = useActionFeedback("info");
  const [isRefreshing, setIsRefreshing] = useState(false);

  const checkHealth = async () => {
    feedback.clear();
    feedback.inform("正在检查服务状态...");
    try {
      const { error, response } = await client.GET("/health", {
        parseAs: "text",
      });
      if (response.ok) {
        feedback.succeed(`服务正常（HTTP ${response.status}）`);
      } else {
        feedback.fail(error || `健康检查失败（HTTP ${response.status}）`);
      }
    } catch (error) {
      feedback.fail(error || "无法连接后端健康检查接口，请确认后端服务正在运行");
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8 grid min-w-0 gap-6"
    >
      <PageHeader
        eyebrow="Admin"
        title="管理员控制台"
        action={
          <SecondaryButton type="button" onClick={checkHealth}>
            <RefreshCw size={16} /> 健康检查
          </SecondaryButton>
        }
      />

      {feedback.message && <StatusMessage value={feedback.message} tone={feedback.tone} />}

      <div className="grid min-w-0 gap-5 lg:grid-cols-[220px_minmax(0,1fr)]">
        <aside className="h-fit rounded-md border border-edge bg-surface p-2">
          {sections.map((section) => (
            <button
              key={section.id}
              type="button"
              onClick={() => setActiveSection(section.id)}
              className={cn(
                "flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm font-semibold transition",
                activeSection === section.id
                  ? "bg-surface-inverted text-content-on-inverted"
                  : "text-content-muted hover:bg-surface-sunken",
              )}
            >
              {section.icon}
              {section.label}
            </button>
          ))}
        </aside>

        <section className="min-w-0 overflow-hidden rounded-md border border-edge bg-surface p-5">
          <RefreshContext.Provider
            value={{
              isRefreshing,
              refreshStart: () => setIsRefreshing(true),
              refreshEnd: () => setIsRefreshing(false),
              setResult: feedback.report,
            }}
          >
            {activeSection === "users" && <UsersAdmin />}
            {activeSection === "clubs" && <ClubsAdmin />}
            {activeSection === "terms" && <TermsAdmin />}
            {activeSection === "activities" && <ActivitiesAdmin />}
            {activeSection === "announcements" && <AnnouncementsAdmin />}
          </RefreshContext.Provider>
        </section>
      </div>
    </motion.div>
  );
}
