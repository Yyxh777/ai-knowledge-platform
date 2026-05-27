# 文档处理管线 · 分会话学习手册

> **用途**：每个编号对应一次（或多次）独立 Cursor 会话。新开会话时，把该节的 **「复制用提示词」** 整段贴给 AI，必要时附上 **「浓缩上下文」**。  
> **仓库路径**：`python-ai-service/`（FastAPI、现有 `service/document_service.py`、`utils/file_utils.py`、`utils/milvus_utils.py`）。

---

## 一、总意图（全管线目标）

在 **本仓库 Python 服务** 中逐步实现：

1. **多格式解析**（MD 含代码块、非扫描 PDF、Word）  
2. **清洗管线**  
3. **智能切割**  
4. **元数据提取**  
5. **Milvus 存储优化**  
6. **文档变更同步**  

学习方式：**边学边写** → 先小 Demo / 小测试 → 再融入项目；**一次会话只做一小步**。

---

## 二、技术选型备忘（给 AI 的硬约束）

| 类型 | 要求 |
|------|------|
| **Markdown** | 需保留 **代码块** 边界，供后续切块策略使用；优先 **Unstructured** 解析。 |
| **PDF（非扫描）** | **文本型**：可用 **LangChain `PyPDFLoader`**；**复杂版式**（表格、多栏）：用 **Unstructured**（如 `partition_pdf`）。最终项目里两条路径都要存在，由路由或策略选择。 |
| **Word** | 用 **Unstructured**（如 `partition_docx`），与 PDF  rich 路径共享「元素 → 统一块模型」思路。 |
| **存储** | 向量仍进 **Milvus**；业务主键与 Java 对齐（`record_id` 等现有字段）。 |

解析层出口目标：**统一的中间结构**（如 `ParsedDocument` + `TextBlock` 列表），再进入清洗 / 切块，**禁止**在业务层长期堆 `if ext == pdf/docx/md` 而不抽象。

---

## 三、会话依赖关系（简图）

```
A0.1 → A0.2 → A0.3
         ↓
B1.1 → B1.2 → B1.3
         ↓
    C1.1 → C1.2 → C1.3  (Word)
         ↓
    D1.1 → D1.2 → D1.3  (PDF 双路径 + 路由)
         ↓
    E1.1 → E1.2 → E1.3  (MD)
         ↓
    F1.1 → F1.2 → F1.3  (注册表 + 接入 document_service)
```

后续（另开「阶段 2」系列会话）：清洗 → 切块 → 元数据 → Milvus 优化 → 变更同步。

---

## 四、浓缩上下文（复制到新会话时可选用）

下面整段可放在任意子会话提示词 **前面**，按需删减。

```
【项目】ai-knowledge-platform / python-ai-service
【目标】实现文档处理管线：多格式解析 → 清洗 → 智能切块 → 元数据 → Milvus 优化 → 文档变更同步；当前子会话只做编号 XXX 描述的那一小步。
【已有】document_service.upload_document_data：URL 下载 → file_utils 按扩展名抽文本 → RecursiveCharacterTextSplitter → DashScopeEmbeddings → Milvus insert。
【约束】MD/含代码块、非扫描 PDF、Word。PDF：PyPDFLoader（简单文本 PDF）+ Unstructured（表格/多栏等复杂排版），项目里要真正用上 Unstructured。解析结果要收敛到统一数据结构（如 ParsedDocument / TextBlock），便于后续清洗与切块。
【风格】中文沟通；改动集中在 python-ai-service；遵循 AGENTS.md；不要一次改太大，给出可运行的小步与验收方式。
```

---

## 五、各会话：上下文说明 + 复制用提示词

### 会话 A0.1 — Unstructured 解析 PDF 入门

**依赖**：无。  
**目标**：安装 `unstructured[pdf]`，用 `partition_pdf` + `strategy="fast"` 解析本地 PDF，打印元素数量与前 3 个元素的类别与文本预览。  
**产出**：`demo/demo_a01_partition_pdf.py`（或等价路径）。

**复制用提示词：**

```
【子任务 A0.1】我在做文档处理管线的第 0 步实验。

【浓缩上下文】
（粘贴「四、浓缩上下文」整段，或至少「二、技术选型」+ 本段目标）

【请你】
1. 确认 Windows 下 pip 安装 unstructured[pdf] 的推荐命令与常见报错处理（不写长文，列要点即可）。
2. 给我一份可直接运行的 demo_a01_partition_pdf.py：partition_pdf(filename=..., strategy="fast")，打印 len(elements) 与前 3 个元素的 category 与 text 前 80 字；说明我要改哪个 PDF_PATH。
3. 告诉我如何自检算「完成」。

【注意】我自己动手创建文件与运行；你只需给出命令与完整脚本内容。
```

