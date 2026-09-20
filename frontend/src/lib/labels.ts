import type { components } from "../api/schema";

export const CATEGORY_OPTIONS: {
  label: string;
  value: components["schemas"]["ClubCategoryEnum"];
}[] = [
  { label: "舞台设计", value: "stage_design" },
  { label: "信息技术", value: "information_technology" },
  { label: "慈善公益", value: "charity" },
  { label: "艺术表演", value: "performing_arts" },
  { label: "社会科学", value: "social_science" },
  { label: "手工制作", value: "handicraft" },
  { label: "文学出版", value: "literature_publishing" },
  { label: "商业经营", value: "business" },
  { label: "艺术设计", value: "art_design" },
  { label: "校园管理", value: "campus_management" },
  { label: "自然科学", value: "natural_science" },
  { label: "语言学习", value: "language_learning" },
  { label: "体育运动", value: "sports" },
  { label: "动漫", value: "anime" },
  { label: "影视新闻传媒", value: "film_news_media" },
];

export const CATEGORY_MAP: Record<components["schemas"]["ClubCategoryEnum"] | "all", string> = {
  stage_design: "舞台设计",
  information_technology: "信息技术",
  charity: "慈善公益",
  performing_arts: "艺术表演",
  social_science: "社会科学",
  handicraft: "手工制作",
  literature_publishing: "文学出版",
  business: "商业经营",
  art_design: "艺术设计",
  campus_management: "校园管理",
  natural_science: "自然科学",
  language_learning: "语言学习",
  sports: "体育运动",
  anime: "动漫",
  film_news_media: "影视新闻传媒",
  all: "全部",
};

export const STAR_LEVEL_OPTIONS: {
  label: string;
  value: components["schemas"]["ClubStarLevelEnum"];
}[] = [
  { label: "无星级", value: "none" },
  { label: "一星社团", value: "one_star" },
  { label: "二星社团", value: "two_star" },
  { label: "三星社团", value: "three_star" },
  { label: "四星社团", value: "four_star" },
  { label: "五星社团", value: "five_star" },
  { label: "荣誉社团", value: "honorary" },
];

export const STAR_LEVEL_MAP: Record<components["schemas"]["ClubStarLevelEnum"], string> = {
  none: "无星级",
  one_star: "一星社团",
  two_star: "二星社团",
  three_star: "三星社团",
  four_star: "四星社团",
  five_star: "五星社团",
  honorary: "荣誉社团",
};

export const CLUB_STATUS_OPTIONS: {
  label: string;
  value: components["schemas"]["ClubStatusEnum"];
}[] = [
  { label: "未审核", value: "unreviewed" },
  { label: "正常运行", value: "normal" },
  { label: "已归档", value: "archived" },
];

export const CLUB_STATUS_MAP: Record<components["schemas"]["ClubStatusEnum"], string> = {
  unreviewed: "未审核",
  normal: "正常运行",
  archived: "已归档",
};

export const ROLE_OPTIONS: {
  label: string;
  value: components["schemas"]["RoleEnum"];
}[] = [
  { label: "已封禁", value: "ban" },
  { label: "普通成员", value: "user" },
  { label: "审核员", value: "moderator" },
  { label: "社联工作人员", value: "federation_staff" },
  { label: "系统管理员", value: "admin" },
  { label: "开发者", value: "dev" },
];

export const ROLE_MAP: Record<components["schemas"]["RoleEnum"], string> = {
  ban: "已封禁",
  user: "普通成员",
  moderator: "审核员",
  federation_staff: "社联工作人员",
  admin: "系统管理员",
  dev: "开发者",
};

export const MEMBERSHIP_MAP: Record<components["schemas"]["ClubMembershipEnum"], string> = {
  pending: "待确认",
  member: "成员",
  president: "社长",
  vice_president: "副社长",
  left: "已退出",
};

export const ACTIVITY_LEVEL_OPTIONS: {
  label: string;
  value: components["schemas"]["GeneralActivityLevelEnum"];
}[] = [
  { label: "校级活动", value: "school" },
  { label: "大型活动", value: "large" },
  { label: "社联活动", value: "club_federation" },
];

export const ACTIVITY_LEVEL_MAP: Record<components["schemas"]["GeneralActivityLevelEnum"], string> =
  {
    school: "校级活动",
    large: "大型活动",
    club_federation: "社联活动",
  };

export const PARTICIPATION_OPTIONS: {
  label: string;
  value: components["schemas"]["ParticipationTypeEnum"];
}[] = [
  { label: "参与", value: "participate_only" },
  { label: "组织", value: "organize" },
];

export const PARTICIPATION_MAP: Record<components["schemas"]["ParticipationTypeEnum"], string> = {
  participate_only: "参与",
  organize: "组织",
};

export const AUDIT_STATUS_OPTIONS: {
  label: string;
  value: components["schemas"]["AuditStatusEnum"];
}[] = [
  { label: "待审核", value: "pending" },
  { label: "已通过", value: "approved" },
  { label: "已驳回", value: "rejected" },
];

export const AUDIT_STATUS_MAP: Record<components["schemas"]["AuditStatusEnum"], string> = {
  pending: "待审核",
  approved: "已通过",
  rejected: "已驳回",
};

export const MODERATION_STATUS_MAP: Record<components["schemas"]["ModerationStatusEnum"], string> =
  {
    pending: "待审核",
    approved: "已通过",
    rejected: "已驳回",
    superseded: "已被替代",
  };

export const VERIFICATION_STATUS_MAP: Record<
  components["schemas"]["VerificationStatusEnum"],
  string
> = {
  pending: "待审核",
  approved: "已通过",
  rejected: "已驳回",
};
