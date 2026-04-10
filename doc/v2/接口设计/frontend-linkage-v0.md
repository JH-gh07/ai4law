# 前端联调验收清单（v0）

## 1. 目标
验证 Streamlit 前端在 v0 阶段的三条链路：
1. 模块入口可达
2. 页面跳转可达
3. 报告下载链路可用（docx/md/pdf/xlsx/zip）

## 2. 检查脚本
- Python：`scripts/frontend_v0_linkage_check.py`
- Shell：`scripts/frontend_v0_linkage_check.sh`

执行：
```bash
bash scripts/frontend_v0_linkage_check.sh
```

日志输出：
- `outputs/qa/frontend_linkage_*.log`
- `outputs/qa/frontend_linkage_check_*.json`

## 3. 检查项
1. Home 页面快捷入口：
- `pages/0_CN_Service_Panel.py`
- `pages/6_Report_Center.py`
- `pages/7_Knowledge_Center.py`
2. 服务面板 cards 对应页面文件存在
3. `render_report_download` 支持 MIME：
- `.docx/.md/.pdf/.xlsx/.zip`
4. 报告中心文件类型筛选支持：
- `.md/.docx/.pdf/.xlsx/.zip`

## 4. 通过标准
- 脚本返回码 `0`
- 所有检查项为 `PASS`

## 5. 说明
- 该检查聚焦前端结构联动，不替代后端功能测试。  
- 后端链路验证仍使用：
  - `scripts/qa_v0_smoke.sh`
  - `scripts/qa_v0_baseline.sh`
