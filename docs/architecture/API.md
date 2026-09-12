## API

### /users

### /auth

### /clubs

#### GET /clubs/{club_id}/

| 参数    | 类型 | 描述                |
| ------- | ---- | ------------------- |
| club_id | int  | 被获取的社团的 `id` |

获取社团基础信息（名称，分类，概要，描述，logo_uri，创建时间，社团星级）

只能获取 `status=normal` 的社团的信息

#### GET /clubs/{club_id}/members :construction:

获取社团成员列表