**验收**：能打印 `元素数量 > 0`，前几个元素有合理 `category` 与可读 `text`。

---

### 会话 A0.2 — PyPDFLoader 对照同一 PDF

**依赖**：A0.1 已完成（有样例 PDF）。  
**目标**：对**同一文件**用 LangChain `PyPDFLoader` 加载，按页打印字符数或前 200 字预览。

**复制用提示词：**

```
【子任务 A0.2】对照 A0.1：用 LangChain PyPDFLoader 加载同一本地 PDF。

【浓缩上下文】
（粘贴「四」中段落）

【请你】
1. 给出 pip 安装 langchain-community（或当前项目已用的 LangChain 包名）中与 PyPDFLoader 相关的依赖说明。
2. 给出完整小脚本：PyPDFLoader(file_path)，遍历 documents，打印每页 metadata 与 page_content 长度或短预览。
3. 说明与 unstructured partition_pdf 在「粒度、顺序」上的预期差异（3～5 条要点）。

我只负责复制运行，你给出可运行代码与命令。
```

**验收**：同一 PDF 下，能列出页数与每页大致字数。

---

### 会话 A0.3 — 对比小结（为双路径定策略做准备）

**依赖**：A0.1、A0.2。  
**目标**：写对比脚本或表格，记录「多栏/表格 PDF」若有时 P 与 U 的差异；**不写**项目合并逻辑，只做观察结论。

**复制用提示词：**

```
【子任务 A0.3】我已分别用 unstructured partition_pdf（fast）和 PyPDFLoader 跑过同一 PDF。请指导我写一个最小「对比」脚本：输出两种方法的总字符数、按页/按块行数；若我只有「简单文本 PDF」和「带表或多栏 PDF」各一份，应分别记录哪些指标。最后给出 3 条「后续 D1.3 路由策略」可选方案（例如默认 U、或先 P 再兜底 U），各一句话优缺点。不要改项目业务代码。
```

**验收**：手上有两张样例的对比数字或笔记，并选定一种你倾向的路由思路（可改）。

---

### 会话 B1.1 — 定义 ParsedDocument / TextBlock

**依赖**：理解 A0 系列输出形态。  
**目标**：在 `pipelines/parsers/models.py`（路径可调整）定义 **dataclass 或 TypedDict**：`TextBlock`（text, page_number 可选, element_type 可选, source 可选）、`ParsedDocument`（blocks, 可选 file_hint）。附 1～2 个单元测试或 assert 小示例。

**复制用提示词：**

```
【子任务 B1.1】在 python-ai-service 中新增解析管线统一数据模型。

【浓缩上下文】
（粘贴「四」）

【请你】
1. 建议包路径，例如 pipelines/parsers/models.py（若需 __init__.py 一并说明）。
2. 给出 TextBlock、ParsedDocument 的字段设计（需兼容后续：PDF 页码、Unstructured category、MD 代码块标记 is_code 或 element_type）。
3. 给出最小 pytest 或 __main__ 自测示例，不依赖真实 PDF。

我本地创建文件；你给我完整代码块与运行测试的命令。
```

**验收**：`pytest` 或脚本运行通过，结构被后续 B1.2 引用不返工。

---

### 会话 B1.2 — Unstructured 元素 → TextBlock 适配器

**依赖**：B1.1、A0.1。  
**目标**：`unstructured_elements_to_blocks(elements) -> list[TextBlock]`，处理 `category`、`metadata.page_number` 等常见字段；缺省用安全默认值。

**复制用提示词：**

```
【子任务 B1.2】实现 unstructured 分区结果到 TextBlock 列表的适配器。

【浓缩上下文】
（粘贴「四」）

【已有】pipelines/parsers/models.py 中 TextBlock / ParsedDocument 定义（我会贴当前文件内容或路径）。

【请你】
1. 在 pipelines/parsers/adapters.py（或你建议的路径）给出 unstructured_elements_to_blocks 完整实现。
2. 说明不同 element 类型如何映射到 element_type / page_number（基于 metadata）。
3. 给一个使用 partition_pdf 读本地 PDF 后调用适配器并 print 前 5 个 TextBlock 的 __main__ 示例。

我会把代码粘进项目；你以当前 unstructured 版本常见 API 为准，若有不兼容处注明。
```

**验收**：本地 PDF 跑通，列表长度与元素大致对应。

---

### 会话 B1.3 — LangChain Document → TextBlock 适配器

