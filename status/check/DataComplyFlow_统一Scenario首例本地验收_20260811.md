# DataComplyFlow 统一 Scenario 阶段验收

> 日期：2026-08-11
> 对应方案：`status/todo/DataComplyFlow_前端与CLI案例统一及Trace可视化改造方案_20260811.md`
> 范围：阶段 3 第一条纵向切片；仅本地，未连接远程，未部署

## 已完成

目前已建立两条统一案例：

```text
benchmarks/cases/us_14117/geneguard_genomic_red/
  scenario.json
  expected.json
benchmarks/cases/us_14117/geneguard_geolocation_yellow/
  scenario.json
  expected.json
```

同一份 `scenario.json` 当前有两个真实消费者：

```text
scenario.request
├── 前端：转换为 formDefaults → 现有 builder → HTTP payload
└── CLI：scenario_path → 后端 US14117Request → US14117Service
```

前端测试要求两个 builder 生成的完整 payload 与各自 `scenario.request` 深度相等。CLI 的 `01_minimal` 和 `02_geolocation_yellow` 已删除内联 `input` 和断言，分别只保留 `scenario_path`、`expected_path`。

## 新增门禁

- `scenario_path` 必须位于仓库内；
- scenario 必须存在并包含非空 `request`；
- 一个 CLI 案例不得同时声明 `input` 和 `scenario_path`；
- 未迁移的旧案例继续使用内联 `input`，支持逐例迁移。

## 验证结果

```text
共享红灯 CLI：PASS，22/22 断言，Traffic light=RED
共享黄灯 CLI：PASS，22/22 断言，Traffic light=YELLOW
llm_calls=0，tokens=0；每条案例 Trace=25 个事件
前端共享 payload 测试：19/19 passed
前端全量测试：149 passed，2 skipped；build 通过
后端相关测试：91 passed
CLI 全量：21 PASS / 0 FAIL，446 leaf checks
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
3e8df7d feat(cases): share EO 14117 red expectations
092daa7 feat(cases): share EO 14117 yellow scenario
2050324 test(cn-flow): verify shared EO scenario parity
```

## 尚未完成

- 目前只有 EO 14117 红灯、黄灯实现前端与 CLI 事实同源；绿灯及其他模块仍未迁移。
- 红灯、黄灯的 CLI 强断言已从案例壳迁移到各自 `expected.json`，门禁和 runner 均读取共享预期。
- `cn_flow` 已完成红灯、黄灯共享 scenario 的核心事实和灯号等价测试，但旧结构丢失字段仍会列入 `lossy_fields`。
- 本地 HTTP、SSE 和浏览器验收尚未执行。

## 结论

共享场景方案已经通过两条真实业务案例证明可行，但阶段 3 仍未完成。主方案继续保留在 `status/todo/`。
