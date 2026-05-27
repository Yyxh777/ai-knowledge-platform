"""RAGAS 评估：faithfulness / context_recall / context_precision / answer_relevancy

用法：
    conda activate my_ap
    cd python-ai-service
    python evals/go_eval.py
"""

import asyncio  # 提供 asyncio.run，驱动异步 main
import os  # 读取环境变量中的 API Key、Base URL
import sys  # 修改模块搜索路径，以便导入项目内包
from pathlib import Path  # 用文件路径定位项目根目录与 .env

# 将 python-ai-service 根目录加入 sys.path，才能 import rag_workflows 等本地模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv  # 从 .env 文件加载环境变量

# 加载项目根目录下的 .env（与 config.py 使用同一套密钥配置）
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from openai import AsyncOpenAI  # RAGAS 评估指标内部调用 LLM/Embedding 的异步客户端
from ragas.llms import llm_factory  # 按模型名创建 RAGAS 兼容的评估用 LLM
from ragas.embeddings import OpenAIEmbeddings  # 创建 RAGAS 兼容的 Embedding（answer_relevancy 需要）
from ragas.metrics.collections import (  # RAGAS 0.4 推荐的 collections 指标 API
    Faithfulness,  # 忠实度：回答是否可由检索上下文支撑
    ContextRecall,  # 上下文召回率：标准答案中的信息是否被检索到
    ContextPrecision,  # 上下文准确率：检索结果中相关片段是否排在前面
    AnswerRelevancy,  # 回答相关性：生成回答与问题的匹配程度
)
from langgraph.checkpoint.memory import InMemorySaver  # 内存检查点（run_rag_pipeline 依赖，见下方原有代码）
from rag_workflows.rag_graph import create_classification_graph  # 项目 RAG 工作流入口（见下方原有代码）

from config import (
    OPENAI_API_KEY,
    OPENAI_BASE_URL
)


async def run_rag_pipeline(question: str) -> dict:
    """调用 LangGraph RAG 管线，返回检索上下文与回答"""
    graph = create_classification_graph(checkpointer=InMemorySaver())
    state = {
        "question": question,
        "user_id": "1123598821738675201",
        "role_id": 1123598816738675201,
        "role_name": "超级管理员",
        "access_levels": "",
        "permission_filter": "",
        "no_permission": False,
        "question_type": "",
        "retrieved_docs": [],
        "answer": "",
        "reasoning": "",
        "personal_data": {},
    }
    config = {
        "configurable": {
            "thread_id": "eval_session",
            "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJibGFkZXguY24iLCJhdWQiOlsiYmxhZGV4Il0sInRva2VuX3R5cGUiOiJhY2Nlc3NfdG9rZW4iLCJjbGllbnRfaWQiOiJzYWJlcjMiLCJ0ZW5hbnRfaWQiOiIwMDAwMDAiLCJ1c2VyX2lkIjoiMTEyMzU5ODgyMTczODY3NTIwMSIsImRlcHRfaWQiOiIxMTIzNTk4ODEzNzM4Njc1MjAxIiwicG9zdF9pZCI6IjExMjM1OTg4MTc3Mzg2NzUyMDEiLCJyb2xlX2lkIjoiMTEyMzU5ODgxNjczODY3NTIwMSIsImFjY291bnQiOiJhZG1pbiIsInVzZXJfbmFtZSI6ImFkbWluIiwibmlja19uYW1lIjoi566h55CG5ZGYIiwicmVhbF9uYW1lIjoi566h55CG5ZGYIiwicm9sZV9uYW1lIjoiYWRtaW5pc3RyYXRvciIsImRldGFpbCI6eyJ0eXBlIjoid2ViIn0sImV4cCI6MTc3OTg2NDQwOCwibmJmIjoxNzc5ODYwODA4fQ.iPaMpxneWd0Z_kUXjBKU-vvbhb1pfYNG4JLOch0_z2k",
        }
    }
    result = await graph.ainvoke(state, config=config)
    return {
        "retrieved_contexts": [d["content"] for d in result.get("retrieved_docs", [])],
        "response": result.get("answer", ""),
    }


TEST_DATA = [
    {
        "user_input": "公司请假需要提前几天申请？",
        "reference": """
            公司请假提前申请的时间根据请假时长不同有所区分，具体规定如下：
            请假 1 天及以下者，应至少提前 1 天向直属主管申请；
            请假 1 天以上者，应至少提前 2 个工作日向直属主管申请；
            请假一周及以上者，必须至少提前一周向直属主管及上级领导申请，经审批同意后方能休假。
            如遇紧急情况未能提前请假，须及时向直属主管说明情况，并在休假结束后的第 1 天上班前补办请假手续。
        """,
    },
    {
        "user_input": "BladeX中Lombok注解有哪些？",
        "reference": """
            BladeX 中提及的 Lombok 注解包含以下这些：
            注解一览中明确列出的
            · @Setter
            · @Getter
            · @Data
            · @Log（泛型注解，有多种具体形式）
            · @AllArgsConstructor
            · @NoArgsConstructor
            · @EqualsAndHashCode
            · @NonNull
            · @Cleanup
            · @ToString
            · @RequiredArgsConstructor
            · @Value
            · @SneakyThrows
            · @Synchronized
        """,
    },
    {
        "user_input": "开发人员加班有什么补贴？",
        "reference": """
            文档中没有针对开发人员制定单独的加班补贴规定，所有经公司审批同意的有效加班，统一执行以下补贴标准：
            一、工作日加班补贴
            工作时间超过晚上 8 时：补贴 25 元 / 晚
            工作时间超过晚上 11 时：次日可申请上班晚到，晚到时间一般不超过 2 个小时
            工作时间超过晚上 12 时：次日安排上午调休半天；若次日正常上班，发放补贴 75 元 / 晚
            通宵工作超过凌晨 3 时：次日安排调休一天；若次日正常上班，发放补贴 150 元 / 晚
            二、公休日加班补贴
            工作时间（不含午休时间）超过 7.5 小时：视为加班 1 天，补贴 150 元 / 天
            工作时间大于 4 小时不足 7.5 小时：按半天计算，补贴 75 元 / 半天
            三、国家法定假日加班补贴
            按国家规定支付加班工资，计算基数为员工基本工资；如低于广州市最低工资标准的按广州市最低工资标准计算。
            其他说明
            1.加班补贴每月核算一次，在每月工资中计发
            2.因员工个人原因未能在规定工作时间内完成所分配工作，需延长工作时间的，不计为加班
            3.公休日加班须提前通过企业 OA 提交 "加班申请" 并经上级主管审批；法定假期加班须发邮件经上级主管及 CEO 批准并知会人力资源部，方可视为有效加班
        """,
    },
]