**依赖**：B1.1、A0.2。  
**目标**：`langchain_documents_to_blocks(docs) -> list[TextBlock]`，把 `metadata["page"]` 等写入 `TextBlock`。

**复制用提示词：**

```
【子任务 B1.3】实现 PyPDFLoader 产出的 List[Document] 到 list[TextBlock] 的适配器，与 B1.1 模型一致。

【浓缩上下文】
（粘贴「四」）

【请你】
1. 在 adapters.py 中增加 langchain_documents_to_blocks，每页默认一个 block，element_type 可标为 "pypdf_page" 或类似。
2. 简短说明与 B1.2 产出的 TextBlock 在粒度上的差异（便于 D1.3 路由）。
3. 最小自测代码。

我会动手写入仓库。
```

**验收**：同 PDF 经 PyPDFLoader → blocks 可打印。

---

### 会话 C1.1 — Word：partition_docx 与类别观察

**依赖**：B1.1（可选先有）。  
**目标**：本地含表格的 docx，`partition_docx`，统计各 `category` 数量。

**复制用提示词：**

```
【子任务 C1.1】用 unstructured 解析 Word（partition_docx），只做观察性 Demo。

【浓缩上下文】
（粘贴「四」）

【请你】
1. Windows 下是否需额外 pip extra（如 docx 相关）的说明。
2. 完整脚本：filename 指向本地 .docx，partition 后统计 category 计数并打印前 3 个元素预览。
3. 提示我应准备的样例 docx 特征（表格、标题、正文）。

不改 document_service。
```

**验收**：能输出类别分布与可读文本片段。

---

### 会话 C1.2 — Table 等元素合并策略

**依赖**：C1.1。  
**目标**：定一条团队可执行的规则（如 Table → 制表符拼行），在适配器或独立函数中实现并打印前后对比。

**复制用提示词：**

```
【子任务 C1.2】基于 C1.1 的 partition_docx 输出，为 Table 与 ListItem 定简单合并/展平策略，输出纯文本友好的单行或多行，便于后续切块。

【浓缩上下文】
（粘贴「四」）

【请你】
1. 给出 1～2 种常见策略（表格转 TSV、列表转前缀 - ）的利弊各一行。
2. 推荐一种作为 MVP，并给出函数草案 table_element_to_text(el) 或统一在 unstructured_elements_to_blocks 里分支的伪代码/真代码。
3. 我提供样例输出时如何验收。

仍不接入 document_service。
```

**验收**：对含表 docx，表格内容可读、顺序合理。

---

### 会话 C1.3 — parse_docx(bytes) → ParsedDocument

**依赖**：B1.1、B1.2、C1.2。  
**目标**：从 **bytes**（BytesIO）入口封装，与 `download_file_from_url` 衔接一致。

**复制用提示词：**

```
【子任务 C1.3】实现 parse_docx(file_content: bytes) -> ParsedDocument，内部用 unstructured partition_docx + 已有元素适配逻辑。

【浓缩上下文】
（粘贴「四」）

【请你】
1. unstructured 从内存传入 docx 的推荐方式（BytesIO / tempfile 二选一说明）。
2. 给出 pipelines/parsers/docx_unstructured.py（文件名可调整）完整模块代码。
3. 与现有 file_utils.extract_text_from_docx 行为对比：说明迁移后检索侧可能的变化（一句话）。

我自行创建文件并运行简单 __main__。
```

**验收**：读入与线上下载一致的 bytes 能返回非空 `ParsedDocument`。

---

### 会话 D1.1 — parse_pdf_simple（PyPDFLoader）

**依赖**：B1.3。  
**目标**：`parse_pdf_simple(bytes) -> ParsedDocument`，内存中喂 PDF 给 PyPDFLoader（若 Loader 只接受路径，说明用 tempfile 的写法）。

**复制用提示词：**

```
【子任务 D1.1】实现 parse_pdf_simple(file_content: bytes) -> ParsedDocument，使用 LangChain PyPDFLoader + B1.3 的 langchain_documents_to_blocks。

【浓缩上下文】
（粘贴「四」）

【请你】
1. 若 PyPDFLoader 必须文件路径，给出 Windows 安全的 tempfile.NamedTemporaryFile/delete=False 用法要点。
2. 完整函数与最小测试方式。
3. 异常：非 PDF magic 时是否提前检测（可选）。

我只写入 pipelines/parsers/pdf.py 等建议路径。
```

**验收**：本地 PDF bytes → `ParsedDocument.blocks` 非空。

---

### 会话 D1.2 — parse_pdf_rich（Unstructured）

