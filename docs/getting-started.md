## 快速开始

### 后端

后端只支持通过 Docker Compose 开发/测试——仓库里没有"脱离 Docker 直接跑 uv/uvicorn"的受支持流程（`uv sync` 装的依赖能跑 `ruff`/`mypy` 这类静态检查，但应用本身需要 Postgres、Docker secrets 等只在 Compose 里配好的环境）。

先决条件：Docker、Docker Compose；仓库根目录执行。

生成本地开发/测试用的 secrets（幂等，重复执行不会覆盖已有文件）：

``` bash
./scripts/gen-secrets.sh
```

构建并启动开发环境（含热重载）：

``` bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

`backend` 容器内监听 `8000` 端口，不直接对宿主机暴露；统一由 `caddy` 反向代理到宿主机 `${CADDY_PORT:-80}`（`infra/Caddyfile.dev`：`/api/*` 转发到 `backend:8000`，其余转发到 Vite dev server），所以本地开发访问 `http://localhost/api/docs`（Swagger UI）、`http://localhost/api/v1/...` 即可。源码通过 volume 挂载到容器内，改代码后 `fastapi dev` 会自动重载。数据库额外映射到 `127.0.0.1:5432`，方便用本地客户端直连调试。

只重建/操作后端相关镜像：

``` bash
docker compose -f docker-compose.yml -f docker-compose.build.yml build postgres backend-dev
```

运行数据库迁移（等价于生产环境应用迁移的方式）：

``` bash
docker compose run alembic-migration                              # alembic upgrade head
docker compose run -e MESSAGE="..." alembic-autorevision           # alembic revision --autogenerate -m "..."
```

#### 后端测试

规范的、基于 Docker 的验收命令：

``` bash
./scripts/gen-secrets.sh
docker compose -f docker-compose.yml -f docker-compose.build.yml build postgres backend-dev
docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile test run test
```

仓库根目录的 `Makefile` 提供了等价的快捷方式：

``` bash
make test     # = 上面三条命令依次执行（secrets → build → test）
```

只跑一部分测试，覆盖 `test` 服务的默认命令：

``` bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile test run test \
  uv run pytest tests/test_auth.py -k test_register_duplicate_username
```

测试套件**必须串行执行**（不能用 `pytest-xdist`）——`backend/tests/conftest.py` 里的 fixture 是 session 级共享的 `test_db` 和 class 级共享的事务。测试运行前会自动创建/清空一个真实的 Postgres `test_db`、配好 `app_user`/`migration_user` 角色与 schema 授权、跑一遍 Alembic 迁移；这也是测试通常要在 `test` 容器里跑（而不是宿主机裸 `pytest`）的原因——它依赖 `/run/secrets` 下的数据库/OSS 密钥。

#### 后端代码检查

以下命令需要本地装好 `uv`（`cd backend` 后执行），不需要 Docker/数据库：

``` bash
uv sync                        # 安装依赖（Python 3.14+, uv 需要能解析 pyproject.toml/uv.lock）
uv run ruff check --fix app
uv run ruff format app
uv run mypy app                 # 严格模式，建议 push 前跑一次
```

### 前端

Node.js 22+

``` bash
cd frontend
npm ci
npm run dev
```

### 提交前检查

在仓库根目录安装 pre-commit 和 pre-push hooks：

``` bash
pre-commit install --install-hooks
```

手动运行完整检查：

``` bash
pre-commit run --all-files
pre-commit run --all-files --hook-stage pre-push
```
