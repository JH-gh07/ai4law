# DataComplyFlow Review 恢复任务空间归并本地验收

## 结论

本地已修复恢复数据造成的重复任务空间问题。远程环境未连接，未执行部署。

## 真实问题

Review 的后端异步任务 ID 与前端任务空间 ID 可能不同。恢复接口会同时返回：

- 原任务空间及其运行记录；
- 只有报告记录时，按报告 `owner_id` 推导出的恢复任务空间。

前端原逻辑仅按 `taskSpace.id` 去重，因此同一条运行可能出现两张卡：原工作区显示运行结果，异步任务 ID 对应的恢复卡显示“尚未运行”。报告也可能挂在后一张卡上。

## 修复逻辑

1. 先按 `asyncTaskId` 合并运行记录，终态记录优先覆盖本地运行中记录。
2. 如果运行的 `taskSpaceId` 已经对应一个现有工作区，且 `asyncTaskId` 只是恢复接口推导出的临时工作区 ID，则移除临时工作区。
3. 将临时工作区 ID 下的恢复产物重新归属到运行实际所属的工作区。
4. 不删除后端任务、报告或历史数据；只在前端恢复合并阶段纠正展示归属。

## 验证

### 自动测试

```text
frontend/src/lib/app-store.test.ts: 2 passed
frontend npm run build: passed
```

新增测试覆盖：

- 原工作区与异步任务 ID 同时存在时只保留原工作区；
- 恢复产物从临时 ID 映射回原工作区。

### 真实本地数据

已确认本地成功 Review 任务 `234d7706-9078-4d32-9fe8-4089c2d69864` 状态为 `COMPLETED`，生成 `review_report.docx` 和 `review_report.pdf`。本修复用于避免该成功结果在刷新恢复时被拆成独立任务卡。

### 未完成项

当前 shell 的 Anaconda Python 在启动 `pytest` 前读取 site 配置时发生 ASCII locale 解码错误，后端测试尚未实际执行：

```text
UnicodeDecodeError: 'ascii' codec can't decode byte 0xe5 ...
```

需要在修复本机 Python/locale 后重跑后端 Review 和事件测试。浏览器截图工具在当前 shell 不可用，因此“执行流”最终视觉截图仍待使用可用浏览器环境验收。

## 相关代码

- `frontend/src/lib/app-store.tsx`
- `frontend/src/lib/app-store.test.ts`

