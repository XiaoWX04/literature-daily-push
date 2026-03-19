#!/usr/bin/env python3
"""
PDF 读取模块
从论文的 PDF 链接下载并提取文本
"""

import os
import logging
import requests
import tempfile
from typing import Optional
from pdfminer.high_level import extract_text

logger = logging.getLogger(__name__)


class PDFReader:
    """PDF 读取器"""
    
    def __init__(self, timeout: int = 30, max_retries: int = 3, retry_delay: float = 2.0):
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.session = requests.Session()
        # 添加浏览器头信息，减少被拒绝的可能性
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
    
    def download_pdf(self, pdf_url: str) -> Optional[str]:
        """
        下载 PDF 文件到临时文件
        
        Args:
            pdf_url: PDF 文件的 URL
            
        Returns:
            临时文件路径，如果下载失败则返回 None
        """
        import time
        
        if not pdf_url:
            logger.warning("PDF URL 为空")
            return None
        
        logger.info(f"下载 PDF: {pdf_url}")
        
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(pdf_url, timeout=self.timeout)
                
                # 检查 HTTP 状态码
                if response.status_code == 403:
                    logger.warning(f"PDF 下载被拒绝 (403 Forbidden): {pdf_url}")
                    logger.info("403 错误通常是服务器访问限制，不再重试")
                    return None
                elif response.status_code == 404:
                    logger.warning(f"PDF 文件不存在 (404 Not Found): {pdf_url}")
                    return None
                
                response.raise_for_status()
                
                # 检查是否是 PDF 文件
                content_type = response.headers.get('Content-Type', '')
                if 'pdf' not in content_type.lower():
                    logger.warning(f"不是 PDF 文件: {content_type}")
                    return None
                
                # 创建临时文件
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
                    f.write(response.content)
                    temp_path = f.name
                
                logger.info(f"PDF 下载成功: {temp_path}")
                return temp_path
                
            except requests.exceptions.HTTPError as e:
                # HTTP 错误通常不需要重试
                logger.warning(f"HTTP 错误: {e}")
                return None
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout) as e:
                # 网络错误，进行重试
                if attempt < self.max_retries - 1:
                    backoff_time = self.retry_delay * (2 ** attempt)  # 指数退避
                    logger.warning(f"第 {attempt + 1} 次下载失败 (网络错误): {e}")
                    logger.info(f"{backoff_time:.1f} 秒后重试...")
                    time.sleep(backoff_time)
                else:
                    logger.error(f"PDF 下载失败 (已达到最大重试次数): {e}")
                    return None
            except Exception as e:
                # 其他错误，进行重试
                if attempt < self.max_retries - 1:
                    backoff_time = self.retry_delay * (2 ** attempt)  # 指数退避
                    logger.warning(f"第 {attempt + 1} 次下载失败: {e}")
                    logger.info(f"{backoff_time:.1f} 秒后重试...")
                    time.sleep(backoff_time)
                else:
                    logger.error(f"PDF 下载失败 (已达到最大重试次数): {e}")
                    return None
    
    def extract_text_from_pdf(self, pdf_path: str) -> Optional[str]:
        """
        从 PDF 文件中提取文本
        
        Args:
            pdf_path: PDF 文件路径
            
        Returns:
            提取的文本，如果提取失败则返回 None
        """
        if not pdf_path or not os.path.exists(pdf_path):
            logger.warning("PDF 文件不存在")
            return None
        
        try:
            logger.info(f"提取 PDF 文本: {pdf_path}")
            text = extract_text(pdf_path)
            
            # 清理临时文件
            try:
                os.unlink(pdf_path)
            except Exception as e:
                logger.warning(f"清理临时文件失败: {e}")
            
            if text:
                logger.info(f"PDF 文本提取成功，长度: {len(text)} 字符")
                return text
            else:
                logger.warning("PDF 文本提取为空")
                return None
                
        except Exception as e:
            logger.error(f"PDF 文本提取失败: {e}")
            # 清理临时文件
            try:
                os.unlink(pdf_path)
            except Exception:
                pass
            return None
    
    def get_pdf_text(self, pdf_url: str) -> Optional[str]:
        """
        从 PDF URL 获取文本
        
        Args:
            pdf_url: PDF 文件的 URL
            
        Returns:
            提取的文本，如果失败则返回 None
        """
        # 下载 PDF
        pdf_path = self.download_pdf(pdf_url)
        if not pdf_path:
            return None
        
        # 提取文本
        return self.extract_text_from_pdf(pdf_path)


# 测试代码
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # 测试 PDF 读取器
    reader = PDFReader()
    
    # 测试链接
    test_url = "https://arxiv.org/pdf/2306.01116.pdf"
    
    text = reader.get_pdf_text(test_url)
    if text:
        print(f"提取的文本长度: {len(text)}")
        print("\n前500个字符:")
        print(text[:500])
    else:
        print("PDF 文本提取失败")
