/**
 * Sample content for the DEV-ONLY layout prototypes.
 *
 * Realistic rather than lorem ipsum, because layout decisions turn on real string
 * lengths — a 社团 name is 3 characters and a 大型活动 name is 15, and a layout that
 * only works with even-length placeholder text is not a layout.
 *
 * Dev-only, so it is tree-shaken with the prototypes.
 */
import type { components } from "../api/schema";

type ClubInfo = components["schemas"]["ClubInfo"];
type GeneralActivity = components["schemas"]["GeneralActivityInfo"];
type ClubCategory = components["schemas"]["ClubCategoryEnum"];
type StarLevel = components["schemas"]["ClubStarLevelEnum"];

function makeClub(
  id: number,
  name: string,
  category: ClubCategory,
  star_level: StarLevel,
  summary: string,
  memberCount: number,
): ClubInfo {
  return {
    id,
    name,
    category,
    star_level,
    summary,
    description: summary,
    logo_uri: null,
    created_at: "2026-03-01T08:00:00Z",
    status: "normal",
    members: Array.from({ length: memberCount }, (_, i) => ({
      id: id * 100 + i,
      user_id: id * 100 + i,
      club_id: id,
      membership: i === 0 ? "president" : "member",
      updated_at: "2026-03-01T08:00:00Z",
    })) as ClubInfo["members"],
    club_activities: [],
    general_activity_records: [],
  };
}

export const SAMPLE_CLUBS: ClubInfo[] = [
  makeClub(1, "天文社", "science", "five_star", "观测、天体摄影与每月公开夜话。社员共同维护校园天文台与两台反射式望远镜。", 48),
  makeClub(2, "辩论社", "humanity", "honorary", "议会制与政策辩论，承办市级邀请赛，历年稳定进入四强。", 36),
  makeClub(3, "民乐团", "arts", "four_star", "四十人编制，古筝、二胡、笛箫与打击乐，每学期举办专场音乐会。", 41),
  makeClub(4, "篮球社", "sports", "three_star", "校队选拔与院际联赛组织，每周三次训练。", 62),
  makeClub(5, "金融投资社", "business", "two_star", "模拟投资组合、财报研读与商赛培训，与校友基金合作开展导师制。", 27),
  makeClub(6, "支教志愿社", "charity", "five_star", "对接京郊两所小学的长期课业辅导，累计志愿时长超过三千小时。", 55),
  makeClub(7, "校园媒体中心", "campus", "one_star", "校刊、公众号与活动摄影，负责各类大型活动的影像记录。", 33),
  makeClub(8, "桌游社", "other", "none", "策略与合作类桌游，每周五晚固定开放，欢迎零基础同学。", 19),
];

export const SAMPLE_ACTIVITIES: GeneralActivity[] = [
  {
    id: 11,
    name: "2026 秋季社团招新嘉年华",
    description: "全校六十余个社团集中展示与招新，主会场设在体育馆及东侧广场，包含舞台展演与摊位体验两个环节。",
    level: "school",
    starts_at: "2026-09-05T01:00:00Z",
    ends_at: "2026-09-05T09:00:00Z",
    poster_uri: null,
    article_url: null,
    created_at: "2026-08-12T02:00:00Z",
    club_records: [],
    academic_term: {
      id: 1,
      term_name: "2026-2027 学年第一学期",
      start_date: "2026-09-01",
      end_date: "2027-01-20",
      is_current: true,
    },
  },
  {
    id: 12,
    name: "第十九届校园科技文化节",
    description: "为期两周的科技展评、讲座与工作坊，设机器人对抗、天文观测与生物标本三个专题展区。",
    level: "large",
    starts_at: "2026-10-12T01:00:00Z",
    ends_at: "2026-10-24T09:00:00Z",
    poster_uri: null,
    article_url: null,
    created_at: "2026-08-08T02:00:00Z",
    club_records: [],
    academic_term: {
      id: 1,
      term_name: "2026-2027 学年第一学期",
      start_date: "2026-09-01",
      end_date: "2027-01-20",
      is_current: true,
    },
  },
  {
    id: 13,
    name: "社联换届选举与述职大会",
    description: "各部门述职、候选人答辩与全体社长投票，同步公布下一学年星级评定细则。",
    level: "club_federation",
    starts_at: "2026-09-20T06:00:00Z",
    ends_at: "2026-09-20T10:00:00Z",
    poster_uri: null,
    article_url: null,
    created_at: "2026-08-01T02:00:00Z",
    club_records: [],
    academic_term: {
      id: 1,
      term_name: "2026-2027 学年第一学期",
      start_date: "2026-09-01",
      end_date: "2027-01-20",
      is_current: true,
    },
  },
];

export const SAMPLE_QUEUE = [
  { id: 1, club: "天文社", kind: "星级评价表", status: "pending" as const, at: "8月18日 14:20" },
  { id: 2, club: "辩论社", kind: "活动创建申请", status: "pending" as const, at: "8月18日 11:05" },
  { id: 3, club: "民乐团", kind: "资料修改申请", status: "pending" as const, at: "8月17日 16:42" },
  { id: 4, club: "篮球社", kind: "活动记录", status: "approved" as const, at: "8月16日 09:30" },
  { id: 5, club: "桌游社", kind: "资料修改申请", status: "rejected" as const, at: "8月15日 15:10" },
];

export const SAMPLE_ANNOUNCEMENTS = [
  { id: 1, title: "2026 学年社团星级评定结果公示", at: "8月18日" },
  { id: 2, title: "招新嘉年华摊位申请开放", at: "8月15日" },
  { id: 3, title: "社联换届选举提名开始", at: "8月11日" },
];
