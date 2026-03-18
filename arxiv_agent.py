#!/usr/bin/env python3
"""
arXiv 每日文章推送智能体
分块筛选策略：
- 两大主题
- 每主题分核心关键词（引用前N篇）和扩展关键词（引用前M篇）
- 数量可配置
"""

import os
import re
import yaml
import json
import logging
import feedparser
import requests
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass, field
from pathlib import Path
from collections import defaultdict

# 导入邮件发送模块
try:
    from email_sender import EmailSender
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False

# 导入 LLM 相关模块
try:
    from llm_client import LLMConfig, LLMClient
    from llm_filter import LLMFilter, load_llm_config_from_env
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

# 导入多源学术搜索模块
try:
    from multi_searcher import MultiSourceSearcher, Paper, ArxivSearcher
    SCHOLAR_AVAILABLE = True
except ImportError:
    SCHOLAR_AVAILABLE = False

# 导入 PDF 读取模块
try:
    from pdf_reader import PDFReader
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# 导入论文总结模块
try:
    from paper_summarizer import PaperSummarizer
    SUMMARIZER_AVAILABLE = True
except ImportError:
    SUMMARIZER_AVAILABLE = False

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Paper:
    """论文数据结构"""
    title: str
    authors: List[str]
    summary: str
    link: str
    pdf_link: str
    published: datetime
    categories: List[str]
    primary_category: str
    external_id: str = ""
    citation_count: int = 0
    matched_keywords: List[str] = field(default_factory=list)
    source_block: str = ""  # 来源主题块
    keyword_type: str = ""  # core 或 extended
    full_text: str = ""  # 全文文本
    paper_summary: dict = field(default_factory=dict)  # 论文总结
    
    def to_dict(self) -> Dict:
        return {
            'title': self.title,
            'authors': self.authors,
            'summary': self.summary[:500] + '...' if len(self.summary) > 500 else self.summary,
            'link': self.link,
            'pdf_link': self.pdf_link,
            'published': self.published.strftime('%Y-%m-%d'),
            'categories': self.categories,
            'primary_category': self.primary_category,
            'external_id': self.external_id,
            'citation_count': self.citation_count,
            'matched_keywords': self.matched_keywords,
            'source_block': self.source_block,
            'keyword_type': self.keyword_type,
            'full_text': self.full_text[:100] + '...' if len(self.full_text) > 100 else self.full_text,
            'paper_summary': self.paper_summary
        }


class KeywordBlock:
    """关键词块 - 代表一个主题领域"""
    
    def __init__(self, name: str, core_keywords: List[str], extended_keywords: List[str]):
        self.name = name
        self.core_keywords = core_keywords
        self.extended_keywords = extended_keywords
        self.all_keywords = core_keywords + extended_keywords
        
        # 生成搜索查询（只使用扩展关键词）
        self.search_queries = self._generate_queries()
    
    def _generate_queries(self) -> List[str]:
        """生成英文搜索查询（只使用扩展关键词）"""
        translations = {
            # AI Agent
            "知识图谱" : "knowledge graph"
        }
        
        queries = set()
        for kw in self.extended_keywords:
            kw_clean = kw.strip().lower()
            # 移除 ** 标记
            kw_clean = kw_clean.replace('**', '').strip()
            
            if not kw_clean:
                continue
                
            # 直接使用英文关键词
            if kw_clean.isascii():
                queries.add(kw_clean)
            # 使用翻译后的英文
            elif kw in translations:
                queries.add(translations[kw])
            elif kw_clean in translations:
                queries.add(translations[kw])
        
        # 如果没有扩展关键词，使用默认查询
        return list(queries) if queries else ['agent for biology', 'knowledge graph']


