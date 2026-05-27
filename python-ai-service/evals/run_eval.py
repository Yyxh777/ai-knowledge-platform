"""
RAGAS 评估脚本 - Step 3 & 4：准备数据 + 跑通评估

用法：
    conda activate my_ap
    cd python-ai-service
    python evals/run_eval.py

前置条件：
    - Milvus 已启动且有数据
    - .env 中已配置 OPENAI_API_KEY / OPENAI_BASE_URL / DASHSCOPE_API_KEY
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from ragas.llms import llm_factory
from ragas.embeddings import OpenAIEmbeddings
from ragas.metrics.collections import Faithfulness, AnswerRelevancy
from openai import AsyncOpenAI

from rag_workflows.rag_graph import create_classification_graph
from langgraph.checkpoint.memory import InMemorySaver


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 第一步：定义测试问题 + 标准答案 (reference)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 第二步：调用 RAG 管线收集 retrieved_contexts 和 response
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def run_rag_pipeline(question: str) -> dict:
    """调用项目的 LangGraph RAG 管线，返回检索结果和生成的回答"""
    graph = create_classification_graph(checkpointer=InMemorySaver())

    initial_state = {
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

    config = {"configurable": {"thread_id": "eval_session", "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJibGFkZXguY24iLCJhdWQiOlsiYmxhZGV4Il0sInRva2VuX3R5cGUiOiJhY2Nlc3NfdG9rZW4iLCJjbGllbnRfaWQiOiJzYWJlcjMiLCJ0ZW5hbnRfaWQiOiIwMDAwMDAiLCJ1c2VyX2lkIjoiMTEyMzU5ODgyMTczODY3NTIwMSIsImRlcHRfaWQiOiIxMTIzNTk4ODEzNzM4Njc1MjAxIiwicG9zdF9pZCI6IjExMjM1OTg4MTc3Mzg2NzUyMDEiLCJyb2xlX2lkIjoiMTEyMzU5ODgxNjczODY3NTIwMSIsImFjY291bnQiOiJhZG1pbiIsInVzZXJfbmFtZSI6ImFkbWluIiwibmlja19uYW1lIjoi566h55CG5ZGYIiwicmVhbF9uYW1lIjoi566h55CG5ZGYIiwicm9sZV9uYW1lIjoiYWRtaW5pc3RyYXRvciIsImRldGFpbCI6eyJ0eXBlIjoid2ViIn0sImV4cCI6MTc3OTc5MTM1NSwibmJmIjoxNzc5Nzg3NzU1fQ.x4i3Tt4rY_EFn94BrFOhmO9Zz1AiEB9AB7eav1FMFbk"}}

    result = await graph.ainvoke(initial_state, config=config)

    return {
        "retrieved_contexts": [
            doc["content"] for doc in result.get("retrieved_docs", [])
        ],
        "response": result.get("answer", ""),
        "question_type": result.get("question_type", ""),
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 第三步：配置评估 LLM + Embeddings
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def create_eval_components():
    """创建 RAGAS 评估用的 LLM 和 Embeddings"""
    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL", "")

    if not api_key:
        raise ValueError("请在 .env 中设置 OPENAI_API_KEY")

    client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    eval_llm = llm_factory("qwen-plus", provider="openai", client=client, max_tokens=4096)

    eval_embeddings = OpenAIEmbeddings(
        model="text-embedding-v3",
        client=client,
    )

    return eval_llm, eval_embeddings


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 第四步：运行评估
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# RAGAS 0.4.3 collections 指标的调用方式：
#   Faithfulness.ascore(user_input: str, response: str, retrieved_contexts: List[str])
#       -> MetricResult (用 .value 取 float)
#   AnswerRelevancy.ascore(user_input: str, response: str)
#       -> MetricResult (用 .value 取 float)

async def score_faithfulness(metric, user_input, response, retrieved_contexts):
    """包装 Faithfulness 评分调用"""
    result = await metric.ascore(
        user_input=user_input,
        response=response,
        retrieved_contexts=retrieved_contexts,
    )
    return result.value


async def score_answer_relevancy(metric, user_input, response):
    """包装 AnswerRelevancy 评分调用"""
    result = await metric.ascore(
        user_input=user_input,
        response=response,
    )
    return result.value


async def main():
    print("=" * 70)
    print("RAGAS 评估开始")
    print("=" * 70)

    # 1. 运行 RAG 管线，收集每个问题的检索结果和回答
    print("\n[1/4] 运行 RAG 管线收集数据...")
    rag_results = []
    for item in TEST_DATA:
        question = item["user_input"]
        print(f"\n  问题: {question}")

        rag_result = await run_rag_pipeline(question)

        print(f"  分类: {rag_result['question_type']}")
        print(f"  检索文档数: {len(rag_result['retrieved_contexts'])}")
        print(f"  回答长度: {len(rag_result['response'])} 字")
        print(f"  回答内容: {rag_result['response']}")

        rag_results.append({
            **item,
            "retrieved_contexts": rag_result["retrieved_contexts"],
            "response": rag_result["response"],
            "question_type": rag_result["question_type"],
        })

    # 2. 配置评估 LLM + Embeddings + 指标
    print("\n[2/4] 配置评估指标...")
    eval_llm, eval_embeddings = create_eval_components()

    faithfulness_metric = Faithfulness(llm=eval_llm)
    answer_relevancy_metric = AnswerRelevancy(llm=eval_llm, embeddings=eval_embeddings)
    print(f"  指标: [{faithfulness_metric.name}, {answer_relevancy_metric.name}]")

    # 3. 逐条评分
    print("\n[3/4] 开始评分...")
    print("=" * 70)

    all_results = []
    for i, item in enumerate(rag_results):
        print(f"\n样本 {i + 1}/{len(rag_results)}: {item['user_input']}")

        # Faithfulness 需要 retrieved_contexts 非空，否则跳过
        f_score = None
        if item["retrieved_contexts"] and item["response"]:
            try:
                f_score = await score_faithfulness(
                    faithfulness_metric,
                    user_input=item["user_input"],
                    response=item["response"],
                    retrieved_contexts=item["retrieved_contexts"],
                )
                print(f"  {faithfulness_metric.name}: {f_score:.4f}")
            except Exception as e:
                print(f"  {faithfulness_metric.name}: 评分失败 ({type(e).__name__}: {e})")
        else:
            print(f"  {faithfulness_metric.name}: 跳过 (检索结果或回答为空)")

        # AnswerRelevancy 需要 response 非空
        ar_score = None
        if item["response"]:
            try:
                ar_score = await score_answer_relevancy(
                    answer_relevancy_metric,
                    user_input=item["user_input"],
                    response=item["response"],
                )
                print(f"  {answer_relevancy_metric.name}: {ar_score:.4f}")
            except Exception as e:
                print(f"  {answer_relevancy_metric.name}: 评分失败 ({type(e).__name__}: {e})")
        else:
            print(f"  {answer_relevancy_metric.name}: 跳过 (回答为空)")

        all_results.append({
            "sample": i + 1,
            "question": item["user_input"],
            "question_type": item["question_type"],
            "faithfulness": f_score,
            "answer_relevancy": ar_score,
        })

    # 4. 汇总
    print("\n" + "=" * 70)
    print("评估汇总")
    print("=" * 70)

    f_scores = [r["faithfulness"] for r in all_results if r["faithfulness"] is not None]
    ar_scores = [r["answer_relevancy"] for r in all_results if r["answer_relevancy"] is not None]

    f_avg = sum(f_scores) / len(f_scores) if f_scores else 0
    ar_avg = sum(ar_scores) / len(ar_scores) if ar_scores else 0

    print(f"  Faithfulness     (忠实度):      平均 {f_avg:.4f}")
    print(f"  AnswerRelevancy  (回答相关性):  平均 {ar_avg:.4f}")
    print(f"\n  样本数: {len(all_results)}")

    print("\n评估完成！")


if __name__ == "__main__":
    asyncio.run(main())
