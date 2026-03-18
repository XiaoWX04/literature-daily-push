#!/usr/bin/env python3
"""
多源学术搜索器
支持 arXiv、bioRxiv、OpenAlex 等学术搜索引擎
"""

import os
import json
import logging
import requests
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, field

# 导入 pyalex
try:
    from pyalex import Works
    PYALEX_AVAILABLE = True
except ImportError:
    PYALEX_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class Paper:
    """统一的论文数据结构"""
    title: str
    authors: List[str]
    summary: str
    link: str
    pdf_link: str = ""
    published: datetime = None
    categories: List[str] = field(default_factory=list)
    primary_category: str = ""
    external_id: str = ""  # 各平台的 ID
    citation_count: int = 0
    source: str = ""  # 来源平台
    matched_keywords: List[str] = field(default_factory=list)


class ArxivSearcher:
    """arXiv 搜索器"""
    
    ARXIV_API_URL = "http://export.arxiv.org/api/query"
    
    def __init__(self, max_results_per_query: int = 100, sort_by: str = 'relevance', max_retries: int = 3, retry_delay: float = 2.0):
        self.max_results_per_query = max_results_per_query
        self.sort_by = sort_by  # 'relevance' 或 'submittedDate'
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def search(self, query: str, days_back: int = 30, max_results: int = 50) -> List[Paper]:
        """
        搜索 arXiv 文章
        
        Args:
            query: 搜索关键词
            days_back: 搜索最近几天的文章
            max_results: 最大结果数
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # 根据配置选择排序方式
        sort_by = getattr(self, 'sort_by', 'relevance')  # 默认按相关性
        
        params = {
            'search_query': f'all:{query}',
            'start': 0,
            'max_results': min(max_results, self.max_results_per_query),
            'sortBy': sort_by,  # 'relevance' 或 'submittedDate'
            'sortOrder': 'descending'
        }
        
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    logger.info(f"arXiv 搜索重试 ({attempt + 1}/{self.max_retries}): {query}")
                    import time
                    time.sleep(self.retry_delay * attempt)
                else:
                    logger.info(f"搜索 arXiv: {query}")
                
                response = requests.get(
                    self.ARXIV_API_URL, 
                    params=params, 
                    timeout=30
                )
                response.raise_for_status()
                
                feed = feedparser.parse(response.content)
                papers = []
                
                for entry in feed.entries:
                    published = datetime.strptime(
                        entry.published, 
                        '%Y-%m-%dT%H:%M:%SZ'
                    )
                    
                    if published < start_date:
                        continue
                    
                    pdf_link = ""
                    for link in entry.links:
                        if link.get('type') == 'application/pdf':
                            pdf_link = link.href
                            break
                    
                    authors = [author.name for author in entry.get('authors', [])]
                    categories = [tag.term for tag in entry.get('tags', [])]
                    primary_cat = entry.get('arxiv_primary_category', {}).get('term', '')
                    
                    arxiv_id = ""
                    if '/abs/' in entry.link:
                        arxiv_id = entry.link.split('/abs/')[-1].split('v')[0]
                    
                    paper = Paper(
                        title=entry.title.replace('\n', ' ').strip(),
                        authors=authors,
                        summary=entry.summary.replace('\n', ' ').strip(),
                        link=entry.link,
                        pdf_link=pdf_link,
                        published=published,
                        categories=categories,
                        primary_category=primary_cat,
                        external_id=arxiv_id,
                        source='arxiv'
                    )
                    papers.append(paper)
                
                logger.info(f"  找到 {len(papers)} 篇文章")
                return papers
                
            except Exception as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"arXiv 搜索失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                    continue
                else:
                    logger.error(f"arXiv 搜索失败，已达到最大重试次数: {e}")
                    return []
        
        return []


class BioRxivSearcher:
    """bioRxiv 搜索器
    
    优势：
    - 专注于生物医学预印本
    - 支持 RSS 格式搜索
    - 包含最新的生物医学研究
    """
    
    BIORXIV_API_URL = "http://connect.biorxiv.org/biorxiv_xml.php"
    
    def __init__(self, max_results_per_query: int = 100, max_retries: int = 3, retry_delay: float = 2.0):
        self.session = requests.Session()
        self.max_results_per_query = max_results_per_query
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def search(self, query: str, days_back: int = 7, max_results: int = 50) -> List[Paper]:
        """
        搜索 bioRxiv
        
        Args:
            query: 搜索关键词
            days_back: 搜索最近几天的文章
            max_results: 最大结果数
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        params = {
            'subject': 'all',  # 所有学科
            'jcode': 'biorxiv',
            'sort': 'rel',  # 按相关性排序
            'limit': min(max_results, self.max_results_per_query),
            'format': 'rss'
        }
        
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    logger.info(f"bioRxiv 搜索重试 ({attempt + 1}/{self.max_retries}): {query}")
                    import time
                    time.sleep(self.retry_delay * attempt)
                else:
                    logger.info(f"搜索 bioRxiv: {query}")
                
                response = self.session.get(self.BIORXIV_API_URL, params=params, timeout=30)
                response.raise_for_status()
                
                feed = feedparser.parse(response.content)
                papers = []
                
                for entry in feed.entries:
                    # 限制结果数量
                    if len(papers) >= min(max_results, self.max_results_per_query):
                        break
                    
                    # 解析发布日期
                    published = None
                    if 'published' in entry:
                        try:
                            published = datetime.strptime(entry.published, '%Y-%m-%dT%H:%M:%SZ')
                        except:
                            published = datetime.now()
                    else:
                        published = datetime.now()
                    
                    if published < start_date:
                        continue
                    
                    # 提取 PDF 链接
                    pdf_link = ""
                    if 'links' in entry:
                        for link in entry.links:
                            if link.get('type') == 'application/pdf':
                                pdf_link = link.href
                                break
                    
                    # 提取作者
                    authors = []
                    if 'authors' in entry:
                        if isinstance(entry.authors, list):
                            for author in entry.authors:
                                if hasattr(author, 'name'):
                                    authors.append(author.name)
                        elif isinstance(entry.authors, str):
                            authors = [entry.authors]
                
                # 提取摘要
                summary = entry.get('summary', '').replace('\n', ' ').strip()
                
                # 提取分类
                categories = []
                if 'tags' in entry:
                    for tag in entry.tags:
                        if hasattr(tag, 'term'):
                            categories.append(tag.term)
                
                # 提取 ID
                biorxiv_id = ""
                if 'id' in entry:
                    biorxiv_id = entry.id.split('/')[-1]
                
                paper = Paper(
                    title=entry.get('title', '').replace('\n', ' ').strip(),
                    authors=authors,
                    summary=summary,
                    link=entry.get('link', ''),
                    pdf_link=pdf_link,
                    published=published,
                    categories=categories,
                    primary_category=categories[0] if categories else '',
                    external_id=biorxiv_id,
                    source='biorxiv'
                )
                papers.append(paper)
            
                logger.info(f"  找到 {len(papers)} 篇文章")
                return papers
                
            except Exception as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"bioRxiv 搜索失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                    continue
                else:
                    logger.error(f"bioRxiv 搜索失败，已达到最大重试次数: {e}")
                    return []
            
        return []


