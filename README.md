# Defensive Writing & Expression v3.2

一个刻意制造“GPT 式防御性表达”的中文 Agent Skill：让普通观点提前应付尚未出现的误读，甚至让免责声明需要再被免责声明澄清。

![防御性写作关系图：不能证明、并不等于、不是而是](assets/defensive-writing-map.jpg)

## 核心特性（v3.2）

- **零新增实体约束**：严格区分“有载体句”（如含测试/哈希/合同）与“纯陈述句”（如仅含主观体验或结果对比），高档位递归不再为了凑层数而凭空脑补监控、日志或统计流程。
- **六级冲突优先级仲裁链与短文本降级**：明确 `安全清晰度 > 0 级退出 > 字数硬上限 > 单点覆盖 > 风格 > 档位默认` 裁决顺序；紧字数约束下自动切换为紧凑同位链（`A ≠ B ≠ C`）以兼顾篇幅与递归层数。
- **增强型离线回归校验（`evaluate.py`）**：在原有表面标记统计基础上，新增 `cases.json` 核心词留存校验（`preserve` recall）、`overrides` / `guardrail` 合规审计，以及 `--batch` 跨样本首尾句式撞车检测。
- **双层误读引擎与内置二次审查**：原观点 → 虚拟误读 → 澄清 → 对澄清的误读 → 元澄清（最多 3 层），内置防复读编辑自检。
- **渐进式上下文加载**：常规 1–3 级仅加载 `SKILL.md`，高递归与诊断评测再按需读取 `references/`。

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
├── SKILL.md                  # 核心指令，含优先级仲裁链、零新增实体规则与短文本降级
├── README.md                 # 使用说明
├── references/
│   ├── patterns.md           # 十类误读、有/无载体双轨递归、六种宏观结构和多维参数
│   ├── examples.md           # 分级、风格、无载体递归、紧字数压缩与六种结构示例
│   └── judge-rubric.md       # 外部模型/人工评审协议（含零新增载体审查项）
├── scripts/
│   └── evaluate.py           # 表层统计、preserve 留存校验、guardrail 检查与跨样本去重检测
└── tests/
    ├── cases.json            # 22 项回归用例（含无载体递归与短字数边界用例）
    └── sample_responses.json # 已编写的基准示例，非真实模型测评结果
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
