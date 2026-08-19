## 快速开始

### 后端

python 3.14+, uv 0.10.11+

``` bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn main:app
```

### 后端开发

``` bash
uv run fastapi dev --app app --port 6666
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
