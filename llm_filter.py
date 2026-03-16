#!/usr/bin/env python3
"""
大模型筛选模块
使用 LLM 判断论文与关键词的相关性
"""

import os
import logging
from typing import List, Dict, Tuple
from dataclasses import dataclass
from llm_client import LLMConfig, LLMClient

logger = logging.getLogger(__name__)


class LLMFilter:
    """大模型论文筛选器"""
    
    def __init__(self, config: LLMConfig, delay: float = 2.0, max_retries: int = 3):
        self.config = config
        self.delay = delay  # 请求之间的延迟（秒）
        self.max_retries = max_retries  # 最大重试次数
        self.llm_client = LLMClient(config, delay, max_retries)
    
    def _call_llm(self, prompt: str) -> str:
        """调用大模型 API"""
        system_prompt = '你是一个学术论文分析专家，擅长判断论文与特定研究领域的相关性。'
        return self.llm_client.call_llm(prompt, system_prompt)
    
    def evaluate_relevance(self, paper_title: str, paper_summary: str, keywords: List[str]) -> Tuple[float, str]:
        """
        评估论文与关键词的相关性
        
        Args:
            paper_title: 论文标题
            paper_summary: 论文摘要
            keywords: 关键词列表
            
        Returns:
            (相关度分数 0-10, 评估理由)
        """
        keywords_str = ', '.join(keywords[:10])  # 最多取10个关键词
        
        prompt = f"""请评估以下学术论文与给定研究关键词的相关性。

【研究关键词】
{keywords_str}

【论文标题】
{paper_title}

【论文摘要】
{paper_summary[:2000]}  # 限制摘要长度

请按以下格式回复：
相关度分数: [0-10的数字，10表示高度相关，0表示完全不相关]
评估理由: [简要说明为什么给出这个分数，100字以内]

注意：
- 只看论文是否真的研究关键词涉及的主题
- 不要仅因为提到关键词就给出高分
- 要判断论文的核心贡献是否与关键词领域匹配"""

        response = self._call_llm(prompt)
        
        if not response:
            return 0.0, "LLM 调用失败"
        
        # 解析响应
        score = 0.0
        reason = ""
        
        try:
            # 尝试解析分数
            for line in response.split('\n'):
                line = line.strip()
                if '相关度分数' in line or '分数' in line:
                    # 提取数字
                    import re
                    numbers = re.findall(r'\d+\.?\d*', line)
                    if numbers:
                        score = float(numbers[0])
                        if score > 10:  # 如果分数是100分制，转换为10分制
                            score = score / 10
                        score = min(10, max(0, score))  # 限制在0-10
                
                if '评估理由' in line or '理由' in line:
                    reason = line.split(':', 1)[-1].strip()
            
            if not reason:
                reason = response[:200]  # 如果没解析出理由，取前200字
                
        except Exception as e:
            logger.error(f"解析 LLM 响应失败: {e}")
            reason = response[:200] if response else "解析失败"
        
        return score, reason
    
    def filter_papers(self, papers: List, keywords: List[str], min_score: float = 5.0, top_n: int = None) -> List:
        """
        使用 LLM 筛选论文
        
        Args:
            papers: 论文列表
            keywords: 关键词列表
            min_score: 最低相关度分数
            top_n: 只取前N篇（按分数排序）
            
        Returns:
            筛选后的论文列表
        """
        import time
        import random
        
        logger.info(f"开始使用 LLM 筛选 {len(papers)} 篇论文...")
        logger.info(f"请求延迟: {self.delay}秒, 最大重试次数: {self.max_retries}")
        
        scored_papers = []
        
        for i, paper in enumerate(papers):
            logger.info(f"  评估第 {i+1}/{len(papers)} 篇: {paper.title[:50]}...")
            
            # 带重试的评估
            score, reason = 0.0, "评估失败"
            for attempt in range(self.max_retries):
                try:
                    score, reason = self.evaluate_relevance(
                        paper.title, 
                        paper.summary, 
                        keywords
                    )
                    if score > 0:  # 成功获取到分数
                        break
                except Exception as e:
                    logger.warning(f"    第 {attempt + 1} 次尝试失败: {e}")
                    if attempt < self.max_retries - 1:
                        # 指数退避: 2, 4, 8 秒
                        retry_delay = (2 ** attempt) + random.uniform(0, 1)
                        logger.info(f"    等待 {retry_delay:.1f} 秒后重试...")
                        time.sleep(retry_delay)
            
            # 将分数添加到论文对象
            paper.llm_score = score
            paper.llm_reason = reason
            
            logger.info(f"    分数: {score:.1f}/10, 理由: {reason[:80]}...")
            
            if score >= min_score:
                scored_papers.append((score, paper))
            
            # 延迟，避免 API 限制（Gemini 建议至少 1-2 秒）
            if i < len(papers) - 1:  # 最后一篇不需要延迟
                time.sleep(self.delay)
        
        # 按分数排序
        scored_papers.sort(key=lambda x: -x[0])
        
        # 取前N篇
        if top_n and len(scored_papers) > top_n:
            scored_papers = scored_papers[:top_n]
        
        result = [paper for _, paper in scored_papers]
        
        logger.info(f"LLM 筛选完成: 从 {len(papers)} 篇中选出 {len(result)} 篇 (最低分数: {min_score})")
        
        return result


def load_llm_config_from_env() -> LLMConfig:
    """从环境变量加载 LLM 配置"""
    api_key = os.environ.get('LLM_API_KEY', '')
    model = os.environ.get('LLM_MODEL', 'gpt-3.5-turbo')
    api_url = os.environ.get('LLM_API_URL', 'openai')
    
    if not api_key:
        raise ValueError("未设置 LLM_API_KEY")
    
    return LLMConfig(
        api_key=api_key,
        model=model,
        api_url=api_url
    )


# 测试代码
if __name__ == "__main__":
    # 测试配置
    config = LLMConfig(
        api_key="your-api-key",
        model="gpt-3.5-turbo",
        api_url="openai"
    )
    
    filter = LLMFilter(config)
    
    # 测试评估
    title = "Market Structure and Innovation in the Automobile Industry"
    summary = "This paper examines how market concentration affects R&D investment..."
    keywords = ["market structure", "innovation", "automobile industry"]
    
    score, reason = filter.evaluate_relevance(title, summary, keywords)
    print(f"分数: {score}")
    print(f"理由: {reason}")
