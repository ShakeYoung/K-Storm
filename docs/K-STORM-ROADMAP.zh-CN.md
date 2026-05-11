# K-Storm 演进路线图与 V1.5 执行分析

> **当前版本：V1.6**。V1.5 规划的功能包已全部落地，V1.6 新增了四种讨论模式、记忆查询、外部论据系统和三栏实验台 UI。本文保留原始规划文本作为设计参考，各功能包的实际完成状态见文末附录。

## 文档目的

本文将 K-Storm 下一阶段的能力演进整理为三个版本层级：

- **V1.5**：把“讨论结果”升级为“可判断、可追溯、可复盘的研究决策产物”
- **V2**：把“输入材料”升级为“可检索、可引用、可覆盖的工作记忆系统”
- **V3**：把“工作台”升级为“可实验、可比较、可评估的研究 ideation 平台”

同时，本文对 **V1.5 的执行思路与实现逻辑** 进行分析，但暂不涉及具体编码实现。

---

## 一、产品定位约束

K-Storm 当前最核心的差异化，不在于“多 Agent”本身，而在于：

1. **任务位置更前**
   - 重点不是自动写综述、自动做实验、自动写论文
   - 重点是科研选题、开题构思、方向初筛、组会前预讨论

2. **输入是研究情境，而不是单句 query**
   - 模板输入包含领域、背景、已有基础、约束、偏好方向、避免方向等
   - 上传文档提供局部证据和已有材料

3. **中间层是工作流核心**
   - intake briefing
   - 多角色 discussion
   - moderator 汇总
   - structured IR
   - final report

4. **本地、轻量、可审计**
   - 适合个人或小团队私有材料 brainstorming
   - 适合可控实验迭代，而非一开始就走重型自治科研路线

因此，后续演进应遵循一条原则：

> 优先增强“证据绑定、结构化收敛、复盘能力、输入质量、评估能力”，避免过早把系统拉向通用 deep research 或自治实验执行器。

---

## 二、版本路线图总览

| 版本 | 核心目标 | 关键词 | 主要产出 |
| --- | --- | --- | --- |
| V1.5 | 让讨论结果可判断、可追溯、可复盘 | 证据绑定、候选聚类、批判机制、可复现 | 更可信的 IR 与研究方向决策面板 |
| V2 | 让输入材料可检索、可引用、可覆盖 | 文档摄入、chunking、本地检索、perspective coverage | 更稳健的 briefing 与证据支撑 |
| V3 | 让工作流本身可实验、可比较、可评估 | benchmark、ablation、checkpoint rerun、workflow eval | 从产品 MVP 升级为研究 ideation 平台 |

---

## 三、V1.5：把“讨论”升级为“可判断”

### 3.1 版本目标

V1.5 的目标不是增加更多 Agent，也不是扩大任务边界，而是补足当前最关键的四个短板：

1. **结论缺少证据绑定**
2. **输出缺少候选方向聚类与排序**
3. **批判机制存在，但还不够制度化**
4. **历史记录可打开，但实验复盘语义还不够完整**

### 3.2 功能包

#### 功能包 A：Claim-Evidence 证据绑定

目标：让结构化 IR 和最终报告中的关键判断，不再只是纯文本结论，而是能指回输入材料。

建议能力：

- 每条关键 claim 允许附带：
  - `source_document`
  - `evidence_excerpt`
  - `evidence_note`
  - `confidence`
- 在 structured IR 中保留“结论-证据”对
- 最终报告可展示为简化形式，IR 中保留完整形式

预期收益：

- 降低多级压缩中的信息漂移
- 让用户判断“这条方向为什么成立”
- 为后续检索、复审、排序提供基础

---

#### 功能包 B：候选方向聚类与排序

目标：把当前偏整合式的报告，升级为更贴近真实组会决策的“方向面板”。

建议能力：

- Moderator 或 IR 阶段输出多个候选方向簇
- 对每个方向给出：
  - novelty
  - feasibility
  - fit_to_existing_basis
  - risk
  - expected_output
- 输出排序与排序理由
- 合并语义重复但表述不同的方向

预期收益：

- 从“生成讨论内容”升级为“生成方向判断”
- 减少伪多样性
- 更适合开题、组会、导师沟通

---

#### 功能包 C：Red-Team Critique 制度化

目标：把批判功能从“可能出现在 debate 中”升级为“被系统显式保障的阶段”。

建议能力：

- 在 debate 后或 moderator 前增加固定 critique 段
- critique 不负责提新 idea，只负责指出：
  - 创新性伪增量
  - 证据不足
  - 与已有基础不匹配
  - 资源约束冲突
  - 路线过大或不可落地
- critique 输出进入 IR，成为排序的重要输入

预期收益：

- 防止多 Agent 讨论变成集体自我强化
- 提高方向筛选质量
- 更贴近真实科研中的评审视角

