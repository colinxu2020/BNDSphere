import type {
  AuditStatusEnum,
  ClubCategoryEnum,
  ClubMembershipEnum,
  ClubStarLevelEnum,
  ClubStatusEnum,
  GeneralActivityLevelEnum,
  ParticipationTypeEnum,
  RoleEnum,
} from '../../client';

export const roleLabels: Record<RoleEnum, string> = {
  ban: '封禁',
  user: '普通用户',
  'union of associations': '社联',
  admin: '管理员',
  dev: '开发者',
};

export const adminRoleLabels = roleLabels;

export const clubCategoryLabels: Record<ClubCategoryEnum, string> = {
  sports: '体育',
  humanity: '人文',
  arts: '艺术',
  science: '科学',
  charity: '公益',
  business: '商业',
  campus: '校园',
  other: '其他',
};

export const clubStatusLabels: Record<ClubStatusEnum, string> = {
  unreviewed: '未审核',
  normal: '正常',
  archived: '已归档',
};

export const clubStarLabels: Record<ClubStarLevelEnum, string> = {
  none: '无评级',
  one_star: '一星',
  two_star: '二星',
  three_star: '三星',
  four_star: '四星',
  five_star: '五星',
  honorary: '荣誉社团',
};

export const generalActivityLevelLabels: Record<GeneralActivityLevelEnum | 'all', string> = {
  all: '全部级别',
  school: '校级',
  large: '大型',
  sua: '社联',
};

export const participationTypeLabels: Record<ParticipationTypeEnum, string> = {
  participate_only: '普通参与',
  organize: '承办/组织',
};

export const auditStatusLabels: Record<AuditStatusEnum, string> = {
  pending: '待审核',
  approved: '已通过',
  rejected: '已拒绝',
};

export const membershipLabels: Record<ClubMembershipEnum, string> = {
  pending: '待审核',
  member: '成员',
  president: '社长',
  'vice president': '副社长',
  left: '已退出',
};

export function getEnumLabel<T extends string>(
  map: Record<T, string>,
  value: string | null | undefined,
): string {
  if (!value) return '';
  return map[value as T] || value;
}

export function getGeneralActivityBadgeVariant(level: string): 'default' | 'secondary' | 'outline' {
  if (level === 'large') return 'secondary';
  if (level === 'sua') return 'outline';
  return 'default';
}