class KeywordManager:
    """关键词管理器 - 管理多个主题块"""
    
    def __init__(self, keywords_file: str = "keywords.txt"):
        self.keywords_file = keywords_file
        self.blocks: List[KeywordBlock] = []
        self._load_keywords()
    
    def _load_keywords(self):
        """从文件加载关键词，支持 ** 标记区分核心和扩展"""
        if not os.path.exists(self.keywords_file):
            raise FileNotFoundError(f"关键词文件不存在: {self.keywords_file}")
        
        with open(self.keywords_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 分割成块（用空行分隔）
        raw_blocks = re.split(r'\n\s*\n', content.strip())
        
        for raw_block in raw_blocks:
            lines = [line.strip() for line in raw_block.strip().split('\n') if line.strip()]
            if not lines:
                continue
            
            # 第一行是块名称/主题描述
            block_name = lines[0]
            # 如果第一行以 ** 开头，说明没有主题名称，直接是关键词
            if block_name.startswith('**'):
                block_name = f"主题块{len(self.blocks) + 1}"
                keyword_lines = lines
            else:
                # 第1行是主题名称，从第2行开始是关键词
                keyword_lines = lines[1:]
            
            # 分离核心关键词和扩展关键词
            # 核心关键词：**关键词** 或没有标记的
            # 扩展关键词：普通关键词或标记为扩展的
            core_keywords = []
            extended_keywords = []
            
            for line in keyword_lines:
                # 跳过标题行
                if '关键词' in line.lower() or line.endswith('关键词'):
                    continue
                
                # 分割一行中的多个关键词（支持 / 分隔）
                sub_keywords = re.split(r'[、,，/]+', line)
                
                for kw in sub_keywords:
                    kw = kw.strip()
                    if not kw or len(kw) <= 1:
                        continue
                    
                    # 检查是否是 ** 标记的核心关键词
                    if kw.startswith('**') and kw.endswith('**'):
                        # **关键词** 格式
                        core_keywords.append(kw.replace('**', '').strip())
                    elif kw.startswith('**'):
                        # **关键词 格式（行尾没有**）
                        core_keywords.append(kw.replace('**', '').strip())
                    elif '**' in kw:
                        # 关键词** 格式
                        core_keywords.append(kw.replace('**', '').strip())
                    else:
                        # 普通关键词，作为扩展
                        extended_keywords.append(kw)
            
            if core_keywords or extended_keywords:
                block = KeywordBlock(block_name, core_keywords, extended_keywords)
                self.blocks.append(block)
                logger.info(f"加载主题块 '{block_name}':")
                logger.info(f"  核心关键词: {core_keywords}")
                logger.info(f"  扩展关键词: {extended_keywords}")
                logger.info(f"  搜索查询: {block.search_queries}")
        
        if not self.blocks:
            logger.warning("未找到关键词块，创建默认块")
            self.blocks = [
                KeywordBlock("产业组织", ['market structure', 'industrial organization'], ['pricing']),
                KeywordBlock("航运环境", ['shipping', 'carbon emission'], ['maritime'])
            ]


class CitationFetcher:
    """引用次数获取器"""
    
    API_URL = "https://api.semanticscholar.org/graph/v1/paper/"
    
    def get_citation_count(self, arxiv_id: str) -> int:
        """获取论文的引用次数"""
        if not arxiv_id:
            return 0
        
        try:
            url = f"{self.API_URL}arXiv:{arxiv_id}"
            params = {'fields': 'citationCount'}
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('citationCount', 0) or 0
            return 0
                
        except Exception:
            return 0
    
    def batch_get_citations(self, papers: List[Paper]) -> None:
        """批量获取引用次数"""
        if not papers:
            return
            
        logger.info(f"正在获取 {len(papers)} 篇论文的引用次数...")
        
        for i, paper in enumerate(papers):
            if paper.external_id:
                paper.citation_count = self.get_citation_count(paper.external_id)
                if (i + 1) % 10 == 0:
                    logger.info(f"  已处理 {i + 1}/{len(papers)} 篇")
                import time
                time.sleep(0.3)
        
        logger.info("引用次数获取完成")



class ArxivAgent:
    """arXiv 文章推送智能体主类"""
    
    def __init__(self, config_file: str = "config.yaml"):
        self.config = self._load_config(config_file)
        self.keyword_manager = KeywordManager(self.config.get('keywords_file', 'keywords.txt'))
        
        # 获取搜索源配置（默认 multi，可选 arxiv, biorxiv, openalex）
        self.search_source = self.config.get('search_source', 'multi')
        logger.info(f"搜索源: {self.search_source}")
        
        # 获取排序配置
        sort_by = self.config.get('sort_by', 'relevance')
        logger.info(f"搜索排序方式: {sort_by} ({'相关性' if sort_by == 'relevance' else '提交日期'})")
        
        # 初始化搜索器
        self.searcher = None
        self.multi_searcher = None
        
        if self.search_source == 'arxiv':
            self.searcher = ArxivSearcher(
                max_results_per_query=self.config.get('max_results_per_query', 100),
                sort_by=sort_by
            )
        elif SCHOLAR_AVAILABLE and self.search_source in ('multi', 'biorxiv', 'openalex', 'pubmed'):
            self.multi_searcher = MultiSourceSearcher(
                openalex_email=self.config.get('openalex_email'),
                pubmed_email=self.config.get('pubmed_email'),
                pubmed_api_key=self.config.get('pubmed_api_key'),
                max_results_per_query=self.config.get('max_results_per_query', 100),
                sort_by=sort_by
            )
            logger.info("多源搜索已初始化，包含 arXiv、bioRxiv、OpenAlex 和 PubMed")
        else:
            # 默认使用 arXiv
            self.searcher = ArxivSearcher(
                max_results_per_query=self.config.get('max_results_per_query', 100),
                sort_by=sort_by
            )
            logger.info("使用默认搜索源: arXiv")
        
        self.citation_fetcher = CitationFetcher()
        
        # 邮件发送器
        self.email_sender: Optional[EmailSender] = None
        if EMAIL_AVAILABLE and self.config.get('email', {}).get('enabled', False):
            try:
                self.email_sender = EmailSender(self.config['email'])
                logger.info("✅ 邮件发送功能已启用")
            except Exception as e:
                logger.error(f"邮件发送器初始化失败: {e}")
        
        # LLM 客户端
        self.llm_client: Optional[LLMClient] = None
        if LLM_AVAILABLE and self.config.get('llm', {}).get('enabled', False):
            try:
                llm_config = LLMConfig(
                    api_key=self.config['llm']['api_key'],
                    model=self.config['llm']['model'],
                    api_url=self.config['llm'].get('api_url', 'openai'),
                    temperature=self.config['llm'].get('temperature', 0.3),
                    max_tokens=self.config['llm'].get('max_tokens', 1000)
                )
                # 获取延迟和重试配置（Gemini 建议延迟至少 2 秒）
                delay = self.config['llm'].get('delay', 2.0)
                max_retries = self.config['llm'].get('max_retries', 3)
                self.llm_client = LLMClient(llm_config, delay=delay, max_retries=max_retries)
                logger.info(f"✅ LLM 客户端已初始化 (模型: {llm_config.model}, 延迟: {delay}s)")
            except Exception as e:
                logger.error(f"LLM 客户端初始化失败: {e}")
        
        # LLM 筛选器
        self.llm_filter: Optional[LLMFilter] = None
        if self.llm_client:
            try:
                self.llm_filter = LLMFilter(self.llm_client.config, self.llm_client.delay, self.llm_client.max_retries)
                logger.info("✅ LLM 筛选功能已启用")
            except Exception as e:
                logger.error(f"LLM 筛选器初始化失败: {e}")
        
        # PDF 读取器
        self.pdf_reader: Optional[PDFReader] = None
        if PDF_AVAILABLE:
            try:
                self.pdf_reader = PDFReader()
                logger.info("✅ PDF 读取功能已启用")
            except Exception as e:
                logger.error(f"PDF 读取器初始化失败: {e}")
        
        # 论文总结器
        self.paper_summarizer: Optional[PaperSummarizer] = None
        if SUMMARIZER_AVAILABLE and self.llm_client:
            try:
                self.paper_summarizer = PaperSummarizer(self.llm_client)
                logger.info("✅ 论文总结功能已启用")
            except Exception as e:
                logger.error(f"论文总结器初始化失败: {e}")
        
        # 去重存储
        self.seen_ids: Set[str] = set()
        self.history_file = self.config.get('history_file', 'paper_history.json')
        self._load_history()
    
    def _load_config(self, config_file: str) -> Dict:
        """加载配置文件"""
        default_config = {
            'keywords_file': 'keywords.txt',
            'max_results_per_query': 100,
            'days_back': 3,  # 默认搜索最近3天
            'output_dir': 'daily_papers',
            'history_file': 'paper_history.json',
            'email': {'enabled': False},
            'block_config': {
                'core_limit': 30,
                'extended_limit': 10,
            }
        }
        
        # 加载 YAML 配置
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                yaml_config = yaml.safe_load(f)
                if yaml_config:
                    default_config.update(yaml_config)
        
        # 加载环境变量配置
        env_config = self._load_config_from_env()
        if env_config:
            default_config.update(env_config)
        
        return default_config
    
    def _load_config_from_env(self) -> Dict:
        """从环境变量加载配置"""
        config = {}
        
        email_enabled = os.environ.get('EMAIL_ENABLED', '').lower()
        if email_enabled in ('true', '1', 'yes'):
            config['email'] = {
                'enabled': True,
                'sender_email': os.environ.get('EMAIL_SENDER', ''),
                'sender_password': os.environ.get('EMAIL_PASSWORD', ''),
                'receiver_emails': [
                    e.strip() for e in os.environ.get('EMAIL_RECEIVERS', '').split(',')
                    if e.strip()
                ],
            }
        
        if os.environ.get('DAYS_BACK'):
            config['days_back'] = int(os.environ['DAYS_BACK'])
        
        if os.environ.get('SORT_BY'):
            config['sort_by'] = os.environ['SORT_BY']
        
        if os.environ.get('SEARCH_SOURCE'):
            config['search_source'] = os.environ['SEARCH_SOURCE']
        
        if os.environ.get('SEMANTIC_SCHOLAR_KEY'):
            config['semantic_scholar_key'] = os.environ['SEMANTIC_SCHOLAR_KEY']
        
        if os.environ.get('OPENALEX_EMAIL'):
            config['openalex_email'] = os.environ['OPENALEX_EMAIL']
        
        block_config = {}
        if os.environ.get('CORE_LIMIT'):
            block_config['core_limit'] = int(os.environ['CORE_LIMIT'])
        if os.environ.get('EXTENDED_LIMIT'):
            block_config['extended_limit'] = int(os.environ['EXTENDED_LIMIT'])
        if block_config:
            config['block_config'] = block_config
        
        # LLM 配置
        llm_api_key = os.environ.get('LLM_API_KEY', '')
        if llm_api_key:
            config['llm'] = {
                'enabled': True,
                'api_key': llm_api_key,
                'model': os.environ.get('LLM_MODEL', 'gpt-3.5-turbo'),
                'api_url': os.environ.get('LLM_API_URL', 'openai'),
                'min_score': float(os.environ.get('LLM_MIN_SCORE', '5.0')),
                'top_n': int(os.environ.get('LLM_TOP_N', '30')) if os.environ.get('LLM_TOP_N') else None
            }
        
        return config
    
    def _load_history(self):
        """加载已推送文章历史"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                    self.seen_ids = set(history.get('paper_ids', []))
                    logger.info(f"加载历史记录: {len(self.seen_ids)} 篇文章")
            except Exception as e:
                logger.warning(f"加载历史记录失败: {e}")
    
    def _save_history(self):
        """保存已推送文章历史"""
        history = {
            'paper_ids': list(self.seen_ids),
            'last_update': datetime.now().isoformat()
        }
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    
    def _convert_scholar_papers(self, scholar_papers: List) -> List[Paper]:
        """将 scholar_searcher 的 Paper 转换为 arxiv_agent 的 Paper"""
        converted = []
        for sp in scholar_papers:
            paper = Paper(
                title=sp.title,
                authors=sp.authors,
                summary=sp.summary,
                link=sp.link,
                pdf_link=sp.pdf_link,
                published=sp.published if sp.published else datetime.now(),
                categories=sp.categories,
                primary_category=sp.categories[0] if sp.categories else '',
                external_id=sp.external_id,
                citation_count=sp.citation_count
            )
            converted.append(paper)
        return converted
    
    def _get_paper_id(self, paper: Paper) -> str:
        """生成文章唯一ID"""
        return paper.external_id if paper.external_id else paper.title[:50]
    
    def _keyword_match(self, text: str, keywords: List[str]) -> Tuple[bool, List[str]]:
        """检查文本是否匹配关键词，返回(是否匹配, 匹配的关键词列表)"""
        text_lower = text.lower()
        matched = []
        
        for kw in keywords:
            kw_lower = kw.lower().strip()
            if not kw_lower:
                continue
            
            # 直接匹配
            if kw_lower in text_lower:
                matched.append(kw)
                continue
            
            # 处理空格差异
            if kw_lower.replace(' ', '') in text_lower.replace(' ', ''):
                matched.append(kw)
        
        return len(matched) > 0, matched
    
    def run(self, send_email: bool = True, reset_history: bool = False) -> str:
        """执行每日文章抓取和推送"""
        logger.info("=" * 60)
        logger.info("开始执行 arXiv 文章推送任务")
        logger.info("=" * 60)
        
        # 如果需要重置历史（用于测试）
        if reset_history:
            logger.info("重置历史记录")
            self.seen_ids = set()
        
        block_config = self.config.get('block_config', {})
        core_limit = block_config.get('core_limit', 30)
        extended_limit = block_config.get('extended_limit', 10)
        days_back = self.config.get('days_back', 90)
        
        logger.info(f"配置：核心关键词前{core_limit}篇，扩展关键词前{extended_limit}篇")
        logger.info(f"搜索最近 {days_back} 天的文章")
        
        all_selected_papers: List[Paper] = []
        
        # 对每个主题块进行处理
        for block in self.keyword_manager.blocks:
            logger.info(f"\n{'='*60}")
            logger.info(f"处理主题块: {block.name}")
            logger.info(f"{'='*60}")
            logger.info(f"核心关键词: {block.core_keywords}")
            logger.info(f"扩展关键词: {block.extended_keywords}")
            logger.info(f"搜索查询: {block.search_queries}")
            
            # 搜索该主题的所有查询词
            block_papers: List[Paper] = []
            
            for query in block.search_queries:
                if self.multi_searcher and self.search_source in ('multi', 'biorxiv', 'openalex', 'pubmed'):
                    # 使用多源搜索
                    try:
                        max_results = self.config.get('max_results_per_query', 100)
                        if self.search_source == 'multi':
                            papers = self._convert_scholar_papers(
                                self.multi_searcher.search_and_merge(query, days_back=days_back, max_per_source=max_results)
                            )
                            logger.info(f"多源搜索完成，获取到 {len(papers)} 篇文章")
                        elif self.search_source == 'biorxiv':
                            papers = self._convert_scholar_papers(
                                self.multi_searcher.searchers['biorxiv'].search(query, days_back, max_results)
                            )
                            logger.info(f"bioRxiv 搜索完成，获取到 {len(papers)} 篇文章")
                        elif self.search_source == 'pubmed':
                            papers = self._convert_scholar_papers(
                                self.multi_searcher.searchers['pubmed'].search(query, days_back, max_results)
                            )
                            logger.info(f"PubMed 搜索完成，获取到 {len(papers)} 篇文章")
                        else:  # openalex
                            papers = self._convert_scholar_papers(
                                self.multi_searcher.searchers['openalex'].search(query, days_back, max_results)
                            )
                            logger.info(f"OpenAlex 搜索完成，获取到 {len(papers)} 篇文章")
                    except Exception as e:
                        logger.error(f"多源搜索失败: {e}")
                        # 回退到 arXiv 搜索
                        logger.info("回退到 arXiv 搜索")
                        papers = self.searcher.search(query, days_back=days_back)
                else:
                    # 使用 arXiv 搜索
                    papers = self.searcher.search(query, days_back=days_back)
                
                for paper in papers:
                    paper_id = self._get_paper_id(paper)
                    if paper_id not in self.seen_ids:
                        paper.source_block = block.name
                        block_papers.append(paper)
                        self.seen_ids.add(paper_id)
                    else:
                        logger.debug(f"  跳过已存在的文章: {paper.title[:40]}...")
                import time
                time.sleep(1)
            
            logger.info(f"找到 {len(block_papers)} 篇新文章")
            
            if not block_papers:
                logger.warning(f"主题块 '{block.name}' 没有找到新文章")
                continue
            
            # 过滤：只保留标题或摘要中包含核心关键词的文章
            filtered_papers = []
            for paper in block_papers:
                title_summary = (paper.title + " " + paper.summary).lower()
                # 检查是否包含核心关键词
                for kw in block.core_keywords:
                    if kw.lower() in title_summary:
                        filtered_papers.append(paper)
                        break
            
            if len(filtered_papers) < len(block_papers):
                logger.info(f"过滤后剩余 {len(filtered_papers)} 篇相关文章 (过滤掉 {len(block_papers) - len(filtered_papers)} 篇)")
            
            block_papers = filtered_papers
            
            if not block_papers:
                logger.warning(f"主题块 '{block.name}' 过滤后没有相关文章")
                continue
            
            # 获取引用次数
            self.citation_fetcher.batch_get_citations(block_papers)
            
            # 按引用次数排序（高到低）
            block_papers.sort(key=lambda p: -p.citation_count)
            
            # 分类：核心关键词匹配 vs 扩展关键词匹配
            # 前core_limit篇为核心，后面为扩展
            core_papers = block_papers[:core_limit] if len(block_papers) >= core_limit else block_papers
            extended_papers = block_papers[core_limit:core_limit+extended_limit] if len(block_papers) > core_limit else []
            
            # 标记类型和匹配的关键词（所有文章都已通过核心关键词过滤）
            all_selected = core_papers + extended_papers
            for paper in all_selected:
                paper.keyword_type = "matched"
                # 找出匹配的核心关键词
                _, matched = self._keyword_match(paper.title + " " + paper.summary, block.core_keywords)
                paper.matched_keywords = matched if matched else ["matched"]
            
            logger.info(f"相关文章: {len(core_papers)} 篇 (核心) + {len(extended_papers)} 篇 (扩展) = {len(all_selected)} 篇")
            
            # 打印前几篇的匹配情况用于调试
            if core_papers:
                logger.info("核心文章示例:")
                for i, p in enumerate(core_papers[:3], 1):
                    kw_str = ','.join(p.matched_keywords[:2]) if p.matched_keywords else 'N/A'
                    logger.info(f"  {i}. {p.title[:60]}... (引用:{p.citation_count}, 关键词:{kw_str})")
            
            if extended_papers:
                logger.info("扩展文章示例:")
                for i, p in enumerate(extended_papers[:3], 1):
                    kw_str = ','.join(p.matched_keywords[:2]) if p.matched_keywords else 'N/A'
                    logger.info(f"  {i}. {p.title[:60]}... (引用:{p.citation_count}, 关键词:{kw_str})")
            
            # 合并该主题的文章（core_papers 和 extended_papers 已经是选取后的结果）
            block_selected = core_papers + extended_papers
            all_selected_papers.extend(block_selected)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"总共选取 {len(all_selected_papers)} 篇文章")
        logger.info(f"{'='*60}")
        
        if not all_selected_papers:
            logger.warning("没有找到任何文章，请检查：")
            logger.warning("  1. 关键词是否正确")
            logger.warning("  2. 搜索时间范围是否合适")
            logger.warning("  3. 是否需要重置历史记录")
            return ""
        
        # 按主题和引用次数排序
        all_selected_papers.sort(key=lambda p: (p.source_block, -p.citation_count))
        
        # 如果使用 LLM 筛选，进行二次过滤
        if self.llm_filter and len(all_selected_papers) > 0:
            logger.info(f"\n{'='*60}")
            logger.info("开始使用 LLM 进行相关性筛选...")
            logger.info(f"{'='*60}")
            
            llm_config = self.config.get('llm', {})
            min_score = llm_config.get('min_score', 5.0)
            top_n = llm_config.get('top_n')
            
            logger.info(f"LLM 筛选配置: 最低分数={min_score}, 最多选取={top_n or '不限'}")
            
            # 按主题分组论文
            block_papers = defaultdict(list)
            for paper in all_selected_papers:
                block_papers[paper.source_block].append(paper)
            
            # 为每个主题单独使用其关键词进行筛选
            filtered_papers = []
            for block_name, papers in block_papers.items():
                # 找到对应的关键词块
                block_keywords = []
                for block in self.keyword_manager.blocks:
                    if block.name == block_name:
                        block_keywords = block.all_keywords
                        break
                
                if not block_keywords:
                    logger.warning(f"主题 '{block_name}' 未找到对应的关键词")
                    continue
                
                logger.info(f"筛选主题 '{block_name}' 的 {len(papers)} 篇论文...")
                logger.info(f"使用关键词: {block_keywords[:5]}...")
                
                # 对该主题的论文进行筛选
                filtered_block_papers = self.llm_filter.filter_papers(
                    papers,
                    block_keywords,
                    min_score=min_score,
                    top_n=top_n
                )
                
                filtered_papers.extend(filtered_block_papers)
                logger.info(f"主题 '{block_name}' 筛选后剩余 {len(filtered_block_papers)} 篇文章")
            
            all_selected_papers = filtered_papers
            logger.info(f"LLM 筛选后剩余 {len(all_selected_papers)} 篇文章")
        
        # 处理PDF读取和论文总结
        if all_selected_papers:
            all_selected_papers = self._process_papers_with_pdf(all_selected_papers)
        
        # 打印最终选中的文章
        logger.info("\n最终选中的文章列表:")
        for i, paper in enumerate(all_selected_papers, 1):
            llm_info = ""
            if hasattr(paper, 'llm_score'):
                llm_info = f" [LLM:{paper.llm_score:.1f}]"
            logger.info(f"{i}. [{paper.source_block}/{paper.keyword_type}] "
                       f"{paper.title[:50]}... (引用:{paper.citation_count}){llm_info}")
        
        # 生成报告
        output_path = self._generate_report(all_selected_papers)
        
        # 发送邮件
        if send_email and all_selected_papers and self.email_sender:
            date_str = datetime.now().strftime('%Y-%m-%d')
            success = self.email_sender.send_papers_email(
                all_selected_papers, output_path, date_str
            )
            if success:
                logger.info("📧 邮件推送成功！")
            else:
                logger.error("📧 邮件推送失败")
        
        # 保存历史
        self._save_history()
        
        if output_path:
            logger.info(f"任务完成！报告已保存: {output_path}")
        return output_path
    
    def _generate_report(self, papers: List[Paper]) -> str:
        """生成 Markdown 报告"""
        if not papers:
            return ""
        
        output_dir = self.config.get('output_dir', 'daily_papers')
        os.makedirs(output_dir, exist_ok=True)
        
        today = datetime.now().strftime('%Y-%m-%d')
        filename = f"arxiv_papers_{today}.md"
        filepath = os.path.join(output_dir, filename)
        
        # 按主题块分组
        block_groups = defaultdict(list)
        for paper in papers:
            block_groups[paper.source_block].append(paper)
        
        # 检查是否有 LLM 评分
        has_llm_score = any(hasattr(p, 'llm_score') for p in papers)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# 📚 arXiv 每日文章推送 ({today})\n\n")
            f.write(f"> 共筛选出 **{len(papers)}** 篇相关文章\n\n")
            
            if has_llm_score:
                f.write("> 🤖 经 **LLM 智能筛选**，按相关性降序排列\n\n")
            else:
                f.write("> 📊 按 **引用次数** 降序排列\n\n")
            
            f.write("---\n\n")
            
            # 汇总统计
            f.write("## 📊 统计概览\n\n")
            for block_name, block_papers in block_groups.items():
                core_count = sum(1 for p in block_papers if p.keyword_type == 'core')
                ext_count = sum(1 for p in block_papers if p.keyword_type == 'extended')
                f.write(f"- **{block_name}**: {len(block_papers)} 篇")
                f.write(f" (核心: {core_count}, 扩展: {ext_count})\n")
            f.write("\n---\n\n")
            
            # 详细列表
            for block_name, block_papers in block_groups.items():
                f.write(f"## {block_name}\n\n")
                
                # 处理所有匹配的论文
                if block_papers:
                    f.write(f"### 匹配论文 ({len(block_papers)}篇)\n\n")
                    self._write_paper_list(f, block_papers)
            
            f.write("\n*由 arXiv Agent 自动生成*\n")
        
        return filepath
    
    def _process_papers_with_pdf(self, papers: List[Paper]) -> List[Paper]:
        """处理论文的PDF读取和总结"""
        if not papers:
            return papers
        
        if not self.pdf_reader or not self.paper_summarizer:
            logger.warning("PDF 读取或总结功能未启用")
            return papers
        
        logger.info(f"\n{'='*60}")
        logger.info(f"开始处理 {len(papers)} 篇论文的PDF和总结...")
        logger.info(f"{'='*60}")
        
        # 按主题分组论文
        block_papers = defaultdict(list)
        for paper in papers:
            block_papers[paper.source_block].append(paper)
        
        processed_papers = []
        for block_name, block_papers_list in block_papers.items():
            # 找到对应的关键词块
            block_keywords = []
            for block in self.keyword_manager.blocks:
                if block.name == block_name:
                    block_keywords = block.all_keywords
                    break
            
            if not block_keywords:
                logger.warning(f"主题 '{block_name}' 未找到对应的关键词")
                processed_papers.extend(block_papers_list)
                continue
            
            logger.info(f"处理主题 '{block_name}' 的 {len(block_papers_list)} 篇论文...")
            logger.info(f"使用关键词: {block_keywords[:5]}...")
            
            for i, paper in enumerate(block_papers_list, 1):
                logger.info(f"处理第 {i}/{len(block_papers_list)} 篇: {paper.title[:50]}...")
                
                try:
                    # 读取PDF全文
                    text_for_summary = None
                    summary_source = ""
                    
                    if paper.pdf_link:
                        full_text = self.pdf_reader.get_pdf_text(paper.pdf_link)
                        if full_text:
                            paper.full_text = full_text
                            text_for_summary = full_text
                            summary_source = "full_text"
                            logger.info(f"  PDF 读取成功，长度: {len(full_text)} 字符")
                        else:
                            logger.warning("  PDF 读取失败，使用摘要进行总结")
                            text_for_summary = paper.summary
                            summary_source = "abstract"
                    else:
                        logger.warning("  没有PDF链接，使用摘要进行总结")
                        text_for_summary = paper.summary
                        summary_source = "abstract"
                    
                    # 生成总结
                    if text_for_summary:
                        summary_result = self.paper_summarizer.summarize_paper(
                            paper.title, 
                            text_for_summary, 
                            block_keywords
                        )
                        if summary_result:
                            paper.paper_summary = {
                                'summary': summary_result.summary,
                                'key_points': summary_result.key_points,
                                'methodology': summary_result.methodology,
                                'conclusions': summary_result.conclusions,
                                'limitations': summary_result.limitations,
                                'score': summary_result.score,
                                'summary_source': summary_source
                            }
                            logger.info(f"  论文总结生成成功，评分: {summary_result.score:.1f}/10，基于: {summary_source}")
                        else:
                            logger.warning("  论文总结生成失败")
                    
                    processed_papers.append(paper)
                    
                except Exception as e:
                    logger.error(f"  处理失败: {e}")
                    processed_papers.append(paper)
                
                # 延迟，避免API限制
                import time
                time.sleep(1)
        
        logger.info(f"PDF和总结处理完成，共处理 {len(processed_papers)} 篇论文")
        return processed_papers
    
    def _write_paper_list(self, f, papers: List[Paper]):
        """写入论文列表"""
        for i, paper in enumerate(papers, 1):
            f.write(f"#### {i}. {paper.title}\n\n")
            f.write(f"- **作者**: {', '.join(paper.authors[:5])}")
            if len(paper.authors) > 5:
                f.write(f" 等 ({len(paper.authors)} 人)")
            f.write("\n")
            f.write(f"- **发布时间**: {paper.published.strftime('%Y-%m-%d')}\n")
            f.write(f"- **分类**: {paper.primary_category}\n")
            f.write(f"- **被引次数**: {paper.citation_count}\n")
            
            # 显示 LLM 评分
            if hasattr(paper, 'llm_score'):
                f.write(f"- **🤖 LLM 相关性评分**: {paper.llm_score:.1f}/10\n")
                if hasattr(paper, 'llm_reason') and paper.llm_reason:
                    f.write(f"- **LLM 评估**: {paper.llm_reason[:100]}...\n")
            
            if paper.matched_keywords:
                f.write(f"- **匹配关键词**: {', '.join(paper.matched_keywords[:5])}\n")
            f.write(f"- **链接**: [arXiv]({paper.link})")
            if paper.pdf_link:
                f.write(f" | [PDF]({paper.pdf_link})")
            f.write("\n\n")
            
            summary = paper.summary[:600]
            if len(paper.summary) > 600:
                summary += "..."
            f.write(f"> **摘要**: {summary}\n\n")
            
            # 显示论文总结
            if hasattr(paper, 'paper_summary') and paper.paper_summary:
                f.write("### 📝 论文总结\n\n")
                summary_source = paper.paper_summary.get('summary_source', 'unknown')
                if summary_source == 'abstract':
                    f.write(f"> 📌 **总结基于摘要** - PDF 不可下载或读取失败\n\n")
                f.write(f"> {paper.paper_summary.get('summary', '')}\n\n")
                
                key_points = paper.paper_summary.get('key_points', [])
                if key_points:
                    f.write("#### 关键点\n\n")
                    for j, point in enumerate(key_points, 1):
                        f.write(f"{j}. {point}\n")
                    f.write("\n")
                
                methodology = paper.paper_summary.get('methodology', '')
                if methodology:
                    f.write("#### 研究方法\n\n")
                    f.write(f"> {methodology}\n\n")
                
                conclusions = paper.paper_summary.get('conclusions', '')
                if conclusions:
                    f.write("#### 结论\n\n")
                    f.write(f"> {conclusions}\n\n")
                
                limitations = paper.paper_summary.get('limitations', '')
                if limitations:
                    f.write("#### 局限性\n\n")
                    f.write(f"> {limitations}\n\n")
            
            f.write("---\n\n")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='arXiv 每日文章推送智能体')
    parser.add_argument('--no-email', action='store_true', help='不发送邮件')
    parser.add_argument('--test-email', action='store_true', help='测试邮件配置')
    parser.add_argument('--config', default='config.yaml', help='配置文件路径')
    parser.add_argument('--core-limit', type=int, default=30, help='核心关键词选取数量')
    parser.add_argument('--extended-limit', type=int, default=10, help='扩展关键词选取数量')
    parser.add_argument('--reset-history', action='store_true', help='重置历史记录')
    
    args = parser.parse_args()
    
    agent = ArxivAgent(config_file=args.config)
    
    # 命令行参数覆盖配置
    if args.core_limit:
        agent.config.setdefault('block_config', {})['core_limit'] = args.core_limit
    if args.extended_limit:
        agent.config.setdefault('block_config', {})['extended_limit'] = args.extended_limit
    
    report_path = agent.run(send_email=not args.no_email, reset_history=args.reset_history)
    
    if report_path:
        print(f"\n✅ 报告已生成: {report_path}")
    else:
        print("\n⚠️ 未生成报告")


if __name__ == "__main__":
    main()
