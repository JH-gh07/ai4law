# 中国模块 Token 实测对比

| 模块 | Provider | Model | Prompt Tokens | Completion Tokens | Total Tokens | LLM Calls | 是否成功 | 备注 |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| diagnosis | siliconflow | deepseek-ai/DeepSeek-V3.2 | 373 | 174 | 547 | 2 | PASS | scc_or_certification |
| assessment | siliconflow | deepseek-ai/DeepSeek-V3.2 | 0 | 0 | 0 | 0 | PASS |  |
| pipia | siliconflow | deepseek-ai/DeepSeek-V3.2 | 0 | 0 | 0 | 0 | PASS |  |
| diagnosis | tencent_hunyuan | hunyuan-lite | 365 | 124 | 489 | 2 | PASS | scc_or_certification |
| assessment | tencent_hunyuan | hunyuan-lite | 0 | 0 | 0 | 0 | PASS |  |
| pipia | tencent_hunyuan | hunyuan-lite | 0 | 0 | 0 | 0 | PASS |  |
