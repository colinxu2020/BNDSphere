# BNDSphere 文档

BNDSphere 是一个校园社团管理平台。后端：FastAPI + SQLAlchemy 2.x（异步）+ PostgreSQL；前端：React 19 + TypeScript + Vite，见 `frontend/`。

## 后端文档

- [快速开始](getting-started.md) —— 本地开发环境搭建（Docker Compose）、测试、代码检查
- [架构概览](architecture/overview.md) —— 分层结构、审核/核验模式、文件上传流程
- [数据库架构](architecture/database.md) —— 全部表结构、枚举、ER 图
- [API 参考](architecture/API.md) —— 按路由分组的接口清单
- [业务流程](business_process.md) —— 关键业务流程的时序描述

## 其它

前端目前没有独立的架构文档；参见仓库根目录 `CLAUDE.md` 中 "Frontend" 一节的概要说明，或直接阅读 `frontend/src/`。
