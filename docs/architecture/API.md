## API

### /users

### /auth

### /clubs

#### GET /clubs/refs/

| 参数   | 类型 | 描述                                            |
| ------ | ---- | ----------------------------------------------- |
| search | str  | 可选，trigram 模糊搜索（与 `GET /clubs/` 相同） |

返回 `Page[ClubRef]`（仅 `id`、`name`），用于下拉选择与被其它实体内嵌引用（Ref 档，见 ADR-0001）

公开可访问，只返回 `status=normal` 的社团；不装载成员、活动、记录等任何关系集合

#### GET /clubs/{club_id}/activities/refs/

返回 `list[ClubActivityRef]`，每项仅含 `id`、`name`，不分页。
按活动开始时间倒序、ID 倒序排列；不存在的社团返回 `CLUB_NOT_FOUND`。
可见性与现有 `GET /clubs/{club_id}/activities/` 一致：匿名可访问，
不按社团状态过滤。查询仅获取引用字段，不装载活动详情或关联集合。

#### GET /clubs/{club_id}/

| 参数    | 类型 | 描述                |
| ------- | ---- | ------------------- |
| club_id | int  | 被获取的社团的 `id` |

获取社团基础信息（名称，分类，概要，描述，logo_uri，创建时间，社团星级）

只能获取 `status=normal` 的社团的信息

#### GET /clubs/{club_id}/members :construction:

获取社团成员列表
