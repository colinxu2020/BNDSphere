## API

### /users

#### GET /users/me/clubs/

返回 `list[UserClubMembership]`：`{membership, club: ClubSummary}`，即当前用户在每个社团中的角色与该社团的摘要（Summary 档，见 ADR-0001）

需登录；包含 `pending` / `member` / `president` / `vice_president`，不包含 `left`

`ClubSummary` 含 `president`（单值，可为空）与 `vice_presidents`（列表），二者通过针对 `membership in (president, vice_president)` 的定向查询按 `club_id` 批量取得；不装载成员、活动、记录等任何集合

首页"我加入的社团 / 我的社团活动"与工作台"我管理的社团"均由此接口推出（后者按 `president` / `vice_president` 过滤）；原 `GET /clubs/managed/` 已删除

### /auth

### /clubs

#### GET /clubs/refs/

| 参数   | 类型 | 描述                                            |
| ------ | ---- | ----------------------------------------------- |
| search | str  | 可选，trigram 模糊搜索（与 `GET /clubs/` 相同） |

返回 `Page[ClubRef]`（仅 `id`、`name`），用于下拉选择与被其它实体内嵌引用（Ref 档，见 ADR-0001）

公开可访问，只返回 `status=normal` 的社团；不装载成员、活动、记录等任何关系集合

#### GET /clubs/{club_id}/

| 参数    | 类型 | 描述                |
| ------- | ---- | ------------------- |
| club_id | int  | 被获取的社团的 `id` |

获取社团基础信息（名称，分类，概要，描述，logo_uri，创建时间，社团星级）

只能获取 `status=normal` 的社团的信息

#### GET /clubs/{club_id}/members :construction:

获取社团成员列表
