import streamlit as st
import pandas as pd
import numpy as np
import re
import logging
from typing import Dict, List, Set, Tuple, Any
import itertools
from collections import defaultdict
import time
from io import BytesIO
from functools import lru_cache

# 设置页面
st.set_page_config(
    page_title="彩票完美覆盖分析系统 - 全彩种增强版",
    page_icon="🎯",
    layout="wide"
)

# ==================== 配置常量 ====================
COVERAGE_CONFIG = {
    'min_number_count': {
        'six_mark': 11,  # 六合彩
        '10_number': 3,   # 10个号码的彩种
    },
    'min_avg_amount': {
        'six_mark': 2,
        '10_number': 1,
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
            '幸运28', '北京28', '加拿大28', '极速PK10', '分分PK10'
        ]
    }
}

# ==================== 日志设置 ====================
def setup_logging():
    """设置日志系统"""
    logger = logging.getLogger('CoverageAnalysis')
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()

# ==================== 全彩种分析器 ====================
class MultiLotteryCoverageAnalyzer:
    """全彩种覆盖分析器 - 支持六合彩、时时彩、PK10等"""
    
    def __init__(self):
        # 定义各彩种的号码范围 - 修正赛车号码范围为1-10
        self.lottery_configs = {
            'six_mark': {
                'number_range': set(range(1, 50)),
                'total_numbers': 49,
                'type_name': '六合彩特码',
                'play_keywords': ['特码', '特玛', '特马', '特碼']
            },
            '10_number': {
                'number_range': set(range(1, 11)),  # 1-10 修正为1-10
                'total_numbers': 10,
                'type_name': '10个号码彩种',
                'play_keywords': ['定位胆', '一字定位', '一字', '定位', '大小单双', '龙虎', '第一名', '第二名', '第三名', '第四名', '第五名', '第六名', '第七名', '第八名', '第九名', '第十名']
            }
        }
        
        # 完整的彩种列表
        self.target_lotteries = {}
        for lottery_type, lotteries in COVERAGE_CONFIG['target_lotteries'].items():
            self.target_lotteries[lottery_type] = lotteries
        
        # 增强的列名映射字典 - 根据示例数据扩展
        self.column_mappings = {
            '会员账号': ['会员账号', '会员账户', '账号', '账户', '用户账号', '玩家账号', '用户ID', '玩家ID'],
            '彩种': ['彩种', '彩神', '彩票种类', '游戏类型', '彩票类型', '游戏彩种', '彩票名称'],
            '期号': ['期号', '期数', '期次', '期', '奖期', '期号信息', '期号编号'],
            '玩法': ['玩法', '玩法分类', '投注类型', '类型', '投注玩法', '玩法类型', '分类'],
            '内容': ['内容', '投注内容', '下注内容', '注单内容', '投注号码', '号码内容', '投注信息'],
            '金额': ['金额', '下注总额', '投注金额', '总额', '下注金额', '投注额', '金额数值', '单注金额']
        }
        
        # 玩法分类映射 - 扩展支持多种彩种，特别是赛车
        self.play_mapping = {
            # 六合彩玩法
            '特码': '特码',
            '特码A': '特码', 
            '特码B': '特码',
            '特码球': '特码',
            '特码_特码': '特码',
            '特玛': '特码',
            '特马': '特码',
            '特碼': '特码',
            
            # 时时彩/PK10/赛车玩法
            '定位胆': '定位胆',
            '一字定位': '定位胆',
            '一字': '定位胆',
            '定位': '定位胆',
            '大小单双': '定位胆',
            '龙虎': '定位胆',
            '第一名': '定位胆',
            '第二名': '定位胆', 
            '第三名': '定位胆',
            '第四名': '定位胆',
            '第五名': '定位胆',
            '第六名': '定位胆',  # 添加第六名
            '第七名': '定位胆',
            '第八名': '定位胆',
            '第九名': '定位胆',
            '第十名': '定位胆'
        }
    
    def identify_lottery_category(self, lottery_name):
        """识别彩种类型 - 增强赛车识别"""
        lottery_str = str(lottery_name).strip().lower()
        
        # 检查六合彩
        for lottery in self.target_lotteries['six_mark']:
            if lottery.lower() in lottery_str:
                return 'six_mark'
        
        # 检查10个号码的彩种
        for lottery in self.target_lotteries['10_number']:
            if lottery.lower() in lottery_str:
                return '10_number'
        
        # 模糊匹配
        if any(word in lottery_str for word in ['六合', 'lhc', '⑥合', '6合']):
            return 'six_mark'
        elif any(word in lottery_str for word in ['时时彩', 'ssc']):
            return '10_number'
        elif any(word in lottery_str for word in ['pk10', 'pk拾', '赛车']):
            return '10_number'
        elif any(word in lottery_str for word in ['28', '幸运28']):
            return '10_number'
        
        return None
    
    def get_lottery_config(self, lottery_category):
        """获取彩种配置"""
        return self.lottery_configs.get(lottery_category, self.lottery_configs['six_mark'])
    
    def enhanced_column_mapping(self, df):
        """增强版列名识别 - 根据示例数据优化"""
        column_mapping = {}
        actual_columns = [str(col).strip() for col in df.columns]
        
        st.info(f"🔍 检测到的列名: {actual_columns}")
        
        for standard_col, possible_names in self.column_mappings.items():
            found = False
            for actual_col in actual_columns:
                actual_col_lower = actual_col.lower().replace(' ', '').replace('_', '').replace('-', '')
                
                for possible_name in possible_names:
                    possible_name_lower = possible_name.lower().replace(' ', '').replace('_', '').replace('-', '')
                    
                    if (possible_name_lower in actual_col_lower or 
                        actual_col_lower in possible_name_lower or
                        len(set(possible_name_lower) & set(actual_col_lower)) / len(possible_name_lower) > 0.7):
                        column_mapping[actual_col] = standard_col
                        st.success(f"✅ 识别列名: {actual_col} -> {standard_col}")
                        found = True
                        break
                if found:
                    break
            
            if not found:
                st.warning(f"⚠️ 未识别到 {standard_col} 对应的列名")
        
        # 检查必要列是否都已识别
        required_columns = ['会员账号', '彩种', '期号', '玩法', '内容']
        missing_columns = [col for col in required_columns if col not in column_mapping.values()]
        
        if missing_columns:
            st.error(f"❌ 缺少必要列: {missing_columns}")
            return None
        
        return column_mapping
    
    def validate_data_quality(self, df):
        """数据质量验证"""
        logger.info("正在进行数据质量验证...")
        issues = []
        
        # 检查必要列
        required_cols = ['会员账号', '彩种', '期号', '玩法', '内容']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            issues.append(f"缺少必要列: {missing_cols}")
        
        # 检查空值
        for col in required_cols:
            if col in df.columns:
                null_count = df[col].isnull().sum()
                if null_count > 0:
                    issues.append(f"列 '{col}' 有 {null_count} 个空值")
        
        # 检查会员账号完整性
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
        
        # 检查期号格式
        if '期号' in df.columns:
            # 修复期号格式问题
            df['期号'] = df['期号'].astype(str).str.replace(r'\.0$', '', regex=True)
            invalid_periods = df[~df['期号'].str.match(r'^[\dA-Za-z]+$')]
            if len(invalid_periods) > 0:
                issues.append(f"发现 {len(invalid_periods)} 条无效期号记录")
        
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
    
    def normalize_play_category(self, play_method, lottery_category='six_mark'):
        """统一玩法分类 - 根据彩种类型，特别增强赛车玩法识别"""
        play_str = str(play_method).strip()
        
        # 直接映射
        if play_str in self.play_mapping:
            return self.play_mapping[play_str]
        
        # 关键词匹配
        for key, value in self.play_mapping.items():
            if key in play_str:
                return value
        
        # 根据彩种类型智能匹配
        play_lower = play_str.lower()
        config = self.get_lottery_config(lottery_category)
        
        if lottery_category == 'six_mark':
            if any(word in play_lower for word in ['特码', '特玛', '特马', '特碼']):
                return '特码'
        elif lottery_category == '10_number':
            # 增强赛车玩法识别
            if any(word in play_lower for word in ['定位胆', '一字定位', '一字', '定位', '大小单双', '龙虎']):
                return '定位胆'
            # 识别名次玩法（第一名到第十名）
            if re.search(r'第[一二三四五六七八九十]名', play_str) or re.search(r'第\d+名', play_str):
                return '定位胆'
        
        return play_str
    
    @lru_cache(maxsize=1000)
    def cached_extract_numbers(self, content, lottery_category='six_mark'):
        """带缓存的号码提取"""
        return self.enhanced_extract_numbers(content, lottery_category)
    
    def enhanced_extract_numbers(self, content, lottery_category='six_mark'):
        """增强号码提取 - 根据彩种类型调整，特别处理赛车格式"""
        content_str = str(content).strip()
        numbers = []
        
        try:
            config = self.get_lottery_config(lottery_category)
            number_range = config['number_range']
            
            # 特别处理赛车格式：02,09,04,10,07
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
        thresholds = COVERAGE_CONFIG['similarity_thresholds']
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

    def analyze_period_lottery(self, group, period, lottery, min_number_count, min_avg_amount):
        """分析特定期数和彩种 - 支持多种彩种"""
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
                numbers = self.cached_extract_numbers(row['内容'], lottery_category)
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
                'lottery_category': lottery_category,
                'total_combinations': total_combinations,
                'all_combinations': all_combinations,
                'filtered_accounts': len(filtered_account_numbers),
                'total_numbers': total_numbers
            }
        
        return None

    def analyze_with_progress(self, df_target, min_number_count, min_avg_amount):
        """带进度显示的分析"""
        grouped = df_target.groupby(['期号', '彩种'])
        all_period_results = {}
        
        total_groups = len(grouped)
        
        if total_groups == 0:
            return all_period_results
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, ((period, lottery), group) in enumerate(grouped):
            # 实时更新进度
            progress = (idx + 1) / total_groups
            progress_bar.progress(progress)
            status_text.text(f"分析进度: {idx+1}/{total_groups} - {period} ({lottery})")
            
            if len(group) >= 2:
                result = self.analyze_period_lottery(
                    group, period, lottery, min_number_count, min_avg_amount
                )
                if result:
                    all_period_results[(period, lottery)] = result
        
        progress_bar.empty()
        status_text.text("分析完成!")
        
        return all_period_results

    def display_enhanced_results(self, all_period_results):
        """增强结果展示 - 支持多种彩种"""
        if not all_period_results:
            st.info("🎉 未发现完美覆盖组合")
            return
        
        # 按账户聚合结果
        account_combinations = defaultdict(list)
        lottery_category_stats = defaultdict(lambda: {'periods': set(), 'combinations': 0})
        
        for (period, lottery), result in all_period_results.items():
            lottery_category = result['lottery_category']
            lottery_category_stats[lottery_category]['periods'].add(period)
            lottery_category_stats[lottery_category]['combinations'] += result['total_combinations']
            
            for combo in result['all_combinations']:
                for account in combo['accounts']:
                    account_combinations[account].append({
                        'period': period,
                        'lottery': lottery,
                        'lottery_category': lottery_category,
                        'combo_info': combo
                    })
        
        # 显示彩种类型统计
        st.subheader("🎲 彩种类型统计")
        col1, col2, col3, col4 = st.columns(4)
        
        category_display = {
            'six_mark': '六合彩',
            '10_number': '时时彩/PK10/赛车'
        }
        
        stats_items = list(lottery_category_stats.items())
        for i, (category, stats) in enumerate(stats_items):
            with [col1, col2, col3, col4][i % 4]:
                st.metric(
                    label=category_display.get(category, category),
                    value=f"{stats['combinations']}组",
                    delta=f"{len(stats['periods'])}期"
                )
        
        # 显示汇总统计
        st.subheader("📊 检测汇总")
        total_combinations = sum(result['total_combinations'] for result in all_period_results.values())
        total_filtered_accounts = sum(result['filtered_accounts'] for result in all_period_results.values())
        total_periods = len(all_period_results)
        total_lotteries = len(set(lottery for (_, lottery) in all_period_results.keys()))
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总完美组合数", total_combinations)
        with col2:
            st.metric("分析期数", total_periods)
        with col3:
            st.metric("有效账户数", total_filtered_accounts)
        with col4:
            st.metric("涉及彩种", total_lotteries)
        
        # 显示账户统计
        st.subheader("👥 参与账户统计")
        account_stats = []
        for account, combinations in account_combinations.items():
            account_stats.append({
                '账户': account,
                '参与组合数': len(combinations),
                '涉及期数': len(set(c['period'] for c in combinations)),
                '涉及彩种': len(set(c['lottery'] for c in combinations)),
                '彩种类型': ', '.join(sorted(set(category_display.get(c['lottery_category'], c['lottery_category']) for c in combinations)))
            })
        
        if account_stats:
            df_stats = pd.DataFrame(account_stats).sort_values('参与组合数', ascending=False)
            st.dataframe(df_stats, use_container_width=True, hide_index=True)
        
        # 按彩种和期号显示详细结果
        st.subheader("📈 详细组合分析")
        
        for (period, lottery), result in all_period_results.items():
            total_combinations = result['total_combinations']
            lottery_category = result['lottery_category']
            total_numbers = result['total_numbers']
            
            category_name = category_display.get(lottery_category, lottery_category)
            
            with st.expander(
                f"🎯 {category_name} - {lottery} 期号: {period}（{total_combinations}组，{total_numbers}个号码）", 
                expanded=True
            ):
                # 显示该期号的所有组合
                for idx, combo in enumerate(result['all_combinations'], 1):
                    accounts = combo['accounts']
                    
                    # 组合标题
                    if len(accounts) == 2:
                        st.markdown(f"**完美组合 {idx}:** {accounts[0]} ↔ {accounts[1]}")
                    else:
                        st.markdown(f"**完美组合 {idx}:** {' ↔ '.join(accounts)}")
                    
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
                    
                    # 各账户详情
                    st.write("**各账户详情:**")
                    for account in accounts:
                        amount_info = combo['individual_amounts'][account]
                        avg_info = combo['individual_avg_per_number'][account]
                        numbers = combo['bet_contents'][account]
                        numbers_count = len(numbers.split(', '))
                        
                        st.write(f"- **{account}**: {numbers_count}个数字")
                        st.write(f"  - 总投注: ¥{amount_info:,.2f}")
                        st.write(f"  - 平均每号: ¥{avg_info:,.2f}")
                        st.write(f"  - 投注内容: {numbers}")
                    
                    # 添加分隔线（除了最后一个）
                    if idx < len(result['all_combinations']):
                        st.markdown("---")

    def enhanced_export(self, all_period_results):
        """增强导出功能 - 支持多种彩种"""
        export_data = []
        
        category_display = {
            'six_mark': '六合彩',
            '10_number': '时时彩/PK10/赛车'
        }
        
        for (period, lottery), result in all_period_results.items():
            lottery_category = result['lottery_category']
            total_numbers = result['total_numbers']
            
            for combo in result['all_combinations']:
                # 基础信息
                export_record = {
                    '期号': period,
                    '彩种': lottery,
                    '彩种类型': category_display.get(lottery_category, lottery_category),
                    '号码总数': total_numbers,
                    '组合类型': f"{combo['account_count']}账户组合",
                    '账户组合': ' ↔ '.join(combo['accounts']),
                    '总投注金额': combo['total_amount'],
                    '平均每号金额': combo['avg_amount_per_number'],
                    '金额匹配度': f"{combo['similarity']:.1f}%",
                    '匹配度等级': combo['similarity_indicator']
                }
                
                # 各账户详情
                for i, account in enumerate(combo['accounts'], 1):
                    export_record[f'账户{i}'] = account
                    export_record[f'账户{i}总金额'] = combo['individual_amounts'][account]
                    export_record[f'账户{i}平均每号'] = combo['individual_avg_per_number'][account]
                    export_record[f'账户{i}号码数量'] = len(combo['bet_contents'][account].split(', '))
                    export_record[f'账户{i}投注内容'] = combo['bet_contents'][account]
                
                export_data.append(export_record)
        
        return pd.DataFrame(export_data)

