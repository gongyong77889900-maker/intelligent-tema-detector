import streamlit as st
import pandas as pd
import numpy as np
import re
import logging
from typing import Dict, List, Set, Tuple, Any, Optional, Union
import itertools
from collections import defaultdict, OrderedDict
import time
from io import BytesIO
from functools import lru_cache, wraps
from abc import ABC, abstractmethod
from dataclasses import dataclass
import hashlib
from enum import Enum

# ==================== 配置管理器 ====================
class ConfigManager:
    """统一的配置管理类"""
    
    @dataclass
    class LotteryConfig:
        """彩种配置数据类"""
        name: str
        number_range: Set[int]
        total_numbers: int
        default_min_number_count: int
        default_min_avg_amount: float
        play_keywords: List[str]
        analysis_strategy: str  # 'position_based' or 'period_merge'
    
    @dataclass  
    class SimilarityThresholds:
        """相似度阈值配置"""
        excellent: float = 90.0
        good: float = 80.0
        fair: float = 70.0
    
    def __init__(self):
        self.lottery_configs = self._init_lottery_configs()
        self.similarity_thresholds = self.SimilarityThresholds()
        self.target_lotteries = self._init_target_lotteries()
        self.column_mappings = self._init_column_mappings()
        self.play_mappings = self._init_play_mappings()
        self.position_mappings = self._init_position_mappings()
    
    def _init_lottery_configs(self) -> Dict[str, LotteryConfig]:
        """初始化彩种配置"""
        return {
            'six_mark': self.LotteryConfig(
                name='六合彩',
                number_range=set(range(1, 50)),
                total_numbers=49,
                default_min_number_count=11,
                default_min_avg_amount=10.0,
                play_keywords=['特码', '特玛', '正码', '正特', '平码', '平特'],
                analysis_strategy='position_based'
            ),
            'six_mark_tail': self.LotteryConfig(
                name='六合彩尾数',
                number_range=set(range(0, 10)),
                total_numbers=10,
                default_min_number_count=3,
                default_min_avg_amount=5.0,
                play_keywords=['尾数', '特尾', '全尾'],
                analysis_strategy='position_based'
            ),
            'pk10_base': self.LotteryConfig(
                name='PK10基础',
                number_range=set(range(1, 11)),
                total_numbers=10,
                default_min_number_count=3,
                default_min_avg_amount=5.0,
                play_keywords=['定位胆', '冠军', '亚军', '季军'],
                analysis_strategy='position_based'
            ),
            'pk10_sum': self.LotteryConfig(
                name='冠亚和',
                number_range=set(range(3, 20)),
                total_numbers=17,
                default_min_number_count=5,
                default_min_avg_amount=5.0,
                play_keywords=['冠亚和', '冠亚和值'],
                analysis_strategy='position_based'
            ),
            'fast_three_base': self.LotteryConfig(
                name='快三基础',
                number_range=set(range(1, 7)),
                total_numbers=6,
                default_min_number_count=2,
                default_min_avg_amount=5.0,
                play_keywords=['三军', '独胆', '单码'],
                analysis_strategy='position_based'
            ),
            'fast_three_sum': self.LotteryConfig(
                name='快三和值',
                number_range=set(range(3, 19)),
                total_numbers=16,
                default_min_number_count=4,
                default_min_avg_amount=5.0,
                play_keywords=['和值', '点数'],
                analysis_strategy='position_based'
            ),
            'ssc_3d': self.LotteryConfig(
                name='时时彩/3D',
                number_range=set(range(0, 10)),
                total_numbers=10,
                default_min_number_count=3,
                default_min_avg_amount=5.0,
                play_keywords=['第1球', '万位', '百位', '十位', '个位'],
                analysis_strategy='position_based'
            )
        }
    
    def _init_target_lotteries(self) -> Dict[str, List[str]]:
        """初始化目标彩种列表"""
        return {
            'six_mark': [
                '新澳门六合彩', '澳门六合彩', '香港六合彩', '一分六合彩',
                '五分六合彩', '三分六合彩', '香港⑥合彩', '分分六合彩',
                '台湾大乐透', '大发六合彩', '快乐6合彩',
                '幸运六合彩', '极速六合彩', '腾讯六合彩', '五分彩六合',
                '三分彩六合', '一分彩六合', '幸运⑥合', '极速⑥合'
            ],
            '10_number': [
                '时时彩', '重庆时时彩', '新疆时时彩', '天津时时彩',
                '分分时时彩', '五分时时彩', '三分时时彩', '北京时时彩',
                'PK10', '北京PK10', 'PK拾', '幸运PK10', '赛车', '大发赛车',
                '幸运28', '北京28', '加拿大28', '极速PK10', '分分PK10', '大发快三',
                '幸运飞艇', '澳洲幸运10', '极速飞艇', '澳洲飞艇',
                '北京赛车', '极速赛车', '幸运赛車', '分分赛车',
                '腾讯分分彩', '五分时时彩', '三分时时彩', '一分时时彩',
                '幸运5', '幸运8', '幸运10', '幸运12'
            ],
            'fast_three': [
                '快三', '快3', 'K3', '分分快三', '五分快三', '三分快三',
                '北京快三', '江苏快三', '安徽快三', '大发快三',
                '澳洲快三', '宾果快三', '加州快三', '幸运快三',
                '澳门快三', '香港快三', '台湾快三', '极速快三'
            ],
            '3d_series': [
                '排列三', '排列3', '福彩3D', '3D', '极速3D',
                '幸运排列3', '一分排列3', '三分排列3', '五分排列3',
                '大发排列3', '好运排列3', '极速排列3'
            ],
            'five_star': [
                '五星彩', '五星直选', '五星组选', '五星通选',
                '五星彩种', '五星彩票', '极速五星'
            ]
        }
    
    def _init_column_mappings(self) -> Dict[str, List[str]]:
        """初始化列名映射"""
        return {
            '会员账号': ['会员账号', '会员账户', '账号', '账户', '用户账号', '玩家账号', '用户ID', '玩家ID'],
            '彩种': ['彩种', '彩神', '彩票种类', '游戏类型', '彩票类型', '游戏彩种'],
            '期号': ['期号', '期数', '期次', '期', '奖期', '开奖期号'],
            '玩法': ['玩法', '玩法分类', '投注类型', '类型', '投注玩法', '玩法类型'],
            '内容': ['内容', '投注内容', '下注内容', '注单内容', '投注号码', '号码内容'],
            '金额': ['金额', '下注总额', '投注金额', '总额', '下注金额', '投注额', '单注金额']
        }
    
    def _init_play_mappings(self) -> Dict[str, str]:
        """初始化玩法映射"""
        mappings = {}
        
        # 六合彩映射
        six_mark_mappings = {
            '特码': '特码', '特玛': '特码', '特马': '特码', '特碼': '特码',
            '正码': '正码', '正码一': '正码一', '正码二': '正码二', '正码三': '正码三',
            '正码四': '正码四', '正码五': '正码五', '正码六': '正码六',
            '正特': '正特', '正一特': '正一特', '正二特': '正二特', '正三特': '正三特',
            '正四特': '正四特', '正五特': '正五特', '正六特': '正六特',
            '平码': '平码', '平特': '平特',
            '尾数': '尾数', '特尾': '特尾', '全尾': '全尾'
        }
        mappings.update(six_mark_mappings)
        
        # PK10/时时彩映射
        pk10_mappings = {
            '定位胆': '定位胆', '一字定位': '定位胆', '一字': '定位胆', '定位': '定位胆',
            '冠军': '冠军', '亚军': '亚军', '季军': '季军',
            '第四名': '第四名', '第五名': '第五名', '第六名': '第六名',
            '第七名': '第七名', '第八名': '第八名', '第九名': '第九名', '第十名': '第十名',
            '第一名': '冠军', '第二名': '亚军', '第三名': '季军',
            '第1名': '冠军', '第2名': '亚军', '第3名': '季军',
            '第4名': '第四名', '第5名': '第五名', '第6名': '第六名',
            '第7名': '第七名', '第8名': '第八名', '第9名': '第九名', '第10名': '第十名',
            '前一': '冠军', '1-5名': '1-5名', '6-10名': '6-10名',
            '1~5名': '1-5名', '6~10名': '6-10名',
            '冠亚和': '冠亚和', '冠亚和值': '冠亚和'
        }
        mappings.update(pk10_mappings)
        
        # 快三映射
        fast_three_mappings = {
            '和值': '和值', '点数': '和值',
            '三军': '三军', '三軍': '三军', '独胆': '三军', '单码': '三军',
            '二不同号': '二不同号', '二不同': '二不同号',
            '三不同号': '三不同号', '三不同': '三不同号'
        }
        mappings.update(fast_three_mappings)
        
        # 3D/时时彩映射
        ssc_3d_mappings = {
            '第1球': '第1球', '第2球': '第2球', '第3球': '第3球',
            '第4球': '第4球', '第5球': '第5球',
            '万位': '万位', '千位': '千位', '百位': '百位', '十位': '十位', '个位': '个位',
            '百十': '百十', '百个': '百个', '十个': '十个', '百十个': '百十个'
        }
        mappings.update(ssc_3d_mappings)
        
        return mappings
    
    def _init_position_mappings(self) -> Dict[str, List[str]]:
        """初始化位置映射"""
        mappings = {}
        
        # 六合彩位置
        mappings.update({
            '特码': ['特码', '特玛', '特马', '特碼', '特码球'],
            '正码一': ['正码一', '正码1', '正一码', 'z1m'],
            '正码二': ['正码二', '正码2', '正二码', 'z2m'],
            '正码三': ['正码三', '正码3', '正三码', 'z3m'],
            '正码四': ['正码四', '正码4', '正四码', 'z4m'],
            '正码五': ['正码五', '正码5', '正五码', 'z5m'],
            '正码六': ['正码六', '正码6', '正六码', 'z6m'],
            '正一特': ['正一特', '正1特', 'zyte'],
            '正二特': ['正二特', '正2特', 'zte'],
            '正三特': ['正三特', '正3特', 'zste'],
            '正四特': ['正四特', '正4特', 'zsite'],
            '正五特': ['正五特', '正5特', 'zwte'],
            '正六特': ['正六特', '正6特', 'zlte'],
            '平码': ['平码', '平特码', 'pm'],
            '平特': ['平特', '平特肖', 'pt'],
            '尾数': ['尾数', '尾码', 'ws'],
            '特尾': ['特尾', '特尾数', 'tw'],
            '全尾': ['全尾', '全尾数', 'qw']
        })
        
        # PK10/时时彩位置
        mappings.update({
            '冠军': ['冠军', '第一名', '第1名', '1st', '前一', 'gj'],
            '亚军': ['亚军', '第二名', '第2名', '2nd', 'yj'],
            '季军': ['季军', '第三名', '第3名', '3rd', 'jj'],
            '第四名': ['第四名', '第4名', '4th', 'dsm'],
            '第五名': ['第五名', '第5名', '5th', 'dwm'],
            '第六名': ['第六名', '第6名', '6th', 'dlm'],
            '第七名': ['第七名', '第7名', '7th', 'dqm'],
            '第八名': ['第八名', '第8名', '8th', 'dbm'],
            '第九名': ['第九名', '第9名', '9th', 'djm'],
            '第十名': ['第十名', '第10名', '10th', 'dsm2'],
            '第1球': ['第1球', '第一球', '万位', 'd1q'],
            '第2球': ['第2球', '第二球', '千位', 'd2q'],
            '第3球': ['第3球', '第三球', '百位', 'd3q'],
            '第4球': ['第4球', '第四球', '十位', 'd4q'],
            '第5球': ['第5球', '第五球', '个位', 'd5q'],
            '1-5名': ['1-5名', '1~5名', '1至5名'],
            '6-10名': ['6-10名', '6~10名', '6至10名'],
            '冠亚和': ['冠亚和', '冠亚和值', 'gyh']
        })
        
        # 快三位置
        mappings.update({
            '和值': ['和值', '和数', '和', '点数', 'hz'],
            '三军': ['三军', '三軍', '独胆', '单码', 'sj'],
            '二不同号': ['二不同号', '二不同', 'ebth'],
            '三不同号': ['三不同号', '三不同', 'sbth']
        })
        
        # 3D/时时彩位置
        mappings.update({
            '百位': ['百位', 'bw', 'baiwei'],
            '十位': ['十位', 'sw', 'shiwei'],
            '个位': ['个位', 'gw', 'gewei'],
            '百十': ['百十', '百十位', 'bs'],
            '百个': ['百个', '百个位', 'bg'],
            '十个': ['十个', '十个位', 'sg'],
            '百十个': ['百十个', '百十个位', 'bsg']
        })
        
        return mappings

