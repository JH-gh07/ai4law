# 中国模块 Token 实测对比

| 模块 | Provider | Model | Prompt Tokens | Completion Tokens | Total Tokens | LLM Calls | 是否成功 | 备注 |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| diagnosis |  |  | 0 | 0 | 0 | 0 | FAIL | ValueError: Active provider is disabled: siliconflow |
| assessment |  |  | 0 | 0 | 0 | 0 | FAIL | ValueError: Active provider is disabled: siliconflow |
| pipia |  |  | 0 | 0 | 0 | 0 | FAIL | TypeError: NoneType takes no arguments |
| diagnosis | tencent_hunyuan | hunyuan-lite | 0 | 0 | 0 | 0 | PASS | scc_or_certification |
| assessment | tencent_hunyuan | hunyuan-lite | 0 | 0 | 0 | 0 | PASS |  |
| pipia |  |  | 0 | 0 | 0 | 0 | FAIL | TypeError: NoneType takes no arguments |
