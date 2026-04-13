# raw 字段表（由 addition PNG 转写）

本目录用于承接 `doc/v2/addition/*.png` 中的表格内容，转成开发可直接使用的结构化原始表。

## 文件
- `module_input_fields.csv`：各模块输入字段与审查项（2.2/2.3/3.2/3.3/3.4/4.1/4.2）
- `module_input_fields.json`：上述 CSV 的 JSON 版本
- `module_output_structure.csv`：当前可识别的输出章节映射（已含 4.2，标注 4.1 缺口）
- `module_output_structure.json`：上述 CSV 的 JSON 版本

## 来源
- `doc/v2/addition/2.2.1.png`
- `doc/v2/addition/2.3.1.png`
- `doc/v2/addition/3.2.png`
- `doc/v2/addition/3.3.png`
- `doc/v2/addition/3.4.png`
- `doc/v2/addition/4.1.png`
- `doc/v2/addition/4.1.2.png`
- `doc/v2/addition/4.2.png`
- `doc/v2/addition/4.2.2.png`

## 注意
1. 本批字段为截图转写，`confidence=中` 的项建议由业务同学二次复核。
2. `4.1` 仍缺输出章节映射图，暂无法形成官方输出模板结构。
3. 当官方 docx 模板解析完成后，应回写并提升对应字段置信度。