# ==================== 日志管理器 ====================
class LogManager:
    """统一的日志管理"""
    
    @staticmethod
    def setup_logger(name: str, level=logging.INFO) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger(name)
        
        if not logger.handlers:
            logger.setLevel(level)
            
            # 控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)
            
            # 文件处理器
            file_handler = logging.FileHandler(
                f'coverage_analysis_{time.strftime("%Y%m%d")}.log',
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            
            # 格式化器
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(formatter)
            file_handler.setFormatter(formatter)
            
            logger.addHandler(console_handler)
            logger.addHandler(file_handler)
        
        return logger

# ==================== 缓存管理器 ====================
class CacheManager:
    """缓存管理器"""
    
    def __init__(self, maxsize=5000):
        self.number_cache = {}
        self.amount_cache = {}
        self.maxsize = maxsize
        
    def _make_key(self, *args, **kwargs) -> str:
        """生成缓存键"""
        key_str = str(args) + str(sorted(kwargs.items()))
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def cached_extract_numbers(self, func):
        """号码提取缓存装饰器"""
        @wraps(func)
        def wrapper(content: str, lottery_category: str, play_method: str = None):
            key = self._make_key(content, lottery_category, play_method)
            
            if key in self.number_cache:
                return self.number_cache[key]
            
            result = func(content, lottery_category, play_method)
            
            # 缓存管理
            if len(self.number_cache) >= self.maxsize:
                # 移除最旧的条目（简单实现）
                oldest_key = next(iter(self.number_cache))
                del self.number_cache[oldest_key]
            
            self.number_cache[key] = result
            return result
        
        return wrapper
    
    def cached_extract_amount(self, func):
        """金额提取缓存装饰器"""
        @wraps(func)
        def wrapper(amount_text: str):
            key = self._make_key(amount_text)
            
            if key in self.amount_cache:
                return self.amount_cache[key]
            
            result = func(amount_text)
            
            if len(self.amount_cache) >= self.maxsize:
                oldest_key = next(iter(self.amount_cache))
                del self.amount_cache[oldest_key]
            
            self.amount_cache[key] = result
            return result
        
        return wrapper

# ==================== 数据提取器基类 ====================
class BaseExtractor(ABC):
    """数据提取器基类"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.cache_manager = CacheManager()
        self.logger = LogManager.setup_logger(self.__class__.__name__)
    
    @abstractmethod
    def extract(self, data: str, **kwargs) -> Any:
        """提取方法"""
        pass

# ==================== 号码提取器 ====================
class NumberExtractor(BaseExtractor):
    """号码提取器"""
    
    def __init__(self, config_manager: ConfigManager):
        super().__init__(config_manager)
        
    def _clean_content(self, content: str) -> str:
        """清理内容"""
        if not content:
            return ""
        
        # 移除中文括号及其内容
        content = re.sub(r'[\(（][^\)）]+[\)）]', '', content)
        # 替换全角字符为半角
        content = content.replace('，', ',').replace('：', ':').replace('；', ';')
        # 移除多余空格
        content = re.sub(r'\s+', ' ', content).strip()
        
        return content
    
    def _extract_from_position_format(self, content: str, number_range: Set[int]) -> List[int]:
        """从位置-号码格式提取"""
        numbers = []
        
        # 多种分隔符处理
        separators = [',', ';', '、']
        for sep in separators:
            if sep in content:
                parts = content.split(sep)
                for part in parts:
                    # 处理位置-号码格式
                    if '-' in part or ':' in part:
                        for sep_char in ['-', ':']:
                            if sep_char in part:
                                _, num_part = part.split(sep_char, 1)
                                num_matches = re.findall(r'\d{1,2}', num_part.strip())
                                for num_str in num_matches:
                                    if num_str.isdigit():
                                        num = int(num_str)
                                        if num in number_range:
                                            numbers.append(num)
                                break
                    else:
                        # 直接提取数字
                        num_matches = re.findall(r'\b\d{1,2}\b', part)
                        for num_str in num_matches:
                            if num_str.isdigit():
                                num = int(num_str)
                                if num in number_range:
                                    numbers.append(num)
        
        return list(set(numbers))
    
    def _extract_from_general_format(self, content: str, number_range: Set[int]) -> List[int]:
        """从通用格式提取"""
        numbers = []
        
        # 提取所有1-2位数字
        num_matches = re.findall(r'\b\d{1,2}\b', content)
        
        for num_str in num_matches:
            if num_str.isdigit():
                num = int(num_str)
                if num in number_range:
                    numbers.append(num)
        
        # 处理汉字数字
        chinese_numbers = {
            '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
            '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
            '零': 0, '〇': 0
        }
        
        for chinese, value in chinese_numbers.items():
            if chinese in content:
                numbers.append(value)
        
        return list(set(numbers))
    
    def _extract_from_special_format(self, content: str, number_range: Set[int], play_method: str = None) -> List[int]:
        """从特殊格式提取"""
        numbers = []
        content_lower = content.lower()
        
        # 特殊格式处理
        special_patterns = [
            (r'投注[：:]\s*\d+[^\d]*(\d+)', 2),  # 投注：XX 格式
            (r'(\d+)\s*[,，]\s*(\d+)', 2),  # 数字,数字 格式
        ]
        
        for pattern, group_index in special_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                try:
                    num_str = match.group(group_index)
                    if num_str and num_str.isdigit():
                        num = int(num_str)
                        if num in number_range:
                            numbers.append(num)
                except (IndexError, ValueError):
                    continue
        
        return numbers
    
    @CacheManager.cached_extract_numbers
    def extract(self, content: str, lottery_category: str, play_method: str = None) -> List[int]:
        """提取号码（主方法）"""
        try:
            if not content or pd.isna(content):
                return []
            
            content_str = str(content)
            
            # 获取彩种配置
            if lottery_category not in self.config.lottery_configs:
                # 尝试模糊匹配
                lottery_category = self._fuzzy_match_lottery_category(lottery_category)
            
            config = self.config.lottery_configs.get(lottery_category)
            if not config:
                self.logger.warning(f"未找到彩种配置: {lottery_category}")
                return []
            
            number_range = config.number_range
            clean_content = self._clean_content(content_str)
            
            # 多种提取策略组合
            all_numbers = []
            
            # 策略1：位置-号码格式提取
            numbers1 = self._extract_from_position_format(clean_content, number_range)
            if numbers1:
                all_numbers.extend(numbers1)
            
            # 策略2：通用格式提取
            numbers2 = self._extract_from_general_format(clean_content, number_range)
            if numbers2:
                all_numbers.extend(numbers2)
            
            # 策略3：特殊格式提取
            numbers3 = self._extract_from_special_format(clean_content, number_range, play_method)
            if numbers3:
                all_numbers.extend(numbers3)
            
            # 去重、排序、验证
            unique_numbers = sorted(set(all_numbers))
            valid_numbers = [num for num in unique_numbers if num in number_range]
            
            return valid_numbers
            
        except Exception as e:
            self.logger.error(f"号码提取失败: {content}, 错误: {str(e)}", exc_info=True)
            return []
    
    def _fuzzy_match_lottery_category(self, lottery_name: str) -> str:
        """模糊匹配彩种类型"""
        lottery_lower = lottery_name.lower()
        
        # 六合彩关键词
        if any(keyword in lottery_lower for keyword in ['六合', 'lhc', '⑥合', '6合', '特码']):
            return 'six_mark'
        # PK10/时时彩关键词
        elif any(keyword in lottery_lower for keyword in ['pk10', 'pk拾', '赛车', '时时彩', '幸运10']):
            return 'pk10_base'
        # 快三关键词
        elif any(keyword in lottery_lower for keyword in ['快三', '快3', 'k3', '骰宝']):
            return 'fast_three_sum'
        # 3D关键词
        elif any(keyword in lottery_lower for keyword in ['3d', '排列三', '排列3', '福彩']):
            return 'ssc_3d'
        
        return 'six_mark'  # 默认

# ==================== 金额提取器 ====================
class AmountExtractor(BaseExtractor):
    """金额提取器"""
    
    def __init__(self, config_manager: ConfigManager):
        super().__init__(config_manager)
    
    @CacheManager.cached_extract_amount
    def extract(self, amount_text: str) -> float:
        """提取金额"""
        try:
            if pd.isna(amount_text) or amount_text is None:
                return 0.0
            
            text = str(amount_text).strip()
            
            if not text or text.lower() in ['', 'null', 'none', 'nan']:
                return 0.0
            
            # 策略1：处理 "投注：20.000" 格式
            if '投注' in text or '下注' in text:
                bet_patterns = [
                    r'投注[：:]\s*([\d\.,]+)',
                    r'下注[：:]\s*([\d\.,]+)',
                    r'投注金额[：:]\s*([\d\.,]+)',
                    r'金额[：:]\s*([\d\.,]+)'
                ]
                
                for pattern in bet_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        amount_str = match.group(1)
                        clean_amount = self._clean_amount_string(amount_str)
                        if clean_amount:
                            return float(clean_amount)
            
            # 策略2：处理千位分隔符
            if ',' in text or '，' in text:
                clean_text = text.replace(',', '').replace('，', '')
                if self._is_valid_amount(clean_text):
                    return float(clean_text)
            
            # 策略3：直接提取数字
            numbers = re.findall(r'\d+\.?\d*', text)
            if numbers:
                for num_str in numbers:
                    if self._is_valid_amount(num_str):
                        return float(num_str)
            
            # 策略4：处理特殊格式
            if '.' in text and text.count('.') == 1:
                parts = text.split('.')
                if len(parts[0]) <= 6 and len(parts[1]) <= 3:
                    if self._is_valid_amount(text):
                        return float(text)
            
            return 0.0
            
        except Exception as e:
            self.logger.warning(f"金额提取失败: {amount_text}, 错误: {str(e)}")
            return 0.0
    
    def _clean_amount_string(self, amount_str: str) -> str:
        """清理金额字符串"""
        if not amount_str:
            return ""
        
        # 移除千位分隔符和空格
        clean = amount_str.replace(',', '').replace('，', '').replace(' ', '')
        
        # 验证是否是有效的数字
        if re.match(r'^\d+(\.\d+)?$', clean):
            return clean
        
        return ""
    
    def _is_valid_amount(self, amount_str: str) -> bool:
        """验证金额是否有效"""
        try:
            amount = float(amount_str)
            return 0 <= amount <= 1000000  # 假设最大金额为100万
        except:
            return False

# ==================== 玩法归一化器 ====================
class PlayNormalizer:
    """玩法归一化器"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.logger = LogManager.setup_logger(self.__class__.__name__)
    
    def normalize(self, play_method: str, lottery_category: str = 'six_mark') -> str:
        """归一化玩法"""
        try:
            if not play_method or pd.isna(play_method):
                return ""
            
            play_str = str(play_method).strip()
            play_lower = play_str.lower()
            
            # 直接映射查找
            if play_str in self.config.play_mappings:
                return self.config.play_mappings[play_str]
            
            # 关键词匹配
            for key, value in self.config.play_mappings.items():
                if key in play_str:
                    return value
            
            # 根据彩种类型智能匹配
            if lottery_category == 'six_mark':
                return self._normalize_six_mark(play_str, play_lower)
            elif lottery_category in ['pk10_base', 'pk10_sum', '10_number']:
                return self._normalize_pk10(play_str, play_lower)
            elif lottery_category in ['fast_three_base', 'fast_three_sum']:
                return self._normalize_fast_three(play_str, play_lower)
            elif lottery_category == 'ssc_3d':
                return self._normalize_ssc_3d(play_str, play_lower)
            
            return play_str
            
        except Exception as e:
            self.logger.error(f"玩法归一化失败: {play_method}, 错误: {str(e)}")
            return play_method if play_method else ""
    
    def _normalize_six_mark(self, play_str: str, play_lower: str) -> str:
        """六合彩玩法归一化"""
        # 特码
        if any(keyword in play_lower for keyword in ['特码', '特玛', '特马', '特碼']):
            return '特码'
        
        # 正码
        if '正码一' in play_lower or '正码1' in play_lower:
            return '正码一'
        elif '正码二' in play_lower or '正码2' in play_lower:
            return '正码二'
        elif '正码三' in play_lower or '正码3' in play_lower:
            return '正码三'
        elif '正码四' in play_lower or '正码4' in play_lower:
            return '正码四'
        elif '正码五' in play_lower or '正码5' in play_lower:
            return '正码五'
        elif '正码六' in play_lower or '正码6' in play_lower:
            return '正码六'
        
        # 正特
        if '正一特' in play_lower or '正1特' in play_lower:
            return '正一特'
        elif '正二特' in play_lower or '正2特' in play_lower:
            return '正二特'
        elif '正三特' in play_lower or '正3特' in play_lower:
            return '正三特'
        elif '正四特' in play_lower or '正4特' in play_lower:
            return '正四特'
        elif '正五特' in play_lower or '正5特' in play_lower:
            return '正五特'
        elif '正六特' in play_lower or '正6特' in play_lower:
            return '正六特'
        elif '正特' in play_lower:
            return '正特'
        
        # 尾数
        if '尾数' in play_lower:
            return '尾数'
        elif '特尾' in play_lower:
            return '特尾'
        elif '全尾' in play_lower:
            return '全尾'
        
        # 平码/平特
        if '平码' in play_lower:
            return '平码'
        elif '平特' in play_lower:
            return '平特'
        
        return play_str
    
    def _normalize_pk10(self, play_str: str, play_lower: str) -> str:
        """PK10玩法归一化"""
        # 名次
        if '冠军' in play_lower or '第1名' in play_lower or '1st' in play_lower:
            return '冠军'
        elif '亚军' in play_lower or '第2名' in play_lower or '2nd' in play_lower:
            return '亚军'
        elif '季军' in play_lower or '第3名' in play_lower or '3rd' in play_lower:
            return '季军'
        elif '第四名' in play_lower or '第4名' in play_lower:
            return '第四名'
        elif '第五名' in play_lower or '第5名' in play_lower:
            return '第五名'
        elif '第六名' in play_lower or '第6名' in play_lower:
            return '第六名'
        elif '第七名' in play_lower or '第7名' in play_lower:
            return '第七名'
        elif '第八名' in play_lower or '第8名' in play_lower:
            return '第八名'
        elif '第九名' in play_lower or '第9名' in play_lower:
            return '第九名'
        elif '第十名' in play_lower or '第10名' in play_lower:
            return '第十名'
        
        # 分组
        if '1-5名' in play_lower or '1~5名' in play_lower:
            return '1-5名'
        elif '6-10名' in play_lower or '6~10名' in play_lower:
            return '6-10名'
        
        # 定位胆
        if any(keyword in play_lower for keyword in ['定位胆', '一字定位', '一字', '定位']):
            return '定位胆'
        
        # 冠亚和
        if any(keyword in play_lower for keyword in ['冠亚和', '冠亚和值']):
            return '冠亚和'
        
        return play_str
    
    def _normalize_fast_three(self, play_str: str, play_lower: str) -> str:
        """快三玩法归一化"""
        if any(keyword in play_lower for keyword in ['和值', '和数', '和', '点数']):
            return '和值'
        elif any(keyword in play_lower for keyword in ['三军', '独胆', '单码']):
            return '三军'
        elif any(keyword in play_lower for keyword in ['二不同号', '二不同']):
            return '二不同号'
        elif any(keyword in play_lower for keyword in ['三不同号', '三不同']):
            return '三不同号'
        
        return play_str
    
    def _normalize_ssc_3d(self, play_str: str, play_lower: str) -> str:
        """时时彩/3D玩法归一化"""
        # 球位
        if '第1球' in play_lower or '第一球' in play_lower or '万位' in play_lower:
            return '第1球'
        elif '第2球' in play_lower or '第二球' in play_lower or '千位' in play_lower:
            return '第2球'
        elif '第3球' in play_lower or '第三球' in play_lower or '百位' in play_lower:
            return '第3球'
        elif '第4球' in play_lower or '第四球' in play_lower or '十位' in play_lower:
            return '第4球'
        elif '第5球' in play_lower or '第五球' in play_lower or '个位' in play_lower:
            return '第5球'
        
        # 3D组合
        if '百十' in play_lower:
            return '百十'
        elif '百个' in play_lower:
            return '百个'
        elif '十个' in play_lower:
            return '十个'
        elif '百十个' in play_lower:
            return '百十个'
        
        return play_str

# ==================== 彩种识别器 ====================
class LotteryIdentifier:
    """彩种识别器"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.logger = LogManager.setup_logger(self.__class__.__name__)
        
    def identify(self, lottery_name: str) -> str:
        """识别彩种类型"""
        try:
            if not lottery_name or pd.isna(lottery_name):
                return 'unknown'
            
            lottery_str = str(lottery_name).strip().lower()
            
            # 精确匹配
            for category, lotteries in self.config.target_lotteries.items():
                for lottery in lotteries:
                    if lottery.lower() in lottery_str:
                        return self._map_category(category)
            
            # 模糊匹配
            return self._fuzzy_identify(lottery_str)
            
        except Exception as e:
            self.logger.error(f"彩种识别失败: {lottery_name}, 错误: {str(e)}")
            return 'unknown'
    
    def _map_category(self, category: str) -> str:
        """映射彩种类别"""
        category_map = {
            'six_mark': 'six_mark',
            '10_number': 'pk10_base',
            'fast_three': 'fast_three_sum',
            '3d_series': 'ssc_3d',
            'five_star': 'ssc_3d'
        }
        return category_map.get(category, 'six_mark')
    
    def _fuzzy_identify(self, lottery_str: str) -> str:
        """模糊识别"""
        # 六合彩关键词
        six_mark_keywords = ['六合', 'lhc', '⑥合', '6合', '特码', '平特', '大乐透']
        if any(keyword in lottery_str for keyword in six_mark_keywords):
            return 'six_mark'
        
        # PK10/时时彩关键词
        pk10_keywords = ['pk10', 'pk拾', '赛车', '时时彩', '幸运10', '飞艇', '澳洲']
        if any(keyword in lottery_str for keyword in pk10_keywords):
            return 'pk10_base'
        
        # 快三关键词
        fast_three_keywords = ['快三', '快3', 'k3', '骰宝', '和值']
        if any(keyword in lottery_str for keyword in fast_three_keywords):
            return 'fast_three_sum'
        
        # 3D关键词
        ssc_3d_keywords = ['3d', '排列三', '排列3', '福彩', '三位']
        if any(keyword in lottery_str for keyword in ssc_3d_keywords):
            return 'ssc_3d'
        
        return 'six_mark'  # 默认

# ==================== 数据预处理器 ====================
class DataPreprocessor:
    """数据预处理器"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.lottery_identifier = LotteryIdentifier(config_manager)
        self.play_normalizer = PlayNormalizer(config_manager)
        self.number_extractor = NumberExtractor(config_manager)
        self.amount_extractor = AmountExtractor(config_manager)
        self.logger = LogManager.setup_logger(self.__class__.__name__)
    
    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """预处理数据"""
        try:
            # 1. 重命名列
            df = self._rename_columns(df)
            
            # 2. 验证必要列
            self._validate_required_columns(df)
            
            # 3. 清理数据
            df = self._clean_data(df)
            
            # 4. 识别彩种类型
            df['彩种类型'] = df['彩种'].apply(self.lottery_identifier.identify)
            
            # 5. 归一化玩法
            df['玩法'] = df.apply(
                lambda row: self.play_normalizer.normalize(
                    row['玩法'], 
                    row['彩种类型'] if not pd.isna(row['彩种类型']) else 'six_mark'
                ), 
                axis=1
            )
            
            # 6. 提取号码
            df['提取号码'] = df.apply(
                lambda row: self.number_extractor.extract(
                    row['内容'], 
                    row['彩种类型'] if not pd.isna(row['彩种类型']) else 'six_mark',
                    row['玩法']
                ), 
                axis=1
            )
            
            # 7. 统计号码数量
            df['号码数量'] = df['提取号码'].apply(len)
            
            # 8. 提取金额（如果存在金额列）
            if '金额' in df.columns:
                df['投注金额'] = df['金额'].apply(self.amount_extractor.extract)
            
            # 9. 过滤非号码投注
            df = self._filter_number_bets(df)
            
            self.logger.info(f"数据预处理完成: 原始 {len(df)} 条记录")
            
            return df
            
        except Exception as e:
            self.logger.error(f"数据预处理失败: {str(e)}", exc_info=True)
            raise
    
    def _rename_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """重命名列"""
        actual_columns = [str(col).strip() for col in df.columns]
        rename_dict = {}
        
        for standard_col, possible_names in self.config.column_mappings.items():
            for actual_col in actual_columns:
                actual_col_lower = actual_col.lower()
                for possible_name in possible_names:
                    possible_name_lower = possible_name.lower()
                    
                    # 模糊匹配
                    if (possible_name_lower in actual_col_lower or 
                        actual_col_lower in possible_name_lower or
                        self._calculate_similarity(possible_name_lower, actual_col_lower) > 0.7):
                        rename_dict[actual_col] = standard_col
                        break
                if actual_col in rename_dict:
                    break
        
        if rename_dict:
            df = df.rename(columns=rename_dict)
        
        return df
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """计算字符串相似度"""
        set1 = set(str1)
        set2 = set(str2)
        
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def _validate_required_columns(self, df: pd.DataFrame):
        """验证必要列"""
        required_columns = ['会员账号', '彩种', '期号', '玩法', '内容']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            error_msg = f"缺少必要列: {missing_columns}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """清理数据"""
        # 去除空白
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip()
        
        # 删除完全空白的行
        df = df.dropna(how='all')
        
        return df
    
    def _filter_number_bets(self, df: pd.DataFrame) -> pd.DataFrame:
        """过滤非号码投注"""
        # 非号码投注关键词
        non_number_keywords = [
            '大小', '单双', '龙虎', '特单', '特双', '特大', '特小',
            '大', '小', '单', '双', '龙', '虎', '合数单双', '合数大小'
        ]
        
        # 过滤条件：有号码且不包含非号码关键词
        has_numbers = df['提取号码'].apply(len) > 0
        not_non_number = ~df['内容'].str.contains('|'.join(non_number_keywords), na=False)
        
        filtered_df = df[has_numbers & not_non_number].copy()
        
        removed_count = len(df) - len(filtered_df)
        if removed_count > 0:
            self.logger.info(f"过滤非号码投注: 移除 {removed_count} 条记录")
        
        return filtered_df

# ==================== 组合查找器 ====================
class CombinationFinder:
    """组合查找器"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.logger = LogManager.setup_logger(self.__class__.__name__)
    
    def find_perfect_combinations(
        self, 
        account_numbers: Dict[str, List[int]],
        account_amount_stats: Dict[str, Dict],
        account_bet_contents: Dict[str, str],
        min_avg_amount: float,
        total_numbers: int,
        lottery_category: str,
        play_method: str = None,
        max_accounts: int = 4,
        max_amount_ratio: float = 10.0
    ) -> Dict[int, List[Dict]]:
        """查找完美组合"""
        all_results = {2: [], 3: [], 4: []}
        
        # 转换账户数据为集合
        account_sets = {account: set(numbers) for account, numbers in account_numbers.items()}
        
        # 预过滤：满足金额阈值的账户
        valid_accounts = []
        for account in account_numbers.keys():
            avg_amount = account_amount_stats[account]['avg_amount_per_number']
            if avg_amount >= float(min_avg_amount):
                valid_accounts.append(account)
        
        if len(valid_accounts) < 2:
            return all_results
        
        # 获取最小号码数量
        min_number_count = self._get_min_number_count(lottery_category, play_method)
        
        # 按号码数量分组
        accounts_by_count = {}
        for account in valid_accounts:
            count = len(account_sets[account])
            if count >= min_number_count:
                if count not in accounts_by_count:
                    accounts_by_count[count] = []
                accounts_by_count[count].append(account)
        
        if not accounts_by_count:
            return all_results
        
        # 查找2账户组合
        if max_accounts >= 2:
            all_results[2] = self._find_2_account_combinations(
                account_sets, account_amount_stats, account_bet_contents,
                accounts_by_count, total_numbers, min_avg_amount, max_amount_ratio
            )
        
        # 查找3账户组合
        if max_accounts >= 3:
            all_results[3] = self._find_3_account_combinations(
                account_sets, account_amount_stats, account_bet_contents,
                accounts_by_count, total_numbers, min_avg_amount, max_amount_ratio
            )
        
        # 查找4账户组合
        if max_accounts >= 4:
            all_results[4] = self._find_4_account_combinations(
                account_sets, account_amount_stats, account_bet_contents,
                accounts_by_count, total_numbers, min_avg_amount, max_amount_ratio
            )
        
        total_found = sum(len(results) for results in all_results.values())
        self.logger.info(f"找到 {total_found} 个完美组合")
        
        return all_results
    
    def _get_min_number_count(self, lottery_category: str, play_method: str = None) -> int:
        """获取最小号码数量"""
        play_str = str(play_method).lower() if play_method else ""
        
        if lottery_category == 'six_mark':
            if any(keyword in play_str for keyword in ['尾数', '全尾', '特尾']):
                return 3
            else:
                return 11
        elif lottery_category == 'pk10_sum':
            return 5
        elif lottery_category == 'fast_three_sum':
            return 4
        elif lottery_category == 'fast_three_base':
            return 2
        else:
            return 3
    
    def _find_2_account_combinations(
        self, account_sets, account_amount_stats, account_bet_contents,
        accounts_by_count, total_numbers, min_avg_amount, max_amount_ratio
    ) -> List[Dict]:
        """查找2账户组合"""
        results = []
        found_combinations = set()
        
        # 获取所有可能的号码数量组合
        counts = list(accounts_by_count.keys())
        
        for i in range(len(counts)):
            for j in range(i, len(counts)):
                count1, count2 = counts[i], counts[j]
                
                if count1 + count2 == total_numbers:
                    if count1 not in accounts_by_count or count2 not in accounts_by_count:
                        continue
                    
                    for acc1 in accounts_by_count[count1]:
                        for acc2 in accounts_by_count[count2]:
                            if acc1 == acc2:
                                continue
                            
                            combo_key = tuple(sorted([acc1, acc2]))
                            if combo_key in found_combinations:
                                continue
                            
                            set1 = account_sets[acc1]
                            set2 = account_sets[acc2]
                            
                            if len(set1 | set2) == total_numbers and set1.isdisjoint(set2):
                                # 检查金额条件
                                if self._check_amount_conditions(
                                    [acc1, acc2], account_amount_stats, min_avg_amount, max_amount_ratio
                                ):
                                    found_combinations.add(combo_key)
                                    results.append(self._create_result_data(
                                        [acc1, acc2], account_sets, account_amount_stats, 
                                        account_bet_contents, total_numbers
                                    ))
        
        return results
    
    def _find_3_account_combinations(
        self, account_sets, account_amount_stats, account_bet_contents,
        accounts_by_count, total_numbers, min_avg_amount, max_amount_ratio
    ) -> List[Dict]:
        """查找3账户组合"""
        results = []
        found_combinations = set()
        
        counts = list(accounts_by_count.keys())
        
        for i in range(len(counts)):
            for j in range(i, len(counts)):
                for k in range(j, len(counts)):
                    count1, count2, count3 = counts[i], counts[j], counts[k]
                    
                    if count1 + count2 + count3 == total_numbers:
                        if (count1 not in accounts_by_count or 
                            count2 not in accounts_by_count or 
                            count3 not in accounts_by_count):
                            continue
                        
                        for acc1 in accounts_by_count[count1]:
                            for acc2 in accounts_by_count[count2]:
                                if acc1 == acc2:
                                    continue
                                
                                set1 = account_sets[acc1]
                                set2 = account_sets[acc2]
                                
                                if not set1.isdisjoint(set2):
                                    continue
                                
                                set1_2 = set1 | set2
                                if len(set1_2) != count1 + count2:
                                    continue
                                
                                for acc3 in accounts_by_count[count3]:
                                    if acc3 in [acc1, acc2]:
                                        continue
                                    
                                    set3 = account_sets[acc3]
                                    if not set1.isdisjoint(set3) or not set2.isdisjoint(set3):
                                        continue
                                    
                                    if len(set1_2 | set3) == total_numbers:
                                        combo_key = tuple(sorted([acc1, acc2, acc3]))
                                        if combo_key in found_combinations:
                                            continue
                                        
                                        # 检查金额条件
                                        if self._check_amount_conditions(
                                            [acc1, acc2, acc3], account_amount_stats, 
                                            min_avg_amount, max_amount_ratio
                                        ):
                                            found_combinations.add(combo_key)
                                            results.append(self._create_result_data(
                                                [acc1, acc2, acc3], account_sets, account_amount_stats,
                                                account_bet_contents, total_numbers
                                            ))
        
        return results
    
    def _find_4_account_combinations(
        self, account_sets, account_amount_stats, account_bet_contents,
        accounts_by_count, total_numbers, min_avg_amount, max_amount_ratio
    ) -> List[Dict]:
        """查找4账户组合"""
        results = []
        found_combinations = set()
        
        counts = list(accounts_by_count.keys())
        
        for i in range(len(counts)):
            for j in range(i, len(counts)):
                for k in range(j, len(counts)):
                    for l in range(k, len(counts)):
                        count1, count2, count3, count4 = counts[i], counts[j], counts[k], counts[l]
                        
                        if count1 + count2 + count3 + count4 == total_numbers:
                            if (count1 not in accounts_by_count or 
                                count2 not in accounts_by_count or 
                                count3 not in accounts_by_count or 
                                count4 not in accounts_by_count):
                                continue
                            
                            for acc1 in accounts_by_count[count1]:
                                for acc2 in accounts_by_count[count2]:
                                    if acc1 == acc2:
                                        continue
                                    
                                    set1 = account_sets[acc1]
                                    set2 = account_sets[acc2]
                                    
                                    if not set1.isdisjoint(set2):
                                        continue
                                    
                                    set1_2 = set1 | set2
                                    if len(set1_2) != count1 + count2:
                                        continue
                                    
                                    for acc3 in accounts_by_count[count3]:
                                        if acc3 in [acc1, acc2]:
                                            continue
                                        
                                        set3 = account_sets[acc3]
                                        if not set1.isdisjoint(set3) or not set2.isdisjoint(set3):
                                            continue
                                        
                                        set1_2_3 = set1_2 | set3
                                        if len(set1_2_3) != count1 + count2 + count3:
                                            continue
                                        
                                        for acc4 in accounts_by_count[count4]:
                                            if acc4 in [acc1, acc2, acc3]:
                                                continue
                                            
                                            set4 = account_sets[acc4]
                                            if (not set1.isdisjoint(set4) or not set2.isdisjoint(set4) or 
                                                not set3.isdisjoint(set4)):
                                                continue
                                            
                                            if len(set1_2_3 | set4) == total_numbers:
                                                combo_key = tuple(sorted([acc1, acc2, acc3, acc4]))
                                                if combo_key in found_combinations:
                                                    continue
                                                
                                                # 检查金额条件
                                                if self._check_amount_conditions(
                                                    [acc1, acc2, acc3, acc4], account_amount_stats,
                                                    min_avg_amount, max_amount_ratio
                                                ):
                                                    found_combinations.add(combo_key)
                                                    results.append(self._create_result_data(
                                                        [acc1, acc2, acc3, acc4], account_sets, 
                                                        account_amount_stats, account_bet_contents,
                                                        total_numbers
                                                    ))
        
        return results
    
    def _check_amount_conditions(
        self, accounts: List[str], account_amount_stats: Dict, 
        min_avg_amount: float, max_amount_ratio: float
    ) -> bool:
        """检查金额条件"""
        # 检查平均金额阈值
        for account in accounts:
            if account_amount_stats[account]['avg_amount_per_number'] < min_avg_amount:
                return False
        
        # 检查金额平衡
        amounts = [account_amount_stats[account]['total_amount'] for account in accounts]
        max_amount = max(amounts)
        min_amount = min(amounts)
        
        if min_amount > 0 and max_amount / min_amount > max_amount_ratio:
            return False
        
        return True
    
    def _create_result_data(
        self, accounts: List[str], account_sets: Dict, account_amount_stats: Dict,
        account_bet_contents: Dict, total_numbers: int
    ) -> Dict:
        """创建结果数据"""
        # 计算相似度
        avg_amounts = [account_amount_stats[acc]['avg_amount_per_number'] for acc in accounts]
        similarity = self._calculate_similarity(avg_amounts)
        
        # 总金额
        total_amount = sum(account_amount_stats[acc]['total_amount'] for acc in accounts)
        
        # 创建结果
        result = {
            'accounts': sorted(accounts),
            'account_count': len(accounts),
            'total_amount': total_amount,
            'avg_amount_per_number': total_amount / total_numbers,
            'similarity': similarity,
            'similarity_indicator': self._get_similarity_indicator(similarity),
            'individual_amounts': {acc: account_amount_stats[acc]['total_amount'] for acc in accounts},
            'individual_avg_per_number': {acc: account_amount_stats[acc]['avg_amount_per_number'] for acc in accounts},
            'bet_contents': {acc: account_bet_contents[acc] for acc in accounts}
        }
        
        return result
    
    def _calculate_similarity(self, avgs: List[float]) -> float:
        """计算相似度"""
        if not avgs or max(avgs) == 0:
            return 0.0
        return (min(avgs) / max(avgs)) * 100
    
    def _get_similarity_indicator(self, similarity: float) -> str:
        """获取相似度指示器"""
        thresholds = self.config.similarity_thresholds
        if similarity >= thresholds.excellent:
            return "🟢"
        elif similarity >= thresholds.good:
            return "🟡"
        elif similarity >= thresholds.fair:
            return "🟠"
        else:
            return "🔴"

# ==================== 分析器基类 ====================
class BaseAnalyzer(ABC):
    """分析器基类"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.combination_finder = CombinationFinder(config_manager)
        self.logger = LogManager.setup_logger(self.__class__.__name__)
    
    @abstractmethod
    def analyze(self, df: pd.DataFrame, params: Dict) -> Dict:
        """分析数据"""
        pass

# ==================== 六合彩分析器 ====================
class SixMarkAnalyzer(BaseAnalyzer):
    """六合彩分析器"""
    
    def analyze(self, df: pd.DataFrame, params: Dict) -> Dict:
        """分析六合彩数据"""
        results = {}
        
        # 按位置分析
        grouped = df.groupby(['期号', '彩种', '玩法'])
        
        for (period, lottery, position), group in grouped:
            if len(group) >= 2:
                result = self._analyze_position(group, period, lottery, position, params)
                if result:
                    key = (period, lottery, position)
                    results[key] = result
        
        return results
    
    def _analyze_position(self, group: pd.DataFrame, period: str, lottery: str, 
                         position: str, params: Dict) -> Optional[Dict]:
        """分析单个位置"""
        # 获取配置
        config = self.config.lottery_configs.get('six_mark')
        if not config:
            return None
        
        # 获取参数
        min_number_count = params.get('min_number_count', config.default_min_number_count)
        min_avg_amount = params.get('min_avg_amount', config.default_min_avg_amount)
        max_amount_ratio = params.get('max_amount_ratio', 10.0)
        
        # 分析账户
        account_data = self._analyze_accounts(group)
        
        if len(account_data['numbers']) < 2:
            return None
        
        # 查找完美组合
        all_results = self.combination_finder.find_perfect_combinations(
            account_data['numbers'],
            account_data['amount_stats'],
            account_data['bet_contents'],
            min_avg_amount,
            config.total_numbers,
            'six_mark',
            position,
            4,
            max_amount_ratio
        )
        
        total_combinations = sum(len(results) for results in all_results.values())
        
        if total_combinations > 0:
            all_combinations = []
            for results in all_results.values():
                all_combinations.extend(results)
            
            all_combinations.sort(key=lambda x: (x['account_count'], -x['similarity']))
            
            return {
                'period': period,
                'lottery': lottery,
                'position': position,
                'lottery_category': 'six_mark',
                'total_combinations': total_combinations,
                'all_combinations': all_combinations,
                'filtered_accounts': len(account_data['numbers']),
                'total_numbers': config.total_numbers
            }
        
        return None
    
    def _analyze_accounts(self, group: pd.DataFrame) -> Dict:
        """分析账户数据"""
        account_numbers = {}
        account_amount_stats = {}
        account_bet_contents = {}
        
        for account in group['会员账号'].unique():
            account_data = group[group['会员账号'] == account]
            
            all_numbers = set()
            total_amount = 0
            
            for _, row in account_data.iterrows():
                numbers = row['提取号码']
                all_numbers.update(numbers)
                
                if '投注金额' in row:
                    amount = row['投注金额']
                    total_amount += amount
            
            if all_numbers:
                account_numbers[account] = sorted(all_numbers)
                account_bet_contents[account] = ", ".join([f"{num:02d}" for num in sorted(all_numbers)])
                
                number_count = len(all_numbers)
                avg_amount_per_number = total_amount / number_count if number_count > 0 else 0
                
                account_amount_stats[account] = {
                    'number_count': number_count,
                    'total_amount': total_amount,
                    'avg_amount_per_number': avg_amount_per_number
                }
        
        return {
            'numbers': account_numbers,
            'amount_stats': account_amount_stats,
            'bet_contents': account_bet_contents
        }

# ==================== PK10分析器 ====================
class PK10Analyzer(BaseAnalyzer):
    """PK10分析器"""
    
    def analyze(self, df: pd.DataFrame, params: Dict) -> Dict:
        """分析PK10数据"""
        results = {}
        
        # 按期号合并分析
        unique_periods = df['期号'].unique()
        
        for period in unique_periods:
            period_lotteries = df[df['期号'] == period]['彩种'].unique()
            
            for lottery in period_lotteries:
                result = self._analyze_period_merge(df, period, lottery, params)
                if result:
                    key = (period, lottery, '按期号合并')
                    results[key] = result
        
        return results
    
    def _analyze_period_merge(self, df: pd.DataFrame, period: str, 
                             lottery: str, params: Dict) -> Optional[Dict]:
        """按期号合并分析"""
        # 筛选数据
        period_data = df[
            (df['期号'] == period) & 
            (df['彩种'] == lottery)
        ]
        
        if len(period_data) < 2:
            return None
        
        # 获取配置
        config = self.config.lottery_configs.get('pk10_base')
        if not config:
            return None
        
        # 获取参数
        min_number_count = params.get('min_number_count', config.default_min_number_count)
        min_avg_amount = params.get('min_avg_amount', config.default_min_avg_amount)
        max_amount_ratio = params.get('max_amount_ratio', 10.0)
        
        # 分析账户
        account_data = self._analyze_accounts(period_data)
        
        if len(account_data['numbers']) < 2:
            return None
        
        # 查找完美组合
        all_results = self.combination_finder.find_perfect_combinations(
            account_data['numbers'],
            account_data['amount_stats'],
            account_data['bet_contents'],
            min_avg_amount,
            config.total_numbers,
            'pk10_base',
            None,
            2,
            max_amount_ratio
        )
        
        total_combinations = sum(len(results) for results in all_results.values())
        
        if total_combinations > 0:
            all_combinations = []
            for results in all_results.values():
                all_combinations.extend(results)
            
            all_combinations.sort(key=lambda x: (x['account_count'], -x['similarity']))
            
            return {
                'period': period,
                'lottery': lottery,
                'position': '按期号合并',
                'lottery_category': 'pk10_base',
                'total_combinations': total_combinations,
                'all_combinations': all_combinations,
                'filtered_accounts': len(account_data['numbers']),
                'total_numbers': config.total_numbers
            }
        
        return None
    
    def _analyze_accounts(self, period_data: pd.DataFrame) -> Dict:
        """分析账户数据"""
        account_numbers = {}
        account_amount_stats = {}
        account_bet_contents = {}
        
        for account in period_data['会员账号'].unique():
            account_data = period_data[period_data['会员账号'] == account]
            
            all_numbers = set()
            total_amount = 0
            
            for _, row in account_data.iterrows():
                numbers = row['提取号码']
                all_numbers.update(numbers)
                
                if '投注金额' in row:
                    amount = row['投注金额']
                    total_amount += amount
            
            if all_numbers:
                account_numbers[account] = sorted(all_numbers)
                account_bet_contents[account] = ", ".join([f"{num:02d}" for num in sorted(all_numbers)])
                
                number_count = len(all_numbers)
                avg_amount_per_number = total_amount / number_count if number_count > 0 else 0
                
                account_amount_stats[account] = {
                    'number_count': number_count,
                    'total_amount': total_amount,
                    'avg_amount_per_number': avg_amount_per_number
                }
        
        return {
            'numbers': account_numbers,
            'amount_stats': account_amount_stats,
            'bet_contents': account_bet_contents
        }

# ==================== 快三分析器 ====================
class FastThreeAnalyzer(BaseAnalyzer):
    """快三分析器"""
    
    def analyze(self, df: pd.DataFrame, params: Dict) -> Dict:
        """分析快三数据"""
        results = {}
        
        # 按位置分析
        grouped = df.groupby(['期号', '彩种', '玩法'])
        
        for (period, lottery, position), group in grouped:
            if len(group) >= 2:
                result = self._analyze_position(group, period, lottery, position, params)
                if result:
                    key = (period, lottery, position)
                    results[key] = result
        
        return results
    
    def _analyze_position(self, group: pd.DataFrame, period: str, lottery: str, 
                         position: str, params: Dict) -> Optional[Dict]:
        """分析单个位置"""
        # 确定配置类型
        if '和值' in position:
            config_key = 'fast_three_sum'
        else:
            config_key = 'fast_three_base'
        
        config = self.config.lottery_configs.get(config_key)
        if not config:
            return None
        
        # 获取参数
        min_number_count = params.get('min_number_count', config.default_min_number_count)
        min_avg_amount = params.get('min_avg_amount', config.default_min_avg_amount)
        max_amount_ratio = params.get('max_amount_ratio', 10.0)
        
        # 分析账户
        account_data = self._analyze_accounts(group)
        
        if len(account_data['numbers']) < 2:
            return None
        
        # 查找完美组合
        all_results = self.combination_finder.find_perfect_combinations(
            account_data['numbers'],
            account_data['amount_stats'],
            account_data['bet_contents'],
            min_avg_amount,
            config.total_numbers,
            config_key,
            position,
            4,
            max_amount_ratio
        )
        
        total_combinations = sum(len(results) for results in all_results.values())
        
        if total_combinations > 0:
            all_combinations = []
            for results in all_results.values():
                all_combinations.extend(results)
            
            all_combinations.sort(key=lambda x: (x['account_count'], -x['similarity']))
            
            return {
                'period': period,
                'lottery': lottery,
                'position': position,
                'lottery_category': config_key,
                'total_combinations': total_combinations,
                'all_combinations': all_combinations,
                'filtered_accounts': len(account_data['numbers']),
                'total_numbers': config.total_numbers
            }
        
        return None
    
    def _analyze_accounts(self, group: pd.DataFrame) -> Dict:
        """分析账户数据"""
        account_numbers = {}
        account_amount_stats = {}
        account_bet_contents = {}
        
        for account in group['会员账号'].unique():
            account_data = group[group['会员账号'] == account]
            
            all_numbers = set()
            total_amount = 0
            
            for _, row in account_data.iterrows():
                numbers = row['提取号码']
                all_numbers.update(numbers)
                
                if '投注金额' in row:
                    amount = row['投注金额']
                    total_amount += amount
            
            if all_numbers:
                account_numbers[account] = sorted(all_numbers)
                account_bet_contents[account] = ", ".join([f"{num:02d}" for num in sorted(all_numbers)])
                
                number_count = len(all_numbers)
                avg_amount_per_number = total_amount / number_count if number_count > 0 else 0
                
                account_amount_stats[account] = {
                    'number_count': number_count,
                    'total_amount': total_amount,
                    'avg_amount_per_number': avg_amount_per_number
                }
        
        return {
            'numbers': account_numbers,
            'amount_stats': account_amount_stats,
            'bet_contents': account_bet_contents
        }

# ==================== 结果展示器 ====================
class ResultPresenter:
    """结果展示器"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.logger = LogManager.setup_logger(self.__class__.__name__)
    
    def display_results(self, all_results: Dict, analysis_mode: str, df_target: pd.DataFrame = None):
        """展示结果"""
        if not all_results:
            st.info("🎉 未发现完美覆盖组合")
            return
        
        # 统计信息
        self._display_summary_statistics(all_results)
        
        # 详细组合
        self._display_detailed_combinations(all_results, analysis_mode, df_target)
    
    def _display_summary_statistics(self, all_results: Dict):
        """显示汇总统计"""
        st.subheader("📊 检测汇总")
        
        # 计算统计
        total_combinations = sum(result['total_combinations'] for result in all_results.values())
        total_filtered_accounts = sum(result['filtered_accounts'] for result in all_results.values())
        total_periods = len(set(result['period'] for result in all_results.values()))
        total_lotteries = len(set(result['lottery'] for result in all_results.values()))
        
        # 组合类型统计
        combo_type_stats = {2: 0, 3: 0, 4: 0}
        for result in all_results.values():
            for combo in result['all_combinations']:
                combo_type_stats[combo['account_count']] += 1
        
        # 显示统计
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总完美组合数", total_combinations)
        with col2:
            st.metric("分析期数", total_periods)
        with col3:
            st.metric("有效账户数", total_filtered_accounts)
        with col4:
            st.metric("涉及彩种", total_lotteries)
        
        st.subheader("🎲 组合类型统计")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("2账户组合", f"{combo_type_stats[2]}组")
        with col2:
            st.metric("3账户组合", f"{combo_type_stats[3]}组")
        with col3:
            st.metric("4账户组合", f"{combo_type_stats[4]}组")
    
    def _display_detailed_combinations(self, all_results: Dict, analysis_mode: str, df_target: pd.DataFrame = None):
        """显示详细组合"""
        st.subheader("📈 详细组合分析")
        
        # 按账户组合分组
        account_pair_groups = defaultdict(lambda: defaultdict(list))
        
        for result_key, result in all_period_results.items():
            lottery = result['lottery']
            position = result.get('position', None)
            
            for combo in result['all_combinations']:
                accounts = combo['accounts']
                account_pair = " ↔ ".join(sorted(accounts))
                
                if position:
                    lottery_key = f"{lottery} - {position}"
                else:
                    lottery_key = lottery
                
                combo_info = {
                    'period': result['period'],
                    'combo': combo,
                    'lottery_category': result['lottery_category'],
                    'total_numbers': result['total_numbers']
                }
                
                account_pair_groups[account_pair][lottery_key].append(combo_info)
        
        # 显示每个组合
        for account_pair, lottery_groups in account_pair_groups.items():
            for lottery_key, combos in lottery_groups.items():
                combos.sort(key=lambda x: x['period'])
                combo_count = len(combos)
                
                with st.expander(f"**{account_pair}** - {lottery_key}（{combo_count}个组合）", expanded=True):
                    for idx, combo_info in enumerate(combos, 1):
                        self._display_single_combo(combo_info, idx, account_pair)
                        
                        if idx < len(combos):
                            st.markdown("---")
    
    def _display_single_combo(self, combo_info: Dict, idx: int, account_pair: str):
        """显示单个组合"""
        combo = combo_info['combo']
        period = combo_info['period']
        
        st.markdown(f"**完美组合 {idx}:** {account_pair}")
        
        # 基本信息
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.write(f"**账户数量:** {combo['account_count']}个")
        with col2:
            st.write(f"**期号:** {period}")
        with col3:
            st.write(f"**总金额:** ¥{combo['total_amount']:,.2f}")
        with col4:
            similarity = combo['similarity']
            indicator = combo['similarity_indicator']
            st.write(f"**金额匹配度:** {similarity:.1f}% {indicator}")
        
        # 彩种类型
        category_name = self._get_category_display(combo_info['lottery_category'])
        st.write(f"**彩种类型:** {category_name}")
        
        # 各账户详情
        st.write("**各账户详情:**")
        for account in combo['accounts']:
            amount_info = combo['individual_amounts'][account]
            avg_info = combo['individual_avg_per_number'][account]
            numbers = combo['bet_contents'][account]
            numbers_count = len(numbers.split(', ')) if numbers else 0
            
            st.write(f"- **{account}**: {numbers_count}个数字")
            st.write(f"  - 总投注: ¥{amount_info:,.2f}")
            st.write(f"  - 平均每号: ¥{avg_info:,.2f}")
            st.write(f"  - 投注内容: {numbers}")
    
    def _get_category_display(self, lottery_category: str) -> str:
        """获取彩种类型显示名称"""
        category_map = {
            'six_mark': '六合彩',
            'six_mark_tail': '六合彩尾数',
            'pk10_base': '时时彩/PK10/赛车',
            'pk10_sum': '冠亚和',
            'fast_three_base': '快三基础',
            'fast_three_sum': '快三和值',
            'ssc_3d': '时时彩/3D'
        }
        return category_map.get(lottery_category, lottery_category)
    
    def export_results(self, all_results: Dict, analysis_mode: str) -> pd.DataFrame:
        """导出结果"""
        export_data = []
        
        for result_key, result in all_results.items():
            lottery_category = result['lottery_category']
            
            for combo in result['all_combinations']:
                # 基础信息
                export_record = {
                    '期号': result['period'],
                    '彩种': result['lottery'],
                    '彩种类型': self._get_category_display(lottery_category),
                    '号码总数': result['total_numbers'],
                    '组合类型': f"{combo['account_count']}账户组合",
                    '账户组合': ' ↔ '.join(combo['accounts']),
                    '总投注金额': combo['total_amount'],
                    '平均每号金额': combo['avg_amount_per_number'],
                    '金额匹配度': f"{combo['similarity']:.1f}%",
                    '匹配度等级': combo['similarity_indicator']
                }
                
                # 位置信息
                if 'position' in result and result['position']:
                    export_record['投注位置'] = result['position']
                
                # 各账户详情
                for i, account in enumerate(combo['accounts'], 1):
                    export_record[f'账户{i}'] = account
                    export_record[f'账户{i}总金额'] = combo['individual_amounts'][account]
                    export_record[f'账户{i}平均每号'] = combo['individual_avg_per_number'][account]
                    export_record[f'账户{i}号码数量'] = len(combo['bet_contents'][account].split(', '))
                    export_record[f'账户{i}投注内容'] = combo['bet_contents'][account]
                
                export_data.append(export_record)
        
        return pd.DataFrame(export_data)

# ==================== 主分析器 ====================
class MultiLotteryCoverageAnalyzer:
    """主分析器（协调器）"""
    
    def __init__(self):
        self.config = ConfigManager()
        self.data_preprocessor = DataPreprocessor(self.config)
        self.six_mark_analyzer = SixMarkAnalyzer(self.config)
        self.pk10_analyzer = PK10Analyzer(self.config)
        self.fast_three_analyzer = FastThreeAnalyzer(self.config)
        self.result_presenter = ResultPresenter(self.config)
        self.logger = LogManager.setup_logger(self.__class__.__name__)
    
    def analyze_with_progress(
        self, 
        df_target: pd.DataFrame, 
        six_mark_params: Dict, 
        ten_number_params: Dict, 
        fast_three_params: Dict, 
        ssc_3d_params: Dict, 
        analysis_mode: str,
        max_amount_ratio: float = 10.0
    ) -> Dict:
        """带进度显示的分析"""
        all_period_results = {}
        
        # 添加金额平衡参数
        six_mark_params['max_amount_ratio'] = max_amount_ratio
        ten_number_params['max_amount_ratio'] = max_amount_ratio
        fast_three_params['max_amount_ratio'] = max_amount_ratio
        ssc_3d_params['max_amount_ratio'] = max_amount_ratio
        
        # 根据分析模式筛选数据
        if analysis_mode == "仅分析六合彩":
            df_target = df_target[df_target['彩种类型'] == 'six_mark']
            all_period_results = self.six_mark_analyzer.analyze(df_target, six_mark_params)
            
        elif analysis_mode == "仅分析时时彩/PK10/赛车":
            df_target = df_target[df_target['彩种类型'] == 'pk10_base']
            all_period_results = self.pk10_analyzer.analyze(df_target, ten_number_params)
            
        elif analysis_mode == "仅分析快三":
            df_target = df_target[df_target['彩种类型'] == 'fast_three_sum']
            all_period_results = self.fast_three_analyzer.analyze(df_target, fast_three_params)
            
        else:
            # 自动识别所有彩种
            # 六合彩
            six_mark_data = df_target[df_target['彩种类型'] == 'six_mark']
            if len(six_mark_data) > 0:
                six_mark_results = self.six_mark_analyzer.analyze(six_mark_data, six_mark_params)
                all_period_results.update(six_mark_results)
            
            # PK10/时时彩
            pk10_data = df_target[df_target['彩种类型'] == 'pk10_base']
            if len(pk10_data) > 0:
                pk10_results = self.pk10_analyzer.analyze(pk10_data, ten_number_params)
                all_period_results.update(pk10_results)
            
            # 快三
            fast_three_data = df_target[df_target['彩种类型'].isin(['fast_three_sum', 'fast_three_base'])]
            if len(fast_three_data) > 0:
                fast_three_results = self.fast_three_analyzer.analyze(fast_three_data, fast_three_params)
                all_period_results.update(fast_three_results)
        
        return all_period_results

# ==================== Streamlit界面 ====================
def main():
    """主函数"""
    st.set_page_config(
        page_title="彩票完美覆盖分析系统",
        page_icon="🎯",
        layout="wide"
    )
    
    st.title("🎯 彩票完美覆盖分析系统")
    st.markdown("### 支持六合彩、时时彩、PK10、赛车、快三等多种彩票的智能对刷检测")
    
    analyzer = MultiLotteryCoverageAnalyzer()
    
    # 侧边栏设置
    st.sidebar.header("⚙️ 分析参数设置")
    
    # 文件上传
    st.sidebar.header("📁 数据上传")
    uploaded_file = st.sidebar.file_uploader(
        "上传投注数据文件", 
        type=['csv', 'xlsx', 'xls'],
        help="请上传包含彩票投注数据的Excel或CSV文件"
    )
    
    # 分析模式选择
    analysis_mode = st.sidebar.radio(
        "分析模式:",
        ["自动识别所有彩种", "仅分析六合彩", "仅分析时时彩/PK10/赛车", "仅分析快三"],
        help="选择要分析的彩种类型"
    )
    
    # 金额平衡设置
    st.sidebar.subheader("💰 金额平衡设置")
    max_amount_ratio = st.sidebar.slider(
        "组内最大金额与最小金额的允许倍数", 
        min_value=1, 
        max_value=50, 
        value=10,
        help="例如：10表示最大金额与最小金额的差距不超过10倍。设置为1则要求金额完全相等。"
    )
    
    # 各彩种参数设置（示例，可根据需要扩展）
    st.sidebar.subheader("🎯 六合彩参数设置")
    six_mark_min_number_count = st.sidebar.slider(
        "六合彩-号码数量阈值", 
        min_value=1, 
        max_value=30, 
        value=11
    )
    six_mark_min_avg_amount = st.sidebar.slider(
        "六合彩-平均金额阈值", 
        min_value=0, 
        max_value=50,
        value=10
    )
    
    st.sidebar.subheader("🏎️ 时时彩/PK10参数设置")
    ten_number_min_number_count = st.sidebar.slider(
        "PK10-号码数量阈值", 
        min_value=1, 
        max_value=10, 
        value=3
    )
    ten_number_min_avg_amount = st.sidebar.slider(
        "PK10-平均金额阈值", 
        min_value=0, 
        max_value=20,
        value=5
    )
    
    st.sidebar.subheader("🎲 快三参数设置")
    fast_three_min_number_count = st.sidebar.slider(
        "快三-号码数量阈值", 
        min_value=1, 
        max_value=16, 
        value=4
    )
    fast_three_min_avg_amount = st.sidebar.slider(
        "快三-平均金额阈值", 
        min_value=0, 
        max_value=20,
        value=5
    )
    
    if uploaded_file is not None:
        try:
            # 读取文件
            if uploaded_file.name.endswith('.csv'):
                try:
                    df = pd.read_csv(uploaded_file)
                except UnicodeDecodeError:
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file, encoding='gbk')
            else:
                df = pd.read_excel(uploaded_file)
            
            st.success(f"✅ 成功读取文件，共 {len(df):,} 条记录")
            
            # 数据预处理
            with st.spinner("正在处理数据..."):
                df_processed = analyzer.data_preprocessor.process(df)
            
            # 筛选有效玩法数据
            valid_plays = [
                '特码', '正码一', '正码二', '正码三', '正码四', '正码五', '正码六',
                '正一特', '正二特', '正三特', '正四特', '正五特', '正六特',
                '平码', '平特', '尾数', '特尾', '全尾',
                '冠军', '亚军', '季军', '第四名', '第五名', '第六名', '第七名', '第八名', '第九名', '第十名',
                '定位胆', '1-5名', '6-10名', '冠亚和',
                '和值', '三军', '二不同号', '三不同号',
                '第1球', '第2球', '第3球', '第4球', '第5球',
                '百位', '十位', '个位', '百十', '百个', '十个', '百十个'
            ]
            
            df_target = df_processed[df_processed['玩法'].isin(valid_plays)]
            
            if len(df_target) == 0:
                st.error("❌ 未找到符合条件的有效玩法数据")
                return
            
            # 分析数据
            with st.spinner("正在分析数据..."):
                six_mark_params = {
                    'min_number_count': six_mark_min_number_count,
                    'min_avg_amount': six_mark_min_avg_amount
                }
                ten_number_params = {
                    'min_number_count': ten_number_min_number_count,
                    'min_avg_amount': ten_number_min_avg_amount
                }
                fast_three_params = {
                    'min_number_count': fast_three_min_number_count,
                    'min_avg_amount': fast_three_min_avg_amount
                }
                ssc_3d_params = {
                    'min_number_count': 3,
                    'min_avg_amount': 5
                }
                
                all_period_results = analyzer.analyze_with_progress(
                    df_target, six_mark_params, ten_number_params, 
                    fast_three_params, ssc_3d_params, analysis_mode, max_amount_ratio
                )
            
            # 显示结果
            if all_period_results:
                total_combinations = sum(result['total_combinations'] for result in all_period_results.values())
                st.success(f"✅ 分析完成，共发现 {total_combinations} 个完美覆盖组合")
                analyzer.result_presenter.display_results(all_period_results, analysis_mode, df_target)
                
                # 导出功能
                st.markdown("---")
                st.subheader("📥 数据导出")
                
                if st.button("📊 生成完美组合数据报告"):
                    download_df = analyzer.result_presenter.export_results(all_period_results, analysis_mode)
                    
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        download_df.to_excel(writer, index=False, sheet_name='完美组合数据')
                    
                    st.download_button(
                        label="📥 下载分析报告",
                        data=output.getvalue(),
                        file_name=f"全彩种完美组合分析报告_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
                    st.success("✅ 数据导出准备完成!")
            else:
                st.info("📊 分析完成: 未发现完美覆盖组合")
            
        except Exception as e:
            st.error(f"❌ 处理文件时出错: {str(e)}")
            st.code(f"""
错误类型: {type(e).__name__}
错误信息: {str(e)}

可能的原因:
1. 文件编码问题 - 尝试将文件另存为UTF-8编码
2. 文件格式问题 - 确保文件是有效的CSV或Excel格式
3. 列名不匹配 - 检查文件是否包含必要的列
            """)
    
    else:
        # 显示使用说明
        st.info("💡 **彩票完美覆盖分析系统**")
        st.markdown("""
        ### 🚀 系统特色功能:

        **🎲 全彩种支持**
        - ✅ **六合彩**: 1-49个号码，支持特码、正码、正特、平码、尾数等多种玩法
        - ✅ **时时彩/PK10/赛车**: 1-10共10个号码，按期号合并分析
        - ✅ **快三**: 3-18共16个和值，按位置精准分析
        - 🔄 **自动识别**: 智能识别彩种类型

        **⚡ 性能优化**
        - 🔄 智能缓存机制
        - 📈 模块化设计，代码清晰
        - 🎨 现代化架构，易于维护

        **📊 分析增强**
        - 👥 支持2-4账户组合检测
        - 💰 金额平衡检查
        - 🎯 精确的位置识别
        """)

if __name__ == "__main__":
    main()
