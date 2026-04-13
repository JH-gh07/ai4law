# AI4Law 前端改版信息架构（科研蓝 V1）

## 1) 信息架构

- `Landing`
- `ModeSelectModal`
- `CreateWorkspaceModal`
- `WorkspaceShell`
- `OnboardingOverlay`

状态流：
- Landing -> 点击主 CTA -> ModeSelectModal
- ModeSelectModal -> 选模式 -> CreateWorkspaceModal
- CreateWorkspaceModal -> 创建成功 -> WorkspaceShell
- 首次进入 WorkspaceShell -> OnboardingOverlay

## 2) 页面布局说明

- 首页：
  - 左侧：叙事型标题、说明、主次 CTA
  - 右侧：关键能力 KPI 玻璃卡
- 工作区：
  - 顶部：全局状态与折叠控制
  - 左栏：证据目录（长期素材）
  - 中栏：主工作面（真实 API 模块运行台 + JSON 编辑）
  - 右栏：持续在线辅助流（不是一次性弹窗）

## 3) 视觉 Token 建议

颜色：
- 主色：`#356fca`（scientific-500）
- 深主色：`#1f457f`（scientific-700）
- 纸面底色：`#f3f6fa`
- 面板玻璃：`rgba(255,255,255,0.64)`

圆角：
- 大容器：`30px`
- 中卡片：`18px`
- 胶囊按钮：`999px`

阴影：
- 玻璃层：`0 12px 38px rgba(21,43,76,0.16)`
- 轻阴影：`0 8px 24px rgba(26,41,67,0.10)`

排版：
- Display：`Noto Serif SC` / `Source Serif 4`
- Body：`Source Sans 3`
- Eyebrow 使用全大写 + 高 tracking

## 4) 关键组件清单

- `TopNav`：语言切换、返回首页
- `LandingPage`：叙事入口 + 双 CTA
- `ModeSelectModal`：模式决策
- `CreateWorkspaceModal`：任务创建
- `WorkspaceShell`：三栏操作系统壳
- `OnboardingOverlay`：步骤引导

## 5) 桌面与移动端策略

- 桌面：三栏并存，保证长期停留效率
- 平板/移动：三栏堆叠为单列，顶部保留关键控制
- 中间工作区始终优先占用最大面积
- 模态宽度自适应 `min(860px, 100%)`

## 6) React + Tailwind 组件结构建议

```text
frontend/src
  App.tsx
  lib/
    i18n.ts
    language.tsx
  components/
    common/
      TopNav.tsx
      ModalShell.tsx
    landing/
      LandingPage.tsx
    modals/
      ModeSelectModal.tsx
      CreateWorkspaceModal.tsx
    workspace/
      WorkspaceShell.tsx
    onboarding/
      OnboardingOverlay.tsx
  styles/
    tokens.css
    app.css
```

下一步接入建议：
- 中栏已接 diagnosis/assessment/scc/pipia/cn_flow 同步接口
- 右栏接入对齐告警与证据链实时提示
- Onboarding 加入目标区域高亮与完成条件判断
