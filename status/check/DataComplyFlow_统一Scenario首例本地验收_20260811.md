# DataComplyFlow 统一 Scenario 首例本地验收

> 日期：2026-08-11
> 对应方案：`status/todo/DataComplyFlow_前端与CLI案例统一及Trace可视化改造方案_20260811.md`
> 范围：阶段 3 第一条纵向切片；仅本地，未连接远程，未部署

## 已完成

首个统一案例已建立：

```text
benchmarks/cases/us_14117/geneguard_genomic_red/
  scenario.json
  expected.json
```

同一份 `scenario.json` 当前有两个真实消费者：

```text
scenario.request
├── 前端：转换为 formDefaults → 现有 builder → HTTP payload
└── CLI：scenario_path → 后端 US14117Request → US14117Service
```

前端测试要求 builder 生成的完整 payload 与 `scenario.request` 深度相等。CLI 的 `backend/tests/us_14117/cases/01_minimal.json` 已删除内联 `input`，只保留 `scenario_path` 和断言。

## 新增门禁

- `scenario_path` 必须位于仓库内；
- scenario 必须存在并包含非空 `request`；
- 一个 CLI 案例不得同时声明 `input` 和 `scenario_path`；
- 未迁移的旧案例继续使用内联 `input`，支持逐例迁移。

## 验证结果

```text
共享红灯 CLI：PASS，22/22 断言
Traffic light：RED
llm_calls=0，tokens=0
Trace：25 个事件，实时输出与落盘保留
前端共享 payload 测试：18/18 passed
前端 build：通过
后端 harness 与门禁测试：48 passed
case parity：通过
```

CLI 运行目录：

```text
runs/us_14117/20260811_184540_451667_01_minimal
```

提交：

```text
b328ce1 feat(cases): share EO 14117 red scenario
```

## 尚未完成

- 目前只有 EO 14117 红灯案例实现前端与 CLI 事实同源；黄灯、绿灯及其他模块仍未迁移。
- `expected.json` 已保存正式预期，但 CLI 强断言仍在案例壳中，下一步需让门禁同时校验二者，消除预期重复。
- `cn_flow` 尚未直接从该 scenario 生成旧请求并与直接 US14117Request 做语义等价验证。
- 本地 HTTP、SSE 和浏览器验收尚未执行。

## 结论

共享场景方案已经通过一个真实业务案例证明可行，但阶段 3 远未完成。主方案继续保留在 `status/todo/`。
