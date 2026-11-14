# Defensive Writing & Expression v3.3

一个刻意制造“GPT 式防御性表达”的中文 Agent Skill：让普通观点提前应付尚未出现的误读，甚至让免责声明需要再被免责声明澄清。

![防御性写作关系图：不能证明、并不等于、不是而是](assets/defensive-writing-map.jpg)

## 核心特性（v3.3）

- **零新增实体约束**：严格区分“有载体句”（如含测试/哈希/合同）与“纯陈述句”（如仅含主观体验或结果对比），高档位递归不再为了凑层数而凭空脑补监控、日志或统计流程。
- **优先级仲裁与短文本降级**：以 `任务与安全 > 0 级退出 > 字数硬上限 > 单点覆盖 > 已有人设 > 防御机制 > 档位默认` 裁决冲突；紧字数约束下自动切换为紧凑同位链（`A ≠ B ≠ C`）以兼顾篇幅与递归层数。
- **增强型离线回归校验（`evaluate.py`）**：在原有表面标记统计基础上，新增 `cases.json` 核心词留存校验（`preserve` recall）、`overrides` / `guardrail` 合规审计，以及 `--batch` 跨样本首尾句式撞车检测。
- **双层误读引擎与内置二次审查**：原观点 → 虚拟误读 → 澄清 → 对澄清的误读 → 元澄清（最多 3 层），内置防复读编辑自检。
- **渐进式上下文加载**：常规 1–3 级仅加载 `SKILL.md`，高递归与诊断评测再按需读取 `references/`。

## v3.3：上下文感知型防御

这次升级处理的是“防御性有了，却没有和语言融合”的问题。典型失败表现是开头和结尾像熟人聊天，中间却突然写成审计公文。现在先保持用户要完成的**真实任务和已有说话方式**，再把过度辩解嵌进词汇、句法、节奏和态度里，而非硬套某个角色的口癖。

- **Rewrite（改写）**：严格保留原句和已有事实；零新增日志、测试、监控等载体，默认单段。
- **Respond（回答）**：先解释问题，再把限定与元澄清交错放在相关观点旁边，不把问答变成完整免责声明。
- **Task（执行）**：先交付可用代码、步骤、方案或回复；禁止用虚构的基线、探针、哈希、门禁、烟测代替修复。
- **Persona（角色层）**：叠加在前三者上，贯穿全文和多轮对话。voice 控制口癖、词序、正式度和身份；style 只控制防御的论证机制。
- **可选参数**：absurdity 0–5 控制小题大做的程度；self_awareness 0–5 控制角色是否意识到自己的过分谨慎；两个参数默认 0。
- **退出**：“直说、不要防御性”立即降到 0 级，不残留“这并不意味着”的尾巴。
- **人格泛化**：角色标签不是台词字典；评判融合程度时看语域、句法、节奏、情绪和社交关系，不能只看某个标志性语气词的出现次数。

### 真实场景调用

```text
沿用刚才轻松的讲解口吻，五级技术递归：解释 scripts/evaluate.py 的功能。
五级，voice=普通朋友，absurdity=5，self_awareness=0：这杯奶茶挺好喝。
以冷淡程序员口吻修复这段 Python；先给正确代码，再用三级技术递归解释边界。
继续聊刚才的问题。（保留上一轮的人设、级别与风格）
现在不要防御性了，正常回答。
```

### 场景目录、回归与语义评审

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
python scripts/evaluate.py --self-test
python scripts/evaluate.py --catalog tests/cases.json --json
python scripts/evaluate.py --batch tests/sample_responses.json --json
```

测试库目前有 **64 例**：原有 22 条短句 + 12 条真实问答 + 12 条角色融合 + 8 组多轮对话 + 10 条复杂边界。角色测试覆盖图书管理员、程序员、朋友、客服、学术作者、叙事人物、英语口语等不同语域；只留 2 例原始角色场景用于定向回归，避免单一角色示例过拟合。为单轮条目填入 response，或为多轮逐项填写 turns[].response 后，才可用 --batch 做表面检查。--catalog 仅校验测试目录，不会生成模型回答，也不等于 64 例通过。

外部语义评审见 references/judge-rubric.md：Rewrite 沿用旧版六维评分；Respond/Task/Persona 可以使用 rubric=context-v3.3，从任务完成度、事实、人设连续性、防御融合、递归逻辑和约束适配六个维度评审。脚本只接收外部评审 JSON，不能替代真实模型或人工理解语义。

## 安装

把整个 `defensive-writing-expression/` 文件夹复制到支持 Agent Skills 的 `skills` 目录；保留下面全部文件。入口为 `SKILL.md`。默认不主动启用，只有用户明确要求此风格才激活。

## 快速调用

```text
三级 GPT 经典型：我觉得这个项目不错。
五级技术递归，误读 6、递归 3：文件哈希校验通过。
五级技术递归：新版本上线后，接口响应快了不少。
50字以内，五级技术递归：接口响应快了不少。
三级，共情 0，和稀泥 0，免责密度 5：Python 容易入门。
```

## 文件结构

```text
defensive-writing-expression/
├── SKILL.md                  # 任务模式、人格泛化、防御融合与短文本降级
├── README.md                 # 使用说明
├── references/
│   ├── patterns.md           # 误读递归、各语体表达机制与多轮继承
│   ├── examples.md           # 跨语域、跨语言、不同任务的正反例
│   └── judge-rubric.md       # 外部语义评审（含角色连续性及任务完成度）
├── scripts/
│   └── evaluate.py           # 表层统计、用例校验、多轮解析和评分文件检查
└── tests/
    ├── cases.json            # 64 项回归用例（22 旧 + 42 新，含对话场景）
    ├── sample_responses.json # 已编写的基准示例，非真实模型测评结果
    └── test_evaluate.py      # 标准库单元测试
.github/workflows/
    └── regression.yml        # CI 确定性回归检查
```

## 运行

```bash
python scripts/evaluate.py --self-test
python scripts/evaluate.py --level 0 --text '这个方案不错。'
python scripts/evaluate.py --level 3 --text '我觉得不错，但这并不意味着所有人都会喜欢，也不是说其他方案没有价值。'
python scripts/evaluate.py --batch tests/sample_responses.json --json
python scripts/evaluate.py --file response.txt --level 5 --judge-json review.json --json
```

`--batch` 支持读取 `[{"id":"...", "level":3, "text":"..."}]`、`{"outputs":[...]}` 或已填入 `"response"` 字段的 `{"cases":[...]}`，自动输出逐条特征、断言核验结果以及跨样本首尾句式重复度汇总。`--judge-json` 读取另一模型或人工评审提交的六维 0–5 分 JSON，计算加权分，不会自动连接模型或生成评审。