**依赖**：B1.2、A0.1。  
**目标**：`partition_pdf` 从 bytes 或临时文件 + `strategy="fast"`（或你环境已支持的策略），→ `ParsedDocument`。

**复制用提示词：**

```
【子任务 D1.2】实现 parse_pdf_rich(file_content: bytes) -> ParsedDocument，使用 unstructured partition_pdf + unstructured_elements_to_blocks。

【浓缩上下文】
（粘贴「四」）

【请你】
1. partition_pdf 接受 file=BytesIO 的写法或与 D1.1 一致的 tempfile 方案，选一种写死并说明原因。
2. 完整 parse_pdf_rich 与 __main__ 自测。
3. 与 parse_pdf_simple 块数量级差异的预期说明。

写入 pipelines/parsers/pdf.py 或拆分文件按你建议。
```

**验收**：同 PDF rich 路径块数通常 ≥ simple 路径页块数。

---

### 会话 D1.3 — PDF 路由 parse_pdf

**依赖**：D1.1、D1.2。  
**目标**：`parse_pdf(content, mode="auto"|"pypdf"|"unstructured")`；`auto` 先给明确规则（例如：默认 unstructured，或先 pypdf 总字数为 0 再 unstructured）。

**复制用提示词：**

```
【子任务 D1.3】在已有 parse_pdf_simple 与 parse_pdf_rich 上实现 parse_pdf(file_content: bytes, mode: Literal["auto","pypdf","unstructured"])。

【浓缩上下文】
（粘贴「四」）

【请你】
1. 给出两种 auto 策略实现草案，我选一种你补全为最终代码。
2. 打 debug 日志的字段建议（可选 logging）。
3. 单元测试：mode 各分支可 mock 小 bytes（或跳过真实 PDF 的条件）。

我动手合并到 pdf.py。
```

**验收**：三种 mode 行为可预测、可测。

---

### 会话 E1.1 — MD：partition_md 与代码块类别

**依赖**：B1.1。  
**目标**：含 ` ``` ` 的 md 文件，Unstructured 分区后确认代码块与正文类别分离情况。

**复制用提示词：**

```
【子任务 E1.1】用 unstructured 解析 Markdown（partition_md 或当前版本推荐 API），样例文件含 fenced code block。

【浓缩上下文】
（粘贴「四」）

【请你】
1. 给出 pip 是否需额外 extra。
2. 完整 demo 脚本与期望看到的 category 名称（以常见版本为例，并注「以本地为准」）。
3. 若代码块与正文合并，指出可能原因与参数。

不改业务代码。
```

**验收**：肉眼或打印可确认代码块边界。

---

### 会话 E1.2 — 代码块元数据策略

**依赖**：E1.1、B1.2。  
**目标**：在 `TextBlock` 或适配层标记 `is_code` / `element_type`，供后续切块「整块保留」使用。

**复制用提示词：**

```
【子任务 E1.2】在元素→TextBlock 映射中，为 Markdown/Unstructured 的代码类元素增加稳定标记（如 is_code=True 或 element_type="code"），并说明与后续切块器的契约（一句话）。

【浓缩上下文】
（粘贴「四」）

【请你】
1. 更新 models.TextBlock 字段建议（若 B1.1 需增量）。
2. 更新 adapters 中映射逻辑片段（完整函数或 diff 说明）。
3. 给一个含代码 md 的打印示例。

我本地改文件。
```

**验收**：代码块对应 block 可被程序识别。

---

### 会话 E1.3 — parse_md(bytes) → ParsedDocument

**依赖**：E1.2。  
**目标**：封装 `parse_md`，接入注册表的前置。

**复制用提示词：**

```
【子任务 E1.3】实现 parse_md(file_content: bytes) -> ParsedDocument，解码后或直接用 bytes 走 unstructured，输出与 Word/PDF rich 一致的 ParsedDocument。

【浓缩上下文】
（粘贴「四」）

【请你】
1. 完整模块 pipelines/parsers/md_unstructured.py（或合并到单一 parsers 包）。
2. 与旧 extract_text_from_txt 仅 decode 的差异说明。
3. __main__ 自测步骤。

我自行创建文件。
```

**验收**：含代码块 md 的 `ParsedDocument` 结构正确。

---

### 会话 F1.1 — 注册表与单元测试

**依赖**：C1.3、D1.3、E1.3。  
**目标**：`PARSERS["pdf"|"docx"|"md"]`，统一 `parse_document(ext, bytes) -> ParsedDocument`。

**复制用提示词：**

```
【子任务 F1.1】实现多格式解析注册表：按扩展名分发到 parse_pdf / parse_docx / parse_md，未知扩展抛清晰异常。补充 pytest：可用小 fixture 文件或 mock。

