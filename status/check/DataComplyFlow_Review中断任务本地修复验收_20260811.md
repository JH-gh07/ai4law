# DataComplyFlow Review 中断任务本地修复验收

> 日期：2026-08-11
> 范围：文档专项智能审查任务重启后长期显示运行中
> 目标任务：`a455fb5f-0a40-42ad-b4f3-ccdb361862ac`
> 代码提交：`866fa2c`
> 远程部署：未执行

## 一、问题事实

目标任务在本地数据库中长期停留于：

```text
status=REVIEWING
progress=57
updated_at=2026-08-10 10:03:05
```

Review 后台任务由当前后端进程内的线程执行。后端重启后线程消失，但数据库中的非终态状态没有收尾，导致前端持续轮询并显示 `RUNNING · REVIEW`。

## 二、修复逻辑

应用完成数据库初始化后，统一检查上一个进程遗留的执行中 Review 任务，并将以下状态收尾为 `FAILED`：

```text
PREPARING
SEGMENTING
CLASSIFYING
MISSING_CHECK
REVIEWING
CROSS_DOC_CHECK
AGGREGATING
RENDERING
```

`CREATED` 和 `UPLOADED` 不处理，因为任务尚未开始执行，仍可继续上传或提交分析。

前端原有全局轮询收到 `FAILED` 后，会写入结束时间、停止轮询并显示失败及“重新运行”入口，因此本次不需要增加第二套前端状态逻辑。

## 三、目标任务结果

修复代码触发本地后端自动重载后，数据库状态为：

```text
id=a455fb5f-0a40-42ad-b4f3-ccdb361862ac
status=FAILED
progress=57
```

任务、上传文件和历史记录均保留，没有执行删除操作。

## 四、自动化验证

执行：

```bash
uv run pytest backend/api/v1/tests/test_review_async.py backend/api/v1/tests/test_me_scope.py -q
```

结果：

```text
13 passed
```

新增回归场景验证：

- 第一个应用进程留下 `REVIEWING / 57%` 任务；
- 第二个应用进程启动后，同一任务状态变为 `FAILED / 57%`；
- 状态 API 返回 `FAILED`；
- `UPLOADED` 任务不会被误改为失败。

## 五、验收结论

- [x] 目标任务不再永久显示运行中。
- [x] 后端重启后会收尾 Review 执行中任务。
- [x] 未开始执行的任务不受影响。
- [x] 历史记录和上传文件保留。
- [x] 本地专项回归通过。
- [ ] 独立浏览器未携带用户登录态，未取得登录后截图。
- [ ] 远程部署未执行。