async def main():
    """RAGAS 评估主流程：先跑 RAG 收集数据，再对每条样本打四项指标分。"""
    samples = []  # 存放「问题 + 标准答案 + 检索上下文 + 模型回答」的完整样本
    for item in TEST_DATA:  # 遍历你定义的测试集
        rag = await run_rag_pipeline(item["user_input"])  # 调用原有 RAG 工作流，拿到检索结果与回答
        # 合并测试项与 RAG 输出；reference 去掉首尾空白，便于与 RAGAS 比对
        samples.append({**item, "reference": item["reference"].strip(), **rag})
        # 打印 RAG 阶段进度：问题文本 + 检索到的 chunk 数量
        print(f"[RAG] {item['user_input']} | ctx={len(rag['retrieved_contexts'])}")

    print("---"*30)
    for i, resp in enumerate(samples, 1):
        print(f"第{i}个问题的回答内容：{resp['response']}\n检索内容：{resp['retrieved_contexts']}")


    # 创建 OpenAI 兼容客户端（可对接 DashScope 等 OpenAI 协议网关）
    client = AsyncOpenAI(
        api_key=OPENAI_API_KEY,  # 评估 LLM 的 API Key
        base_url=OPENAI_BASE_URL,  # 可选：自定义 API 地址
    )
    # 评估用 LLM，供 faithfulness / context_* 等需要 LLM 判分的指标使用
    llm = llm_factory("qwen-plus", provider="openai", client=client, max_tokens=32768)
    # 评估用 Embedding，answer_relevancy 需计算问题与回答的向量相似度
    emb = OpenAIEmbeddings(model="text-embedding-v3", client=client)

    # 实例化四个 RAGAS 指标（均绑定同一套 llm，保证评判模型一致）
    faithfulness = Faithfulness(llm=llm)
    context_recall = ContextRecall(llm=llm)
    context_precision = ContextPrecision(llm=llm)
    answer_relevancy = AnswerRelevancy(llm=llm, embeddings=emb)  # 仅此指标额外需要 embeddings

    # 按指标名收集各样本得分，用于最后算平均值
    scores = {n: [] for n in ("faithfulness", "context_recall", "context_precision", "answer_relevancy")}
    print("\n[RAGAS]")  # 进入 RAGAS 打分阶段
    for i, s in enumerate(samples, 1):  # 逐条样本评估，i 从 1 开始便于阅读输出
        # 拆出 RAGAS 各指标需要的字段缩写
        ui, resp, ctx, ref = s["user_input"], s["response"], s["retrieved_contexts"], s["reference"]
        row = {}  # 当前样本在本轮得到的各指标分数
        if resp and ctx:  # 忠实度需要「有回答」且「有检索上下文」
            # ascore 异步打分，.value 取 0~1 的浮点结果
            row["faithfulness"] = (await faithfulness.ascore(ui, resp, ctx)).value
        if ctx:  # 上下文类指标至少需要检索结果非空
            # 召回率：标准答案中的陈述能否在检索上下文中找到依据
            row["context_recall"] = (await context_recall.ascore(ui, ctx, ref)).value
            # 准确率：检索到的片段与标准答案的相关性及其排序质量
            row["context_precision"] = (await context_precision.ascore(ui, ref, ctx)).value
        if resp:  # 回答相关性只需要有问题和模型回答
            row["answer_relevancy"] = (await answer_relevancy.ascore(ui, resp)).value
        for k, v in row.items():  # 将本样本各指标分数汇入总表
            scores[k].append(v)
        # 打印当前样本编号、问题摘要及各项得分（保留 4 位小数）
        print(f"  {i}. {ui[:24]}…  " + "  ".join(f"{k}={v:.4f}" for k, v in row.items()))

    print("\n[平均]")  # 输出全数据集各指标均值
    for k, vals in scores.items():  # 遍历四个指标名及其得分列表
        # 有有效分数则求平均；若某指标全部被跳过则提示无样本
        print(f"  {k}: {sum(vals) / len(vals):.4f}" if vals else f"  {k}: (无有效样本)")


if __name__ == "__main__":  # 仅在被直接执行时运行（被 import 时不执行）
    asyncio.run(main())  # 在事件循环中运行异步 main，直到评估结束

# 暴露的问题：
# 第一个问题：policy节点，上下文准确率低：检索内容的相关性排序
# 第二个问题：tech节点，忠诚度低：温度调的高，允许LLM拓展，所以不是很忠诚
# 第三个问题：mixed节点，检索的内容topK太长，无关内容太多