【浓缩上下文】
（粘贴「四」）

【请你】
1. 建议模块路径 pipelines/parsers/registry.py。
2. 完整代码与 tests/parsers/test_registry.py 示例。
3. 不在此步修改 document_service。

我本地添加文件并运行 pytest。
```

**验收**：`pytest` 对注册表通过。

---

### 会话 F1.2 — blocks → 过渡用纯文本

**依赖**：F1.1。  
**目标**：`blocks_to_plain_text(blocks, sep="\n\n")` 仅供过渡，接现有 `RecursiveCharacterTextSplitter`；文档注释写明后续会改为直接对 blocks 切块。

**复制用提示词：**

```
【子任务 F1.2】实现 blocks_to_plain_text(blocks: list[TextBlock], sep: str) -> str，顺序拼接；可选在块间插入页码注释行（由你建议是否默认开启）。用于暂时衔接 document_service 旧切片逻辑。

【浓缩上下文】
（粘贴「四」）

【请你】
1. 函数实现 + 与「丢失块边界信息」的风险说明（一句话）。
2. 放在哪个模块（如 pipelines/compose.py）。
3. 最小测试。

不改 document_service（若改则单独说明 diff）。
```

**验收**：拼接结果与旧整串提取大致可比（允许格式差异）。

---

### 会话 F1.3 — 接入 document_service.upload_document_data

**依赖**：F1.1、F1.2。  
**目标**：下载后走新解析链，再 `blocks_to_plain_text` → 现有 splitter/embeddings/milvus；行为可回归对比。

**复制用提示词：**

```
【子任务 F1.3】将 document_service.upload_document_data 改为：下载 → parse_document(扩展名, bytes) → blocks_to_plain_text → 现有 RecursiveCharacterTextSplitter 与 Milvus 写入逻辑。保留对 txt 等旧逻辑或显式不支持列表。

【浓缩上下文】
（粘贴「四」）

【请你】
1. 基于我贴出的当前 document_service.py 与 file_utils 给出最小 diff 思路。
2. 给出完整修改后的 upload_document_data 或明确分步补丁。
3. 回归检查清单（条数变化、空文档、异常类型）。

我会贴当前文件版本供你对齐。
```

**验收**：通过 Java/Postman 调用上传接口或本地脚本，三种格式至少各通一次。

---

## 六、阶段 2 起（会话标题 + 一句提示词，细节到新开会话再展开）

| 编号 | 主题 | 新开会话时一句话提示 |
|------|------|----------------------|
| **G1** | 清洗管线 | 「在 ParsedDocument 的每个 TextBlock.text 上实现 Unicode 规范化与空白压缩纯函数链，pytest 固定样例，暂不接入 Milvus。」 |
| **G2** | 智能切块 | 「输入 list[TextBlock]，输出 list[Chunk]（text+metadata）；先实现 token 或字符策略之一；MD 的 is_code 块不切分。」 |
| **G3** | 元数据 | 「扩展 Milvus 字段或 metadata JSON 方案，含 record_id、页码、element_type；给出迁移策略。」 |
| **G4** | Milvus 优化 | 「批量 embed/insert、失败重试、createCollection 与现有集合兼容方案。」 |
| **G5** | 变更同步 | 「基于 content hash 或版本号，封装 sync：删 record_id 旧向量再全量重解析重插，幂等。」 |

每开一个 **G*** 会话时，同样先贴 **「四、浓缩上下文」**，并把 **「五、已完成到 F1.x」** 写进提示词，避免 AI 推翻解析层设计。

---

## 七、文件路径建议（便于多会话一致）

```
python-ai-service/
  pipelines/
    parsers/
      __init__.py
      models.py          # B1.1
      adapters.py        # B1.2, B1.3
      docx_unstructured.py
      md_unstructured.py
      pdf.py             # D1.x
      registry.py        # F1.1
    compose.py           # F1.2 可选
  demo/
    demo_a01_partition_pdf.py
    ...
  tests/
    parsers/
      test_registry.py
  docs/
    document-pipeline-learning-sessions.md  # 本文档
```

---

## 八、版本与协作提示

- 每完成一个会话，在 git **小提交**：例如 `feat(parsers): add partition_pdf demo (A0.1)`。  
- 新开 Cursor 会话时：**附件**或粘贴相关已实现文件（`models.py`、`registry.py` 等）。  
- `unstructured` / `langchain` **钉版本**到 `requirements.txt`，避免半年后 API 漂移。

---

**文档结束。** 你当前进度若在 **A0.1**，下一会话直接用 **「五、会话 A0.2」** 的复制块即可。
