#!/usr/bin/env python3
"""
文献总结模块
利用 LLM 对论文全文进行总结
"""

import json
import logging
import re
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from llm_client import LLMConfig, LLMClient

logger = logging.getLogger(__name__)


@dataclass
class SummaryResult:
    """论文总结结果"""
    title: str
    summary: str
    key_points: List[str]
    methodology: str
    conclusions: str
    limitations: str
    novelty: str
    applications: List[str]
    related_work: str
    score: float
    tags: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'title': self.title,
            'summary': self.summary,
            'key_points': self.key_points,
            'methodology': self.methodology,
            'conclusions': self.conclusions,
            'limitations': self.limitations,
            'novelty': self.novelty,
            'applications': self.applications,
            'related_work': self.related_work,
            'score': self.score,
            'tags': self.tags
        }


class PaperSummarizer:
    """论文总结器"""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def summarize_paper(self, title: str, text: str, keywords: List[str]) -> Optional[SummaryResult]:
        """
        对论文全文进行总结

        Args:
            title: 论文标题
            text: 论文全文文本
            keywords: 相关关键词列表

        Returns:
            总结结果，如果总结失败则返回 None
        """
        if not title or not text:
            logger.warning("标题或文本为空")
            return None

        logger.info(f"总结论文: {title[:50]}...")

        max_text_length = 100000
        if len(text) > max_text_length:
            logger.info(f"文本过长 ({len(text)} 字符)，截断到 {max_text_length} 字符")
            text = text[:max_text_length]

        keywords_str = ', '.join(keywords[:10])

        prompt = f"""请对以下学术论文进行详细总结。

【论文标题】
{title}

【论文全文】
{text}

【相关关键词】
{keywords_str}

请严格按照以下JSON格式输出总结结果：

{{
    "title": "论文标题",
    "summary": "300-500字的详细总结，包括研究背景、目的、方法、主要发现等",
    "key_points": [
        "关键点1：具体描述",
        "关键点2：具体描述",
        "关键点3：具体描述",
        "关键点4：具体描述",
        "关键点5：具体描述"
    ],
    "methodology": "100-200字的研究方法描述",
    "conclusions": "100-200字的主要结论总结",
    "limitations": "100-150字的局限性分析",
    "novelty": "50-100字的创新点描述",
    "applications": [
        "应用场景1",
        "应用场景2"
    ],
    "related_work": "50-100字的相关工作简述",
    "score": 0-10的数字评分,
    "tags": ["标签1", "标签2", "标签3", "标签4", "标签5"]
}}

注意：
- 必须输出有效的JSON格式，不要包含任何其他内容
- score必须是0-10的数字
- key_points必须是数组格式
- 所有字段都必须填写"""

        system_prompt = '你是一个学术论文分析专家，擅长对论文进行详细总结和分析。请严格按照JSON格式输出。'
        response = self.llm_client.call_llm(prompt, system_prompt)
        # logger.info(response)

        if not response:
            logger.error("LLM 调用失败")
            return None

        return self._parse_json_response(response, title)

    def _parse_json_response(self, response: str, title: str) -> Optional[SummaryResult]:
        """解析JSON格式的响应"""
        try:
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            elif response.startswith('```'):
                response = response[3:]
            if response.endswith('```'):
                response = response[:-3]

            response = response.strip()

            data = json.loads(response)

            result = SummaryResult(
                title=data.get('title', title),
                summary=data.get('summary', ''),
                key_points=data.get('key_points', []),
                methodology=data.get('methodology', ''),
                conclusions=data.get('conclusions', ''),
                limitations=data.get('limitations', ''),
                novelty=data.get('novelty', ''),
                applications=data.get('applications', []),
                related_work=data.get('related_work', ''),
                score=float(data.get('score', 5.0)),
                tags=data.get('tags', [])
            )

            logger.info(f"论文总结完成，评分: {result.score:.1f}/10")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            logger.error(f"原始响应: {response[:500]}")
            return self._fallback_parse(response, title)
        except Exception as e:
            logger.error(f"解析总结响应失败: {e}")
            return None

    def _fallback_parse(self, response: str, title: str) -> Optional[SummaryResult]:
        """备用解析方法：当JSON解析失败时使用"""
        try:
            summary_match = re.search(r'"summary"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', response)
            key_points_match = re.findall(r'"key_points"\s*:\s*\[([^\]]+)\]', response)
            methodology_match = re.search(r'"methodology"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', response)
            conclusions_match = re.search(r'"conclusions"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', response)
            limitations_match = re.search(r'"limitations"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', response)
            score_match = re.search(r'"score"\s*:\s*(\d+\.?\d*)', response)

            key_points = []
            if key_points_match:
                kp_text = key_points_match[0]
                key_points = re.findall(r'"([^"]+)"', kp_text)

            result = SummaryResult(
                title=title,
                summary=summary_match.group(1) if summary_match else response[:500],
                key_points=key_points,
                methodology=methodology_match.group(1) if methodology_match else '',
                conclusions=conclusions_match.group(1) if conclusions_match else '',
                limitations=limitations_match.group(1) if limitations_match else '',
                novelty='',
                applications=[],
                related_work='',
                score=float(score_match.group(1)) if score_match else 5.0,
                tags=[]
            )

            logger.info(f"论文总结完成（备用解析），评分: {result.score:.1f}/10")
            return result

        except Exception as e:
            logger.error(f"备用解析也失败: {e}")
            return None


if __name__ == "__main__":
    import os

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    api_key = os.environ.get('LLM_API_KEY', '')
    if not api_key:
        print("请设置 LLM_API_KEY 环境变量")
        exit(1)

    config = LLMConfig(
        api_key=api_key,
        model="tongyi-xiaomi-analysis-pro",
        api_url="dashscope"
    )

    llm_client = LLMClient(config)
    summarizer = PaperSummarizer(llm_client)

    test_title = "Market Structure and Innovation in the Automobile Industry"
    test_text = """This paper examines how market concentration affects R&D investment in the automobile industry.
    We use data from 1990-2020 for major automobile manufacturers across multiple countries.
    Our findings suggest that moderate competition promotes innovation, while both monopolies and perfect competition may hinder R&D investment.
    We employ a panel data regression model and find significant relationships between market structure variables and innovation outputs.
    The study contributes to the literature by providing new evidence on the relationship between competition and innovation in a specific industry context."""

    test_keywords = ["market structure", "innovation", "automobile industry"]

    result = summarizer.summarize_paper(test_title, test_text, test_keywords)
    if result:
        print("\n=== 论文总结结果 ===")
        print(f"\n标题: {result.title}")
        print(f"\n详细总结: {result.summary}")
        print(f"\n关键点:")
        for i, point in enumerate(result.key_points, 1):
            print(f"  {i}. {point}")
        print(f"\n研究方法: {result.methodology}")
        print(f"\n结论: {result.conclusions}")
        print(f"\n局限性: {result.limitations}")
        print(f"\n创新点: {result.novelty}")
        print(f"\n应用场景: {result.applications}")
        print(f"\n相关工作: {result.related_work}")
        print(f"\n评分: {result.score}/10")
        print(f"\n标签: {result.tags}")
    else:
        print("总结失败")
