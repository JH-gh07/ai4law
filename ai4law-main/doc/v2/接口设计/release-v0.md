# v0 打包与演示说明（T-REL-01）

## 1. 目标
提供可复现的 v0 交付流程：
1. 一键冒烟校验  
2. 产物打包归档  
3. 演示命令清单  

## 2. 打包命令
```bash
bash scripts/release_v0_package.sh
```

产出：
- `dist/ai4law_v0_<timestamp>.tar.gz`
- 包内包含：`backend/`、`pyproject.toml`、`README.md`、`doc/v2/plan.md`、演示与QA脚本、`release_manifest.txt`

## 3. 演示命令
```bash
bash scripts/demo_v0.sh
```
脚本会输出标准演示步骤：
- 启动服务
- health 检查
- 创建任务
- 查询状态 / 产物 / 审计

## 4. 发布前检查
1. 当前分支测试通过：`bash scripts/qa_v0_smoke.sh`
2. 基准对比通过：`bash scripts/qa_v0_baseline.sh`
3. 前端联调检查通过：`bash scripts/frontend_v0_linkage_check.sh`
4. 计划文档状态同步：`doc/v2/plan.md`
5. Git 存档完成（至少 1 条 commit）