---

#### 功能包 D：历史记录与运行配置的完整可复现

目标：让历史记录不只是可查看，而是真正可复盘、可比较、可重新实验。

建议能力：

- 在运行记录中显式保存：
  - `rounds`
  - `parallel_first_round`
  - `model_settings` 脱敏快照
  - `phase_outputs`
- 支持从完整历史语义重新发起分析
- 为后续 checkpoint rerun 留接口

预期收益：

- 从结果归档升级为实验记录
- 便于比较不同运行配置
- 为 V3 的 workflow evaluation 打基础

---

### 3.3 V1.5 完成后的系统形态

完成 V1.5 后，K-Storm 应从当前的：

> “能生成多 Agent 讨论和最终报告的本地 brainstorming MVP”

升级为：

> “能够输出候选方向、排序理由、风险批判、证据支撑，并支持复盘的研究选题决策工作台”

---

## 四、V2：把“输入材料”升级为“工作记忆”

### 4.1 版本目标

V2 的核心不是继续加讨论轮次，而是增强输入层与检索层，使系统对用户材料的理解更稳健。

### 4.2 功能包

#### 功能包 A：文档摄入升级

建议能力：

- 支持 PDF / DOCX / Markdown / TXT 等更多格式
- 支持目录导入与批量 ingest
- 支持长文自动切块
- 为 chunk 记录元数据：
  - 文档名
  - 页码 / section
  - 文档类型
  - 用户注释

收益：

- 输入材料不再受限于简单文本
- 为证据引用提供更细粒度基础

---

#### 功能包 B：本地检索与 chunk 级引用

建议能力：

- 对导入材料做 chunk 级检索
- briefing 与 critique 阶段允许按需拉取 chunk
- IR 中引用具体 chunk，而非整篇文档

收益：

- 降低 intake 全文压缩损耗
- 降低 hallucination 与误归纳

---

#### 功能包 C：Perspective Discovery / Coverage

建议能力：

- 在 intake 后自动抽取研究视角：
  - 机制
  - 数据
  - 方法
  - 资源与约束
  - 风险
  - 转化方向
- 跟踪哪些视角已覆盖，哪些未覆盖
- 在 moderator 中输出 coverage 结果

收益：

- 让多 Agent 讨论从“多角色发言”升级为“多视角扫描”
- 避免遗漏关键讨论维度

---

#### 功能包 D：双入口模式

建议能力：

- **模板模式**：适合已有明确研究背景
- **参考文献模式**：适合只提供一些 paper / notes，希望系统先帮助形成方向

收益：

- 扩大适用场景
- 保持当前 workflow 的同时增强灵活性

---

### 4.3 V2 完成后的系统形态

完成 V2 后，K-Storm 应从：

> “能够围绕已有输入进行讨论收敛”

升级为：

> “能够稳定摄入多源材料、按需检索证据、识别视角覆盖缺口，并形成更可信 briefing 的研究工作记忆系统”

---

## 五、V3：把“工作台”升级为“研究 ideation 平台”

### 5.1 版本目标

V3 的核心不是继续叠产品功能，而是让 **workflow 本身变成可研究对象**。

### 5.2 功能包

#### 功能包 A：Workflow Benchmark

建议能力：

- 定义一批固定科研选题样本
- 评价维度包括：
  - novelty
  - feasibility
  - fit_to_basis
  - evidence_support
  - redundancy
  - human preference

收益：

- 让系统优化从经验判断走向实验比较

---

#### 功能包 B：Ablation / Topology Comparison

建议能力：

- 比较不同 workflow 配置：
  - 单轮 vs 多轮
  - 并行首轮 vs 全串行
  - 有无 critique 阶段
  - persona diversity 高低
  - 有无 evidence binding
- 输出质量/多样性/用户偏好差异

收益：

- 让 K-Storm 具备明确研究价值
- 可形成论文或内部方法论沉淀

---

#### 功能包 C：Checkpoint Rerun

建议能力：

- 从 intake 结果开始 rerun
- 从 debate 某一轮开始 rerun
- 替换 moderator 模型或 IR 模型后局部 rerun
- 对比不同路径的最终输出

收益：

- 极大提升实验效率
- 让历史记录真正成为研究资产

---

#### 功能包 D：可视化分析层

建议能力：

- debate 关系图
- claim-evidence 图
- unresolved question 列表
- direction ranking dashboard

收益：

- 让系统从文本工作流进一步升级为分析界面

---

### 5.3 V3 完成后的系统形态

完成 V3 后，K-Storm 应从：

> “一个可用的研究 brainstorming 工作台”

升级为：

> “一个既能服务实际科研构思，又能研究多 Agent ideation workflow 设计本身的实验平台”

---

## 六、版本优先级判断

### 第一优先级

