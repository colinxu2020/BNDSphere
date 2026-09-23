# 角色权限

后端角色能力统一声明在 `backend/app/services/policies.py` 的
`ROLE_CAPABILITIES` 中，由 `AccessPolicy.ensure_role_allowed` 与
`AccessPolicy.ensure_club_role_allowed` 共用。调整角色继承或全局通行规则时，
应修改这张表，并验证权限测试。

| 用户角色 | 可满足的全局角色要求 | 可绕过社团成员角色检查 |
| --- | --- | --- |
| `ban` | 无；检查一律先返回 `USER_BANNED` | 否，即使有社长记录 |
| `user` | `user` | 否 |
| `moderator` | `moderator` | 否 |
| `federation_staff` | `federation_staff`、`moderator` | 否 |
| `admin` | 任意（包括空允许列表） | 是 |
| `dev` | 任意（包括空允许列表） | 是 |

这不是按高低排列的角色等级。例如审核员不会自动满足仅允许 `user` 的检查，
社联也不会仅凭全局身份获得社团管理权限。除 `admin`、`dev` 外，社团权限
检查要求调用方提供的成员记录具有允许的成员角色；无成员记录则拒绝。

能力表只统一角色检查，不绕过具体业务流程的状态校验或其他限制。
前端入口可见性仍是独立逻辑（见 issue #90）；后端检查始终是授权依据。
