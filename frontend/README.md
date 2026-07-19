# DataComplyFlow Frontend

本目录是 DataComplyFlow 当前活动的 React 单页应用。前端负责页面路由、任务工作台、运行状态展示和后端 API 调用；业务判断、报告生成与持久化仍由后端负责。

## 技术栈

- React 18 + TypeScript
- Vite
- React Router
- Vitest + Testing Library
- Tailwind/PostCSS（含现有项目样式）

Node.js 版本要求见 `.nvmrc` 和 `package.json#engines`，依赖版本以 `package-lock.json` 为准。

## 目录边界

| 路径 | 职责 |
|---|---|
| `src/main.tsx` | 浏览器入口；装配正式应用或显式启用的 Trace Probe |
| `src/App.tsx` | 应用 Provider、页面路由和全局 UI 装配 |
| `src/pages/` | 路由级页面 |
| `src/components/` | 被页面或工作台复用的界面组件 |
| `src/lib/` | API 客户端、状态、模块注册、任务模板和前端领域类型 |
| `src/integrations/` | 外部或生成式 UI 的隔离集成区，不作为公共组件目录 |
| `src/styles/` | 当前全局设计 token 与应用样式 |
| `src/test/` | Vitest 公共测试初始化；测试文件与被测模块就近放置 |
| `public/` | 被活动页面直接引用的静态资源 |

## 真实入口关系

```text
index.html
→ src/main.tsx
→ src/App.tsx
→ React Router pages
→ components / lib adapters
→ /api/v1（Vite 本地代理到 127.0.0.1:8000）
```

`?trace_probe=1` 是显式的开发诊断入口，由 `src/main.tsx` 装配，不属于不可达遗留文件。


## 开发与验证

```bash
cd frontend
npm install
npm run dev
npm test
npm run build
```

- `npm test` 运行全部前端测试；
- `npm run build` 同时执行严格 TypeScript 检查和生产构建；
- 测试文件采用 `*.test.ts` / `*.test.tsx`，与被测模块就近放置；
- `src/test/setup.ts` 仅提供共享测试环境初始化。

## 生成与本地资产

以下内容不属于版本库源码，由 `.gitignore` 管理：

- `node_modules/`：本地依赖安装目录；
- `dist/`：生产构建产物；
- `*.tsbuildinfo`：TypeScript 增量构建缓存；
- `tmp/`：历史实验、Trace、上传副本或一次性比较结果。

不得把凭据、用户上传件、运行 Trace 或模型实验结果写入 `src/` 或提交到 Git。