## API

### User

- [x] 注册
- [x] 登录
- [x] 获取当前用户信息
- [x] 申请编辑当前用户信息（用户名、头像、描述、年级）
- [x] 获取 {user_id} 用户信息（不包括用户角色）
- [ ] 连接企业微信，获取姓名、年级等信息

### Club

- [x] 创建社团（此时创建者自动成为社团社长）
  创建时社团状态为 `unreviewed`，需要 `admin` 审核通过，否则在平台上是查无此社的。
- [x] 查询社团
- [x] 获取社团信息
  `GET /clubs/{club_id}` 返回 `ClubInfo`，已聚合：基本信息 + 社团成员列表 + 社团活动列表 + 社团参加过的大型活动列表。
- [x] 更新社团信息（社长/副社长经 `update-requests` 审核；`admin` 直接 PATCH）
- [ ] 解散社团（社长/副社长申请解散，`admin` 审核通过；`admin` 直接解散社团）
  注：目前无独立解散端点，`admin` 可通过 `PATCH /admin/clubs/{club_id}` 将 `status` 置为 `archived`。
- [x] 加入社团
  加入时状态为 `pending`，需社长/副社长审核通过。
- [x] 审核加入社团请求（社长/副社长，`verifications/club_memberships.py`）
- [x] 退出社团（社长/副社长不能直接退出）

### Club Activities

- [x] 获取 {club_id} 社团的活动列表
- [x] 创建社团活动（社长/副社长，经 `create-requests` + 审核）
- [x] 申请修改社团活动（社长/副社长，经 `update-requests` + 审核）

### General Activities

- [x] 查询大型活动
- [x] 获取大型活动信息
- [x] 创建大型活动（`admin` / 社联）
- [x] 编辑大型活动信息
- [x] 删除大型活动

### Club General Activities

- [x] 创建社团参加大型活动的记录
- [x] 获取 {club_id} 参加大型活动的记录
- [x] 编辑 {club_id} 在 {activity_id} 活动的记录（记录状态应当为 `pending`）

### Joint Activities

- [x] 查询联合活动（公开，仅预审通过）
- [x] 获取联合活动信息
- [x] 创建联合活动（社长/副社长）
- [x] 编辑联合活动（社长/副社长）
- [x] 报名参与联合活动（社长/副社长）
- [x] 归档联合活动（社长/副社长）
- [x] 提交终审（社长/副社长）
- [x] 联合活动预审（社联）
- [x] 联合活动终审（社联）

### Admin

- [x] 编辑 {user_id} 用户信息（包括用户角色）
- [x] 审核创建的社团（`admin` 通过 `PATCH /admin/clubs/{club_id}` 设置 `status`）
- [x] 编辑社团信息
- [x] 管理公告（增删改查）

### Academic Terms

除获取以外的所有功能都需要 `admin`

- [x] 创建学期
- [x] 获取学期列表
- [x] 获取学期信息
- [x] 编辑学期信息
- [x] 删除学期
- [x] 设置 {term_id} 为当前学期

### Star Level

- [x] 查询星级评定申请（公开）
- [x] 获取星级评定申请
- [x] 社团创建星级评定申请（社长）
- [x] 更新星级评定申请（未审核时，社长）
- [x] 预览星级评审结果（社联）
- [x] 评审星级评定申请（社联）
- [x] 计算社团星级评分（star-rating）

### Moderation

- [x] 审核更改用户信息的申请
- [x] 审核社团信息更新申请
- [x] 审核社团活动创建申请
- [x] 审核社团活动修改申请

### Announcements

- [x] 查询公告（公开，`active_only`）
- [x] 创建/编辑/删除公告（`admin`）

### Uploads

- [x] 发起上传（预签名 URL）
- [x] 确认上传（换取可访问 URL）

## Misc

- [ ] 将后端传输时间最小单位改为“天”
