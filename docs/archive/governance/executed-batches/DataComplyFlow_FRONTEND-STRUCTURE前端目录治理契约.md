# DataComplyFlow FRONTEND-STRUCTURE 前端目录治理契约

> 状态：completed
> 执行日期：2026-07-17
> 范围：`frontend/` 的目录边界、活动入口、测试分布、生成式 UI 集成、本地生成物和高置信度不可达源码。

## 1. 执行原则

本批遵循“正确 → 简洁 → 补强”。只删除同时满足以下条件的资产：

1. 不可从 `src/main.tsx` 的静态或动态导入图到达；
2. 无页面路由、脚本、测试或其他仓库代码消费者；
3. 删除不改变 API 路径、请求响应、状态模型与页面行为；
4. 前端测试和生产构建在删除后通过。

本批不拆分大型组件、不重写 CSS、不迁移业务逻辑、不优化 bundle 算法，也不整理生成式 UI 的内部组件命名。

## 2. 修改前事实基线

- `frontend/src/`：191 个源码/样式文件，静态入口图可达 169 个；
- 静态不可达 22 个，其中 4 个是测试文件、测试初始化和类型声明等合法例外；
- `src/integrations/superdesign002/`：被 `/superdesign/002` 活动路由调用，不能整体删除；
- `frontend/tmp/`：162 个文件、约 9.05 MB，内容为 2026-06 模型比较脚本、Trace、报告和上传副本；无活动代码消费者且已被 Git 忽略；
- `dist/`、`node_modules/`、`*.tsbuildinfo` 均未被 Git 追踪；
- `public/media/homepage2.mp4` 无源码、样式或文档消费者；`homepage.mp4` 仍由落地页使用。

## 3. 删除与保留

### 3.1 删除

- 18 个无消费者源码文件：旧认证按钮、旧引用卡片、旧运行面板/适配器、完整未接入的 `resource-explorer` 组件组，以及生成式 UI 自带但未使用的独立入口；
- 未引用静态资源 `public/media/homepage2.mp4`；
- 本地 `tmp/`、`dist/` 与 `*.tsbuildinfo` 生成物。

### 3.2 保留

- `src/main.tsx`、`src/App.tsx` 与全部活动页面/组件；
- `src/lib/module-adapter.ts` 作为当前模块调用权威适配器；
- `TraceProbe.tsx`，因为它由 `main.tsx` 的显式查询参数入口调用；
- 两个就近测试文件、`src/test/setup.ts` 和 `src/types/jsx-modules.d.ts`；
- `superdesign002/Component.jsx`、其完整活动依赖树和隔离样式；
- `node_modules/` 本地依赖缓存，不进入 Git，也不计入源码结构。

## 4. 修改后结构结论

- `pages/` 只承载路由级页面；
- `components/` 只保留当前页面或组件树能够到达的组件；
- `lib/` 删除与 `module-adapter.ts` 重复且无消费者的旧 API 路径；
- 测试采用就近 `*.test.*`，公共初始化集中在 `src/test/setup.ts`；
- 生成式 UI 保持在 `integrations/` 隔离边界，不伪装成普通自研公共组件；
- 构建产物、依赖和实验运行物由 `.gitignore` 排除。

修改后静态入口图中，除测试、测试初始化和类型声明外，不再存在高置信度不可达源码。

## 5. 验收结果

```text
npm test
2 test files passed
6 tests passed

npm run build
tsc -b passed
vite build passed
432 modules transformed
```

构建仍提示 `WorkspacePage` 与 `SuperDesign002Page` chunk 超过 500 kB。该提示不影响本批正确性，记录为后续性能优化事项，不在结构清理阶段通过业务重写解决。

## 6. 回退条件

如人工审查发现被删除组件存在未纳入仓库的外部引用，应只恢复对应文件并补充消费者证据；不得因此整体回滚本批其他已验证清理。