- Claim-Evidence 证据绑定
- 候选方向聚类与排序
- Red-Team Critique 制度化
- 完整运行配置可复现

原因：

这四项直接补当前系统最关键的可信度、可判断性和复盘能力短板。

### 第二优先级

- 文档摄入升级
- 本地检索与 chunk 引用
- perspective coverage
- 双入口模式

原因：

这几项会显著增强输入质量，但应建立在 V1.5 的中间结构更稳之后。

### 第三优先级

- workflow benchmark
- topology ablation
- checkpoint rerun
- 可视化分析层

原因：

这几项最有研究价值，但需要前面两层先打好结构基础，否则比较对象不稳定。

---

## 七、V1.5 执行思路与实现逻辑分析

> 本节只分析执行思路，不涉及具体实现提交。

### 7.1 V1.5 的总目标到底是什么

V1.5 的本质不是“增加几个功能按钮”，而是把 K-Storm 当前的主链条从：

`输入材料 → briefing → debate → summary → final report`

升级为：

`输入材料 → briefing → 多视角讨论 → 批判审查 → 候选方向整理 → 证据绑定的 IR → 决策型报告`

也就是说，V1.5 改的不是单点 UI，而是：

- **IR 的语义结构**
- **讨论到总结的收敛逻辑**
- **历史记录的实验语义**

其目标是让“报告”不再只是总结，而是能支撑研究选择。

---

### 7.2 V1.5 的依赖关系

四个功能包之间不是平铺关系，而是有前后依赖。

#### 第一层：数据与结构基础

必须先明确：

- IR 结构是否允许 claim-evidence 对
- run record 是否允许保存更完整的配置与阶段输出

如果这一层不先改，后面排序、critique、复盘都只能停留在表面文本。

#### 第二层：批判与聚类逻辑

有了更结构化的中间层后，才能稳定做：

- critique 结果进入 IR
- 候选方向去重、聚类、排名

#### 第三层：报告呈现与历史复盘

最后再把上述结构体映射到：

- final report
- 历史详情页
- 导出格式

所以执行顺序不应是“先改前端按钮”，而应是：

1. schema / record semantics
2. orchestrator logic
3. IR generation
4. report rendering
5. history / export presentation

---

### 7.3 V1.5 的最小闭环应该长什么样

为了避免一次改动过大，V1.5 最好先落一个 **最小可行闭环**。

#### 最小闭环建议

1. **Structured IR 从纯文本升级为半结构化对象**
   - 至少内部先支持：
     - candidate_directions
     - key_claims
     - critique_points
     - evidence_refs

2. **Moderator 产出“候选方向列表”**
   - 不再只是总结合并文本
   - 而是显式识别 A/B/C 三类方向

3. **新增一个 critique 汇总步骤**
   - 可由现有 Reviewer / Feasibility 角色承担第一版
   - 暂不一定需要新增 Agent

4. **最终报告新增排序与理由区块**
   - 给出 Top 1 / Top 2 / Top 3
   - 说明每个方向为何入选

5. **运行记录保存完整配置语义**
   - 为 rerun 和历史解释提供稳定基础

这个最小闭环的好处是：

- 改动集中
- 可以较快验证价值
- 不会一下子把系统拉得太重

---

### 7.4 V1.5 的推荐执行顺序

#### 步骤 1：先定义新的中间对象

先定义 V1.5 的核心数据结构，而不是先改 prompt。

建议先抽象：

- `EvidenceRef`
- `CandidateDirection`
- `CritiquePoint`
- `StructuredIRV2`

这样做的原因是：

- prompt、数据库、前端展示、导出都要围绕它对齐
- 不先有中间对象，后续就会再次退回纯文本拼接

---

#### 步骤 2：改 moderator / summary 语义

让 moderator 和 summary 的职责重新划分：

- **moderator**：整理冲突、候选方向、未解决问题
- **summary / IR**：形成结构化方向判断与证据映射

这一步的关键不是让 summary 更长，而是让 summary 更像“判决表”。

---

#### 步骤 3：把 critique 变成强约束输入

当前 critique 容易淹没在 debate 文本里。V1.5 应把它提纯为强约束。

例如每个候选方向都要回答：

- 最强创新点是什么
- 最弱证据点是什么
- 最可能失败在哪
- 与用户现有基础是否匹配
- 如果要降风险，替代路线是什么

这样 critique 才会真正进入决策逻辑。

---

#### 步骤 4：再做 final report 模板升级

等 IR 稳定以后，再调整 final report 模板，输出更适合决策与汇报的结构：

- 候选方向总览
- 排序结果
- 每个方向的支持证据 / 风险 / 资源匹配度
- 推荐下一步

否则如果先改 final report，只会变成表面格式升级。

---

#### 步骤 5：最后做历史记录与导出增强

