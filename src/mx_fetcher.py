# -*- coding: utf-8 -*-
"""
东方财富妙想 MX API 封装
mx-data: 行情/财务/资金流向
mx-search: 金融资讯搜索
"""
import os
import json
import logging
import requests
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

MX_DATA_URL = "https://mkapi2.dfcfs.com/finskillshub/api/claw/query"
MX_SEARCH_URL = "https://mkapi2.dfcfs.com/finskillshub/api/claw/news-search"


class MXFetcher:
    """妙想金融数据客户端"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("MX_APIKEY", "")
        if not self.api_key:
            logger.warning("MX_APIKEY 未设置，妙想金融接口不可用")

    def _query_data(self, text: str) -> Optional[Dict]:
        """查询金融数据"""
        if not self.api_key:
            return None
        try:
            resp = requests.post(
                MX_DATA_URL,
                headers={"Content-Type": "application/json", "apikey": self.api_key},
                json={"toolQuery": text},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning(f"[MX] 数据查询失败: {e}")
            return None

    def search_news(self, query: str, max_results: int = 10) -> List[Dict]:
        """搜索金融资讯"""
        if not self.api_key:
            return []
        try:
            resp = requests.post(
                MX_SEARCH_URL,
                headers={"Content-Type": "application/json", "apikey": self.api_key},
                json={"query": query},
                timeout=30,
            )
            resp.raise_for_status()
            result = resp.json()
        except Exception as e:
            logger.warning(f"[MX] 资讯搜索失败: {e}")
            return []

        news_list = []
        try:
            articles = result.get("data", {}).get("data", {}).get("llmSearchResponse", {}).get("data", [])
            for art in articles[:max_results]:
                title = art.get("title", "")
                if title:
                    news_list.append({
                        "title": title,
                        "snippet": (art.get("content", ""))[:500],
                        "source": "东方财富妙想",
                        "date": str(art.get("code", "")),
                    })
        except Exception as e:
            logger.warning(f"[MX] 解析搜索结果失败: {e}")

        return news_list

    def get_market_overview(self) -> List[str]:
        """获取今日大盘综述文本"""
        news = self.search_news("今日A股市场综述 领涨板块 资金流向", 5)
        return [f"{n['title']}\n{n['snippet']}" for n in news]

    def get_stock_quote(self, codes: List[str]) -> List[Dict]:
        """批量获取个股实时行情"""
        if not codes:
            return []
        code_str = " ".join(codes)
        query = f"{code_str} 最新价 涨跌幅 成交量 成交额 换手率"
        result = self._query_data(query)
        if not result:
            return []

        quotes = []
        try:
            data = result.get("data", {}).get("data", {})
            tables = data.get("searchDataResultDTO", {}).get("dataTableDTOList", [])
            for tbl in tables:
                entity = tbl.get("entityName", "")
                code = tbl.get("code", "")
                table = tbl.get("table", {})
                name_map = tbl.get("nameMap", {})

                if not table:
                    continue
                # Parse MX table format
                quote = {"code": code, "name": entity}
                for key, values in table.items():
                    if key == "headName":
                        continue
                    label = name_map.get(key, key)
                    val = values[-1] if isinstance(values, list) and values else values
                    quote[label] = val
                quotes.append(quote)
        except Exception as e:
            logger.warning(f"[MX] 解析行情失败: {e}")

        return quotes

    def get_sector_fund_flow(self) -> List[Dict]:
        """获取行业资金流向排名"""
        result = self._query_data("今日行业板块资金净流入排名 前10 后10")
        if not result:
            return []

        sectors = []
        try:
            data = result.get("data", {}).get("data", {})
            tables = data.get("searchDataResultDTO", {}).get("dataTableDTOList", [])
            for tbl in tables:
                table = tbl.get("table", {})
                name_map = tbl.get("nameMap", {})
                headers = table.get("headName", [])
                if not headers:
                    continue
                for i, date in enumerate(headers):
                    row = {"date": str(date)}
                    for key, values in table.items():
                        if key == "headName":
                            continue
                        label = name_map.get(key, str(key))
                        val = values[i] if i < len(values) else ""
                        row[label] = val
                    sectors.append(row)
        except Exception as e:
            logger.warning(f"[MX] 解析资金流向失败: {e}")

        return sectors

    def get_hot_stocks(self) -> List[Dict]:
        """获取市场热门个股"""
        result = self._query_data("今日市场关注度最高热门个股排名 前5")
        if not result:
            return []

        stocks = []
        try:
            data = result.get("data", {}).get("data", {})
            tables = data.get("searchDataResultDTO", {}).get("dataTableDTOList", [])
            for tbl in tables[:1]:
                table = tbl.get("table", {})
                name_map = tbl.get("nameMap", {})
                headers = table.get("headName", [])
                if not headers:
                    continue
                for i, date in enumerate(headers):
                    row = {}
                    for key, values in table.items():
                        if key == "headName":
                            continue
                        label = name_map.get(key, str(key))
                        val = values[i] if i < len(values) else ""
                        row[label] = val
                    stocks.append(row)
        except Exception as e:
            logger.warning(f"[MX] 解析热门个股失败: {e}")

        return stocks