# ==================== Streamlit界面 ====================
def main():
    st.title("🎯 彩票完美覆盖分析系统 - 全彩种增强版")
    st.markdown("### 支持六合彩、时时彩、PK10、赛车等多种彩票的智能对刷检测")
    
    analyzer = MultiLotteryCoverageAnalyzer()
    
    # 侧边栏设置 - 移除彩种选择，只保留自动识别
    st.sidebar.header("⚙️ 分析参数设置")
    
    # 使用统一的参数设置，不再区分彩种类型
    min_number_count = st.sidebar.number_input(
        "账户投注号码数量阈值", 
        min_value=1, 
        max_value=30, 
        value=3,
        help="只分析投注号码数量大于等于此值的账户"
    )
    
    min_avg_amount = st.sidebar.number_input(
        "平均每号金额阈值", 
        min_value=0.0, 
        max_value=10.0, 
        value=1.0,
        step=0.5,
        help="只分析平均每号金额大于等于此值的账户"
    )
    
    # 调试模式
    debug_mode = st.sidebar.checkbox("调试模式", value=False)
    
    st.sidebar.markdown("---")
    
    # 文件上传
    st.sidebar.header("📁 数据上传")
    uploaded_file = st.sidebar.file_uploader(
        "上传投注数据文件", 
        type=['csv', 'xlsx', 'xls'],
        help="请上传包含彩票投注数据的Excel或CSV文件"
    )
    
    if uploaded_file is not None:
        try:
            # 读取文件
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.success(f"✅ 成功读取文件，共 {len(df):,} 条记录")
            
            # 显示当前阈值设置
            st.info(f"📊 当前分析参数: 号码数量阈值 ≥ {min_number_count}, 平均金额阈值 ≥ {min_avg_amount}")
            
            # 增强版列名映射
            with st.spinner("正在进行列名识别..."):
                column_mapping = analyzer.enhanced_column_mapping(df)
            
            if column_mapping is None:
                st.error("❌ 列名映射失败，无法继续分析")
                return
            
            df = df.rename(columns=column_mapping)
            st.success("✅ 列名映射完成")

            # 数据质量验证
            with st.spinner("正在进行数据质量验证..."):
                quality_issues = analyzer.validate_data_quality(df)
            
            # 数据清理
            required_columns = ['会员账号', '彩种', '期号', '玩法', '内容']
            available_columns = [col for col in required_columns if col in df.columns]
            
            has_amount_column = '金额' in df.columns
            if has_amount_column:
                available_columns.append('金额')
                st.success("💰 检测到金额列，将进行金额分析")
            else:
                st.warning("⚠️ 未检测到金额列，将只分析号码覆盖")

            if len(available_columns) >= 5:
                df_clean = df[available_columns].copy()
                df_clean = df_clean.dropna(subset=required_columns)
                
                for col in available_columns:
                    df_clean[col] = df_clean[col].astype(str).str.strip()
                
                # 识别彩种类型并统一玩法分类
                with st.spinner("正在识别彩种类型和统一玩法分类..."):
                    df_clean['彩种类型'] = df_clean['彩种'].apply(analyzer.identify_lottery_category)
                    df_clean['玩法'] = df_clean.apply(
                        lambda row: analyzer.normalize_play_category(
                            row['玩法'], 
                            row['彩种类型'] if not pd.isna(row['彩种类型']) else 'six_mark'
                        ), 
                        axis=1
                    )
                
                if has_amount_column:
                    # 应用金额提取
                    with st.spinner("正在提取金额数据..."):
                        df_clean['投注金额'] = df_clean['金额'].apply(analyzer.cached_extract_amount)
                    
                    total_bet_amount = df_clean['投注金额'].sum()
                    valid_amount_count = (df_clean['投注金额'] > 0).sum()
                    
                    st.success(f"💰 金额提取完成: 总投注额 {total_bet_amount:,.2f} 元")
                    st.info(f"📊 有效金额记录: {valid_amount_count:,} / {len(df_clean):,}")

                # 显示数据预览
                with st.expander("📊 数据预览", expanded=False):
                    st.dataframe(df_clean.head(10))
                    st.write(f"数据形状: {df_clean.shape}")
                    
                    # 显示彩种类型分布
                    if '彩种类型' in df_clean.columns:
                        st.write("🎲 彩种类型分布:")
                        lottery_type_dist = df_clean['彩种类型'].value_counts()
                        display_dist = lottery_type_dist.rename({
                            'six_mark': '六合彩',
                            '10_number': '时时彩/PK10/赛车'
                        })
                        st.dataframe(display_dist.reset_index().rename(columns={'index': '彩种类型', '彩种类型': '数量'}))
                    
                    # 显示玩法分布
                    if '玩法' in df_clean.columns:
                        st.write("🎯 玩法分布:")
                        play_dist = df_clean['玩法'].value_counts()
                        st.dataframe(play_dist.reset_index().rename(columns={'index': '玩法', '玩法': '数量'}))
                    
                    # 显示金额分布
                    if has_amount_column:
                        st.write("💰 金额统计:")
                        st.write(f"- 总投注额: {total_bet_amount:,.2f} 元")
                        st.write(f"- 平均每注: {df_clean['投注金额'].mean():.2f} 元")
                        st.write(f"- 最大单注: {df_clean['投注金额'].max():.2f} 元")
                        st.write(f"- 最小单注: {df_clean['投注金额'].min():.2f} 元")

                # 筛选有效玩法数据
                valid_plays = ['特码', '定位胆']
                df_target = df_clean[df_clean['玩法'].isin(valid_plays)]
                
                # 筛选支持的彩种
                df_target = df_target[df_target['彩种类型'].notna()]
                
                st.write(f"✅ 有效玩法数据行数: {len(df_target):,}")

                if len(df_target) == 0:
                    st.error("❌ 未找到符合条件的有效玩法数据")
                    st.info("""
                    **可能原因:**
                    1. 彩种名称不匹配 - 当前支持的彩种类型:
                       - **六合彩**: 新澳门六合彩, 澳门六合彩, 香港六合彩等
                       - **时时彩/PK10/赛车**: 时时彩, PK10, 赛车, 幸运28等
                    
                    2. 玩法名称不匹配
                    3. 数据格式问题
                    """)
                    return

                # 分析数据 - 使用增强版分析
                with st.spinner("正在进行完美覆盖分析..."):
                    all_period_results = analyzer.analyze_with_progress(
                        df_target, min_number_count, min_avg_amount
                    )

                # 显示结果 - 使用增强版展示
                st.header("📊 完美覆盖组合检测结果")
                analyzer.display_enhanced_results(all_period_results)
                
                # 导出功能
                if all_period_results:
                    st.markdown("---")
                    st.subheader("📥 数据导出")
                    
                    if st.button("📊 生成完美组合数据报告"):
                        download_df = analyzer.enhanced_export(all_period_results)
                        
                        # 转换为Excel
                        output = BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            download_df.to_excel(writer, index=False, sheet_name='完美组合数据')
                            
                            # 添加统计工作表
                            account_stats = []
                            for (period, lottery), result in all_period_results.items():
                                for combo in result['all_combinations']:
                                    for account in combo['accounts']:
                                        account_stats.append({
                                            '账户': account,
                                            '期号': period,
                                            '彩种': lottery,
                                            '彩种类型': result['lottery_category'],
                                            '组合类型': f"{combo['account_count']}账户组合"
                                        })
                            
                            if account_stats:
                                df_account_stats = pd.DataFrame(account_stats)
                                df_account_stats.to_excel(writer, index=False, sheet_name='账户参与统计')
                        
                        # 提供下载
                        st.download_button(
                            label="📥 下载完整分析报告",
                            data=output.getvalue(),
                            file_name=f"全彩种完美组合分析报告_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        
                        st.success("✅ 数据导出准备完成！")
                
            else:
                st.error(f"❌ 缺少必要数据列，可用列: {available_columns}")
                st.info("💡 请确保文件包含以下必要列:")
                for col in ['会员账号', '彩种', '期号', '玩法', '内容']:
                    st.write(f"- {col}")
        
        except Exception as e:
            st.error(f"❌ 处理文件时出错: {str(e)}")
            if debug_mode:
                import traceback
                st.code(traceback.format_exc())
    
    else:
        st.info("💡 **彩票完美覆盖分析系统 - 全彩种增强版**")
        st.markdown("""
        ### 🚀 系统特色功能:

        **🎲 全彩种支持**
        - ✅ **六合彩**: 1-49个号码，特码玩法
        - ✅ **时时彩/PK10/赛车**: 1-10共10个号码，定位胆玩法  
        - 🔄 **自动识别**: 智能识别彩种类型

        **🔍 智能数据识别**
        - ✅ 增强列名识别：支持多种列名变体
        - 📊 数据质量验证：完整的数据检查流程
        - 🎯 玩法分类统一：智能识别各彩种玩法
        - 💰 金额提取优化：支持多种金额格式

        **⚡ 性能优化**
        - 🔄 缓存机制：号码和金额提取缓存
        - 📈 进度显示：实时分析进度
        - 🎨 界面优化：现代化Streamlit界面

        **📊 分析增强**
        - 👥 账户聚合视图：按账户统计参与情况
        - 📋 详细组合分析：完整的组合信息展示
        - 📊 汇总统计：多维度数据统计

        ### 🎯 各彩种分析原理:

        **六合彩 (49个号码)**
        - 检测同一期号内不同账户的投注号码是否形成完美覆盖（1-49全部覆盖）
        - 分析各账户的投注金额匹配度，识别可疑的协同投注行为

        **时时彩/PK10/赛车 (10个号码)**  
        - 检测定位胆玩法中，不同账户是否覆盖全部10个号码（1-10）
        - 识别对刷行为：多个账户合作覆盖所有号码

        ### 📝 支持的列名格式:
        """)
        
        for standard_col, possible_names in analyzer.column_mappings.items():
            st.write(f"- **{standard_col}**: {', '.join(possible_names[:3])}{'...' if len(possible_names) > 3 else ''}")
        
        st.markdown("""
        ### 🎯 数据要求:
        - ✅ 必须包含: 会员账号, 彩种, 期号, 玩法, 内容
        - ✅ 玩法必须为支持的类型
        - ✅ 彩种必须是支持的彩票类型
        - 💰 可选包含金额列进行深度分析
        """)

if __name__ == "__main__":
    main()