class OpenAlexSearcher:
    """OpenAlex 搜索器
    
    优势：
    - 完全免费开源
    - 无 Rate Limit（请礼貌使用）
    - 数据覆盖广（包括 arXiv、DOI 等）
    - 支持复杂查询语法
    - 包含 citation count
    """
    
    API_URL = "https://api.openalex.org/works"
    
    def __init__(self, email: Optional[str] = None, max_results_per_query: int = 100):
        """
        Args:
            email: 你的邮箱（OpenAlex 建议提供，会被添加到 User-Agent）
            max_results_per_query: 每次查询的最大结果数
        """
        self.email = email
        self.max_results_per_query = max_results_per_query
        self.session = requests.Session()
        if email:
            self.session.headers.update({
                'User-Agent': f'mailto:{email}'
            })
    
    def search(self, query: str, days_back: int = 7, max_results: int = 50) -> List[Paper]:
        """
        搜索 OpenAlex
        
        Args:
            query: 搜索关键词
            days_back: 搜索最近几天的文章
            max_results: 最大结果数
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # OpenAlex 使用 filter 语法
        # from_publication_date 格式: YYYY-MM-DD
        from_date = start_date.strftime('%Y-%m-%d')
        
        try:
            logger.info(f"搜索 OpenAlex: {query}")
            
            # 暂时使用传统的 API 调用方式，优化 PDF 链接获取
            logger.info("使用传统 API 调用方式进行 OpenAlex 搜索")
            params = {
                'search': query,
                'filter': f'from_publication_date:{from_date}',
                'sort': 'relevance_score:desc',
                'per-page': min(max_results, self.max_results_per_query),  # 使用传入的最大结果数
            }
            
            response = self.session.get(self.API_URL, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            papers = []
            
            for item in data.get('results', []):
                # 获取日期
                pub_date = item.get('publication_date', '')
                if pub_date:
                    try:
                        published = datetime.strptime(pub_date, '%Y-%m-%d')
                    except:
                        published = datetime.now()
                else:
                    published = datetime.now()
                
                # 获取作者
                authors = []
                for authorship in item.get('authorships', []):
                    author = authorship.get('author', {})
                    if isinstance(author, dict):
                        authors.append(author.get('display_name', ''))
                
                # 优化 PDF 链接获取
                pdf_link = ""
                oa_info = item.get('open_access', {})
                if oa_info and oa_info.get('is_oa'):
                    # 尝试多种 PDF 链接来源
                    pdf_link = oa_info.get('oa_url', '')
                    if not pdf_link and oa_info.get('locations'):
                        for loc in oa_info.get('locations', []):
                            if loc.get('is_oa') and loc.get('url'):
                                pdf_link = loc.get('url')
                                break
                    # 尝试从 external_ids 中获取
                    if not pdf_link and item.get('external_ids'):
                        external_ids = item.get('external_ids', {})
                        if external_ids.get('arXiv'):
                            arxiv_id = external_ids.get('arXiv')
                            pdf_link = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
                        elif external_ids.get('DOI'):
                            doi = external_ids.get('DOI')
                            pdf_link = f"https://doi.org/{doi}"
                
                # 获取引用次数
                cited_by_count = item.get('cited_by_count', 0)
                
                # 获取概念/分类
                concepts = [c.get('display_name', '') for c in item.get('concepts', [])]
                
                paper = Paper(
                    title=item.get('display_name', ''),
                    authors=authors,
                    summary=item.get('abstract', '') or '',
                    link=item.get('id', ''),
                    pdf_link=pdf_link,
                    published=published,
                    categories=concepts[:5],  # 前5个概念
                    external_id=item.get('id', '').split('/')[-1],
                    citation_count=cited_by_count,
                    source='openalex'
                )
                papers.append(paper)
            
            logger.info(f"  找到 {len(papers)} 篇文章")
            return papers
            
        except Exception as e:
            logger.error(f"OpenAlex 搜索失败: {e}")
            return []


class PubMedSearcher:
    """PubMed 搜索器
    
    优势：
    - 生物医学领域最权威的文献数据库
    - 包含 MEDLINE 和 PubMed Central
    - 支持复杂的医学主题词检索
    - 提供丰富的文献元数据
    """
    
    EUTILS_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    def __init__(self, email: Optional[str] = None, api_key: Optional[str] = None, 
                 max_results_per_query: int = 100, max_retries: int = 3, retry_delay: float = 2.0):
        """
        Args:
            email: 你的邮箱（NCBI 建议提供）
            api_key: NCBI API Key（可选，有 API Key 可以提高请求限制）
            max_results_per_query: 每次查询的最大结果数
            max_retries: 最大重试次数
            retry_delay: 重试延迟时间
        """
        self.email = email
        self.api_key = api_key
        self.max_results_per_query = max_results_per_query
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.session = requests.Session()
        
        # 设置请求头
        headers = {}
        if email:
            headers['User-Agent'] = f'Python-Script mailto:{email}'
        if api_key:
            headers['api_key'] = api_key
        if headers:
            self.session.headers.update(headers)
    
    def search(self, query: str, days_back: int = 30, max_results: int = 50) -> List[Paper]:
        """
        搜索 PubMed
        
        Args:
            query: 搜索关键词
            days_back: 搜索最近几天的文章
            max_results: 最大结果数
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # 构建日期范围
        date_range = f"{start_date.strftime('%Y/%m/%d')}:{end_date.strftime('%Y/%m/%d')}[pdat]"
        
        # 构建搜索参数
        search_params = {
            'db': 'pubmed',
            'term': f'{query} AND {date_range}',
            'retmax': min(max_results, self.max_results_per_query),
            'retmode': 'json',
            'sort': 'relevance'
        }
        
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    logger.info(f"PubMed 搜索重试 ({attempt + 1}/{self.max_retries}): {query}")
                    import time
                    time.sleep(self.retry_delay * attempt)
                else:
                    logger.info(f"搜索 PubMed: {query}")
                
                # 第一步：搜索获取 PMID 列表
                search_url = f"{self.EUTILS_BASE_URL}/esearch.fcgi"
                response = self.session.get(search_url, params=search_params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                id_list = data.get('esearchresult', {}).get('idlist', [])
                
                if not id_list:
                    logger.info(f"  找到 0 篇文章")
                    return []
                
                # 第二步：获取文献详情
                fetch_params = {
                    'db': 'pubmed',
                    'id': ','.join(id_list),
                    'retmode': 'xml'
                }
                
                fetch_url = f"{self.EUTILS_BASE_URL}/efetch.fcgi"
                fetch_response = self.session.get(fetch_url, params=fetch_params, timeout=60)
                fetch_response.raise_for_status()
                
                # 解析 XML
                papers = self._parse_pubmed_xml(fetch_response.content, start_date)
                
                logger.info(f"  找到 {len(papers)} 篇文章")
                return papers
                
            except Exception as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"PubMed 搜索失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                    continue
                else:
                    logger.error(f"PubMed 搜索失败，已达到最大重试次数: {e}")
                    return []
        
        return []
    
    def _parse_pubmed_xml(self, xml_content: bytes, start_date: datetime) -> List[Paper]:
        """解析 PubMed XML 响应"""
        papers = []
        
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml_content)
            
            for article in root.findall('.//PubmedArticle'):
                try:
                    # 提取 PMID
                    pmid = article.find('.//PMID').text if article.find('.//PMID') is not None else ''
                    
                    # 提取标题
                    title_elem = article.find('.//ArticleTitle')
                    title = title_elem.text if title_elem is not None and title_elem.text else ''
                    
                    # 提取作者
                    authors = []
                    author_list = article.findall('.//Author')
                    for author in author_list:
                        lastname = author.find('LastName')
                        forename = author.find('ForeName')
                        if lastname is not None and lastname.text:
                            if forename is not None and forename.text:
                                authors.append(f"{lastname.text} {forename.text}")
                            else:
                                authors.append(lastname.text)
                    
                    # 提取摘要
                    abstract_elem = article.find('.//Abstract/AbstractText')
                    summary = abstract_elem.text if abstract_elem is not None and abstract_elem.text else ''
                    
                    # 提取发布日期
                    pub_date_elem = article.find('.//PubDate')
                    published = datetime.now()
                    if pub_date_elem is not None:
                        year = pub_date_elem.find('Year')
                        month = pub_date_elem.find('Month')
                        day = pub_date_elem.find('Day')
                        
                        year_text = year.text if year is not None and year.text else str(datetime.now().year)
                        month_text = month.text if month is not None and month.text else '1'
                        day_text = day.text if day is not None and day.text else '1'
                        
                        try:
                            # 处理月份可能是英文缩写的情况
                            month_map = {
                                'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                                'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
                            }
                            if month_text in month_map:
                                month_num = month_map[month_text]
                            else:
                                month_num = int(month_text)
                            
                            published = datetime(int(year_text), month_num, int(day_text))
                        except:
                            published = datetime.now()
                    
                    # 过滤掉早于 start_date 的文章
                    if published < start_date:
                        continue
                    
                    # 提取期刊信息
                    journal_elem = article.find('.//Journal/Title')
                    journal = journal_elem.text if journal_elem is not None and journal_elem.text else ''
                    
                    # 提取 DOI
                    doi = ''
                    for article_id in article.findall('.//ArticleId'):
                        if article_id.get('IdType') == 'doi':
                            doi = article_id.text if article_id.text else ''
                            break
                    
                    # 构建链接
                    link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ''
                    
                    # PDF 链接（如果有 DOI）
                    pdf_link = f"https://doi.org/{doi}" if doi else ''
                    
                    paper = Paper(
                        title=title,
                        authors=authors,
                        summary=summary,
                        link=link,
                        pdf_link=pdf_link,
                        published=published,
                        categories=[journal] if journal else [],
                        primary_category=journal,
                        external_id=pmid,
                        citation_count=0,  # PubMed API 不直接提供引用数
                        source='pubmed'
                    )
                    papers.append(paper)
                    
                except Exception as e:
                    logger.warning(f"解析 PubMed 文章失败: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"解析 PubMed XML 失败: {e}")
        
        return papers


class MultiSourceSearcher:
    """多源搜索器 - 整合多个学术搜索引擎"""
    
    def __init__(self, 
                 openalex_email: Optional[str] = None,
                 pubmed_email: Optional[str] = None,
                 pubmed_api_key: Optional[str] = None,
                 max_results_per_query: int = 100,
                 sort_by: str = 'relevance'):
        self.searchers = {}
        self.max_results_per_query = max_results_per_query
        
        # 初始化 arXiv
        self.searchers['arxiv'] = ArxivSearcher(max_results_per_query, sort_by)
        
        # 初始化 bioRxiv
        self.searchers['biorxiv'] = BioRxivSearcher(max_results_per_query)
        
        # 初始化 OpenAlex
        self.searchers['openalex'] = OpenAlexSearcher(openalex_email, max_results_per_query)
        
        # 初始化 PubMed
        self.searchers['pubmed'] = PubMedSearcher(pubmed_email, pubmed_api_key, max_results_per_query)
    
    def search_all(self, query: str, days_back: int = 7, max_per_source: int = 50) -> Dict[str, List[Paper]]:
        """
        在所有源中搜索
        
        Returns:
            Dict[source_name, papers]
        """
        results = {}
        
        for name, searcher in self.searchers.items():
            try:
                papers = searcher.search(query, days_back, max_per_source)
                results[name] = papers
            except Exception as e:
                logger.error(f"{name} 搜索失败: {e}")
                results[name] = []
        
        return results
    
    def search_and_merge(self, query: str, days_back: int = 7, max_per_source: int = 50) -> List[Paper]:
        """
        在所有源中搜索并合并结果，去重
        """
        all_results = self.search_all(query, days_back, max_per_source)
        
        # 合并所有结果
        seen_ids = set()
        merged_papers = []
        
        for source, papers in all_results.items():
            for paper in papers:
                # 使用标题前50字符作为去重键
                paper_key = paper.title[:50].lower()
                if paper_key not in seen_ids:
                    seen_ids.add(paper_key)
                    merged_papers.append(paper)
        
        logger.info(f"多源搜索完成，共找到 {len(merged_papers)} 篇不重复文章")
        return merged_papers


if __name__ == "__main__":
    # 测试代码
    import time
    
    print("测试多源学术搜索器...")
    
    # 创建搜索器
    searcher = MultiSourceSearcher(
        openalex_email="your@email.com"  # 建议提供邮箱
    )
    
    # 测试搜索
    query = "AI agent for biology"
    
    print(f"\n搜索: {query}")
    results = searcher.search_all(query, days_back=30, max_per_source=10)
    
    for source, papers in results.items():
        print(f"\n{source}: {len(papers)} 篇")
        for i, paper in enumerate(papers, 1):
            print(f"  {i}. {paper.title} (引用: {paper.citation_count})")
    
    # 测试合并
    print("\n\n合并结果:")
    merged = searcher.search_and_merge(query, days_back=30, max_per_source=10)
    print(f"共 {len(merged)} 篇不重复文章")
