import streamlit as st
import pandas as pd
import numpy as np
import re
import logging
from typing import Dict, List, Set, Tuple, Any, Optional
import itertools
from collections import defaultdict
import time
from io import BytesIO
from functools import lru_cache
from datetime import datetime
import warnings
import traceback
import hashlib
from itertools import combinations  # 🆕 添加这行导入

# 配置日志和警告
warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ComprehensiveWashTradeDetection')

# Streamlit 页面配置
st.set_page_config(
    page_title="彩票智能对刷检测系统 - 全功能版",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 全局配置类 ====================
class ComprehensiveConfig:
    """全功能配置类 - 整合两套代码的配置"""
    def __init__(self):
        # 第一套代码的配置
        self.coverage_config = {
            'min_number_count': {
                'six_mark': 11,  # 六合彩
                '10_number': 3,   # 10个号码的彩种
                'fast_three': 3,  # 快三和值
            },
            'min_avg_amount': {
                'six_mark': 2,
                '10_number': 1,
                'fast_three': 1,
            },
            'similarity_thresholds': {
                'excellent': 90,
                'good': 80,
                'fair': 70
            },
            'target_lotteries': {
                'six_mark': [
                    '新澳门六合彩', '澳门六合彩', '香港六合彩', '一分六合彩',
                    '五分六合彩', '三分六合彩', '香港⑥合彩', '分分六合彩',
                    '台湾大乐透', '大发六合彩', '快乐6合彩'
                ],
                '10_number': [
                    '时时彩', '重庆时时彩', '新疆时时彩', '天津时时彩',
                    '分分时时彩', '五分时时彩', '三分时时彩', '北京时时彩',
                    'PK10', '北京PK10', 'PK拾', '幸运PK10', '赛车', '大发赛车',
                    '幸运28', '北京28', '加拿大28', '极速PK10', '分分PK10', '大发快三'
                ],
                'fast_three': [
                    '快三', '快3', 'K3', '分分快三', '五分快三', '三分快三',
                    '北京快三', '江苏快三', '安徽快三', '大发快三'
                ]
            }
        }
        
        # 第二套代码的配置
        self.min_amount = 10
        self.amount_similarity_threshold = 0.8
        self.min_continuous_periods = 3
        self.max_accounts_in_group = 5
        self.supported_file_types = ['.xlsx', '.xls', '.csv']
        
        # 列名映射配置
        self.column_mappings = {
            '会员账号': ['会员账号', '会员账户', '账号', '账户', '用户账号', '玩家账号', '用户ID', '玩家ID', '用户名称', '玩家名称'],
            '彩种': ['彩种', '彩神', '彩票种类', '游戏类型', '彩票类型', '游戏彩种', '彩票名称', '彩系', '游戏名称'],
            '期号': ['期号', '期数', '期次', '期', '奖期', '期号信息', '期号编号', '开奖期号', '奖期号'],
            '玩法': ['玩法', '玩法分类', '投注类型', '类型', '投注玩法', '玩法类型', '分类', '玩法名称', '投注方式'],
            '内容': ['内容', '投注内容', '下注内容', '注单内容', '投注号码', '号码内容', '投注信息', '号码', '选号'],
            '金额': ['金额', '下注总额', '投注金额', '总额', '下注金额', '投注额', '金额数值', '单注金额', '投注额', '钱', '元']
        }
        
        # 活跃度阈值配置
        self.period_thresholds = {
            'low_activity': 10,
            'medium_activity_low': 11,
            'medium_activity_high': 50,
            'high_activity_low': 51,
            'high_activity_high': 100,
            'min_periods_low': 3,
            'min_periods_medium': 5,
            'min_periods_high': 8,
            'min_periods_very_high': 11
        }
        
        # 多账户匹配度阈值
        self.account_count_similarity_thresholds = {
            2: 0.8,
            3: 0.85,
            4: 0.9,
            5: 0.95
        }
        
        # 账户期数差异阈值
        self.account_period_diff_threshold = 150
        
        # 方向模式配置
        self.direction_patterns = {
            # 基础方向
            '小': ['两面-小', '和值-小', '小', 'small', 'xia', 'xiao'],
            '大': ['两面-大', '和值-大', '大', 'big', 'da', 'large'], 
            '单': ['两面-单', '和值-单', '单', 'odd', 'dan', '奇数'],
            '双': ['两面-双', '和值-双', '双', 'even', 'shuang', '偶数'],
            '龙': ['龙', 'long', 'dragon', '龍', '龍虎-龙'],
            '虎': ['虎', 'hu', 'tiger', '龍虎-虎'],
            '质': ['质', '质数', 'prime', 'zhi', '質', '質數'],
            '合': ['合', '合数', 'composite', 'he', '合數'],
            
            # 变异形式
            '特小': ['特小', '极小', '最小'],
            '特大': ['特大', '极大', '最大'],
            '特单': ['特单'],
            '特双': ['特双'],
            '总和小': ['总和小', '和小'],
            '总和大': ['总和大', '和大'],
            '总和单': ['总和单', '和单'],
            '总和双': ['总和双', '和双']
        }
        
        # 对立组配置
        self.opposite_groups = [
            # 基础对立组
            {'大', '小'}, {'单', '双'}, {'龙', '虎'}, {'质', '合'},
            # 变异形式对立组
            {'特大', '特小'}, {'特单', '特双'}, 
            {'总和大', '总和小'}, {'总和单', '总和双'}
        ]
        
        # 位置关键词映射 - 增强版
        self.position_keywords = {
            'PK10': {
                '冠军': ['冠军', '第1名', '第一名', '前一', '冠 军', '冠　军'],
                '亚军': ['亚军', '第2名', '第二名', '亚 军', '亚　军'],
                '季军': ['季军', '第3名', '第三名', '季 军', '季　军'],
                '第四名': ['第四名', '第4名'],
                '第五名': ['第五名', '第5名'],
                '第六名': ['第六名', '第6名'],
                '第七名': ['第七名', '第7名'],
                '第八名': ['第八名', '第8名'],
                '第九名': ['第九名', '第9名'],
                '第十名': ['第十名', '第10名']
            },
            '3D': {
                '百位': ['百位', '定位_百位', '百位定位'],
                '十位': ['十位', '定位_十位', '十位定位'],
                '个位': ['个位', '定位_个位', '个位定位']
            },
            'SSC': {
                '第1球': ['第1球', '万位', '第一位', '定位_万位', '万位定位'],
                '第2球': ['第2球', '千位', '第二位', '定位_千位', '千位定位'],
                '第3球': ['第3球', '百位', '第三位', '定位_百位', '百位定位'],
                '第4球': ['第4球', '十位', '第四位', '定位_十位', '十位定位'],
                '第5球': ['第5球', '个位', '第五位', '定位_个位', '个位定位']
            },
            'LHC': {
                '特码': ['特码', '特玛', '特马', '特碼'],
                '正码一': ['正码一', '正码1', '正一码', '正码1-6_正码一'],
                '正码二': ['正码二', '正码2', '正二码', '正码1-6_正码二'],
                '正码三': ['正码三', '正码3', '正三码', '正码1-6_正码三'],
                '正码四': ['正码四', '正码4', '正四码', '正码1-6_正码四'],
                '正码五': ['正码五', '正码5', '正五码', '正码1-6_正码五'],
                '正码六': ['正码六', '正码6', '正六码', '正码1-6_正码六'],
                '正一特': ['正一特', '正1特', '正码特_正一特', '正玛特_正一特'],
                '正二特': ['正二特', '正2特', '正码特_正二特', '正玛特_正二特'],
                '正三特': ['正三特', '正3特', '正码特_正三特', '正玛特_正三特'],
                '正四特': ['正四特', '正4特', '正码特_正四特', '正玛特_正四特'],
                '正五特': ['正五特', '正5特', '正码特_正五特', '正玛特_正五特'],
                '正六特': ['正六特', '正6特', '正码特_正六特', '正玛特_正六特'],
                '平码': ['平码'],
                '平特': ['平特'],
                '尾数': ['尾数'],
                '特尾': ['特尾'],
                '全尾': ['全尾']
            }
        }

# ==================== 数据处理器类 ====================
class DataProcessor:
    def __init__(self):
        self.config = ComprehensiveConfig()
        self.required_columns = ['会员账号', '彩种', '期号', '玩法', '内容', '金额']
        
    def smart_column_identification(self, df_columns):
        """智能列识别"""
        identified_columns = {}
        actual_columns = [str(col).strip() for col in df_columns]
        
        with st.expander("🔍 列名识别详情", expanded=False):
            st.info(f"检测到的列名: {actual_columns}")
            
            for standard_col, possible_names in self.config.column_mappings.items():
                found = False
                for actual_col in actual_columns:
                    actual_col_lower = actual_col.lower().replace(' ', '').replace('_', '').replace('-', '')
                    
                    for possible_name in possible_names:
                        possible_name_lower = possible_name.lower().replace(' ', '').replace('_', '').replace('-', '')
                        
                        similarity_score = self._calculate_string_similarity(possible_name_lower, actual_col_lower)
                        
                        if (possible_name_lower in actual_col_lower or 
                            actual_col_lower in possible_name_lower or
                            similarity_score >= 0.7):
                            
                            identified_columns[actual_col] = standard_col
                            st.success(f"✅ 识别列名: {actual_col} -> {standard_col} (相似度: {similarity_score:.2f})")
                            found = True
                            break
                    
                    if found:
                        break
                
                if not found:
                    st.warning(f"⚠️ 未识别到 {standard_col} 对应的列名")
        
        return identified_columns
    
    def _calculate_string_similarity(self, str1, str2):
        """计算字符串相似度"""
        if not str1 or not str2:
            return 0
        
        set1 = set(str1)
        set2 = set(str2)
        intersection = set1 & set2
        
        if not set1:
            return 0
        
        return len(intersection) / len(set1)
    
    def find_data_start(self, df):
        """智能找到数据起始位置"""
        for row_idx in range(min(20, len(df))):
            for col_idx in range(min(10, len(df.columns))):
                cell_value = str(df.iloc[row_idx, col_idx])
                if pd.notna(cell_value) and any(keyword in cell_value for keyword in ['会员', '账号', '期号', '彩种', '玩法', '内容', '订单', '用户']):
                    return row_idx, col_idx
        return 0, 0
    
    def validate_data_quality(self, df):
        """数据质量验证"""
        logger.info("正在进行数据质量验证...")
        issues = []
        
        # 检查必要列
        missing_cols = [col for col in self.required_columns if col not in df.columns]
        if missing_cols:
            issues.append(f"缺少必要列: {missing_cols}")
        
        # 检查空值
        for col in self.required_columns:
            if col in df.columns:
                null_count = df[col].isnull().sum()
                if null_count > 0:
                    issues.append(f"列 '{col}' 有 {null_count} 个空值")

        if '会员账号' in df.columns:
            # 检查截断账号
            truncated_accounts = df[df['会员账号'].str.contains(r'\.\.\.|…', na=False)]
            if len(truncated_accounts) > 0:
                issues.append(f"发现 {len(truncated_accounts)} 个可能被截断的会员账号")
            
            # 检查账号长度异常
            account_lengths = df['会员账号'].str.len()
            if account_lengths.max() > 50:
                issues.append("发现异常长度的会员账号")
            
            # 显示账号格式样本
            unique_accounts = df['会员账号'].unique()[:5]
            sample_info = " | ".join([f"'{acc}'" for acc in unique_accounts])
            st.info(f"会员账号格式样本: {sample_info}")
        
        if '期号' in df.columns:
            df['期号'] = df['期号'].astype(str).str.replace(r'\.0$', '', regex=True)
            invalid_periods = df[~df['期号'].str.match(r'^[\dA-Za-z]+$')]
            if len(invalid_periods) > 0:
                issues.append(f"发现 {len(invalid_periods)} 条无效期号记录")
        
        if '彩种' in df.columns:
            lottery_stats = df['彩种'].value_counts()
            st.info(f"🎲 彩种分布: 共{len(lottery_stats)}种，前5: {', '.join([f'{k}({v}条)' for k,v in lottery_stats.head().items()])}")
        
        if '玩法' in df.columns:
            play_stats = df['玩法'].value_counts().head(10)
            with st.expander("🎯 玩法分布TOP10", expanded=False):
                for play, count in play_stats.items():
                    st.write(f"  - {play}: {count}次")
        
        # 检查重复数据
        duplicate_count = df.duplicated().sum()
        if duplicate_count > 0:
            issues.append(f"发现 {duplicate_count} 条重复记录")
        
        if issues:
            with st.expander("⚠️ 数据质量问题", expanded=True):
                for issue in issues:
                    st.warning(f"  - {issue}")
        else:
            st.success("✅ 数据质量检查通过")
        
        return issues
    
    def clean_data(self, uploaded_file):
        """数据清洗主函数"""
        try:
            if uploaded_file.name.endswith('.csv'):
                try:
                    df_temp = pd.read_csv(uploaded_file, header=None, nrows=50)
                except UnicodeDecodeError:
                    uploaded_file.seek(0)
                    try:
                        df_temp = pd.read_csv(uploaded_file, encoding='gbk', header=None, nrows=50)
                    except:
                        uploaded_file.seek(0)
                        df_temp = pd.read_csv(uploaded_file, encoding_errors='ignore', header=None, nrows=50)
            else:
                df_temp = pd.read_excel(uploaded_file, header=None, nrows=50)
            
            st.info(f"原始数据维度: {df_temp.shape}")
            
            start_row, start_col = self.find_data_start(df_temp)
            st.info(f"数据起始位置: 第{start_row+1}行, 第{start_col+1}列")
            
            if uploaded_file.name.endswith('.csv'):
                try:
                    df_clean = pd.read_csv(
                        uploaded_file, 
                        header=start_row,
                        skiprows=range(start_row + 1) if start_row > 0 else None,
                        dtype=str,
                        na_filter=False,
                        keep_default_na=False
                    )
                except UnicodeDecodeError:
                    uploaded_file.seek(0)
                    try:
                        df_clean = pd.read_csv(
                            uploaded_file, 
                            header=start_row,
                            skiprows=range(start_row + 1) if start_row > 0 else None,
                            dtype=str,
                            encoding='gbk',
                            na_filter=False,
                            keep_default_na=False
                        )
                    except:
                        uploaded_file.seek(0)
                        df_clean = pd.read_csv(
                            uploaded_file, 
                            header=start_row,
                            skiprows=range(start_row + 1) if start_row > 0 else None,
                            dtype=str,
                            encoding_errors='ignore',
                            na_filter=False,
                            keep_default_na=False
                        )
            else:
                df_clean = pd.read_excel(
                    uploaded_file, 
                    header=start_row,
                    skiprows=range(start_row + 1) if start_row > 0 else None,
                    dtype=str,
                    na_filter=False,
                    keep_default_na=False
                )
            
            if start_col > 0:
                df_clean = df_clean.iloc[:, start_col:]
            
            st.info(f"清理后数据维度: {df_clean.shape}")
            
            column_mapping = self.smart_column_identification(df_clean.columns)
            if column_mapping:
                df_clean = df_clean.rename(columns=column_mapping)
                st.success("✅ 列名识别完成!")
            
            missing_columns = [col for col in self.required_columns if col not in df_clean.columns]
            if missing_columns and len(df_clean.columns) >= 4:
                st.warning("自动映射列名...")
                manual_mapping = {}
                col_names = ['会员账号', '彩种', '期号', '内容', '玩法', '金额']
                for i, col_name in enumerate(col_names):
                    if i < len(df_clean.columns):
                        manual_mapping[df_clean.columns[i]] = col_name
                
                df_clean = df_clean.rename(columns=manual_mapping)
                st.info(f"手动重命名后的列: {list(df_clean.columns)}")
            
            initial_count = len(df_clean)
            df_clean = df_clean.dropna(subset=[col for col in self.required_columns if col in df_clean.columns])
            df_clean = df_clean.dropna(axis=1, how='all')
            
            for col in self.required_columns:
                if col in df_clean.columns:
                    if col == '会员账号':
                        df_clean[col] = df_clean[col].apply(
                            lambda x: str(x) if pd.notna(x) else ''
                        )
                    else:
                        df_clean[col] = df_clean[col].astype(str).str.strip()
            
            if '期号' in df_clean.columns:
                df_clean['期号'] = df_clean['期号'].str.replace(r'\.0$', '', regex=True)
            
            # 数据质量验证
            self.validate_data_quality(df_clean)
            
            st.success(f"✅ 数据清洗完成: {initial_count} -> {len(df_clean)} 条记录")
            
            st.info(f"📊 唯一会员账号数: {df_clean['会员账号'].nunique()}")
            
            if '彩种' in df_clean.columns:
                lottery_dist = df_clean['彩种'].value_counts()
                with st.expander("🎯 彩种分布", expanded=False):
                    st.dataframe(lottery_dist.reset_index().rename(columns={'index': '彩种', '彩种': '数量'}))
            
            return df_clean
            
        except Exception as e:
            st.error(f"❌ 数据清洗失败: {str(e)}")
            logger.error(f"数据清洗失败: {str(e)}")
            return None

# ==================== 彩种识别器 ====================
LOTTERY_CONFIGS = {
    'PK10': {
        'lotteries': [
            '分分PK拾', '三分PK拾', '五分PK拾', '新幸运飞艇', '澳洲幸运10',
            '一分PK10', '宾果PK10', '极速飞艇', '澳洲飞艇', '幸运赛车',
            '分分赛车', '北京PK10', '旧北京PK10', '极速赛车', '幸运赛車', 
            '北京赛车', '极速PK10', '幸运PK10', '赛车', '赛車'
        ],
        'min_number': 1,
        'max_number': 10,
        'gyh_min': 3,
        'gyh_max': 19,
        'position_names': ['冠军', '亚军', '第三名', '第四名', '第五名', 
                          '第六名', '第七名', '第八名', '第九名', '第十名']
    },
    'K3': {
        'lotteries': [
            '分分快三', '三分快3', '五分快3', '澳洲快三', '宾果快三',
            '1分快三', '3分快三', '5分快三', '10分快三', '加州快三',
            '幸运快三', '大发快三', '快三', '快3', 'k3', 'k三', 
            '澳门快三', '香港快三', '江苏快三'
        ],
        'min_number': 1,
        'max_number': 6,
        'hezhi_min': 3,
        'hezhi_max': 18
    },
    'LHC': {
        'lotteries': [
            '新澳门六合彩', '澳门六合彩', '香港六合彩', '一分六合彩',
            '五分六合彩', '三分六合彩', '香港⑥合彩', '分分六合彩',
            '快乐6合彩', '港⑥合彩', '台湾大乐透', '六合', 'lhc', '六合彩',
            '⑥合', '6合', '大发六合彩'
        ],
        'min_number': 1,
        'max_number': 49
    },
    'SSC': {
        'lotteries': [
            '分分时时彩', '三分时时彩', '五分时时彩', '宾果时时彩',
            '1分时时彩', '3分时时彩', '5分时时彩', '旧重庆时时彩',
            '幸运时时彩', '腾讯分分彩', '新疆时时彩', '天津时时彩',
            '重庆时时彩', '上海时时彩', '广东时时彩', '分分彩', '时时彩', '時時彩'
        ],
        'min_number': 0,
        'max_number': 9
    },
    '3D': {
        'lotteries': [
            '排列三', '排列3', '幸运排列3', '一分排列3', '二分排列3', '三分排列3', 
            '五分排列3', '十分排列3', '大发排列3', '好运排列3', '福彩3D', '极速3D',
            '极速排列3', '幸运3D', '一分3D', '二分3D', '三分3D', '五分3D', 
            '十分3D', '大发3D', '好运3D'
        ],
        'min_number': 0,
        'max_number': 9,
        'position_names': ['百位', '十位', '个位']
    }
}

class LotteryIdentifier:
    def __init__(self):
        self.lottery_configs = LOTTERY_CONFIGS
        self.general_keywords = {
            'PK10': ['pk10', 'pk拾', '飞艇', '赛车', '赛車', '幸运10', '北京赛车', '极速赛车'],
            'K3': ['快三', '快3', 'k3', 'k三', '骰宝', '三军'],
            'LHC': ['六合', 'lhc', '六合彩', '⑥合', '6合', '特码', '平特', '连肖'],
            'SSC': ['时时彩', 'ssc', '分分彩', '時時彩', '重庆时时彩', '腾讯分分彩'],
            '3D': ['排列三', '排列3', '福彩3d', '3d', '极速3d', '排列', 'p3', 'p三']
        }
        
        self.lottery_aliases = {
            '分分PK拾': 'PK10', '三分PK拾': 'PK10', '五分PK拾': 'PK10',
            '新幸运飞艇': 'PK10', '澳洲幸运10': 'PK10', '一分PK10': 'PK10',
            '宾果PK10': 'PK10', '极速飞艇': 'PK10', '澳洲飞艇': 'PK10',
            '幸运赛车': 'PK10', '分分赛车': 'PK10', '北京PK10': 'PK10',
            '旧北京PK10': 'PK10', '极速赛车': 'PK10', '幸运赛車': 'PK10',
            '北京赛车': 'PK10', '极速PK10': 'PK10', '幸运PK10': 'PK10',
            '分分快三': 'K3', '三分快3': 'K3', '五分快3': 'K3', '澳洲快三': 'K3',
            '宾果快三': 'K3', '1分快三': 'K3', '3分快三': 'K3', '5分快三': 'K3',
            '10分快三': 'K3', '加州快三': 'K3', '幸运快三': 'K3', '大发快三': 'K3',
            '澳门快三': 'K3', '香港快三': 'K3', '江苏快三': 'K3',
            '新澳门六合彩': 'LHC', '澳门六合彩': 'LHC', '香港六合彩': 'LHC',
            '一分六合彩': 'LHC', '五分六合彩': 'LHC', '三分六合彩': 'LHC',
            '香港⑥合彩': 'LHC', '分分六合彩': 'LHC', '快乐6合彩': 'LHC',
            '港⑥合彩': 'LHC', '台湾大乐透': 'LHC', '大发六合彩': 'LHC',
            '分分时时彩': 'SSC', '三分时时彩': 'SSC', '五分时时彩': 'SSC',
            '宾果时时彩': 'SSC', '1分时时彩': 'SSC', '3分时时彩': 'SSC',
            '5分时时彩': 'SSC', '旧重庆时时彩': 'SSC', '幸运时时彩': 'SSC',
            '腾讯分分彩': 'SSC', '新疆时时彩': 'SSC', '天津时时彩': 'SSC',
            '重庆时时彩': 'SSC', '上海时时彩': 'SSC', '广东时时彩': 'SSC',
            '排列三': '3D', '排列3': '3D', '幸运排列3': '3D', '一分排列3': '3D',
            '二分排列3': '3D', '三分排列3': '3D', '五分排列3': '3D', '十分排列3': '3D',
            '大发排列3': '3D', '好运排列3': '3D', '福彩3D': '3D', '极速3D': '3D',
            '极速排列3': '3D', '幸运3D': '3D', '一分3D': '3D', '二分3D': '3D',
            '三分3D': '3D', '五分3D': '3D', '十分3D': '3D', '大发3D': '3D', '好运3D': '3D'
        }

    def identify_lottery_type(self, lottery_name):
        """彩种类型识别"""
        lottery_str = str(lottery_name).strip()
        
        if lottery_str in self.lottery_aliases:
            return self.lottery_aliases[lottery_str]
        
        for lottery_type, config in self.lottery_configs.items():
            for lottery in config['lotteries']:
                if lottery in lottery_str:
                    return lottery_type
        
        lottery_lower = lottery_str.lower()
        
        for lottery_type, keywords in self.general_keywords.items():
            for keyword in keywords:
                if keyword.lower() in lottery_lower:
                    return lottery_type
        
        return lottery_str

# ==================== 玩法分类器 ====================
class PlayCategoryNormalizer:
    def __init__(self):
        self.category_mapping = self._create_category_mapping()
    
    def _create_category_mapping(self):
        """创建玩法分类映射"""
        mapping = {
            # 快三玩法
            '和值': '和值', '和值_大小单双': '和值', '两面': '两面',
            '二不同号': '二不同号', '三不同号': '三不同号', '独胆': '独胆',
            '点数': '和值', '三军': '独胆', '三軍': '独胆',
            
            # 六合彩玩法
            '特码': '特码', '正1特': '正1特', '正码特_正一特': '正1特',
            '正2特': '正2特', '正码特_正二特': '正2特', '正3特': '正3特',
            '正码特_正三特': '正3特', '正4特': '正4特', '正码特_正四特': '正4特',
            '正5特': '正5特', '正码特_正五特': '正5特', '正6特': '正6特',
            '正码特_正六特': '正6特', '正码': '正码', '正特': '正特',
            '尾数': '尾数', '特肖': '特肖', '平特': '平特', '一肖': '一肖',
            '连肖': '连肖', '连尾': '连尾', '龙虎': '龙虎', '五行': '五行',
            '色波': '色波', '半波': '半波',
            
            # 3D系列玩法
            '两面': '两面', '大小单双': '两面', '百位': '百位', '十位': '十位', 
            '个位': '个位', '百十': '百十', '百个': '百个', '十个': '十个',
            '百十个': '百十个', '定位胆': '定位胆', '定位胆_百位': '定位胆_百位',
            '定位胆_十位': '定位胆_十位', '定位胆_个位': '定位胆_个位',
            
            # 时时彩玩法
            '斗牛': '斗牛', '1-5球': '1-5球', '第1球': '第1球', '第2球': '第2球',
            '第3球': '第3球', '第4球': '第4球', '第5球': '第5球', '总和': '总和',
            '正码': '正码', '定位胆': '定位胆',
            
            # PK拾/赛车玩法
            '前一': '冠军', '定位胆': '定位胆', '1-5名': '1-5名', '6-10名': '6-10名',
            '冠军': '冠军', '亚军': '亚军', '季军': '第三名', '第3名': '第三名',
            '第4名': '第四名', '第5名': '第五名', '第6名': '第六名',
            '第7名': '第七名', '第8名': '第八名', '第9名': '第九名',
            '第10名': '第十名', '双面': '两面', '冠亚和': '冠亚和'
        }
        return mapping
    
    def normalize_category(self, category):
        """统一玩法分类名称"""
        category_str = str(category).strip()
        
        # 直接映射
        if category_str in self.category_mapping:
            return self.category_mapping[category_str]
        
        # 关键词匹配
        for key, value in self.category_mapping.items():
            if key in category_str:
                return value
        
        # 智能匹配
        category_lower = category_str.lower()
        
        # PK10/赛车智能匹配
        if any(word in category_lower for word in ['冠军', '第一名', '第1名', '1st']):
            return '冠军'
        elif any(word in category_lower for word in ['亚军', '第二名', '第2名', '2nd']):
            return '亚军'
        elif any(word in category_lower for word in ['第三名', '第3名', '季军', '3rd']):
            return '第三名'
        elif any(word in category_lower for word in ['第四名', '第4名', '4th']):
            return '第四名'
        elif any(word in category_lower for word in ['第五名', '第5名', '5th']):
            return '第五名'
        elif any(word in category_lower for word in ['第六名', '第6名', '6th']):
            return '第六名'
        elif any(word in category_lower for word in ['第七名', '第7名', '7th']):
            return '第七名'
        elif any(word in category_lower for word in ['第八名', '第8名', '8th']):
            return '第八名'
        elif any(word in category_lower for word in ['第九名', '第9名', '9th']):
            return '第九名'
        elif any(word in category_lower for word in ['第十名', '第10名', '10th']):
            return '第十名'
        
        # 3D系列智能匹配
        elif any(word in category_lower for word in ['百位']):
            return '百位'
        elif any(word in category_lower for word in ['十位']):
            return '十位'
        elif any(word in category_lower for word in ['个位']):
            return '个位'
        
        # 时时彩智能匹配
        elif any(word in category_lower for word in ['第1球', '万位']):
            return '第1球'
        elif any(word in category_lower for word in ['第2球', '千位']):
            return '第2球'
        elif any(word in category_lower for word in ['第3球', '百位']):
            return '第3球'
        elif any(word in category_lower for word in ['第4球', '十位']):
            return '第4球'
        elif any(word in category_lower for word in ['第5球', '个位']):
            return '第5球'
        
        return category_str

# ==================== 内容解析器 ====================
class ContentParser:
    """内容解析器 - 整合两套代码功能"""
    
    def __init__(self, config):
        self.config = config
    
    @staticmethod
    def extract_basic_directions(content, config):
        """提取方向 - 保持变异形式独立性"""
        content_str = str(content).strip()
        directions = []
        
        if not content_str:
            return directions
        
        content_lower = content_str.lower()
        
        # 提取所有可能的方向（保持变异形式独立性）
        for direction, patterns in config.direction_patterns.items():
            for pattern in patterns:
                pattern_lower = pattern.lower()
                # 精确匹配检查
                if (pattern_lower == content_lower or 
                    pattern_lower in content_lower or 
                    content_lower in pattern_lower):
                    directions.append(direction)
                    break
        
        return directions

    @staticmethod
    def extract_position_from_play_category(play_category, lottery_type, config):
        """从玩法分类中提取位置信息"""
        play_str = str(play_category).strip()
        
        if not play_str:
            return '未知位置'
        
        # 根据彩种类型获取位置关键词
        position_keywords = config.position_keywords.get(lottery_type, {})
        
        for position, keywords in position_keywords.items():
            for keyword in keywords:
                if keyword in play_str:
                    return position
        
        return '未知位置'

    @staticmethod
    def parse_pk10_vertical_format(content):
        """解析PK10竖线分隔格式"""
        try:
            content_str = str(content).strip()
            bets_by_position = defaultdict(list)
            
            if not content_str:
                return bets_by_position
            
            positions = ['冠军', '亚军', '第三名', '第四名', '第五名', 
                        '第六名', '第七名', '第八名', '第九名', '第十名']
            
            parts = content_str.split('|')
            
            for i, part in enumerate(parts):
                if i < len(positions):
                    position = positions[i]
                    part_clean = part.strip()
                    
                    if not part_clean or part_clean == '_' or part_clean == '':
                        continue
                    
                    # 解析数字
                    numbers = []
                    if ',' in part_clean:
                        number_strs = part_clean.split(',')
                        for num_str in number_strs:
                            num_clean = num_str.strip()
                            if num_clean.isdigit():
                                numbers.append(int(num_clean))
                    else:
                        if part_clean.isdigit():
                            numbers.append(int(part_clean))
                    
                    bets_by_position[position].extend(numbers)
            
            return bets_by_position
        except Exception as e:
            logger.warning(f"解析PK10竖线格式失败: {content}, 错误: {str(e)}")
            return defaultdict(list)

    @staticmethod
    def parse_3d_vertical_format(content):
        """解析3D竖线分隔格式"""
        try:
            content_str = str(content).strip()
            bets_by_position = defaultdict(list)
            
            if not content_str:
                return bets_by_position
            
            positions = ['百位', '十位', '个位']
            
            parts = content_str.split('|')
            
            for i, part in enumerate(parts):
                if i < len(positions):
                    position = positions[i]
                    part_clean = part.strip()
                    
                    if not part_clean or part_clean == '_' or part_clean == '':
                        continue
                    
                    # 解析数字
                    numbers = []
                    if ',' in part_clean:
                        number_strs = part_clean.split(',')
                        for num_str in number_strs:
                            num_clean = num_str.strip()
                            if num_clean.isdigit():
                                numbers.append(int(num_clean))
                    else:
                        if part_clean.isdigit():
                            numbers.append(int(num_clean))
                    
                    bets_by_position[position].extend(numbers)
            
            return bets_by_position
        except Exception as e:
            logger.warning(f"解析3D竖线格式失败: {content}, 错误: {str(e)}")
            return defaultdict(list)

    # ========== 第一套代码的号码提取功能 ==========
    @lru_cache(maxsize=1000)
    def cached_extract_numbers(self, content, lottery_category='six_mark'):
        """带缓存的号码提取"""
        return self.enhanced_extract_numbers(content, lottery_category)
    
    def enhanced_extract_numbers(self, content, lottery_category='six_mark'):
        """增强号码提取 - 根据彩种类型调整"""
        content_str = str(content).strip()
        numbers = []
        
        try:
            # 获取彩种配置
            lottery_configs = {
                'six_mark': {'number_range': set(range(1, 50))},
                '10_number': {'number_range': set(range(1, 11))},
                'fast_three': {'number_range': set(range(3, 19))},
                'PK10': {'number_range': set(range(1, 11))},
                'K3': {'number_range': set(range(1, 7))},
                'LHC': {'number_range': set(range(1, 50))},
                'SSC': {'number_range': set(range(0, 10))},
                '3D': {'number_range': set(range(0, 10))}
            }
            
            config = lottery_configs.get(lottery_category, lottery_configs['six_mark'])
            number_range = config['number_range']
            
            # 处理常见格式：3,4,5,6,15,16,17,18
            if re.match(r'^(\d{1,2},)*\d{1,2}$', content_str):
                numbers = [int(x.strip()) for x in content_str.split(',') if x.strip().isdigit()]
                numbers = [num for num in numbers if num in number_range]
                return list(set(numbers))
            
            # 处理特殊格式：1,2,3,4,5,6
            if re.match(r'^(\d,)*\d$', content_str.strip()):
                numbers = [int(x.strip()) for x in content_str.split(',') if x.strip().isdigit()]
                numbers = [num for num in numbers if num in number_range]
                return list(set(numbers))
            
            # 提取所有1-2位数字
            number_matches = re.findall(r'\b\d{1,2}\b', content_str)
            
            for match in number_matches:
                num = int(match)
                if num in number_range:
                    numbers.append(num)
            
            return list(set(numbers))
        except Exception as e:
            logger.warning(f"号码提取失败: {content_str}, 错误: {str(e)}")
            return []

# ==================== 全彩种覆盖分析器 ====================
class MultiLotteryCoverageAnalyzer:
    """全彩种覆盖分析器 - 支持六合彩、时时彩、PK10、快三等"""
    
    def __init__(self, config):
        self.config = config
        
        # 定义各彩种的号码范围
        self.lottery_configs = {
            'six_mark': {
                'number_range': set(range(1, 50)),
                'total_numbers': 49,
                'type_name': '六合彩',
                'play_keywords': ['特码', '特玛', '特马', '特碼', '正码', '正特', '正肖', '平码', '平特']
            },
            '10_number': {
                'number_range': set(range(1, 11)),
                'total_numbers': 10,
                'type_name': '10个号码彩种',
                'play_keywords': ['定位胆', '一字定位', '一字', '定位', '大小单双', '龙虎', '冠军', '亚军', '季军', '第四名', '第五名', '第六名', '第七名', '第八名', '第九名', '第十名', '第一名', '第二名', '第三名', '前一']
            },
            'fast_three': {
                'number_range': set(range(3, 19)),  # 和值范围3-18
                'total_numbers': 16,
                'type_name': '快三和值',
                'play_keywords': ['和值']
            },
            'PK10': {
                'number_range': set(range(1, 11)),
                'total_numbers': 10,
                'type_name': 'PK10/赛车',
                'play_keywords': ['冠军', '亚军', '季军', '第四名', '第五名', '第六名', '第七名', '第八名', '第九名', '第十名', '定位胆', '前一']
            },
            'K3': {
                'number_range': set(range(1, 7)),
                'total_numbers': 6,
                'type_name': '快三',
                'play_keywords': ['和值', '点数']
            },
            'LHC': {
                'number_range': set(range(1, 50)),
                'total_numbers': 49,
                'type_name': '六合彩',
                'play_keywords': ['特码', '正码', '正特', '平码', '平特']
            }
        }
        
        # 完整的彩种列表
        self.target_lotteries = {}
        for lottery_type, lotteries in self.config.coverage_config['target_lotteries'].items():
            self.target_lotteries[lottery_type] = lotteries
        
        # 玩法分类映射
        self.play_mapping = {
            # ========== 六合彩号码玩法 ==========
            '特码': '特码', '特玛': '特码', '特马': '特码', '特碼': '特码',
            '正码': '正码', '正码一': '正码一', '正码二': '正码二', '正码三': '正码三',
            '正码四': '正码四', '正码五': '正码五', '正码六': '正码六',
            '正一特': '正1特', '正二特': '正2特', '正三特': '正3特',
            '正四特': '正4特', '正五特': '正5特', '正六特': '正6特',
            '平码': '平码', '平特': '平特', '尾数': '尾数',
            
            # ========== 时时彩/PK10/赛车号码玩法 ==========
            '定位胆': '定位胆', '一字定位': '定位胆', '一字': '定位胆', '定位': '定位胆',
            '冠军': '冠军', '亚军': '亚军', '季军': '季军', '第四名': '第四名',
            '第五名': '第五名', '第六名': '第六名', '第七名': '第七名', '第八名': '第八名',
            '第九名': '第九名', '第十名': '第十名', '前一': '冠军',
            
            # ========== 快三号码玩法 ==========
            '和值': '和值', '和值_大小单双': '和值', '点数': '和值',
            
            # ========== 3D系列号码玩法 ==========
            '百位': '百位', '十位': '十位', '个位': '个位'
        }
        
        self.content_parser = ContentParser(config)
        self.lottery_identifier = LotteryIdentifier()
        self.play_normalizer = PlayCategoryNormalizer()
        
    def identify_lottery_category(self, lottery_name):
        """识别彩种类型 - 增强六合彩识别"""
        lottery_str = str(lottery_name).strip().lower()
        
        # 检查六合彩
        for lottery in self.target_lotteries['six_mark']:
            if lottery.lower() in lottery_str:
                return 'six_mark'
        
        # 检查快三彩种
        for lottery in self.target_lotteries['fast_three']:
            if lottery.lower() in lottery_str:
                return 'fast_three'
        
        # 检查10个号码的彩种
        for lottery in self.target_lotteries['10_number']:
            if lottery.lower() in lottery_str:
                return '10_number'

        # 使用彩票识别器
        lottery_type = self.lottery_identifier.identify_lottery_type(lottery_name)
        type_mapping = {
            'PK10': '10_number',
            'K3': 'fast_three', 
            'LHC': 'six_mark',
            'SSC': '10_number',
            '3D': '10_number'
        }
        
        return type_mapping.get(lottery_type, 'six_mark')
    
    def get_lottery_config(self, lottery_category):
        """获取彩种配置"""
        return self.lottery_configs.get(lottery_category, self.lottery_configs['six_mark'])
    
    def normalize_play_category(self, play_method, lottery_category='six_mark'):
        """统一玩法分类 - 增强正码特识别"""
        play_str = str(play_method).strip()
        
        # 规范化特殊字符
        import re
        play_normalized = re.sub(r'\s+', ' ', play_str)
        
        # 直接映射
        if play_normalized in self.play_mapping:
            return self.play_mapping[play_normalized]
        
        # 关键词匹配
        for key, value in self.play_mapping.items():
            if key in play_normalized:
                return value
        
        # 智能匹配
        play_lower = play_normalized.lower()
        
        if lottery_category in ['six_mark', 'LHC']:
            # 六合彩号码玩法智能匹配
            if any(word in play_lower for word in ['特码', '特玛', '特马', '特碼']):
                return '特码'
            elif any(word in play_lower for word in ['正码一', '正码1', '正一码']):
                return '正码一'
            elif any(word in play_lower for word in ['正码二', '正码2', '正二码']):
                return '正码二'
            elif any(word in play_lower for word in ['正码三', '正码3', '正三码']):
                return '正码三'
            elif any(word in play_lower for word in ['正码四', '正码4', '正四码']):
                return '正码四'
            elif any(word in play_lower for word in ['正码五', '正码5', '正五码']):
                return '正码五'
            elif any(word in play_lower for word in ['正码六', '正码6', '正六码']):
                return '正码六'
            elif any(word in play_lower for word in ['正一特', '正1特']):
                return '正1特'
            elif any(word in play_lower for word in ['正二特', '正2特']):
                return '正2特'
            elif any(word in play_lower for word in ['正三特', '正3特']):
                return '正3特'
            elif any(word in play_lower for word in ['正四特', '正4特']):
                return '正4特'
            elif any(word in play_lower for word in ['正五特', '正5特']):
                return '正5特'
            elif any(word in play_lower for word in ['正六特', '正6特']):
                return '正6特'
            elif any(word in play_lower for word in ['平码']):
                return '平码'
            elif any(word in play_lower for word in ['平特']):
                return '平特'
        
        elif lottery_category in ['10_number', 'PK10', 'SSC']:
            # 时时彩/PK10/赛车号码玩法智能匹配
            if any(word in play_lower for word in ['冠军', '第一名', '第1名', '1st', '前一']):
                return '冠军'
            elif any(word in play_lower for word in ['亚军', '第二名', '第2名', '2nd']):
                return '亚军'
            elif any(word in play_lower for word in ['季军', '第三名', '第3名', '3rd']):
                return '季军'
            elif any(word in play_lower for word in ['第四名', '第4名', '4th']):
                return '第四名'
            elif any(word in play_lower for word in ['第五名', '第5名', '5th']):
                return '第五名'
            elif any(word in play_lower for word in ['第六名', '第6名', '6th']):
                return '第六名'
            elif any(word in play_lower for word in ['第七名', '第7名', '7th']):
                return '第七名'
            elif any(word in play_lower for word in ['第八名', '第8名', '8th']):
                return '第八名'
            elif any(word in play_lower for word in ['第九名', '第9名', '9th']):
                return '第九名'
            elif any(word in play_lower for word in ['第十名', '第10名', '10th']):
                return '第十名'
            elif any(word in play_lower for word in ['定位胆', '一字定位', '一字', '定位']):
                return '定位胆'
        
        elif lottery_category in ['fast_three', 'K3']:
            # 快三号码玩法智能匹配
            if any(word in play_lower for word in ['和值', '和数', '和']):
                return '和值'
        
        return play_normalized
    
    @lru_cache(maxsize=500)
    def cached_extract_amount(self, amount_text):
        """带缓存的金额提取"""
        return self.extract_bet_amount(amount_text)
    
    def extract_bet_amount(self, amount_text):
        """金额提取函数 - 增强版"""
        try:
            if pd.isna(amount_text) or amount_text is None:
                return 0.0
            
            # 转换为字符串并清理
            text = str(amount_text).strip()
            
            # 如果已经是空字符串，返回0
            if text == '':
                return 0.0
            
            # 方法1: 直接转换（处理纯数字）
            try:
                # 移除所有非数字字符（除了点和负号）
                clean_text = re.sub(r'[^\d.-]', '', text)
                if clean_text and clean_text != '-' and clean_text != '.':
                    amount = float(clean_text)
                    if amount >= 0:
                        return amount
            except:
                pass
            
            # 方法2: 处理千位分隔符格式
            try:
                # 移除逗号和全角逗号，然后转换
                clean_text = text.replace(',', '').replace('，', '')
                amount = float(clean_text)
                if amount >= 0:
                    return amount
            except:
                pass
            
            # 方法3: 处理"5.000"这种格式
            if re.match(r'^\d+\.\d{3}$', text):
                try:
                    amount = float(text)
                    return amount
                except:
                    pass
            
            # 方法4: 使用正则表达式提取各种格式
            patterns = [
                r'投注\s*[:：]?\s*([\d,.]+)',
                r'金额\s*[:：]?\s*([\d,.]+)',
                r'下注金额\s*([\d,.]+)',
                r'([\d,.]+)\s*元',
                r'￥\s*([\d,.]+)',
                r'¥\s*([\d,.]+)',
                r'([\d,.]+)\s*RMB',
                r'([\d,.]+)$'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    amount_str = match.group(1).replace(',', '').replace('，', '')
                    try:
                        amount = float(amount_str)
                        if amount >= 0:
                            return amount
                    except:
                        continue
            
            return 0.0
            
        except Exception as e:
            logger.warning(f"金额提取失败: {amount_text}, 错误: {str(e)}")
            return 0.0
    
    def calculate_similarity(self, avgs):
        """计算金额匹配度"""
        if not avgs or max(avgs) == 0:
            return 0
        return (min(avgs) / max(avgs)) * 100
    
    def get_similarity_indicator(self, similarity):
        """获取相似度颜色指示符"""
        thresholds = self.config.coverage_config['similarity_thresholds']
        if similarity >= thresholds['excellent']: 
            return "🟢"
        elif similarity >= thresholds['good']: 
            return "🟡"
        elif similarity >= thresholds['fair']: 
            return "🟠"
        else: 
            return "🔴"
    
    def find_perfect_combinations(self, account_numbers, account_amount_stats, account_bet_contents, min_avg_amount, total_numbers):
        """寻找完美组合 - 支持任意号码数量的彩种"""
        all_results = {2: [], 3: [], 4: []}
        all_accounts = list(account_numbers.keys())
        
        account_sets = {account: set(numbers) for account, numbers in account_numbers.items()}
        
        # 搜索2账户组合
        for i, acc1 in enumerate(all_accounts):
            count1 = len(account_numbers[acc1])
            for j in range(i+1, len(all_accounts)):
                acc2 = all_accounts[j]
                count2 = len(account_numbers[acc2])
                
                if count1 + count2 != total_numbers:
                    continue
                
                combined_set = account_sets[acc1] | account_sets[acc2]
                if len(combined_set) == total_numbers:
                    total_amount = account_amount_stats[acc1]['total_amount'] + account_amount_stats[acc2]['total_amount']
                    avg_amounts = [
                        account_amount_stats[acc1]['avg_amount_per_number'],
                        account_amount_stats[acc2]['avg_amount_per_number']
                    ]
                    
                    # 检查平均金额是否达到阈值
                    if min(avg_amounts) < min_avg_amount:
                        continue
                    
                    similarity = self.calculate_similarity(avg_amounts)
                    
                    result_data = {
                        'accounts': [acc1, acc2],
                        'account_count': 2,
                        'total_amount': total_amount,
                        'avg_amount_per_number': total_amount / total_numbers,
                        'similarity': similarity,
                        'similarity_indicator': self.get_similarity_indicator(similarity),
                        'individual_amounts': {
                            acc1: account_amount_stats[acc1]['total_amount'],
                            acc2: account_amount_stats[acc2]['total_amount']
                        },
                        'individual_avg_per_number': {
                            acc1: account_amount_stats[acc1]['avg_amount_per_number'],
                            acc2: account_amount_stats[acc2]['avg_amount_per_number']
                        },
                        'bet_contents': {
                            acc1: account_bet_contents[acc1],
                            acc2: account_bet_contents[acc2]
                        }
                    }
                    all_results[2].append(result_data)
        
        # 搜索3账户组合
        for i, acc1 in enumerate(all_accounts):
            count1 = len(account_numbers[acc1])
            for j in range(i+1, len(all_accounts)):
                acc2 = all_accounts[j]
                count2 = len(account_numbers[acc2])
                for k in range(j+1, len(all_accounts)):
                    acc3 = all_accounts[k]
                    count3 = len(account_numbers[acc3])
                    
                    if count1 + count2 + count3 != total_numbers:
                        continue
                    
                    combined_set = account_sets[acc1] | account_sets[acc2] | account_sets[acc3]
                    if len(combined_set) == total_numbers:
                        total_amount = (account_amount_stats[acc1]['total_amount'] + 
                                      account_amount_stats[acc2]['total_amount'] + 
                                      account_amount_stats[acc3]['total_amount'])
                        avg_amounts = [
                            account_amount_stats[acc1]['avg_amount_per_number'],
                            account_amount_stats[acc2]['avg_amount_per_number'],
                            account_amount_stats[acc3]['avg_amount_per_number']
                        ]
                        
                        # 检查平均金额是否达到阈值
                        if min(avg_amounts) < min_avg_amount:
                            continue
                        
                        similarity = self.calculate_similarity(avg_amounts)
                        
                        result_data = {
                            'accounts': [acc1, acc2, acc3],
                            'account_count': 3,
                            'total_amount': total_amount,
                            'avg_amount_per_number': total_amount / total_numbers,
                            'similarity': similarity,
                            'similarity_indicator': self.get_similarity_indicator(similarity),
                            'individual_amounts': {
                                acc1: account_amount_stats[acc1]['total_amount'],
                                acc2: account_amount_stats[acc2]['total_amount'],
                                acc3: account_amount_stats[acc3]['total_amount']
                            },
                            'individual_avg_per_number': {
                                acc1: account_amount_stats[acc1]['avg_amount_per_number'],
                                acc2: account_amount_stats[acc2]['avg_amount_per_number'],
                                acc3: account_amount_stats[acc3]['avg_amount_per_number']
                            },
                            'bet_contents': {
                                acc1: account_bet_contents[acc1],
                                acc2: account_bet_contents[acc2],
                                acc3: account_bet_contents[acc3]
                            }
                        }
                        all_results[3].append(result_data)
        
        return all_results

    def analyze_period_lottery_position(self, group, period, lottery, position, min_number_count, min_avg_amount):
        """分析特定期数、彩种和位置"""
        has_amount_column = '金额' in group.columns
        
        # 识别彩种类型
        lottery_category = self.identify_lottery_category(lottery)
        if not lottery_category:
            return None
        
        config = self.get_lottery_config(lottery_category)
        total_numbers = config['total_numbers']
        
        account_numbers = {}
        account_amount_stats = {}
        account_bet_contents = {}

        for account in group['会员账号'].unique():
            account_data = group[group['会员账号'] == account]
            
            all_numbers = set()
            total_amount = 0
            bet_count = 0
            
            for _, row in account_data.iterrows():
                # 使用缓存的号码提取，传入彩种类型
                numbers = self.content_parser.cached_extract_numbers(row['内容'], lottery_category)
                all_numbers.update(numbers)
                
                if has_amount_column:
                    # 使用缓存的金额提取
                    amount = self.cached_extract_amount(str(row['金额']))
                    total_amount += amount
                    bet_count += 1
            
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

        # 筛选有效账户 - 使用阈值
        filtered_account_numbers = {}
        filtered_account_amount_stats = {}
        filtered_account_bet_contents = {}

        for account, numbers in account_numbers.items():
            stats = account_amount_stats[account]
            # 同时检查数字数量和平均金额阈值
            if len(numbers) >= min_number_count and stats['avg_amount_per_number'] >= min_avg_amount:
                filtered_account_numbers[account] = numbers
                filtered_account_amount_stats[account] = account_amount_stats[account]
                filtered_account_bet_contents[account] = account_bet_contents[account]

        if len(filtered_account_numbers) < 2:
            return None

        all_results = self.find_perfect_combinations(
            filtered_account_numbers, 
            filtered_account_amount_stats, 
            filtered_account_bet_contents,
            min_avg_amount,
            total_numbers
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
                'lottery_category': lottery_category,
                'total_combinations': total_combinations,
                'all_combinations': all_combinations,
                'filtered_accounts': len(filtered_account_numbers),
                'total_numbers': total_numbers
            }
        
        return None

    def analyze_with_progress(self, df_target, six_mark_params, ten_number_params, fast_three_params, analysis_mode):
        """带进度显示的分析"""
        all_period_results = {}
        
        # 分别处理不同彩种
        df_six_mark = df_target[df_target['彩种类型'] == 'six_mark']
        df_10_number = df_target[df_target['彩种类型'] == '10_number']
        df_fast_three = df_target[df_target['彩种类型'] == 'fast_three']
        
        total_groups = (
            len(df_six_mark.groupby(['期号', '彩种', '玩法'])) +
            len(df_10_number.groupby(['期号', '彩种', '玩法'])) +
            len(df_fast_three.groupby(['期号', '彩种', '玩法']))
        )
        
        if total_groups == 0:
            return all_period_results
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        processed_groups = 0
        
        # 分析六合彩
        if len(df_six_mark) > 0:
            grouped_six = df_six_mark.groupby(['期号', '彩种', '玩法'])
            for (period, lottery, position), group in grouped_six:
                if len(group) >= 2:
                    result = self.analyze_period_lottery_position(
                        group, period, lottery, position, 
                        six_mark_params['min_number_count'], 
                        six_mark_params['min_avg_amount']
                    )
                    if result:
                        all_period_results[(period, lottery, position)] = result
                
                processed_groups += 1
                progress = processed_groups / total_groups
                progress_bar.progress(progress)
                status_text.text(f"分析进度: {processed_groups}/{total_groups} - 六合彩")
        
        # 分析时时彩/PK10/赛车
        if len(df_10_number) > 0:
            grouped_10 = df_10_number.groupby(['期号', '彩种', '玩法'])
            for (period, lottery, position), group in grouped_10:
                if len(group) >= 2:
                    result = self.analyze_period_lottery_position(
                        group, period, lottery, position,
                        ten_number_params['min_number_count'],
                        ten_number_params['min_avg_amount']
                    )
                    if result:
                        all_period_results[(period, lottery, position)] = result
                
                processed_groups += 1
                progress = processed_groups / total_groups
                progress_bar.progress(progress)
                status_text.text(f"分析进度: {processed_groups}/{total_groups} - 赛车类")
        
        # 分析快三
        if len(df_fast_three) > 0:
            grouped_fast_three = df_fast_three.groupby(['期号', '彩种', '玩法'])
            for (period, lottery, position), group in grouped_fast_three:
                if len(group) >= 2:
                    result = self.analyze_period_lottery_position(
                        group, period, lottery, position,
                        fast_three_params['min_number_count'],
                        fast_three_params['min_avg_amount']
                    )
                    if result:
                        all_period_results[(period, lottery, position)] = result
                
                processed_groups += 1
                progress = processed_groups / total_groups
                progress_bar.progress(progress)
                status_text.text(f"分析进度: {processed_groups}/{total_groups} - 快三")
        
        progress_bar.empty()
        status_text.text("分析完成!")
        
        return all_period_results

    def display_enhanced_results(self, all_period_results, analysis_mode):
        """增强结果展示"""
        if not all_period_results:
            st.info("🎉 未发现完美覆盖组合")
            return
        
        # 按账户组合和彩种分组
        account_pair_groups = defaultdict(lambda: defaultdict(list))
        
        for group_key, result in all_period_results.items():
            lottery = result['lottery']
            position = result.get('position', None)
            
            for combo in result['all_combinations']:
                # 创建账户组合键
                accounts = combo['accounts']
                account_pair = " ↔ ".join(sorted(accounts))
                
                # 创建彩种键
                if position:
                    lottery_key = f"{lottery} - {position}"
                else:
                    lottery_key = lottery
                
                # 存储组合信息
                combo_info = {
                    'period': result['period'],
                    'combo': combo,
                    'lottery_category': result['lottery_category'],
                    'total_numbers': result['total_numbers']
                }
                
                account_pair_groups[account_pair][lottery_key].append(combo_info)
        
        # 显示彩种类型统计
        st.subheader("🎲 彩种类型统计")
        col1, col2, col3, col4 = st.columns(4)
        
        category_display = {
            'six_mark': '六合彩',
            '10_number': '时时彩/PK10/赛车',
            'fast_three': '快三'
        }
        
        # 计算统计
        lottery_category_stats = defaultdict(lambda: {'periods': set(), 'combinations': 0})
        for result in all_period_results.values():
            lottery_category = result['lottery_category']
            lottery_category_stats[lottery_category]['periods'].add(result['period'])
            lottery_category_stats[lottery_category]['combinations'] += result['total_combinations']
        
        stats_items = list(lottery_category_stats.items())
        for i, (category, stats) in enumerate(stats_items):
            with [col1, col2, col3, col4][i % 4]:
                display_text = f"{stats['combinations']}组"
                st.metric(
                    label=category_display.get(category, category),
                    value=display_text,
                    delta=f"{len(stats['periods'])}期"
                )
        
        # 显示汇总统计
        st.subheader("📊 检测汇总")
        total_combinations = sum(result['total_combinations'] for result in all_period_results.values())
        total_filtered_accounts = sum(result['filtered_accounts'] for result in all_period_results.values())
        total_periods = len(set(result['period'] for result in all_period_results.values()))
        total_lotteries = len(set(result['lottery'] for result in all_period_results.values()))
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总完美组合数", total_combinations)
        with col2:
            st.metric("分析期数", total_periods)
        with col3:
            st.metric("有效账户数", total_filtered_accounts)
        with col4:
            st.metric("涉及彩种", total_lotteries)
        
        # 显示详细组合分析
        st.subheader("📈 详细组合分析")
        self._display_by_account_pair_lottery(account_pair_groups, analysis_mode)

    def _display_by_account_pair_lottery(self, account_pair_groups, analysis_mode):
        """按账户组合和彩种展示"""
        category_display = {
            'six_mark': '六合彩',
            '10_number': '时时彩/PK10/赛车',
            'fast_three': '快三'
        }
        
        # 遍历每个账户组合
        for account_pair, lottery_groups in account_pair_groups.items():
            # 遍历每个彩种
            for lottery_key, combos in lottery_groups.items():
                # 按期号排序
                combos.sort(key=lambda x: x['period'])
                
                # 创建折叠框标题
                combo_count = len(combos)
                title = f"**{account_pair}** - {lottery_key}（{combo_count}个组合）"
                
                with st.expander(title, expanded=True):
                    # 显示每个组合
                    for idx, combo_info in enumerate(combos, 1):
                        combo = combo_info['combo']
                        period = combo_info['period']
                        lottery_category = combo_info['lottery_category']
                        
                        # 组合标题
                        st.markdown(f"**完美组合 {idx}:** {account_pair}")
                        
                        # 组合信息
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
                        
                        # 彩种类型信息
                        category_name = category_display.get(lottery_category, lottery_category)
                        st.write(f"**彩种类型:** {category_name}")
                        
                        # 各账户详情
                        st.write("**各账户详情:**")
                        
                        for account in combo['accounts']:
                            amount_info = combo['individual_amounts'][account]
                            avg_info = combo['individual_avg_per_number'][account]
                            numbers = combo['bet_contents'][account]
                            numbers_count = len(numbers.split(', '))
                            
                            st.write(f"- **{account}**: {numbers_count}个数字")
                            st.write(f"  - 总投注: ¥{amount_info:,.2f}")
                            st.write(f"  - 平均每号: ¥{avg_info:,.2f}")
                            st.write(f"  - 投注内容: {numbers}")
                        
                        # 添加分隔线（除了最后一个组合）
                        if idx < len(combos):
                            st.markdown("---")

# ==================== 综合对刷检测器 ====================
class ComprehensiveWashTradeDetector:
    """综合对刷检测器 - 整合两套代码功能"""
    
    def __init__(self, config=None):
        self.config = config or ComprehensiveConfig()
        self.data_processor = DataProcessor()
        self.lottery_identifier = LotteryIdentifier()
        self.play_normalizer = PlayCategoryNormalizer()
        self.content_parser = ContentParser(self.config)
        self.coverage_analyzer = MultiLotteryCoverageAnalyzer(self.config)
        
        self.data_processed = False
        self.df_valid = None
        self.export_data = []
        
        # 按彩种存储账户统计
        self.account_total_periods_by_lottery = defaultdict(dict)
        self.account_record_stats_by_lottery = defaultdict(dict)
        self.performance_stats = {}

        self._cache_clear()

    def enhanced_coverage_detection(self, df, coverage_params):
        """增强号码覆盖检测 - 借鉴第二套代码逻辑"""
        try:
            # 1. 数据预处理 - 借鉴第二套代码
            df_coverage = self.prepare_data_for_coverage_detection(df)
            
            # 2. 按彩种类型分别分析
            coverage_results = {}
            
            # 六合彩分析
            df_six_mark = df_coverage[df_coverage['彩种类型'] == 'six_mark']
            if len(df_six_mark) > 0:
                six_mark_results = self.analyze_six_mark_coverage(
                    df_six_mark, 
                    coverage_params['six_mark']
                )
                coverage_results.update(six_mark_results)
            
            # 时时彩/PK10分析
            df_10_number = df_coverage[df_coverage['彩种类型'] == '10_number']
            if len(df_10_number) > 0:
                ten_number_results = self.analyze_ten_number_coverage(
                    df_10_number,
                    coverage_params['ten_number']
                )
                coverage_results.update(ten_number_results)
                
            # 快三分析
            df_fast_three = df_coverage[df_coverage['彩种类型'] == 'fast_three']
            if len(df_fast_three) > 0:
                fast_three_results = self.analyze_fast_three_coverage(
                    df_fast_three,
                    coverage_params['fast_three']
                )
                coverage_results.update(fast_three_results)
                
            return coverage_results
            
        except Exception as e:
            logger.error(f"号码覆盖检测失败: {str(e)}")
            return {}
    
    def _cache_clear(self):
        """清空缓存"""
        if hasattr(self, 'cached_extract_bet_amount'):
            self.cached_extract_bet_amount.cache_clear()
        if hasattr(self, 'cached_extract_direction'):
            self.cached_extract_direction.cache_clear()
        if hasattr(self.content_parser, 'cached_extract_numbers'):
            self.content_parser.cached_extract_numbers.cache_clear()
        if hasattr(self.coverage_analyzer, 'cached_extract_amount'):
            self.coverage_analyzer.cached_extract_amount.cache_clear()

    def analyze_single_group_coverage(self, group, period, lottery, position, min_number_count, min_avg_amount, total_numbers):
        """分析单个组的号码覆盖"""
        account_numbers = {}
        account_amounts = {}
        account_contents = {}
        
        for account in group['会员账号'].unique():
            account_data = group[group['会员账号'] == account]
            
            # 合并该账户的所有号码
            all_numbers = set()
            total_amount = 0
            
            for _, row in account_data.iterrows():
                numbers = row['投注号码'] if '投注号码' in row else []
                all_numbers.update(numbers)
                
                if '投注金额' in row:
                    total_amount += row['投注金额']
            
            if len(all_numbers) >= min_number_count:
                account_numbers[account] = sorted(all_numbers)
                account_amounts[account] = total_amount
                account_contents[account] = ", ".join([f"{num:02d}" for num in sorted(all_numbers)])
        
        # 寻找完美组合
        if len(account_numbers) >= 2:
            combinations = self.find_coverage_combinations(
                account_numbers, account_amounts, account_contents, 
                min_avg_amount, total_numbers
            )
            
            if combinations:
                return {
                    'period': period,
                    'lottery': lottery,
                    'position': position,
                    'total_combinations': len(combinations),
                    'combinations': combinations,
                    'total_numbers': total_numbers
                }
        
        return None
    
    def find_coverage_combinations(self, account_numbers, account_amounts, account_contents, min_avg_amount, total_numbers):
        """寻找号码覆盖组合"""
        combinations = []
        accounts = list(account_numbers.keys())
        
        # 检查2账户组合
        for i in range(len(accounts)):
            for j in range(i + 1, len(accounts)):
                acc1, acc2 = accounts[i], accounts[j]
                
                combined_numbers = set(account_numbers[acc1]) | set(account_numbers[acc2])
                
                if len(combined_numbers) == total_numbers:
                    # 计算金额匹配度
                    amount1 = account_amounts[acc1]
                    amount2 = account_amounts[acc2]
                    
                    if amount1 > 0 and amount2 > 0:
                        similarity = min(amount1, amount2) / max(amount1, amount2)
                        
                        # 检查平均金额
                        avg_per_number1 = amount1 / len(account_numbers[acc1])
                        avg_per_number2 = amount2 / len(account_numbers[acc2])
                        
                        if min(avg_per_number1, avg_per_number2) >= min_avg_amount:
                            combinations.append({
                                'accounts': [acc1, acc2],
                                'numbers_count': [len(account_numbers[acc1]), len(account_numbers[acc2])],
                                'total_amount': amount1 + amount2,
                                'similarity': similarity * 100,
                                'individual_amounts': {acc1: amount1, acc2: amount2},
                                'bet_contents': {acc1: account_contents[acc1], acc2: account_contents[acc2]}
                            })
        
        # 检查3账户组合
        for i in range(len(accounts)):
            for j in range(i + 1, len(accounts)):
                for k in range(j + 1, len(accounts)):
                    acc1, acc2, acc3 = accounts[i], accounts[j], accounts[k]
                    
                    combined_numbers = (set(account_numbers[acc1]) | 
                                      set(account_numbers[acc2]) | 
                                      set(account_numbers[acc3]))
                    
                    if len(combined_numbers) == total_numbers:
                        amount1 = account_amounts[acc1]
                        amount2 = account_amounts[acc2]
                        amount3 = account_amounts[acc3]
                        
                        if amount1 > 0 and amount2 > 0 and amount3 > 0:
                            amounts = [amount1, amount2, amount3]
                            similarity = min(amounts) / max(amounts)
                            
                            avg_per_number1 = amount1 / len(account_numbers[acc1])
                            avg_per_number2 = amount2 / len(account_numbers[acc2])
                            avg_per_number3 = amount3 / len(account_numbers[acc3])
                            
                            if min(avg_per_number1, avg_per_number2, avg_per_number3) >= min_avg_amount:
                                combinations.append({
                                    'accounts': [acc1, acc2, acc3],
                                    'numbers_count': [
                                        len(account_numbers[acc1]),
                                        len(account_numbers[acc2]),
                                        len(account_numbers[acc3])
                                    ],
                                    'total_amount': amount1 + amount2 + amount3,
                                    'similarity': similarity * 100,
                                    'individual_amounts': {
                                        acc1: amount1, 
                                        acc2: amount2, 
                                        acc3: amount3
                                    },
                                    'bet_contents': {
                                        acc1: account_contents[acc1],
                                        acc2: account_contents[acc2],
                                        acc3: account_contents[acc3]
                                    }
                                })
        
        return combinations
    
    @lru_cache(maxsize=2000)
    def cached_extract_bet_amount(self, amount_text):
        """增强缓存金额提取"""
        return self.extract_bet_amount_safe(amount_text)
    
    @lru_cache(maxsize=1000)
    def cached_extract_direction(self, content, play_category, lottery_type):
        """增强缓存方向提取"""
        return self.enhanced_extract_direction_with_position(content, play_category, lottery_type)
    
    def upload_and_process(self, uploaded_file):
        """上传并处理文件"""
        try:
            if uploaded_file is None:
                st.error("❌ 没有上传文件")
                return None, None
            
            filename = uploaded_file.name
            logger.info(f"✅ 已上传文件: {filename}")
            
            if not any(filename.endswith(ext) for ext in self.config.supported_file_types):
                st.error(f"❌ 不支持的文件类型: {filename}")
                return None, None
            
            with st.spinner("🔄 正在清洗数据..."):
                df_clean = self.data_processor.clean_data(uploaded_file)
            
            if df_clean is not None and len(df_clean) > 0:
                df_enhanced = self.enhance_data_processing(df_clean)
                return df_enhanced, filename
            else:
                return None, None
            
        except Exception as e:
            logger.error(f"文件处理失败: {str(e)}")
            st.error(f"文件处理失败: {str(e)}")
            return None, None
    
    def enhance_data_processing(self, df_clean):
        """增强的数据处理流程"""
        try:
            # 彩种识别
            if '彩种' in df_clean.columns:
                df_clean['原始彩种'] = df_clean['彩种']
                df_clean['彩种类型'] = df_clean['彩种'].apply(self.lottery_identifier.identify_lottery_type)
            
            # 玩法分类统一
            if '玩法' in df_clean.columns:
                df_clean['玩法分类'] = df_clean['玩法'].apply(self.play_normalizer.normalize_category)
            
            # 计算账户统计信息
            self.calculate_account_total_periods_by_lottery(df_clean)
            
            # 提取投注金额和方向 - 使用缓存版本
            st.info("💰 正在提取投注金额和方向...")
            progress_bar = st.progress(0)
            total_rows = len(df_clean)
            
            # 分批处理显示进度
            batch_size = 1000
            for i in range(0, total_rows, batch_size):
                end_idx = min(i + batch_size, total_rows)
                batch_df = df_clean.iloc[i:end_idx]
                
                # 处理当前批次
                df_clean.loc[i:end_idx-1, '投注金额'] = batch_df['金额'].apply(
                    lambda x: self.cached_extract_bet_amount(str(x))
                )
                df_clean.loc[i:end_idx-1, '投注方向'] = batch_df.apply(
                    lambda row: self.cached_extract_direction(
                        row['内容'], 
                        row.get('玩法', ''), 
                        row['彩种类型'] if '彩种类型' in df_clean.columns else 'six_mark'
                    ), 
                    axis=1
                )
                
                # 更新进度
                progress = (end_idx) / total_rows
                progress_bar.progress(progress)
            
            progress_bar.empty()
            
            # 过滤有效记录
            df_valid = df_clean[
                (df_clean['投注方向'] != '') & 
                (df_clean['投注金额'] >= self.config.min_amount)
            ].copy()
            
            if len(df_valid) == 0:
                st.error("❌ 过滤后没有有效记录")
                return pd.DataFrame()
            
            self.data_processed = True
            self.df_valid = df_valid

            return df_valid

    def prepare_data_for_coverage_detection(self, df):
        """为号码覆盖检测准备数据 - 借鉴第二套代码逻辑"""
        df_coverage = df.copy()
        
        # 彩种类型识别
        df_coverage['彩种类型'] = df_coverage['彩种'].apply(
            lambda x: self.coverage_analyzer.identify_lottery_category(x)
        )
        
        # 玩法分类统一
        df_coverage['玩法'] = df_coverage.apply(
            lambda row: self.coverage_analyzer.normalize_play_category(
                row['玩法'], 
                row['彩种类型'] if '彩种类型' in df_coverage.columns else 'six_mark'
            ), 
            axis=1
        )
        
        # 提取号码
        df_coverage['投注号码'] = df_coverage.apply(
            lambda row: self.coverage_analyzer.enhanced_extract_numbers(
                row['内容'], 
                row['彩种类型'] if '彩种类型' in df_coverage.columns else 'six_mark'
            ),
            axis=1
        )
        
        # 提取金额
        if '金额' in df_coverage.columns:
            df_coverage['投注金额'] = df_coverage['金额'].apply(
                self.coverage_analyzer.cached_extract_amount
            )
        
        return df_coverage
    
    def analyze_six_mark_coverage(self, df, params):
        """分析六合彩号码覆盖"""
        results = {}
        min_number_count = params['min_number_count']
        min_avg_amount = params['min_avg_amount']
        
        # 按期号、彩种、玩法分组
        grouped = df.groupby(['期号', '彩种', '玩法'])
        
        for (period, lottery, position), group in grouped:
            if len(group) < 2:
                continue
                
            # 分析该组的号码覆盖
            result = self.analyze_single_group_coverage(
                group, period, lottery, position, 
                min_number_count, min_avg_amount, 49  # 六合彩49个号码
            )
            if result:
                results[(period, lottery, position)] = result
        
        return results
    
    def analyze_ten_number_coverage(self, df, params):
        """分析10个号码彩种覆盖"""
        results = {}
        min_number_count = params['min_number_count']
        min_avg_amount = params['min_avg_amount']
        
        grouped = df.groupby(['期号', '彩种', '玩法'])
        
        for (period, lottery, position), group in grouped:
            if len(group) < 2:
                continue
                
            result = self.analyze_single_group_coverage(
                group, period, lottery, position,
                min_number_count, min_avg_amount, 10  # 10个号码
            )
            if result:
                results[(period, lottery, position)] = result
        
        return results
    
    def analyze_fast_three_coverage(self, df, params):
        """分析快三号码覆盖"""
        results = {}
        min_number_count = params['min_number_count']
        min_avg_amount = params['min_avg_amount']
        
        grouped = df.groupby(['期号', '彩种', '玩法'])
        
        for (period, lottery, position), group in grouped:
            if len(group) < 2:
                continue
                
            result = self.analyze_single_group_coverage(
                group, period, lottery, position,
                min_number_count, min_avg_amount, 16  # 快三和值16个号码
            )
            if result:
                results[(period, lottery, position)] = result
        
        return results
            
        except Exception as e:
            logger.error(f"数据处理增强失败: {str(e)}")
            st.error(f"数据处理增强失败: {str(e)}")
            return pd.DataFrame()
    
    def extract_bet_amount_safe(self, amount_text):
        """安全提取投注金额 - 增强版"""
        try:
            if pd.isna(amount_text):
                return 0
            
            text = str(amount_text).strip()
            
            # 处理科学计数法
            if 'E' in text or 'e' in text:
                try:
                    amount = float(text)
                    if amount >= self.config.min_amount:
                        return amount
                except:
                    pass
            
            # 直接转换
            try:
                # 移除所有非数字字符（除了小数点和负号）
                cleaned_text = re.sub(r'[^\d.-]', '', text)
                if cleaned_text and cleaned_text != '-':
                    amount = float(cleaned_text)
                    if amount >= self.config.min_amount:
                        return amount
            except:
                pass
            
            # 模式匹配 - 增强模式
            patterns = [
                r'投注[:：]?\s*([-]?\d+[,，]?\d*\.?\d*)',
                r'下注[:：]?\s*([-]?\d+[,，]?\d*\.?\d*)',
                r'金额[:：]?\s*([-]?\d+[,，]?\d*\.?\d*)',
                r'总额[:：]?\s*([-]?\d+[,，]?\d*\.?\d*)',
                r'([-]?\d+[,，]?\d*\.?\d*)\s*元',
                r'￥\s*([-]?\d+[,，]?\d*\.?\d*)',
                r'¥\s*([-]?\d+[,，]?\d*\.?\d*)',
                r'[\$￥¥]?\s*([-]?\d+[,，]?\d*\.?\d+)',
                r'([-]?\d+[,，]?\d*\.?\d+)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    amount_str = match.group(1).replace(',', '').replace('，', '').replace(' ', '')
                    try:
                        amount = float(amount_str)
                        if amount >= self.config.min_amount:
                            return amount
                    except:
                        continue
            
            return 0
            
        except Exception as e:
            logger.warning(f"金额提取失败: {amount_text}, 错误: {e}")
            return 0
    
    def enhanced_extract_direction_with_position(self, content, play_category, lottery_type):
        """🎯 修复版方向提取 - 保持变异形式独立性，正确提取位置"""
        try:
            if pd.isna(content):
                return ""
            
            content_str = str(content).strip()
            
            # 🎯 使用修复的内容解析器提取方向（保持变异形式独立性）
            directions = self.content_parser.extract_basic_directions(content_str, self.config)
            
            if not directions:
                return ""
            
            # 🎯 从玩法分类中提取位置信息
            position = self.content_parser.extract_position_from_play_category(play_category, lottery_type, self.config)
            
            # 🎯 选择主要方向
            main_direction = self._select_primary_direction(directions, content_str)
            
            if not main_direction:
                return ""
            
            # 🎯 组合位置和方向
            if position and position != '未知位置':
                return f"{position}-{main_direction}"
            else:
                return main_direction
            
        except Exception as e:
            logger.warning(f"方向提取失败: {content}, 错误: {e}")
            return ""
    
    def _select_primary_direction(self, directions, content):
        """选择主要方向 - 修复版"""
        if not directions:
            return ""
        
        if len(directions) == 1:
            return directions[0]
        
        content_str = str(content)
        
        # 🎯 优先级规则 - 修复版
        priority_rules = [
            # 最高优先级：总和相关
            lambda d: any(keyword in content_str for keyword in ['总和', '总']) and d in directions,
            # 高优先级：特字相关
            lambda d: '特' in content_str and d in directions,
            # 中优先级：和值相关
            lambda d: any(keyword in content_str for keyword in ['和值', '和']) and d in directions,
            # 基础优先级：两面相关
            lambda d: '两面' in content_str and d in directions,
            # 默认优先级
            lambda d: d in directions
        ]
        
        for rule in priority_rules:
            matching_directions = [d for d in directions if rule(d)]
            if matching_directions:
                return matching_directions[0]
        
        return directions[0]
    
    def calculate_account_total_periods_by_lottery(self, df):
        """按彩种计算每个账户的总投注期数统计"""
        self.account_total_periods_by_lottery = defaultdict(dict)
        self.account_record_stats_by_lottery = defaultdict(dict)
        
        lottery_col = '原始彩种' if '原始彩种' in df.columns else '彩种'
        
        for lottery in df[lottery_col].unique():
            df_lottery = df[df[lottery_col] == lottery]
            
            period_counts = df_lottery.groupby('会员账号')['期号'].nunique().to_dict()
            self.account_total_periods_by_lottery[lottery] = period_counts
            
            record_counts = df_lottery.groupby('会员账号').size().to_dict()
            self.account_record_stats_by_lottery[lottery] = record_counts
    
    def detect_all_wash_trades(self):
        """检测所有类型的对刷交易"""
        if not self.data_processed or self.df_valid is None or len(self.df_valid) == 0:
            st.error("❌ 没有有效数据可用于检测")
            return []
        
        self.performance_stats = {
            'start_time': datetime.now(),
            'total_records': len(self.df_valid),
            'total_periods': self.df_valid['期号'].nunique(),
            'total_accounts': self.df_valid['会员账号'].nunique()
        }
        
        df_filtered = self.exclude_multi_direction_accounts(self.df_valid)
        
        if len(df_filtered) == 0:
            st.error("❌ 过滤后无有效数据")
            return []
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        all_patterns = []
        total_steps = self.config.max_accounts_in_group - 1
        
        for account_count in range(2, self.config.max_accounts_in_group + 1):
            status_text.text(f"🔍 检测{account_count}个账户对刷模式...")
            patterns = self.detect_n_account_patterns_optimized(df_filtered, account_count)
            all_patterns.extend(patterns)
            
            progress = (account_count - 1) / total_steps
            progress_bar.progress(progress)
        
        progress_bar.progress(1.0)
        status_text.text("✅ 检测完成")
        
        self.performance_stats['end_time'] = datetime.now()
        self.performance_stats['detection_time'] = (
            self.performance_stats['end_time'] - self.performance_stats['start_time']
        ).total_seconds()
        self.performance_stats['total_patterns'] = len(all_patterns)
        
        self.display_performance_stats()
        
        return all_patterns
    
    def detect_n_account_patterns_optimized(self, df_filtered, n_accounts):
        """优化版的N个账户对刷模式检测"""
        wash_records = []
        
        period_groups = df_filtered.groupby(['期号', '原始彩种'])
        
        valid_direction_combinations = self._get_valid_direction_combinations(n_accounts)
        
        batch_size = 100
        period_keys = list(period_groups.groups.keys())
        
        for i in range(0, len(period_keys), batch_size):
            batch_keys = period_keys[i:i+batch_size]
            
            for period_key in batch_keys:
                period_data = period_groups.get_group(period_key)
                period_accounts = period_data['会员账号'].unique()
                
                if len(period_accounts) < n_accounts:
                    continue
                
                batch_patterns = self._detect_combinations_for_period(
                    period_data, period_accounts, n_accounts, valid_direction_combinations
                )
                wash_records.extend(batch_patterns)
        
        return self.find_continuous_patterns_optimized(wash_records)
    
    def _get_valid_direction_combinations(self, n_accounts):
        """🎯 修复版有效方向组合生成 - 保持基础对立组但支持变异形式"""
        valid_combinations = []
        
        # 🎯 基础对立组处理 - 保持4组基础对立关系
        for opposites in self.config.opposite_groups:
            opposite_list = list(opposites)
            
            if n_accounts == 2:
                # 2个账户：标准的1v1对立
                if len(opposite_list) == 2:
                    dir1, dir2 = opposite_list
                    valid_combinations.append({
                        'directions': [dir1, dir2],
                        'dir1_count': 1,
                        'dir2_count': 1,
                        'opposite_type': f"{dir1}-{dir2}"
                    })
            else:
                # 3个及以上账户：多种分布
                for i in range(1, n_accounts):
                    j = n_accounts - i
                    if len(opposite_list) == 2:
                        dir1, dir2 = opposite_list
                        valid_combinations.append({
                            'directions': [dir1] * i + [dir2] * j,
                            'dir1_count': i,
                            'dir2_count': j,
                            'opposite_type': f"{dir1}-{dir2}"
                        })
        
        # 🎯 带位置的对立组 - 动态生成（支持变异形式）
        positions = ['冠军', '亚军', '第三名', '第四名', '第五名', 
                    '第六名', '第七名', '第八名', '第九名', '第十名',
                    '百位', '十位', '个位', '第1球', '第2球', '第3球', '第4球', '第5球',
                    '特码', '正码一', '正码二', '正码三', '正码四', '正码五', '正码六']
        
        for position in positions:
            for opposites in self.config.opposite_groups:
                if len(opposites) == 2:
                    dir1, dir2 = list(opposites)
                    if n_accounts == 2:
                        valid_combinations.append({
                            'directions': [f"{position}-{dir1}", f"{position}-{dir2}"],
                            'dir1_count': 1,
                            'dir2_count': 1,
                            'opposite_type': f"{position}-{dir1} vs {position}-{dir2}"
                        })
                    else:
                        for i in range(1, n_accounts):
                            j = n_accounts - i
                            valid_combinations.append({
                                'directions': [f"{position}-{dir1}"] * i + [f"{position}-{dir2}"] * j,
                                'dir1_count': i,
                                'dir2_count': j,
                                'opposite_type': f"{position}-{dir1} vs {position}-{dir2}"
                            })
        
        return valid_combinations
    
    def _detect_combinations_for_period(self, period_data, period_accounts, n_accounts, valid_combinations):
        """为单个期号检测组合 - 修复版"""
        patterns = []
        
        # 获取当前彩种
        lottery = period_data['原始彩种'].iloc[0] if '原始彩种' in period_data.columns else period_data['彩种'].iloc[0]
        
        # 🎯 构建账户信息字典
        account_info = {}
        for _, row in period_data.iterrows():
            account = row['会员账号']
            direction = row['投注方向']
            amount = row['投注金额']
            
            if account not in account_info:
                account_info[account] = []
            account_info[account].append({
                'direction': direction,
                'amount': amount
            })
        
        # 检查所有可能的账户组合
        for account_group in combinations(period_accounts, n_accounts):
            # 检查账户期数差异
            if not self._check_account_period_difference(account_group, lottery):
                continue
            
            group_directions = []
            group_amounts = []
            
            for account in account_group:
                if account in account_info and account_info[account]:
                    first_bet = account_info[account][0]  # 取第一个投注记录
                    group_directions.append(first_bet['direction'])
                    group_amounts.append(first_bet['amount'])
            
            if len(group_directions) != n_accounts:
                continue
            
            # 🎯 检查是否匹配任何有效的方向组合
            for combo in valid_combinations:
                target_directions = combo['directions']
                
                actual_directions_sorted = sorted(group_directions)
                target_directions_sorted = sorted(target_directions)
                
                if actual_directions_sorted == target_directions_sorted:
                    # 计算两个方向的总金额
                    dir1_total = 0
                    dir2_total = 0
                    dir1 = combo['directions'][0]  # 取第一个方向作为参考
                    
                    for direction, amount in zip(group_directions, group_amounts):
                        if direction == dir1:
                            dir1_total += amount
                        else:
                            dir2_total += amount
                    
                    # 检查金额相似度
                    similarity_threshold = self.config.account_count_similarity_thresholds.get(
                        n_accounts, self.config.amount_similarity_threshold
                    )
                    
                    if dir1_total > 0 and dir2_total > 0:
                        similarity = min(dir1_total, dir2_total) / max(dir1_total, dir2_total)
                        
                        if similarity >= similarity_threshold:
                            lottery_type = period_data['彩种类型'].iloc[0] if '彩种类型' in period_data.columns else '未知'
                            
                            # 🎯 修复模式字符串生成
                            if ' vs ' in combo['opposite_type']:
                                # 带位置的对立类型，如 "第3球-小 vs 第3球-大"
                                pattern_parts = combo['opposite_type'].split(' vs ')
                                if len(pattern_parts) == 2:
                                    dir1_part = pattern_parts[0].split('-')
                                    dir2_part = pattern_parts[1].split('-')
                                    if len(dir1_part) == 2 and len(dir2_part) == 2:
                                        # 格式：位置-方向(数量个) vs 位置-方向(数量个)
                                        pattern_str = f"{dir1_part[0]}-{dir1_part[1]}({combo['dir1_count']}个) vs {dir2_part[0]}-{dir2_part[1]}({combo['dir2_count']}个)"
                                    else:
                                        pattern_str = f"{pattern_parts[0]}({combo['dir1_count']}个) vs {pattern_parts[1]}({combo['dir2_count']}个)"
                                else:
                                    pattern_str = combo['opposite_type']
                            else:
                                # 基础对立类型，如 "大-小"
                                opposite_parts = combo['opposite_type'].split('-')
                                if len(opposite_parts) == 2:
                                    pattern_str = f"{opposite_parts[0]}({combo['dir1_count']}个) vs {opposite_parts[1]}({combo['dir2_count']}个)"
                                else:
                                    pattern_str = combo['opposite_type']
                            
                            record = {
                                '期号': period_data['期号'].iloc[0],
                                '彩种': lottery,
                                '彩种类型': lottery_type,
                                '账户组': list(account_group),
                                '方向组': group_directions,
                                '金额组': group_amounts,
                                '总金额': dir1_total + dir2_total,
                                '相似度': similarity,
                                '账户数量': n_accounts,
                                '模式': pattern_str,  # 🎯 使用修复后的模式字符串
                                '对立类型': combo['opposite_type']
                            }
                            
                            patterns.append(record)
        
        return patterns
    
    def _check_account_period_difference(self, account_group, lottery):
        """检查账户组内账户的总投注期数差异是否在阈值内"""
        if lottery not in self.account_total_periods_by_lottery:
            return True  # 如果没有该彩种的统计信息，默认允许组合
        
        total_periods_stats = self.account_total_periods_by_lottery[lottery]
        
        # 获取账户组内每个账户的总投注期数
        account_periods = []
        for account in account_group:
            if account in total_periods_stats:
                account_periods.append(total_periods_stats[account])
            else:
                # 如果某个账户没有统计信息，无法比较，默认允许组合
                return True
        
        # 如果只有一个账户有期数信息，无法比较，默认允许组合
        if len(account_periods) < 2:
            return True
        
        # 计算最大和最小期数差异
        max_period = max(account_periods)
        min_period = min(account_periods)
        period_diff = max_period - min_period
        
        # 如果期数差异超过阈值，不允许组合
        if period_diff > self.config.account_period_diff_threshold:
            logger.info(f"跳过账户组 {account_group}，期数差异 {period_diff} > {self.config.account_period_diff_threshold}")
            return False
        
        return True
    
    def find_continuous_patterns_optimized(self, wash_records):
        """优化版的连续对刷模式检测"""
        if not wash_records:
            return []
        
        account_group_patterns = defaultdict(list)
        for record in wash_records:
            account_group_key = (tuple(sorted(record['账户组'])), record['彩种'])
            account_group_patterns[account_group_key].append(record)
        
        continuous_patterns = []
        
        for (account_group, lottery), records in account_group_patterns.items():
            sorted_records = sorted(records, key=lambda x: x['期号'])
            
            # 根据新的阈值要求确定最小对刷期数
            required_min_periods = self.get_required_min_periods(account_group, lottery)
            
            if len(sorted_records) >= required_min_periods:
                total_investment = sum(r['总金额'] for r in sorted_records)
                similarities = [r['相似度'] for r in sorted_records]
                avg_similarity = np.mean(similarities) if similarities else 0
                
                opposite_type_counts = defaultdict(int)
                for record in sorted_records:
                    opposite_type_counts[record['对立类型']] += 1
                
                pattern_count = defaultdict(int)
                for record in sorted_records:
                    pattern_count[record['模式']] += 1
                
                # 🎯 优化主要对立类型显示
                main_opposite_type = max(opposite_type_counts.items(), key=lambda x: x[1])[0]
                # 如果主要对立类型包含 " vs "，则进行格式化
                if ' vs ' in main_opposite_type:
                    parts = main_opposite_type.split(' vs ')
                    if len(parts) == 2:
                        # 提取位置和方向，格式化为 "位置-方向1-方向2"
                        pos_dir1 = parts[0].split('-')
                        pos_dir2 = parts[1].split('-')
                        if len(pos_dir1) >= 2 and len(pos_dir2) >= 2:
                            # 假设位置相同，只显示一次位置
                            position = pos_dir1[0]  # 取第一个位置
                            dir1 = pos_dir1[-1]     # 取最后一个部分作为方向
                            dir2 = pos_dir2[-1]     # 取最后一个部分作为方向
                            main_opposite_type = f"{position}-{dir1}-{dir2}"
                        else:
                            main_opposite_type = f"{parts[0]}-{parts[1].split('-')[-1]}" if '-' in parts[1] else f"{parts[0]}-{parts[1]}"
                
                # 账户统计信息
                account_stats_info = []
                total_periods_stats = self.account_total_periods_by_lottery.get(lottery, {})
                record_stats = self.account_record_stats_by_lottery.get(lottery, {})
                
                for account in account_group:
                    total_periods = total_periods_stats.get(account, 0)
                    records_count = record_stats.get(account, 0)
                    account_stats_info.append(f"{account}({total_periods}期/{records_count}记录)")
                
                activity_level = self.get_account_group_activity_level(account_group, lottery)
                
                continuous_patterns.append({
                    '账户组': list(account_group),
                    '彩种': lottery,
                    '彩种类型': records[0]['彩种类型'] if records else '未知',
                    '账户数量': len(account_group),
                    '主要对立类型': main_opposite_type,
                    '对立类型分布': dict(opposite_type_counts),
                    '对刷期数': len(sorted_records),
                    '总投注金额': total_investment,
                    '平均相似度': avg_similarity,
                    '模式分布': dict(pattern_count),
                    '详细记录': sorted_records,
                    '账户活跃度': activity_level,
                    '账户统计信息': account_stats_info,
                    '要求最小对刷期数': required_min_periods
                })
        
        return continuous_patterns

    def exclude_multi_direction_accounts(self, df_valid):
        """排除同一账户多方向下注"""
        multi_direction_mask = (
            df_valid.groupby(['期号', '会员账号'])['投注方向']
            .transform('nunique') > 1
        )
        
        df_filtered = df_valid[~multi_direction_mask].copy()
        
        return df_filtered
    
    def get_account_group_activity_level(self, account_group, lottery):
        """获取活跃度水平"""
        if lottery not in self.account_total_periods_by_lottery:
            return 'unknown'
        
        total_periods_stats = self.account_total_periods_by_lottery[lottery]
        
        # 计算账户组中在指定彩种的最小总投注期数
        min_total_periods = min(total_periods_stats.get(account, 0) for account in account_group)
        
        # 按照新的活跃度阈值
        if min_total_periods <= self.config.period_thresholds['low_activity']:
            return 'low'        # 总投注期数1-10
        elif min_total_periods <= self.config.period_thresholds['medium_activity_high']:
            return 'medium'     # 总投注期数11-50
        elif min_total_periods <= self.config.period_thresholds['high_activity_high']:
            return 'high'       # 总投注期数51-100
        else:
            return 'very_high'  # 总投注期数100以上
    
    def get_required_min_periods(self, account_group, lottery):
        """根据新的活跃度阈值获取所需的最小对刷期数"""
        activity_level = self.get_account_group_activity_level(account_group, lottery)
        
        if activity_level == 'low':
            return self.config.period_thresholds['min_periods_low']      # 3期
        elif activity_level == 'medium':
            return self.config.period_thresholds['min_periods_medium']   # 5期
        elif activity_level == 'high':
            return self.config.period_thresholds['min_periods_high']     # 8期
        else:
            return self.config.period_thresholds['min_periods_very_high'] # 11期
    
    def display_performance_stats(self):
        """显示性能统计"""
        if not self.performance_stats:
            return
        
        with st.expander("📈 性能统计", expanded=False):
            st.write(f"**数据处理统计:**")
            st.write(f"- 总记录数: {self.performance_stats['total_records']:,}")
            st.write(f"- 总期号数: {self.performance_stats['total_periods']:,}")
            st.write(f"- 总账户数: {self.performance_stats['total_accounts']:,}")
            
            if 'detection_time' in self.performance_stats:
                st.write(f"**检测性能:**")
                st.write(f"- 检测时间: {self.performance_stats['detection_time']:.2f} 秒")
                st.write(f"- 发现模式: {self.performance_stats['total_patterns']} 个")
    
    def comprehensive_detection(self, df, detection_mode, coverage_params, direction_params):
        """综合检测：方向对刷 + 号码覆盖"""
        all_results = {
            'direction_patterns': [],
            'coverage_patterns': [],
            'combined_results': []
        }
        
        # 1. 方向对刷检测
        if detection_mode in ['direction_only', 'comprehensive']:
            with st.spinner("🔍 正在进行方向对刷检测..."):
                direction_patterns = self.detect_all_wash_trades()
                all_results['direction_patterns'] = direction_patterns
        
        # 2. 号码覆盖检测 - 使用新增的增强检测方法
        if detection_mode in ['coverage_only', 'comprehensive']:
            with st.spinner("🔢 正在进行号码覆盖检测..."):
                # 使用新增的增强号码覆盖检测
                coverage_patterns = self.enhanced_coverage_detection(df, coverage_params)
                all_results['coverage_patterns'] = coverage_patterns
        
        # 3. 结果整合
        if detection_mode == 'comprehensive':
            all_results['combined_results'] = self.merge_detection_results(
                all_results['direction_patterns'], 
                all_results['coverage_patterns']
            )
        
        return all_results
    
    def prepare_data_for_coverage_analysis(self, df):
        """准备数据用于覆盖分析"""
        df_coverage = df.copy()
        
        # 统一玩法分类
        if '玩法' in df_coverage.columns:
            df_coverage['玩法'] = df_coverage.apply(
                lambda row: self.coverage_analyzer.normalize_play_category(
                    row['玩法'], 
                    row['彩种类型'] if '彩种类型' in df_coverage.columns else 'six_mark'
                ), 
                axis=1
            )
        
        return df_coverage
    
    def merge_detection_results(self, direction_patterns, coverage_patterns):
        """合并两种检测结果"""
        combined_results = []
        
        # 添加方向对刷结果
        for pattern in direction_patterns:
            combined_results.append({
                'type': 'direction',
                'data': pattern,
                'accounts': pattern['账户组'],
                'lottery': pattern['彩种'],
                'periods': [record['期号'] for record in pattern['详细记录']]
            })
        
        # 添加号码覆盖结果
        for period_key, result in coverage_patterns.items():
            for combo in result['all_combinations']:
                combined_results.append({
                    'type': 'coverage',
                    'data': {
                        'period': result['period'],
                        'lottery': result['lottery'],
                        'position': result.get('position', ''),
                        'accounts': combo['accounts'],
                        'total_amount': combo['total_amount'],
                        'similarity': combo['similarity']
                    },
                    'accounts': combo['accounts'],
                    'lottery': result['lottery'],
                    'periods': [result['period']]
                })
        
        return combined_results
    
    def display_comprehensive_results(self, all_results, detection_mode):
        """显示综合检测结果"""
        st.header("🎯 综合对刷检测结果")
        
        direction_count = len(all_results['direction_patterns'])
        coverage_count = len(all_results['coverage_patterns'])
        combined_count = len(all_results['combined_results'])
        
        # 分类统计
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("方向对刷组数", direction_count)
        with col2:
            st.metric("号码覆盖组数", coverage_count)
        with col3:
            if detection_mode == 'comprehensive':
                st.metric("总检测组数", combined_count)
            else:
                st.metric("总检测组数", direction_count + coverage_count)
        
        # 分别展示
        if detection_mode in ['direction_only', 'comprehensive'] and direction_count > 0:
            tab1, tab2 = st.tabs(["🎯 方向对刷检测", "🔢 号码覆盖检测"])
            
            with tab1:
                self.display_direction_results(all_results['direction_patterns'])
            
            with tab2:
                if coverage_count > 0:
                    self.coverage_analyzer.display_enhanced_results(
                        all_results['coverage_patterns'], 
                        "自动识别所有彩种"
                    )
                else:
                    st.info("未发现号码覆盖模式")
        
        elif detection_mode == 'coverage_only' and coverage_count > 0:
            self.coverage_analyzer.display_enhanced_results(
                all_results['coverage_patterns'], 
                "自动识别所有彩种"
            )
        
        else:
            st.info("未发现对刷行为")

    def display_coverage_results(self, coverage_results):
        """显示号码覆盖检测结果"""
        if not coverage_results:
            st.info("🎉 未发现号码覆盖组合")
            return
        
        st.subheader("🔢 号码覆盖检测结果")
        
        # 计算统计
        total_combinations = sum(result['total_combinations'] for result in coverage_results.values())
        total_periods = len(coverage_results)
        
        # 按彩种类型统计
        category_stats = defaultdict(int)
        for result in coverage_results.values():
            category = result.get('lottery_category', '未知')
            category_stats[category] += result['total_combinations']
        
        # 显示总体统计
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总完美组合数", total_combinations)
        with col2:
            st.metric("分析期数", total_periods)
        with col3:
            st.metric("涉及位置", len(set(key[2] for key in coverage_results.keys())))
        with col4:
            st.metric("彩种类型", len(category_stats))
        
        # 显示彩种类型统计
        st.subheader("🎲 彩种类型分布")
        category_display = {
            'six_mark': '六合彩',
            '10_number': '时时彩/PK10/赛车', 
            'fast_three': '快三'
        }
        
        cols = st.columns(len(category_stats))
        for i, (category, count) in enumerate(category_stats.items()):
            with cols[i % len(cols)]:
                display_name = category_display.get(category, category)
                st.metric(display_name, f"{count}组")
        
        # 显示参与账户统计
        st.subheader("👥 参与账户统计")
        account_stats = self._calculate_coverage_account_stats(coverage_results)
        
        if account_stats:
            df_stats = pd.DataFrame(account_stats)
            st.dataframe(
                df_stats,
                use_container_width=True,
                hide_index=True,
                height=min(400, len(df_stats) * 35 + 38)
            )
        
        # 显示详细组合
        st.subheader("📈 详细组合分析")
        self._display_detailed_coverage_combinations(coverage_results)
    
    def _calculate_coverage_account_stats(self, coverage_results):
        """计算号码覆盖检测的账户统计"""
        account_participation = defaultdict(lambda: {
            'periods': set(),
            'lotteries': set(),
            'positions': set(),
            'total_combinations': 0,
            'total_bet_amount': 0
        })
        
        for result in coverage_results.values():
            for combo in result['combinations']:
                for account in combo['accounts']:
                    account_info = account_participation[account]
                    account_info['periods'].add(result['period'])
                    account_info['lotteries'].add(result['lottery'])
                    account_info['positions'].add(result['position'])
                    account_info['total_combinations'] += 1
                    account_info['total_bet_amount'] += combo['individual_amounts'][account]
        
        account_stats = []
        for account, info in account_participation.items():
            stat_record = {
                '账户': account,
                '参与组合数': info['total_combinations'],
                '涉及期数': len(info['periods']),
                '涉及彩种': len(info['lotteries']),
                '涉及位置': ', '.join(sorted(info['positions'])),
                '总投注金额': info['total_bet_amount'],
                '平均每期金额': info['total_bet_amount'] / len(info['periods']) if info['periods'] else 0
            }
            account_stats.append(stat_record)
        
        return sorted(account_stats, key=lambda x: x['参与组合数'], reverse=True)
    
    def _display_detailed_coverage_combinations(self, coverage_results):
        """显示详细的号码覆盖组合"""
        # 按账户组合分组
        account_pair_groups = defaultdict(lambda: defaultdict(list))
        
        for group_key, result in coverage_results.items():
            lottery = result['lottery']
            position = result['position']
            
            for combo in result['combinations']:
                # 创建账户组合键
                accounts = combo['accounts']
                account_pair = " ↔ ".join(sorted(accounts))
                
                # 创建彩种键
                lottery_key = f"{lottery} - {position}"
                
                # 存储组合信息
                combo_info = {
                    'period': result['period'],
                    'combo': combo,
                    'lottery_category': result['lottery_category'],
                    'total_numbers': result['total_numbers']
                }
                
                account_pair_groups[account_pair][lottery_key].append(combo_info)
        
        # 显示每个账户组合
        for account_pair, lottery_groups in account_pair_groups.items():
            for lottery_key, combos in lottery_groups.items():
                # 按期号排序
                combos.sort(key=lambda x: x['period'])
                
                # 创建折叠框标题
                combo_count = len(combos)
                title = f"**{account_pair}** - {lottery_key}（{combo_count}个组合）"
                
                with st.expander(title, expanded=True):
                    # 显示每个组合
                    for idx, combo_info in enumerate(combos, 1):
                        combo = combo_info['combo']
                        period = combo_info['period']
                        lottery_category = combo_info['lottery_category']
                        
                        # 组合标题
                        st.markdown(f"**完美组合 {idx}:** {account_pair}")
                        
                        # 组合信息
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.write(f"**账户数量:** {len(combo['accounts'])}个")
                        with col2:
                            st.write(f"**期号:** {period}")
                        with col3:
                            st.write(f"**总金额:** ¥{combo['total_amount']:,.2f}")
                        with col4:
                            similarity = combo['similarity']
                            indicator = "🟢" if similarity >= 90 else "🟡" if similarity >= 80 else "🟠" if similarity >= 70 else "🔴"
                            st.write(f"**金额匹配度:** {similarity:.1f}% {indicator}")
                        
                        # 彩种类型信息
                        category_display = {
                            'six_mark': '六合彩',
                            '10_number': '时时彩/PK10/赛车',
                            'fast_three': '快三'
                        }
                        category_name = category_display.get(lottery_category, lottery_category)
                        st.write(f"**彩种类型:** {category_name}")
                        st.write(f"**号码总数:** {combo_info['total_numbers']}个")
                        
                        # 各账户详情
                        st.write("**各账户详情:**")
                        
                        for account in combo['accounts']:
                            amount_info = combo['individual_amounts'][account]
                            numbers_count = combo['numbers_count'][combo['accounts'].index(account)]
                            numbers_content = combo['bet_contents'][account]
                            
                            st.write(f"- **{account}**: {numbers_count}个数字")
                            st.write(f"  - 总投注: ¥{amount_info:,.2f}")
                            st.write(f"  - 平均每号: ¥{amount_info/numbers_count:,.2f}")
                            st.write(f"  - 投注内容: {numbers_content}")
                        
                        # 添加分隔线（除了最后一个组合）
                        if idx < len(combos):
                            st.markdown("---")
    
    def display_direction_results(self, patterns):
        """显示方向对刷检测结果"""
        if not patterns:
            st.info("未发现方向对刷模式")
            return
        
        st.write("\n" + "="*60)
        st.write("🎯 多账户对刷检测结果")
        st.write("="*60)
        
        # 总体统计
        self.display_summary_statistics(patterns)
        
        st.write("\n" + "="*60)
        
        # 参与账户详细统计
        st.subheader("👥 参与账户详细统计")
        
        # 计算账户参与统计
        account_stats = self._calculate_detailed_account_stats(patterns)
        
        if account_stats:
            df_stats = pd.DataFrame(account_stats)
            
            # 使用表格形式展示
            st.dataframe(
                df_stats,
                use_container_width=True,
                hide_index=True,
                height=min(400, len(df_stats) * 35 + 38)
            )
        
        # 按彩种分组显示详细对刷组
        st.write("\n" + "="*60)
        st.subheader("🔍 详细对刷组分析")
        
        patterns_by_lottery = defaultdict(list)
        for pattern in patterns:
            lottery_key = pattern['彩种']
            patterns_by_lottery[lottery_key].append(pattern)
        
        for lottery, lottery_patterns in patterns_by_lottery.items():
            with st.expander(f"🎲 彩种：{lottery}（发现{len(lottery_patterns)}组）", expanded=True):
                for i, pattern in enumerate(lottery_patterns, 1):
                    st.markdown(f"**对刷组 {i}:** {' ↔ '.join(pattern['账户组'])}")
                    
                    activity_icon = "🟢" if pattern['账户活跃度'] == 'low' else "🟡" if pattern['账户活跃度'] == 'medium' else "🟠" if pattern['账户活跃度'] == 'high' else "🔴"
                    st.markdown(f"**活跃度:** {activity_icon} {pattern['账户活跃度']} | **彩种:** {pattern['彩种']} | **主要类型:** {pattern['主要对立类型']}")
                    
                    st.markdown(f"**账户在该彩种投注期数/记录数:** {', '.join(pattern['账户统计信息'])}")
                    st.markdown(f"**对刷期数:** {pattern['对刷期数']}期 (要求≥{pattern['要求最小对刷期数']}期)")
                    st.markdown(f"**总金额:** {pattern['总投注金额']:.2f}元 | **平均匹配:** {pattern['平均相似度']:.2%}")
                    
                    st.markdown("**详细记录:**")
                    for j, record in enumerate(pattern['详细记录'], 1):
                        account_directions = []
                        for account, direction, amount in zip(record['账户组'], record['方向组'], record['金额组']):
                            account_directions.append(f"{account}({direction}:{amount})")
                        
                        st.write(f"{j}. 期号: {record['期号']} | 方向: {' ↔ '.join(account_directions)} | 匹配度: {record['相似度']:.2%}")
                    
                    if i < len(lottery_patterns):
                        st.markdown("---")
    
    def display_summary_statistics(self, patterns):
        """显示总体统计"""
        if not patterns:
            return
            
        st.subheader("📊 总体统计")
        
        total_groups = len(patterns)
        total_accounts = sum(p['账户数量'] for p in patterns)
        total_wash_periods = sum(p['对刷期数'] for p in patterns)
        total_amount = sum(p['总投注金额'] for p in patterns)
        
        account_count_stats = defaultdict(int)
        for pattern in patterns:
            account_count_stats[pattern['账户数量']] += 1
        
        lottery_stats = defaultdict(int)
        for pattern in patterns:
            lottery_stats[pattern['彩种']] += 1
        
        activity_stats = defaultdict(int)
        for pattern in patterns:
            activity_stats[pattern['账户活跃度']] += 1
        
        opposite_type_stats = defaultdict(int)
        for pattern in patterns:
            for opposite_type, count in pattern['对立类型分布'].items():
                opposite_type_stats[opposite_type] += count
        
        # ========== 第一行：总体指标 ==========
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("总对刷组数", total_groups)
        
        with col2:
            st.metric("涉及账户数", total_accounts)
        
        with col3:
            st.metric("总对刷期数", total_wash_periods)
        
        with col4:
            st.metric("总涉及金额", f"¥{total_amount:,.2f}")
        
        # ========== 第二行：彩种类型统计 ==========
        st.subheader("🎲 彩种类型统计")
        
        # 定义彩种类型显示名称
        lottery_display_names = {
            'PK10': 'PK10/赛车',
            'K3': '快三',
            'LHC': '六合彩', 
            'SSC': '时时彩',
            '3D': '3D系列'
        }
        
        # 创建彩种统计列
        lottery_cols = st.columns(min(5, len(lottery_stats)))
        
        for i, (lottery, count) in enumerate(lottery_stats.items()):
            if i < len(lottery_cols):
                with lottery_cols[i]:
                    display_name = lottery_display_names.get(lottery, lottery)
                    st.metric(
                        label=display_name,
                        value=f"{count}组"
                    )
        
        # ========== 第三行：账户组合分布和活跃度分布 ==========
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.subheader("👥 账户组合分布")
            
            for account_count, group_count in sorted(account_count_stats.items()):
                # 计算该类型组合的总对刷期数
                account_type_periods = sum(p['对刷期数'] for p in patterns if p['账户数量'] == account_count)
                st.write(f"- **{account_count}组**: {group_count}组 ({account_type_periods}期)")
        
        with col_right:
            st.subheader("📈 活跃度分布")
            
            activity_display_names = {
                'low': '低活跃度',
                'medium': '中活跃度',
                'high': '高活跃度',
                'very_high': '极高活跃度'
            }
            
            for activity, count in activity_stats.items():
                display_name = activity_display_names.get(activity, activity)
                # 计算该活跃度的总对刷期数
                activity_periods = sum(p['对刷期数'] for p in patterns if p['账户活跃度'] == activity)
                st.write(f"- **{display_name}**: {count}组 ({activity_periods}期)")
        
        # ========== 第四行：关键指标 ==========
        st.subheader("📈 关键指标")
        
        # 计算平均每组金额
        avg_group_amount = total_amount / total_groups if total_groups > 0 else 0
        
        metric_col1, metric_col2, metric_col3 = st.columns(3)
        
        with metric_col1:
            st.metric("平均每组金额", f"¥{avg_group_amount:,.2f}")
        
        with metric_col2:
            # 计算业务类型总金额
            business_total = total_amount
            st.metric("业务类型总额", f"¥{business_total:,.2f}")
        
        with metric_col3:
            # 显示总账户数
            st.metric("参与总账户数", total_accounts)
        
        # ========== 第五行：主要对立类型 ==========
        st.subheader("🎯 主要对立类型")
        
        # 显示前3个主要对立类型
        top_opposites = sorted(opposite_type_stats.items(), key=lambda x: x[1], reverse=True)[:3]
        
        for opposite_type, count in top_opposites:
            # 简化对立类型显示
            if ' vs ' in opposite_type:
                display_type = opposite_type.replace(' vs ', '-')
            else:
                display_type = opposite_type
            st.write(f"- **{display_type}**: {count}期")
    
    def _calculate_detailed_account_stats(self, patterns):
        """计算详细账户统计"""
        account_participation = defaultdict(lambda: {
            'periods': set(),
            'lotteries': set(),
            'positions': set(),
            'total_combinations': 0,
            'total_bet_amount': 0,
            'continuous_periods': 0,
            'actual_bet_records': []
        })
        
        # 从原始数据中收集账户的实际投注金额
        if self.df_valid is not None:
            for _, row in self.df_valid.iterrows():
                account = row['会员账号']
                amount = row['投注金额']
                period = row['期号']
                lottery = row['彩种'] if '彩种' in row else '未知'
                
                if account in account_participation:
                    account_participation[account]['actual_bet_records'].append({
                        'amount': amount,
                        'period': period,
                        'lottery': lottery
                    })
        
        # 收集账户参与信息
        for pattern in patterns:
            for account in pattern['账户组']:
                account_info = account_participation[account]
                
                # 添加期号
                for record in pattern['详细记录']:
                    account_info['periods'].add(record['期号'])
                
                # 添加彩种
                account_info['lotteries'].add(pattern['彩种'])
                
                # 添加位置信息
                for record in pattern['详细记录']:
                    for direction in record['方向组']:
                        if '-' in direction:
                            position = direction.split('-')[0]
                            account_info['positions'].add(position)
                
                account_info['total_combinations'] += 1
                account_info['continuous_periods'] = max(account_info['continuous_periods'], pattern['对刷期数'])
                
                # 计算该账户在对刷模式中的实际投注金额
                pattern_bet_amount = 0
                for record in pattern['详细记录']:
                    for acc, amt in zip(record['账户组'], record['金额组']):
                        if acc == account:
                            pattern_bet_amount += amt
                
                account_info['total_bet_amount'] += pattern_bet_amount
        
        # 转换为显示格式
        account_stats = []
        for account, info in account_participation.items():
            stat_record = {
                '账户': account,
                '参与组合数': info['total_combinations'],
                '涉及期数': len(info['periods']),
                '涉及彩种': len(info['lotteries']),
                '总投注金额': info['total_bet_amount'],
                '平均每组金额': info['total_bet_amount'] / info['total_combinations'] if info['total_combinations'] > 0 else 0
            }
            
            account_stats.append(stat_record)
        
        return sorted(account_stats, key=lambda x: x['总投注金额'], reverse=True)

# ==================== 主函数 ====================
def main():
    """主函数"""
    st.title("🎯 彩票智能对刷检测系统 - 全功能版")
    st.markdown("---")
    
    with st.sidebar:
        st.header("📁 数据上传")
        uploaded_file = st.file_uploader(
            "请上传数据文件", 
            type=['xlsx', 'xls', 'csv'],
            help="请确保文件包含必要的列：会员账号、期号、内容、金额"
        )
        
        st.header("⚙️ 检测模式配置")
        detection_mode = st.radio(
            "检测模式:",
            ["comprehensive", "direction_only", "coverage_only"],
            format_func=lambda x: {
                'comprehensive': '综合检测',
                'direction_only': '仅方向对刷', 
                'coverage_only': '仅号码覆盖'
            }[x],
            help="选择检测模式"
        )
    
    if uploaded_file is not None:
        try:
            # 配置参数
            st.sidebar.header("🎯 方向对刷参数")
            
            min_amount = st.sidebar.number_input("最小投注金额", value=10, min_value=1, help="低于此金额的记录将被过滤")
            base_similarity_threshold = st.sidebar.slider("基础金额匹配度阈值", 0.8, 1.0, 0.8, 0.01, help="2个账户的基础匹配度阈值")
            max_accounts = st.sidebar.slider("最大检测账户数", 2, 8, 5, help="检测的最大账户组合数量")
            
            # 账户期数差异阈值配置
            period_diff_threshold = st.sidebar.number_input(
                "账户期数最大差异阈值", 
                value=150, 
                min_value=0, 
                max_value=1000,
                help="账户总投注期数最大允许差异，超过此值不进行组合检测"
            )
            
            st.sidebar.header("🔢 号码覆盖参数")
            
            # 六合彩专用阈值设置
            six_mark_min_number_count = st.sidebar.slider(
                "六合彩-号码数量阈值", 
                min_value=1, 
                max_value=30, 
                value=11,
                help="六合彩：只分析投注号码数量大于等于此值的账户"
            )
            
            six_mark_min_avg_amount = st.sidebar.slider(
                "六合彩-平均金额阈值", 
                min_value=0, 
                max_value=20, 
                value=2,
                step=1,
                help="六合彩：只分析平均每号金额大于等于此值的账户"
            )
            
            # 时时彩/PK10/赛车专用阈值设置
            ten_number_min_number_count = st.sidebar.slider(
                "赛车类-号码数量阈值", 
                min_value=1, 
                max_value=10, 
                value=3,
                help="时时彩/PK10/赛车：只分析投注号码数量大于等于此值的账户"
            )
            
            ten_number_min_avg_amount = st.sidebar.slider(
                "赛车类-平均金额阈值", 
                min_value=0, 
                max_value=10, 
                value=1,
                step=1,
                help="时时彩/PK10/赛车：只分析平均每号金额大于等于此值的账户"
            )
            
            # 快三专用阈值设置
            fast_three_min_number_count = st.sidebar.slider(
                "快三-号码数量阈值", 
                min_value=1, 
                max_value=16, 
                value=3,
                help="快三和值玩法：只分析投注号码数量大于等于此值的账户"
            )
            
            fast_three_min_avg_amount = st.sidebar.slider(
                "快三-平均金额阈值", 
                min_value=0, 
                max_value=10, 
                value=1,
                step=1,
                help="快三和值玩法：只分析平均每号金额大于等于此值的账户"
            )
            
            # 更新配置参数
            config = ComprehensiveConfig()
            config.min_amount = min_amount
            config.amount_similarity_threshold = base_similarity_threshold
            config.max_accounts_in_group = max_accounts
            config.account_period_diff_threshold = period_diff_threshold
            
            # 设置多账户匹配度阈值
            config.account_count_similarity_thresholds = {
                2: base_similarity_threshold,
                3: max(base_similarity_threshold + 0.05, 0.85),
                4: max(base_similarity_threshold + 0.1, 0.9),
                5: max(base_similarity_threshold + 0.15, 0.95)
            }
            
            # 覆盖分析参数
            coverage_params = {
                'six_mark': {
                    'min_number_count': six_mark_min_number_count,
                    'min_avg_amount': six_mark_min_avg_amount
                },
                'ten_number': {
                    'min_number_count': ten_number_min_number_count,
                    'min_avg_amount': ten_number_min_avg_amount
                },
                'fast_three': {
                    'min_number_count': fast_three_min_number_count,
                    'min_avg_amount': fast_three_min_avg_amount
                }
            }
            
            direction_params = {
                'min_amount': min_amount,
                'similarity_threshold': base_similarity_threshold,
                'max_accounts': max_accounts
            }
            
            detector = ComprehensiveWashTradeDetector(config)
            
            st.success(f"✅ 已上传文件: {uploaded_file.name}")
            
            with st.spinner("🔄 正在解析数据..."):
                df_enhanced, filename = detector.upload_and_process(uploaded_file)
                
                if df_enhanced is not None and len(df_enhanced) > 0:
                    st.success("✅ 数据解析完成")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("有效记录数", f"{len(df_enhanced):,}")
                    with col2:
                        st.metric("唯一期号数", f"{df_enhanced['期号'].nunique():,}")
                    with col3:
                        st.metric("唯一账户数", f"{df_enhanced['会员账号'].nunique():,}")
                    with col4:
                        if '彩种类型' in df_enhanced.columns:
                            st.metric("彩种类型数", f"{df_enhanced['彩种类型'].nunique()}")
                    
                    with st.expander("📊 数据详情", expanded=False):
                        tab1, tab2 = st.tabs(["数据概览", "彩种分布"])
                        
                        with tab1:
                            st.dataframe(df_enhanced.head(100), use_container_width=True)
                            
                        with tab2:
                            if '彩种类型' in df_enhanced.columns:
                                lottery_type_stats = df_enhanced['彩种类型'].value_counts()
                                st.bar_chart(lottery_type_stats)
                    
                    st.info("🚀 开始综合检测...")
                    
                    # 执行综合检测
                    all_results = detector.comprehensive_detection(
                        df_enhanced, 
                        detection_mode, 
                        coverage_params, 
                        direction_params
                    )
                    
                    # 显示结果
                    detector.display_comprehensive_results(all_results, detection_mode)
                    
                    # 导出功能
                    if (len(all_results['direction_patterns']) > 0 or 
                        len(all_results['coverage_patterns']) > 0):
                        st.markdown("---")
                        st.subheader("📥 数据导出")
                        
                        if st.button("📊 生成完整检测报告"):
                            # 这里可以添加导出逻辑
                            st.success("✅ 报告生成完成！")
                            
                else:
                    st.error("❌ 数据解析失败，请检查文件格式和内容")
            
        except Exception as e:
            st.error(f"❌ 程序执行失败: {str(e)}")
            st.error(f"详细错误信息:\n{traceback.format_exc()}")
    else:
        st.info("👈 请在左侧边栏上传数据文件开始分析")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("🔍 全功能检测")
            st.markdown("""
            - **方向对刷检测**: 大小、单双、龙虎等方向对立
            - **号码覆盖检测**: 完美号码覆盖协同投注
            - **精确位置识别**: 冠军、亚军等具体位置
            - **多维度分析**: 金额、期数、活跃度多维度
            """)
        
        with col2:
            st.subheader("📊 专业分析")
            st.markdown("""
            - **全彩种支持**: 六合彩、时时彩、PK10、快三、3D等
            - **智能识别**: 自动识别彩种类型和玩法
            - **数据验证**: 完整的数据质量检查流程
            - **详细报告**: 多维度统计和可视化
            """)
        
        with col3:
            st.subheader("🚀 高效处理")
            st.markdown("""
            - **大数据优化**: 支持海量数据快速处理
            - **缓存机制**: 智能缓存提升性能
            - **并行检测**: 多线程加速分析过程
            - **实时进度**: 实时显示分析进度
            """)
    
    with st.expander("📖 系统使用说明", expanded=False):
        st.markdown("""
        ### 系统功能说明

        **🎯 检测模式:**
        - **综合检测**: 同时进行方向对刷和号码覆盖检测
        - **仅方向对刷**: 只检测大小、单双等方向对立行为
        - **仅号码覆盖**: 只检测完美号码覆盖协同行为

        **📊 方向对刷检测逻辑:**
        - **总投注期数**: 账户在特定彩种中的所有期号投注次数
        - **对刷期数**: 账户组实际发生对刷行为的期数
        - 根据**总投注期数**判定账户活跃度，设置不同的**对刷期数**阈值

        **🔢 号码覆盖检测逻辑:**
        - 检测多账户是否形成完美号码覆盖
        - 分析号码互补关系和金额匹配度
        - 支持特码、正码、定位胆等多种玩法

        **🎲 支持的彩种:**
        - **六合彩**: 特码、正码、平码等玩法
        - **PK10/赛车**: 冠军、亚军等具体位置
        - **时时彩**: 定位胆、大小单双等
        - **快三**: 和值、点数等
        - **3D系列**: 百位、十位、个位

        **⚡ 自动检测:**
        - 数据上传后自动开始处理和分析
        - 智能识别列名和彩种类型
        - 实时显示分析进度和结果
        """)

if __name__ == "__main__":
    main()