历史页与导出应消费前面已经稳定的结构体，而不是反过来驱动后端设计。

建议展示：

- 候选方向卡片
- critique 摘要
- evidence 简表
- 完整 run 配置快照

---

### 7.5 V1.5 中最容易踩的坑

#### 坑 1：把证据绑定做成装饰性引用

如果只是最终报告里加几行“来源：xxx 文档”，但 IR 内部仍然是纯文本总结，那么这不是真正的 evidence binding。

真正要做的是：

- 先让中间结构知道“哪条 claim 对应哪段证据”
- 再决定前端如何展示

#### 坑 2：过早引入复杂检索系统

V1.5 的目标是让已有材料的使用更可信，而不是立刻做完整 RAG。若过早引入检索，会让问题空间变大。

#### 坑 3：把 critique 变成另一轮重复发言

如果 critique 只是“再让一个 agent 说一段话”，效果会很弱。

critique 必须被结构化吸收进排序逻辑，而不是仅仅增加文本长度。

#### 坑 4：只在前端做排序展示

如果排序只是 UI 层拼出来的，而不是中间 IR 已经明确表达的判断，那么系统内部仍然没有真正收敛。

---

### 7.6 V1.5 完成判据

V1.5 是否真正完成，不应只看“按钮有没有出现”，而应看以下问题是否都能回答：

1. 打开任一完成 run，能否清楚看到 **有哪些候选方向**？
2. 每个方向能否看到 **支持它的证据**？
3. 每个方向能否看到 **主要风险和反对意见**？
4. 系统是否明确给出 **排序和排序理由**？
5. 历史 run 是否能在完整配置语义上被 **复盘与重跑**？

只有这五项成立，V1.5 才算真的从 brainstorming 报告器升级成研究决策工作台。

---

## 八、建议的后续文档拆分

当前本文适合作为总路线图。若进入实施阶段，建议继续拆成三份子文档：

1. `V1_5-DESIGN.zh-CN.md`
   - schema 设计
   - workflow 变更
   - UI 变更
   - migration 方案

2. `V2-DESIGN.zh-CN.md`
   - ingestion / chunking / retrieval 设计

3. `V3-EVAL.zh-CN.md`
   - benchmark、ablation、评价指标设计

---

## 九、结语

K-Storm 后续最重要的进化方向，不是单纯扩张 agent 数量，而是：

- 让结构化中间层更强
- 让证据链更可追踪
- 让方向判断更明确
- 让历史运行更可复盘
- 让 workflow 本身更可研究

沿着这条路径推进，K-Storm 才会从一个“能跑通的 brainstorming MVP”，逐步演进成一个真正有研究价值、也有使用价值的科研 ideation 工作台。


---

## 附录：V1.5 / V1.6 实际完成状态

### V1.5 功能包完成情况

| 功能包 | 状态 | 实际实现 |
|:--|:--|:--|
| A. Claim-Evidence 证据绑定 | ✅ 已完成 | `StructuredIRV2` 包含 `evidence_refs`（id/source_type/source_title/quote_or_summary/supports），`fallback_structured_ir_v2` 自动从讨论中提取证据 |
| B. 候选方向聚类与排序 | ✅ 已完成 | `candidate_directions` 含 id/title/research_question/novelty/feasibility/risks/priority/priority_reason/evidence_refs/critique_refs/next_actions，3-5 个方向按优先级排序 |
| C. Red-Team Critique 制度化 | ✅ 已完成 | `critique_points` 含 id/target_id/dimension/severity/content/mitigation，每个候选方向必须绑定 critique_refs |
| D. 历史记录可复现 | ✅ 已完成 | 运行记录保存 rounds、parallel_first_round、mode、selected_agents、model_settings 脱敏快照、timeline（含每阶段开始/完成时间）、source_run_id |

### V1.6 新增功能

| 功能 | 说明 |
|:--|:--|
| 四种讨论模式 | Full Deliberation / Focused Panel / Quick Probe / Memory Query |
| 记忆查询 | 基于历史 Run 的记忆上下文（briefing + IR）启动新讨论 |
| 三栏实验台 UI | 深色左导航 + 主舞台 + 右侧情报栏，六个页面 |
| 外部论据系统 | Agent 角色化引用要求、二级提取（显式小节 + 正则 fallback）、分组展示、MD/PDF 导出 |
| 统一导出 | DownloadMenu 组件，所有下载按钮弹出 MD/PDF 选择器 |
| 证据绑定校验 | `validate_structured_ir` 检测悬空引用、空绑定、仅泛化引用，前端黄色警告面板 |
| 结构化 IR 隐藏 | IR 作为中间产物不对用户展示，仅在打包导出中包含 |
| 停止/继续/重跑 | 运行中停止、从失败位置继续、确认后预填模板重跑 |
| PDF 导出 | window.print 方案，所有导出点统一支持 |
