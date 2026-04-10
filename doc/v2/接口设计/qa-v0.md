# v0 冒烟与回归清单（T-QA-01）

## 1. 执行入口
- 脚本：`scripts/qa_v0_smoke.sh`
- 命令：
```bash
bash scripts/qa_v0_smoke.sh
```
- 日志输出目录：`outputs/qa/`

## 2. 冒烟范围
- 统一网关：`/api/v0/tasks` 覆盖 `2.2/2.3/3.2/3.3/3.4/4.1/4.2`
- 产物下载链路：`artifacts + download`
- 审计链路：`/api/v0/tasks/{task_id}/audit`
- 各模块异步链路：`/api/v1/*/generate_async`

## 3. 通过标准
1. `pytest` 返回 0。  
2. 各模块任务状态可达 `COMPLETED`。  
3. 产物字段满足模块要求：  
- 2.x/3.x 至少 `docx + zip`
- 4.x 至少 `docx + pdf + xlsx + zip`
4. audit 返回结构化 `rule_hits`（`rule_id/hit/evidence`）。

## 4. 失败处理
1. 先看 `outputs/qa/*.log`。  
2. 定位失败模块后运行单测文件复现。  
3. 修复后重新执行全量 `qa_v0_smoke.sh`。  
