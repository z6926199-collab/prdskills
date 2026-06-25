# 知识库集成速查表

> 产品规划部知识库（MCP）集成指南。仅按需加载，不预取不驻留。

## 检索策略（两段式省 Token）

**核心原则：先看摘要再拉全文，避免为不相关文档浪费 token。**

```
Phase 1 — 元数据扫描（低成本）
  └─ viking_knowledge_search (mode="find")
  └─ 返回：文件名 + ~200 字摘要
  └─ 成本：~200 tokens / 次

Phase 2 — 全文拉取（仅命中后）
  └─ get_knowledgebase_data
  └─ 返回：完整文档片段
  └─ 成本：~14K tokens / 次
  └─ 触发条件：Phase 1 摘要判断该文档确实相关
```

**扫描后决策**：
- 摘要与当前功能高度相关 → 进入 Phase 2 拉全文
- 摘要仅部分相关 → 提取摘要中的关键信息，标记引用为 `来源：产品规划部知识库 / {文档名}（摘要级）`
- 摘要完全不相关 → 静默丢弃，不告知用户

**节省效果**：6 场景中通常仅 1-3 个真正命中全文，相比直接拉全文节省 49%-82% token。

## 知识库工具

| 工具 | 用途 | 模式 |
|------|------|------|
| `mcp__knowledgebase__viking_knowledge_search` | Phase 1：语义检索元数据（文件名 + 摘要） | `mode: "find"` |
| `mcp__knowledgebase__viking_knowledge_search` | 精确文件名/路径定位 | `mode: "glob"` / `mode: "grep"` |
| `mcp__knowledgebase__get_knowledgebase_data` | Phase 2：RAG 向量检索，返回文档全文片段 | `user_input` + `knowledgebase_names: ["产品规划部知识库"]` |

**选择规则**：
- 语义扫描（Phase 1）→ `viking_knowledge_search` (find)
- 全文拉取（Phase 2）→ `get_knowledgebase_data`
- 文件名/路径定位 → `viking_knowledge_search` (glob/grep)

## 场景速查

### S0 开放式任意查询

- **触发词**：`/cpghbkb`、`查产品规划部知识库`、`查部门知识库`
- **时机**：任意 Step，用户主动
- **执行**：解析用户查询意图 → 选择合适工具 → 静默检索 → 结果注入当前上下文
- **示例**：`/cpghbkb 投影仪C2上一版PRD`、`查部门知识库 无障碍适配规范`

### S1 历史版本回溯

- **触发条件**：项目类型判定为 1-to-100 或 1-to-1.5
- **时机**：Step 0.5 末尾（一次性卡片）
- **查询模板**：`"{product_name} PRD SPEC 需求 版本变更 {function_module}"`
- **目标**：命中该产品/模块的历史 PRD，提取变更日志、已知问题、技术约束
- **两段式**：
  1. Phase 1：`viking_knowledge_search` find 模式 → 获取文档名 + 摘要列表
  2. Phase 2：对摘要相关的文档调用 `get_knowledgebase_data` 拉全文

### S2 功能参考检索

- **触发条件**：当前功能涉及：无障碍/隐私合规/OTA/多语言/安全合规/卖场演示/FAQ
- **时机**：Step 0.5 末尾（一次性卡片）
- **查询模板**：
  - 无障碍：`"无障碍 适配 规范 checklist {function_name}"`
  - 隐私合规：`"隐私合规 PIA 权限 {function_name}"`
  - OTA/升级：`"OTA 升级 兼容 {function_name}"`
  - 多语言：`"国际化 多语言 翻译 {function_name}"`
  - 卖场/演示：`"卖场模式 演示 {function_name}"`
  - 安全合规：`"安全合规 GMS 认证 安全审计 漏洞 {function_name}"`
- **目标**：命中该主题的历史规范/模板/最佳实践
- **两段式**：
  1. Phase 1：`viking_knowledge_search` find 模式 → 获取文档名 + 摘要列表
  2. Phase 2：对摘要相关的文档调用 `get_knowledgebase_data` 拉全文

### S3 竞品/背景证据

- **触发条件**：撰写 2.1 背景说明 或 2.2 竞品分析
- **时机**：Step 4 开始起草对应章节前（一次性卡片中预登记，到 Step 4 时执行）
- **查询模板**：`"竞品分析 {product_category} {feature_name}"` / `"市场研究 行业报告 {topic}"`
- **目标**：命中 KB 中已有的竞品分析、研究报告
- **两段式**：
  1. Phase 1：`viking_knowledge_search` find 模式 → 获取文档名 + 摘要列表
  2. Phase 2：对摘要相关的文档调用 `get_knowledgebase_data` 拉全文

### S4 精确文档检索

- **触发条件**：Step 4 起草中遇"待确认"且涉及已命名文档
- **时机**：Step 4 中实时
- **查询模板**：`viking mode="glob" query="*{文档名}*"`
- **目标**：定位具体文件路径，读取关键章节
- **工具**：`viking_knowledge_search` (glob → 定位；find → 读取)
- **降级**：glob 无结果 → 回退 `get_knowledgebase_data` 语义检索

### S5 模板/规范查询

- **触发条件**：撰写 FAQ/使用技巧/词条提报/埋点规范/附录
- **时机**：Step 4 写入对应章节前（一次性卡片中预登记，到 Step 4 时执行）
- **查询模板**：
  - FAQ/玩机技巧：`"玩机技巧 FAQ 使用指南 {function_name}"`
  - 词条/翻译：`"词条 翻译对照 命名规范 {function_name}"`
  - 埋点/统计：`"埋点规范 Telemetry 数据统计 {function_name}"`
- **目标**：命中历史模板和规范文档
- **两段式**：
  1. Phase 1：`viking_knowledge_search` find 模式 → 获取文档名 + 摘要列表
  2. Phase 2：对摘要相关的文档调用 `get_knowledgebase_data` 拉全文
## 使用规范

1. **结果只注入当前章节**，不跨 Step 驻留。一次查询 = 一次使用。
2. **引用标注**：来源写 `"来源：产品规划部知识库 / {文档名}"`；Phase 1 摘要级引用加注 `（摘要级）`。
3. **Session 去重**：同 session 内相同 query 不重查，复用前次结果。
4. **不确定仍标待确认**：KB 内容 ≠ 权威结论，无法交叉验证的仍写 `待确认`。
5. **top_k=3**：`get_knowledgebase_data` 默认取 top 3 条；`viking_knowledge_search` 设置 `node_limit:5`。

## 降级策略

| 情况 | 处理 |
|------|------|
| KB 查询超时/返回空 | ⚠ 告知用户"KB 检索失败，已跳过，继续起草"，流程不中断 |
| KB 返回内容不相关 | 静默丢弃，不告知用户 |
| 工具本身不可用 | ⚠ 告知用户"KB 连接不可用，本次跳过所有 KB 检索"，整 session 禁用 KB |
| Phase 1 find 无结果 | 静默跳过该场景，不进入 Phase 2（无意义的全文拉取） |
