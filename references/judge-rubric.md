# v3.3 语义评审规则（兼容 v3.2 Rewrite）（给另一模型 / 人工审稿者）

这是一个**独立评审提示词**，不是 `scripts/evaluate.py` 的内置模型。脚本只做表面特征统计与断言校验；若要在真实模型上评分，调用者需提供原始观点、目标配置与候选输出，再用具有语义能力的模型或人工审查。

## 评审输入

- 原始观点（original）
- 目标强度 level（0–5）
- 风格 style
- 额外维度 overrides（任选：密度、误读数量、递归层数、共情、和稀泥、长度）
- 候选文本 response

## 六维评分：每项 0–5 分

| 键 | 权重 | 5 分标准 | 0 分标准 |
|---|---:|---|---|
| claim_preservation | 25 | 原观点的肯否、范围、证据、时间、对象全部保留 | 观点反转或严重偷换 |
| factual_integrity | 20 | 没有引入不可支持的真实事件、事实、引用和假指控，也未凭空脑补原文不存在的测试/监控/合同等载体 | 编造真实信息、实体载体或严重误导 |
| misread_diversity | 15 | 否认多个独立逻辑轴的误读，不仅是不同词汇 | 重复一个同义免责声明 |
| recursive_logic | 15 | 递归层数符合目标且每层增加新逻辑限定 | 凭空套娃或完全无递进 |
| naturalness | 15 | 严肃、流畅、像真实 AI 的过度谨慎（紧字数下允许紧凑同位链） | 词条堆砌、明显机械拼接 |
| target_fit | 10 | 档位、主风格、独立参数、优先级仲裁和长度上限全部相符 | 完全不符合要求 |

加权总分：`sum(score / 5 * weight)`，满分 100。**门槛**：事实和观点两项均至少 4/5，且总分至少 80，才建议接受。安全问题与捏造事实/实体载体属于否决项，不被平均分抵消；并非说 80 分可以替代事实审查。

`recursive_logic` 在目标递归为 0 时，应以“没有无谓套娃、遵守禁用”给分；不应因为没有递归而惩罚低级别。

## 可复制的评审指令

> 你是一名防御性写作文风审稿者。根据提供的 original、level、style、overrides 和 response，对 claim_preservation、factual_integrity、misread_diversity、recursive_logic、naturalness、target_fit 六项分别评分 0–5。指出具体句段里最大的问题，提出最多三条可执行的修订建议。重点识别“免责声明越写越长但逻辑没加深”“将虚拟反对者说成现实反对者”“原句未提测试/监控/合同却为了凑递归凭空编造外围流程载体”“批评作品变成批评人格”“超出显式字数上限”。只输出下列 JSON，不加 Markdown 代码围栏。

```json
{
  "scores": {
    "claim_preservation": 5,
    "factual_integrity": 5,
    "misread_diversity": 4,
    "recursive_logic": 4,
    "naturalness": 4,
    "target_fit": 5
  },
  "veto": false,
  "issues": ["一句话问题的具体证据"],
  "suggestions": ["一条具体修订策略"]
}
```

样例仅示范字段格式，不是某段实际文本的评审结果。

## 二次审查指令（用于生成模型内部自检）

> 根据原观点、目标参数、当前草稿：先检查事实、立场与是否凭空新增了原文不存在的载体；再寻找一个尚未被澄清、且与已有免责声明逻辑维度不同的可能误读；如存在且适合本档位与字数上限，添加一项澄清并重写自然段（紧字数下折叠为紧凑同位链），删除同义复读。不许虚构现实指责，不许改变原观点。若没有有效新误读，保持原稿不变。最多修订一次（四五级可再修订一次）。仅返回最终改写文本。

## JSON 与脚本协作

`python scripts/evaluate.py --file response.txt --level 5 --judge-json review.json --json`

脚本负责校验 0–5 的评分范围、计算加权总分与审核门槛，**不会自动生成 review.json**。调用者必须自己获取来自人工或另一个模型的评审结果，不能把示例 JSON 当成实际评分。

---

## v3.3：Respond / Persona / Task 上下文六维评分

旧六维规则**继续用于 Rewrite**。但对解释问题、执行编程任务、角色对话和多轮聊天，原先只评“观点保留”和“免责声明数量”的框架不足以判断任务是否真的完成。此时使用以下新权重：

| 键 | 权重 | 5 分标准 | 0 分标准 |
| --- | ---: | --- | --- |
| task_completion | 25 | 正确、完整完成原任务，必要代码/步骤/答案齐全 | 输出被免责淹没，任务没有完成 |
| factual_integrity | 20 | 事实准确，区分已知与推断，不编造流程或结果 | 编造真实数据、测试、行动或指控 |
| persona_continuity | 20 | 同一 voice 贯穿开头、中段、结尾，多轮口癖与语言稳定 | 角色化首尾夹住法务报告或中途换人设 |
| defensive_integration | 15 | 防御交错嵌入对应观点，像角色自己在辩解 | 先正常答，再复制一大段免责声明 |
| recursive_logic | 15 | 预判误读有独立逻辑，递归层数与目标相符 | 同义复读，假设前后矛盾 |
| target_fit | 5 | 符合 level/style/voice/mode/篇幅/退出要求 | 明显忽略设定或退出指令 |

**验收条件**：总分至少 80，且 task_completion、factual_integrity、persona_continuity 均至少 4/5；真实危险行为、编造事实与任务失败一票否决。多轮场景另评参数继承、按用户要求切换及干净退出；这些内容计入 persona_continuity 和 target_fit。

### 场景评审输入

除原始输入、候选 response 外，额外提供 mode、voice、scene、level、style、absurdity、self_awareness、prior_turns（如果存在）。对于代码场景，应实际检查代码能否按题意运行；对于引用上下文和事实的场景，应查实依据。不要求每句都带口癖，重点是整段身份连续。

**复制给外部评审者的指令：**

> 你要评价“任务优先、角色保持、过度防御自然融合”的表达。按 task_completion、factual_integrity、persona_continuity、defensive_integration、recursive_logic、target_fit 六维各 0–5 打分。首先指出有没有准确回答用户或交付有效成果，然后比较开头、中间、结尾的人设、词汇、语体是否一致，识别独立免责声明段、虚构工程流程及多轮设定遗失。五级应表现得明显过度谨慎，但不得为了完成递归层数牺牲正常答题。对真实危险、虚构事实、未完成任务设置 veto。只输出 JSON。

```json
{
  "rubric": "context-v3.3",
  "scores": {
    "task_completion": 5,
    "factual_integrity": 5,
    "persona_continuity": 4,
    "defensive_integration": 4,
    "recursive_logic": 5,
    "target_fit": 5
  },
  "veto": false,
  "issues": [],
  "suggestions": []
}
```

此 JSON 同样是**格式示范**，不是对实际模型回答的测试。旧版不写 rubric 的六维评分文件仍被 evaluate.py 识别为 legacy-rewrite；新版 context-v3.3 必须提供全部新维度。evaluate.py 不会自己充当语义评审者。

### 重点反例

- 夹心风格：猫娘开头和结尾都有“喵”，中间却整段“根据已有验证体系，必须明确……”。
- 任务偷换：用户请求修复 Python，回答只说“先建基线、快照、哈希、门禁”但没有修复。
- 递归堆词：三层分别是“不能保证”“不等于保证”“无法绝对保证”，无新增逻辑。
- 有据补充被误杀：Respond 合理引用用户给的脚本事实，却因原始提问未逐字出现而被认成“新增载体”。
- 0 级残留：用户明确说不要防御，模型仍补一句“这也不代表……”。
