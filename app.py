import pandas as pd
import numpy as np
import streamlit as st
import re
import io
import logging
from collections import defaultdict
from itertools import combinations
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('NumberCoverageDetector')

# Streamlit 页面配置
st.set_page_config(
    page_title="彩票号码覆盖检测系统",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 配置类 ====================
class CoverageConfig:
    def __init__(self):
        # 号码范围定义
        self.number_ranges = {
            'LHC': list(range(1, 50)),      # 六合彩: 1-49
            'K3': list(range(3, 19)),       # 快三和值: 3-18  
            'PK10': list(range(1, 11)),     # PK拾: 1-10
            'SSC': list(range(0, 10)),      # 时时彩: 0-9
            '3D': list(range(0, 10))        # 3D: 0-9
        }
        
        # 默认阈值配置
        self.default_thresholds = {
            'LHC': {'min_numbers': 11, 'min_amount_per_number': 10},
            'K3': {'min_numbers': 4, 'min_amount_per_number': 5},
            'PK10': {'min_numbers': 3, 'min_amount_per_number': 5},
            'SSC': {'min_numbers': 3, 'min_amount_per_number': 5},
            '3D': {'min_numbers': 3, 'min_amount_per_number': 5}
        }
        
        # 列名映射配置
        self.column_mappings = {
            '会员账号': ['会员账号', '会员账户', '账号', '账户', '用户账号', '玩家账号', '用户ID', '玩家ID'],
            '彩种': ['彩种', '彩神', '彩票种类', '游戏类型', '彩票类型', '游戏彩种', '彩票名称'],
            '期号': ['期号', '期数', '期次', '期', '奖期', '期号信息', '期号编号'],
            '玩法': ['玩法', '玩法分类', '投注类型', '类型', '投注玩法', '玩法类型', '分类'],
            '内容': ['内容', '投注内容', '下注内容', '注单内容', '投注号码', '号码内容', '投注信息'],
            '金额': ['金额', '下注总额', '投注金额', '总额', '下注金额', '投注额', '金额数值']
        }
        
        # 彩种关键词映射
        self.lottery_keywords = {
            'LHC': ['六合彩', 'lhc', '六合', '特码', '正码', '平特', '连肖', '港彩', '澳门六合彩'],
            'K3': ['快三', '快3', 'k3', '和值', '骰宝', '三军', '江苏快三', '安徽快三'],
            'PK10': ['pk10', 'pk拾', '飞艇', '赛车', '赛車', '幸运10', '北京赛车', '极速赛车', '幸运飞艇'],
            'SSC': ['时时彩', 'ssc', '分分彩', '重庆时时彩', '腾讯分分彩', '新疆时时彩', '天津时时彩'],
            '3D': ['3d', '福彩3d', '排列三', '排列3', 'p3', '排三', '排3']
        }
        
        # 位置名称映射
        self.position_mappings = {
            # 六合彩位置
            '特码': ['特码', '特肖', '正码特', '特码A', '特码B', '特码-特码'],
            '正码': ['正码', '正码1-6', '正码_正码', '正码-正码'],
            '正码1': ['正码1', '正一', '正码_正一', '正码-正一', '正码1码'],
            '正码2': ['正码2', '正二', '正码_正二', '正码-正二', '正码2码'],
            '正码3': ['正码3', '正三', '正码_正三', '正码-正三', '正码3码'],
            '正码4': ['正码4', '正四', '正码_正四', '正码-正四', '正码4码'],
            '正码5': ['正码5', '正五', '正码_正五', '正码-正五', '正码5码'],
            '正码6': ['正码6', '正六', '正码_正六', '正码-正六', '正码6码'],
            '正1特': ['正1特', '正一特', '正码特_正一特', '正码特-正一特'],
            '正2特': ['正2特', '正二特', '正码特_正二特', '正码特-正二特'],
            '正3特': ['正3特', '正三特', '正码特_正三特', '正码特-正三特'],
            '正4特': ['正4特', '正四特', '正码特_正四特', '正码特-正四特'],
            '正5特': ['正5特', '正五特', '正码特_正五特', '正码特-正五特'],
            '正6特': ['正6特', '正六特', '正码特_正六特', '正码特-正六特'],
            
            # PK拾位置
            '冠军': ['冠军', '第1名', '第一名', '前一', '冠 军', '冠　军'],
            '亚军': ['亚军', '第2名', '第二名', '前二', '亚 军', '亚　军'],
            '第三名': ['第三名', '第3名', '三名', '季军', '前三'],
            '第四名': ['第四名', '第4名'],
            '第五名': ['第五名', '第5名'],
            '第六名': ['第六名', '第6名'],
            '第七名': ['第七名', '第7名'],
            '第八名': ['第八名', '第8名'],
            '第九名': ['第九名', '第9名'],
            '第十名': ['第十名', '第10名'],
            '冠亚和': ['冠亚和', '冠亚和值', '冠亚和_和值'],
            
            # 时时彩位置
            '第1球': ['第1球', '万位', '第一位', '定位_万位', '万位定位'],
            '第2球': ['第2球', '千位', '第二位', '定位_千位', '千位定位'],
            '第3球': ['第3球', '百位', '第三位', '定位_百位', '百位定位'],
            '第4球': ['第4球', '十位', '第四位', '定位_十位', '十位定位'],
            '第5球': ['第5球', '个位', '第五位', '定位_个位', '个位定位'],
            
            # 3D位置
            '百位': ['百位', '定位_百位', '百位定位'],
            '十位': ['十位', '定位_十位', '十位定位'],
            '个位': ['个位', '定位_个位', '个位定位'],
            
            # 快三位置
            '和值': ['和值', '和值_大小单双', '点数', '总和']
        }

# ==================== 数据处理器 ====================
class DataProcessor:
    def __init__(self, config):
        self.config = config
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
                        
                        # 计算相似度
                        set1 = set(possible_name_lower)
                        set2 = set(actual_col_lower)
                        intersection = set1 & set2
                        
                        similarity_score = len(intersection) / len(set1) if set1 else 0
                        
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
    
    def find_data_start(self, df):
        """智能找到数据起始位置"""
        for row_idx in range(min(20, len(df))):
            for col_idx in range(min(10, len(df.columns))):
                cell_value = str(df.iloc[row_idx, col_idx])
                if pd.notna(cell_value) and any(keyword in cell_value for keyword in ['会员', '账号', '期号', '彩种', '玩法', '内容', '订单', '用户']):
                    return row_idx, col_idx
        return 0, 0
    
    def clean_data(self, uploaded_file):
        """数据清洗主函数"""
        try:
            # 读取文件进行初步分析
            df_temp = pd.read_excel(uploaded_file, header=None, nrows=50)
            st.info(f"原始数据维度: {df_temp.shape}")
            
            # 找到数据起始位置
            start_row, start_col = self.find_data_start(df_temp)
            st.info(f"数据起始位置: 第{start_row+1}行, 第{start_col+1}列")
            
            # 重新读取数据
            df_clean = pd.read_excel(
                uploaded_file, 
                header=start_row,
                skiprows=range(start_row + 1) if start_row > 0 else None,
                dtype=str,
                na_filter=False,
                keep_default_na=False
            )
            
            # 移除起始列之前的数据
            if start_col > 0:
                df_clean = df_clean.iloc[:, start_col:]
            
            st.info(f"清理后数据维度: {df_clean.shape}")
            
            # 智能列识别
            column_mapping = self.smart_column_identification(df_clean.columns)
            if column_mapping:
                df_clean = df_clean.rename(columns=column_mapping)
                st.success("✅ 列名识别完成!")
            
            # 检查必要列
            missing_columns = [col for col in self.required_columns if col not in df_clean.columns]
            if missing_columns:
                st.error(f"❌ 缺少必要列: {missing_columns}")
                return None
            
            # 数据清洗
            initial_count = len(df_clean)
            df_clean = df_clean.dropna(subset=self.required_columns)
            
            # 数据类型标准化
            for col in self.required_columns:
                if col in df_clean.columns:
                    df_clean[col] = df_clean[col].astype(str).str.strip()
            
            st.success(f"✅ 数据清洗完成: {initial_count} -> {len(df_clean)} 条记录")
            
            return df_clean
            
        except Exception as e:
            st.error(f"❌ 数据清洗失败: {str(e)}")
            logger.error(f"数据清洗失败: {str(e)}")
            return None

# ==================== 彩种识别器 ====================
class LotteryIdentifier:
    def __init__(self, config):
        self.config = config
    
    def identify_lottery_type(self, lottery_name):
        """彩种类型识别"""
        lottery_str = str(lottery_name).strip().lower()
        
        for lottery_type, keywords in self.config.lottery_keywords.items():
            for keyword in keywords:
                if keyword.lower() in lottery_str:
                    return lottery_type
        
        return '未知'

# ==================== 位置标准化器 ====================
class PositionNormalizer:
    def __init__(self, config):
        self.config = config
    
    def normalize_position(self, play_category):
        """统一位置名称"""
        play_str = str(play_category).strip()
        
        # 精确匹配
        for standard_pos, variants in self.config.position_mappings.items():
            for variant in variants:
                if variant == play_str:
                    return standard_pos
        
        # 包含匹配
        for standard_pos, variants in self.config.position_mappings.items():
            for variant in variants:
                if variant in play_str:
                    return standard_pos
        
        # 智能匹配
        play_lower = play_str.lower()
        
        # 六合彩智能匹配
        if any(word in play_lower for word in ['特码', '特肖']):
            return '特码'
        elif any(word in play_lower for word in ['正码1', '正一']):
            return '正码1'
        elif any(word in play_lower for word in ['正码2', '正二']):
            return '正码2'
        elif any(word in play_lower for word in ['正码3', '正三']):
            return '正码3'
        elif any(word in play_lower for word in ['正码4', '正四']):
            return '正码4'
        elif any(word in play_lower for word in ['正码5', '正五']):
            return '正码5'
        elif any(word in play_lower for word in ['正码6', '正六']):
            return '正码6'
        elif any(word in play_lower for word in ['正1特', '正一特']):
            return '正1特'
        elif any(word in play_lower for word in ['正2特', '正二特']):
            return '正2特'
        elif any(word in play_lower for word in ['正3特', '正三特']):
            return '正3特'
        elif any(word in play_lower for word in ['正4特', '正四特']):
            return '正4特'
        elif any(word in play_lower for word in ['正5特', '正五特']):
            return '正5特'
        elif any(word in play_lower for word in ['正6特', '正六特']):
            return '正6特'
        
        # PK10智能匹配
        elif any(word in play_lower for word in ['冠军', '第1名', '第一名']):
            return '冠军'
        elif any(word in play_lower for word in ['亚军', '第2名', '第二名']):
            return '亚军'
        elif any(word in play_lower for word in ['第三名', '第3名', '季军']):
            return '第三名'
        elif any(word in play_lower for word in ['冠亚和']):
            return '冠亚和'
        
        return play_str

# ==================== 内容解析器 ====================
class ContentParser:
    def __init__(self, config):
        self.config = config
    
    def extract_numbers(self, content_text):
        """从内容中提取号码"""
        try:
            if pd.isna(content_text):
                return []
            
            text = str(content_text).strip()
            
            # 🎯 处理 "特码-16,28" 这种格式
            if '-' in text:
                # 分割后取号码部分
                parts = text.split('-')
                if len(parts) > 1:
                    number_part = parts[-1]  # 取最后一个部分作为号码
                else:
                    number_part = text
            else:
                number_part = text
            
            numbers = []
            
            # 🎯 多种分隔符处理
            # 先按逗号分割
            if ',' in number_part:
                comma_parts = number_part.split(',')
                for part in comma_parts:
                    part_clean = part.strip()
                    # 处理每个部分中的数字
                    digits = re.findall(r'\d+', part_clean)
                    numbers.extend([int(d) for d in digits if 0 <= int(d) <= 49])  # 限制号码范围
            
            # 如果没有逗号，尝试其他分隔符
            elif ' ' in number_part:
                space_parts = number_part.split()
                for part in space_parts:
                    part_clean = part.strip()
                    if part_clean.isdigit() and 0 <= int(part_clean) <= 49:
                        numbers.append(int(part_clean))
            
            # 如果是单个数字
            elif number_part.isdigit() and 0 <= int(number_part) <= 49:
                numbers.append(int(number_part))
            
            # 🎯 最后尝试直接提取所有数字
            if not numbers:
                all_digits = re.findall(r'\d+', number_part)
                numbers = [int(d) for d in all_digits if 0 <= int(d) <= 49]
            
            # 去重并返回
            return list(set(numbers))
            
        except Exception as e:
            logger.warning(f"号码提取失败: {content_text}, 错误: {e}")
            return []
    
    def extract_amount(self, amount_text):
        """提取金额"""
        try:
            if pd.isna(amount_text):
                return 0
            
            text = str(amount_text).strip()
            
            # 🎯 处理 "投注：60,000 抵用；0 中奖：0.000" 格式
            if '投注：' in text:
                # 提取投注金额部分
                bet_match = re.search(r'投注：\s*([\d,]+\.?\d*)', text)
                if bet_match:
                    amount_str = bet_match.group(1).replace(',', '')
                    return float(amount_str)
            
            # 备用方案：提取第一个数字
            numbers = re.findall(r'\d+\.?\d*', text.replace(',', ''))
            if numbers:
                return float(numbers[0])
            
            return 0
        except Exception as e:
            logger.warning(f"金额提取失败: {amount_text}, 错误: {e}")
            return 0

# ==================== 号码覆盖检测器 ====================
class NumberCoverageDetector:
    def __init__(self, config):
        self.config = config
        self.data_processor = DataProcessor(config)
        self.lottery_identifier = LotteryIdentifier(config)
        self.position_normalizer = PositionNormalizer(config)
        self.content_parser = ContentParser(config)
        
        self.processed_data = None
        self.performance_stats = {}

    def process_uploaded_data(self, uploaded_file):
        """处理上传的数据"""
        try:
            # 数据清洗
            df_clean = self.data_processor.clean_data(uploaded_file)
            if df_clean is None:
                return None
            
            # 彩种识别
            df_clean['彩种类型'] = df_clean['彩种'].apply(self.lottery_identifier.identify_lottery_type)
            
            # 位置标准化
            df_clean['标准位置'] = df_clean['玩法'].apply(self.position_normalizer.normalize_position)
            
            # 提取号码和金额
            st.info("🔢 正在提取号码和金额...")
            progress_bar = st.progress(0)
            total_rows = len(df_clean)
            
            # 分批处理显示进度
            batch_size = 1000
            numbers_list = []
            amounts_list = []
            
            for i in range(0, total_rows, batch_size):
                end_idx = min(i + batch_size, total_rows)
                batch_df = df_clean.iloc[i:end_idx]
                
                # 提取号码
                batch_numbers = batch_df['内容'].apply(self.content_parser.extract_numbers)
                numbers_list.extend(batch_numbers)
                
                # 提取金额
                batch_amounts = batch_df['金额'].apply(self.content_parser.extract_amount)
                amounts_list.extend(batch_amounts)
                
                # 更新进度
                progress = (end_idx) / total_rows
                progress_bar.progress(progress)
            
            progress_bar.empty()
            
            df_clean['投注号码'] = numbers_list
            df_clean['投注金额'] = amounts_list
            df_clean['号码数量'] = df_clean['投注号码'].apply(len)
            
            self.processed_data = df_clean
            
            # 显示处理结果
            st.success("✅ 数据预处理完成")
            with st.expander("📋 处理结果样本", expanded=False):
                sample_cols = ['会员账号', '彩种', '期号', '玩法', '标准位置', '内容', '投注号码', '投注金额', '号码数量']
                display_cols = [col for col in sample_cols if col in df_clean.columns]
                st.dataframe(df_clean[display_cols].head(10))
            
            return df_clean
            
        except Exception as e:
            st.error(f"❌ 数据处理失败: {str(e)}")
            return None

    def detect_coverage_patterns(self, df, thresholds):
        """检测号码覆盖模式"""
        try:
            # 过滤有效记录
            df_valid = self.filter_valid_records(df, thresholds)
            
            if len(df_valid) == 0:
                st.warning("⚠️ 没有符合条件的有效记录")
                return []
            
            st.info(f"📊 有效记录数: {len(df_valid)}")
            
            # 按位置分组检测
            all_patterns = []
            grouped = df_valid.groupby(['期号', '彩种类型', '标准位置'])
            
            total_groups = len(grouped)
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, ((period, lottery, position), group) in enumerate(grouped):
                status_text.text(f"🔍 分析 {lottery} - {position}... ({i+1}/{total_groups})")
                
                # 获取该位置的全集号码
                full_set = self.get_full_number_set(lottery, position)
                if not full_set:
                    continue
                
                # 检测2-4个账户的组合
                for account_count in [2, 3, 4]:
                    patterns = self.find_coverage_combinations(
                        group, full_set, account_count, period, lottery, position
                    )
                    all_patterns.extend(patterns)
                
                progress_bar.progress((i + 1) / total_groups)
            
            progress_bar.empty()
            status_text.empty()
            
            return all_patterns
            
        except Exception as e:
            st.error(f"❌ 检测失败: {str(e)}")
            return []

    def filter_valid_records(self, df, thresholds):
        """根据阈值过滤有效记录"""
        valid_rows = []
        
        for _, row in df.iterrows():
            lottery = row.get('彩种类型', '未知')
            numbers = row.get('投注号码', [])
            amount = row.get('投注金额', 0)
            number_count = len(numbers)
            
            # 跳过未知彩种
            if lottery not in thresholds:
                continue
            
            # 获取阈值
            min_numbers = thresholds[lottery]['min_numbers']
            min_amount = thresholds[lottery]['min_amount_per_number']
            
            # 计算平均每号金额
            if number_count > 0:
                avg_amount = amount / number_count
            else:
                avg_amount = 0
            
            # 应用阈值过滤
            if number_count >= min_numbers and avg_amount >= min_amount:
                valid_rows.append(row)
        
        result_df = pd.DataFrame(valid_rows)
        st.info(f"📊 阈值过滤: {len(df)} → {len(result_df)} 条记录")
        return result_df

    def get_full_number_set(self, lottery, position):
        """获取完整的号码集合"""
        if lottery not in self.config.number_ranges:
            return None
        
        base_numbers = set(self.config.number_ranges[lottery])
        
        # 特殊处理冠亚和
        if position == '冠亚和' and lottery == 'PK10':
            return set(range(3, 20))
        
        return base_numbers

    def find_coverage_combinations(self, group_data, full_set, account_count, period, lottery, position):
        """查找号码覆盖组合"""
        patterns = []
        
        # 构建账户数据
        account_data = {}
        for _, row in group_data.iterrows():
            account = row['会员账号']
            numbers = set(row['投注号码'])
            amount = row['投注金额']
            
            if not numbers:  # 跳过没有号码的记录
                continue
                
            if account not in account_data:
                account_data[account] = {
                    'numbers': set(),
                    'total_amount': 0
                }
            
            account_data[account]['numbers'] |= numbers
            account_data[account]['total_amount'] += amount
        
        # 检查所有账户组合
        accounts = list(account_data.keys())
        if len(accounts) < account_count:
            return patterns
        
        for account_group in combinations(accounts, account_count):
            # 检查是否完美覆盖
            if self.check_perfect_coverage(account_group, account_data, full_set):
                pattern = self.analyze_coverage_pattern(
                    account_group, account_data, full_set, period, lottery, position, account_count
                )
                if pattern:
                    patterns.append(pattern)
        
        return patterns

    def check_perfect_coverage(self, account_group, account_data, full_set):
        """检查是否完美覆盖"""
        try:
            # 检查并集是否等于全集
            union_numbers = set()
            for account in account_group:
                union_numbers |= account_data[account]['numbers']
            
            if union_numbers != full_set:
                return False
            
            # 检查号码是否不重叠
            for i in range(len(account_group)):
                for j in range(i + 1, len(account_group)):
                    set1 = account_data[account_group[i]]['numbers']
                    set2 = account_data[account_group[j]]['numbers']
                    if set1 & set2:  # 有交集
                        return False
            
            return True
            
        except:
            return False

    def analyze_coverage_pattern(self, account_group, account_data, full_set, period, lottery, position, account_count):
        """分析覆盖模式"""
        try:
            coverage_details = []
            avg_amounts = []
            
            for account in account_group:
                data = account_data[account]
                numbers = data['numbers']
                total_amount = data['total_amount']
                number_count = len(numbers)
                
                if number_count > 0:
                    avg_amount = total_amount / number_count
                else:
                    avg_amount = 0
                
                avg_amounts.append(avg_amount)
                coverage_details.append({
                    '账户': account,
                    '号码数量': number_count,
                    '总金额': total_amount,
                    '平均每号金额': avg_amount,
                    '具体号码': sorted(list(numbers))
                })
            
            # 计算金额相似度
            if avg_amounts and max(avg_amounts) > 0:
                similarity = min(avg_amounts) / max(avg_amounts)
            else:
                similarity = 0
            
            # 确定相似度等级
            similarity_level = self.get_similarity_level(similarity)
            
            return {
                '期号': period,
                '彩种': lottery,
                '位置': position,
                '账户组': list(account_group),
                '账户数量': account_count,
                '全集大小': len(full_set),
                '全集号码': sorted(list(full_set)),
                '覆盖详情': coverage_details,
                '金额相似度': similarity,
                '相似度等级': similarity_level,
                '总投注金额': sum(account_data[account]['total_amount'] for account in account_group)
            }
            
        except Exception as e:
            logger.warning(f"模式分析失败: {e}")
            return None

    def get_similarity_level(self, similarity_score):
        """获取相似度等级"""
        if similarity_score >= 0.9:
            return "🟢 优秀"
        elif similarity_score >= 0.8:
            return "🟡 良好" 
        elif similarity_score >= 0.7:
            return "🟠 一般"
        else:
            return "🔴 较差"

    def display_detailed_results(self, patterns):
        """显示详细检测结果"""
        if not patterns:
            st.error("❌ 未发现符合条件的号码覆盖模式")
            return
    
        # ========== 显示总体统计 ==========
        st.subheader("📊 总体统计")
        
        total_groups = len(patterns)
        total_accounts = sum(p['账户数量'] for p in patterns)
        total_amount = sum(p['总投注金额'] for p in patterns)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总覆盖组数", total_groups)
        with col2:
            st.metric("涉及账户数", total_accounts)
        with col3:
            st.metric("总投注金额", f"¥{total_amount:,.2f}")
        with col4:
            avg_similarity = np.mean([p['金额相似度'] for p in patterns])
            st.metric("平均相似度", f"{avg_similarity:.1%}")
        
        # ========== 彩种类型统计 ==========
        st.subheader("🎲 彩种类型统计")
        
        lottery_stats = defaultdict(lambda: {'count': 0, 'amount': 0})
        for pattern in patterns:
            lottery = pattern['彩种']
            lottery_stats[lottery]['count'] += 1
            lottery_stats[lottery]['amount'] += pattern['总投注金额']
        
        # 创建彩种统计列
        lottery_cols = st.columns(min(5, len(lottery_stats)))
        for i, (lottery, stats) in enumerate(lottery_stats.items()):
            if i < len(lottery_cols):
                with lottery_cols[i]:
                    st.metric(
                        label=lottery,
                        value=f"{stats['count']}组",
                        delta=f"¥{stats['amount']:,.0f}"
                    )
        
        # ========== 详细对刷组分析 ==========
        st.subheader("🔍 详细覆盖模式分析")
        
        patterns_by_lottery = defaultdict(list)
        for pattern in patterns:
            lottery_key = pattern['彩种']
            patterns_by_lottery[lottery_key].append(pattern)
        
        for lottery, lottery_patterns in patterns_by_lottery.items():
            with st.expander(f"🎲 彩种：{lottery}（发现{len(lottery_patterns)}组）", expanded=True):
                for i, pattern in enumerate(lottery_patterns, 1):
                    st.markdown(f"**覆盖组 {i}:** {' ↔ '.join(pattern['账户组'])}")
                    
                    st.markdown(f"**基本信息:**")
                    st.markdown(f"- **位置:** {pattern['位置']} | **期号:** {pattern['期号']}")
                    st.markdown(f"- **账户数量:** {pattern['账户数量']}个 | **全集大小:** {pattern['全集大小']}个号码")
                    st.markdown(f"- **总投注金额:** ¥{pattern['总投注金额']:,.2f}")
                    st.markdown(f"- **金额相似度:** {pattern['金额相似度']:.1%} ({pattern['相似度等级']})")
                    
                    st.markdown("**账户详情:**")
                    for coverage in pattern['覆盖详情']:
                        st.markdown(f"- **{coverage['账户']}**: "
                                  f"{coverage['号码数量']}个号码, "
                                  f"总金额¥{coverage['总金额']:,.2f}, "
                                  f"平均每号¥{coverage['平均每号金额']:,.2f}")
                        st.markdown(f"  投注号码: {coverage['具体号码']}")
                    
                    st.markdown(f"**全集号码:** {pattern['全集号码']}")
                    
                    if i < len(lottery_patterns):
                        st.markdown("---")

# ==================== 主函数 ====================
def main():
    """主函数"""
    st.title("🎯 彩票号码覆盖检测系统")
    st.markdown("---")
    
    # 初始化配置和检测器
    config = CoverageConfig()
    detector = NumberCoverageDetector(config)
    
    with st.sidebar:
        st.header("📁 数据上传")
        uploaded_file = st.file_uploader(
            "上传投注数据文件", 
            type=['xlsx', 'xls'],
            help="请上传包含彩票投注数据的Excel文件"
        )
        
        st.header("⚙️ 检测参数设置")
        
        # 各彩种阈值设置
        thresholds = {}
        for lottery in ['LHC', 'K3', 'PK10', 'SSC', '3D']:
            st.subheader(f"{lottery} 阈值设置")
            
            min_numbers = st.number_input(
                f"{lottery}最小号码数", 
                min_value=1, 
                max_value=50,
                value=config.default_thresholds[lottery]['min_numbers'],
                key=f"min_num_{lottery}"
            )
            
            min_amount = st.number_input(
                f"{lottery}最低每号金额", 
                min_value=1, 
                max_value=20,
                value=config.default_thresholds[lottery]['min_amount_per_number'],
                key=f"min_amt_{lottery}"
            )
            
            thresholds[lottery] = {
                'min_numbers': min_numbers,
                'min_amount_per_number': min_amount
            }
    
    if uploaded_file is not None:
        try:
            st.success(f"✅ 已上传文件: {uploaded_file.name}")
            
            # 处理数据
            with st.spinner("🔄 正在处理数据..."):
                processed_data = detector.process_uploaded_data(uploaded_file)
            
            if processed_data is not None and len(processed_data) > 0:
                # 显示数据概览
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("总记录数", f"{len(processed_data):,}")
                with col2:
                    st.metric("唯一期号", f"{processed_data['期号'].nunique():,}")
                with col3:
                    st.metric("唯一账户", f"{processed_data['会员账号'].nunique():,}")
                with col4:
                    st.metric("彩种类型", f"{processed_data['彩种类型'].nunique()}")
                
                # 开始检测
                st.info("🚀 开始检测号码覆盖模式...")
                with st.spinner("🔍 正在检测号码覆盖模式..."):
                    patterns = detector.detect_coverage_patterns(processed_data, thresholds)
                
                if patterns:
                    st.success(f"✅ 检测完成！发现 {len(patterns)} 个覆盖模式")
                    detector.display_detailed_results(patterns)
                    
                    # 导出功能
                    st.subheader("📤 结果导出")
                    if st.button("生成检测报告"):
                        report_data = []
                        for pattern in patterns:
                            for detail in pattern['覆盖详情']:
                                report_data.append({
                                    '期号': pattern['期号'],
                                    '彩种': pattern['彩种'],
                                    '位置': pattern['位置'],
                                    '账户': detail['账户'],
                                    '号码数量': detail['号码数量'],
                                    '总金额': detail['总金额'],
                                    '平均每号金额': detail['平均每号金额'],
                                    '投注号码': str(detail['具体号码']),
                                    '全集号码': str(pattern['全集号码']),
                                    '金额相似度': pattern['金额相似度'],
                                    '相似度等级': pattern['相似度等级'],
                                    '账户组': str(pattern['账户组'])
                                })
                        
                        report_df = pd.DataFrame(report_data)
                        
                        # 生成Excel文件
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            report_df.to_excel(writer, sheet_name='检测结果', index=False)
                        
                        st.download_button(
                            label="📥 下载检测报告",
                            data=output.getvalue(),
                            file_name=f"号码覆盖检测报告_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.xlsx",
                            mime="application/vnd.ms-excel"
                        )
                else:
                    st.warning("⚠️ 未发现符合条件的号码覆盖模式")
            else:
                st.error("❌ 数据处理失败")
                
        except Exception as e:
            st.error(f"❌ 程序执行失败: {str(e)}")
    else:
        # 系统介绍
        show_system_introduction()

def show_system_introduction():
    """显示系统介绍"""
    st.info("👈 请在左侧上传Excel文件开始分析")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎯 系统功能")
        st.markdown("""
        **支持的彩种:**
        - 🎲 六合彩: 1-49个号码
        - 🎯 快三和值: 3-18个和值  
        - 🚗 PK拾: 1-10个号码
        - ⏰ 时时彩: 0-9个号码
        - 🔢 3D: 0-9个号码
        
        **检测能力:**
        - 2个账户完美互补覆盖
        - 3个账户三方互补覆盖
        - 4个账户四方互补覆盖
        - 自动计算金额相似度
        - 智能列名识别
        """)
    
    with col2:
        st.subheader("📊 相似度标准")
        st.markdown("""
        **金额相似度等级:**
        - 🟢 优秀: 90%及以上
        - 🟡 良好: 80%-89%  
        - 🟠 一般: 70%-79%
        - 🔴 较差: 70%以下
        
        **默认阈值:**
        - 六合彩: ≥11号码, ≥10元/号
        - 和值类: ≥4号码, ≥5元/号
        - 定位类: ≥3号码, ≥5元/号
        """)
    
    with st.expander("📖 使用说明", expanded=True):
        st.markdown("""
        ### 使用步骤
        
        1. **准备数据**: 确保Excel文件包含投注数据
        2. **上传文件**: 在左侧边栏选择Excel文件
        3. **设置参数**: 调整各彩种的检测阈值
        4. **开始检测**: 系统自动分析号码覆盖情况
        5. **查看结果**: 浏览检测到的覆盖模式
        6. **导出报告**: 下载详细的检测结果
        
        ### 检测原理
        
        系统会检查同一期号、同一彩种、同一位置的多个账户投注是否满足：
        - 所有账户投注的号码合并后正好是该位置的全部号码
        - 各个账户投注的号码没有重复
        - 每个账户的投注金额满足阈值要求
        
        这样的模式表明可能存在协调性的对刷行为。
        
        ### 技术支持
        
        系统采用模块化设计，包含：
        - 数据处理器: 智能列识别和数据清洗
        - 彩种识别器: 自动识别彩种类型
        - 位置标准化器: 统一位置名称
        - 内容解析器: 精确提取号码和金额
        - 覆盖检测器: 核心检测算法
        """)

if __name__ == "__main__":
    main()
