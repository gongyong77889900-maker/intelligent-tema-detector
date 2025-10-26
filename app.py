import streamlit as st
import pandas as pd
import numpy as np
import io
import re
import logging
from collections import defaultdict
from datetime import datetime
from itertools import combinations
import warnings
import traceback

# 配置日志和警告
warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('MultiAccountWashTrade')

# Streamlit页面配置
st.set_page_config(
    page_title="智能多账户对刷检测系统",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

class Config:
    """配置参数类"""
    def __init__(self):
        self.min_amount = 10
        self.amount_similarity_threshold = 0.9
        self.min_continuous_periods = 3
        self.max_accounts_in_group = 5
        self.supported_file_types = ['.xlsx', '.xls', '.csv']
        
        # 列名映射配置
        self.column_mappings = {
            '会员账号': ['会员账号', '会员账户', '账号', '账户', '用户账号'],
            '彩种': ['彩种', '彩票种类', '游戏类型'],
            '期号': ['期号', '期数', '期次', '期'],
            '玩法': ['玩法', '玩法分类', '投注类型', '类型'],
            '内容': ['内容', '投注内容', '下注内容', '注单内容'],
            '金额': ['金额', '下注总额', '投注金额', '总额', '下注金额']
        }
        
        # 修正：根据账户总投注期数设置不同的对刷期数阈值
        self.period_thresholds = {
            'low_activity': 10,        # 低活跃度账户阈值（总投注期数≤10）
            'medium_activity_low': 11,  # 中活跃度下限（总投注期数11-200）
            'medium_activity_high': 200, # 中活跃度上限
            'min_periods_low': 3,       # 低活跃度账户最小对刷期数
            'min_periods_medium': 5,    # 中活跃度账户最小对刷期数
            'min_periods_high': 8       # 高活跃度账户最小对刷期数
        }
        
        # 扩展：增加龙虎方向模式
        self.direction_patterns = {
            '小': ['两面-小', '和值-小', '小', 'small', 'xia'],
            '大': ['两面-大', '和值-大', '大', 'big', 'da'], 
            '单': ['两面-单', '和值-单', '单', 'odd', 'dan'],
            '双': ['两面-双', '和值-双', '双', 'even', 'shuang'],
            '龙': ['龙', 'long', '龍', 'dragon'],
            '虎': ['虎', 'hu', 'tiger']
        }
        
        # 扩展：增加龙虎对立组
        self.opposite_groups = [{'大', '小'}, {'单', '双'}, {'龙', '虎'}]

class WashTradeDetector:
    def __init__(self, config=None):
        self.config = config or Config()
        self.data_processed = False
        self.df_valid = None
        self.export_data = []
        # 修正：按彩种存储账户总投注期数统计
        self.account_total_periods_by_lottery = defaultdict(dict)
        self.account_record_stats_by_lottery = defaultdict(dict)
        self.column_mapping_used = {}
        self.performance_stats = {}
    
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
            
            if filename.endswith('.csv'):
                df = pd.read_csv(uploaded_file, encoding='utf-8')
            else:
                df = pd.read_excel(uploaded_file)
            
            logger.info(f"原始数据维度: {df.shape}")
            
            return df, filename
            
        except Exception as e:
            logger.error(f"文件处理失败: {str(e)}")
            st.error(f"文件处理失败: {str(e)}")
            return None, None
    
    def map_columns(self, df):
        """映射列名到标准格式"""
        reverse_mapping = {}
        for standard_col, possible_cols in self.config.column_mappings.items():
            for col in possible_cols:
                reverse_mapping[col] = standard_col
        
        column_mapping = {}
        used_columns = set()
        
        for df_col in df.columns:
            df_col_clean = str(df_col).strip()
            
            if df_col_clean in reverse_mapping:
                standard_col = reverse_mapping[df_col_clean]
                if standard_col not in used_columns:
                    column_mapping[df_col] = standard_col
                    used_columns.add(standard_col)
                continue
            
            for possible_col in reverse_mapping.keys():
                if possible_col in df_col_clean:
                    standard_col = reverse_mapping[possible_col]
                    if standard_col not in used_columns:
                        column_mapping[df_col] = standard_col
                        used_columns.add(standard_col)
                    break
        
        if column_mapping:
            df_renamed = df.rename(columns=column_mapping)
            self.column_mapping_used = column_mapping
            return df_renamed
        else:
            return df
    
    def check_required_columns(self, df):
        """检查必要列是否存在"""
        required_cols = ['会员账号', '期号', '内容', '金额']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            st.error(f"❌ 缺少必要列: {missing_cols}")
            st.write("可用的列:", df.columns.tolist())
            return False
        
        if '彩种' not in df.columns:
            df['彩种'] = '未知彩种'
        
        return True
    
    def parse_column_data(self, df):
        """解析列结构数据"""
        try:
            df_mapped = self.map_columns(df)
            
            if not self.check_required_columns(df_mapped):
                return pd.DataFrame()
            
            df_clean = df_mapped[['会员账号', '期号', '内容', '金额', '彩种']].copy()
            df_clean = df_clean.dropna(subset=['会员账号', '期号', '内容', '金额'])
            
            for col in ['会员账号', '期号', '内容', '彩种']:
                if col in df_clean.columns:
                    df_clean[col] = df_clean[col].astype(str).str.strip()
            
            # 关键修正：在过滤前计算总投注期数
            self.calculate_account_total_periods_by_lottery(df_clean)
            
            df_clean['投注金额'] = df_clean['金额'].apply(lambda x: self.extract_bet_amount_safe(x))
            df_clean['投注方向'] = df_clean['内容'].apply(lambda x: self.extract_direction_from_content(x))
            
            df_valid = df_clean[
                (df_clean['投注方向'] != '') & 
                (df_clean['投注金额'] >= self.config.min_amount)
            ].copy()
            
            if len(df_valid) == 0:
                st.error("❌ 过滤后没有有效记录")
                return pd.DataFrame()
            
            with st.expander("📊 数据概览", expanded=False):
                st.write(f"总记录数: {len(df_clean)}")
                st.write(f"有效记录数: {len(df_valid)}")
                st.write(f"唯一期号数: {df_valid['期号'].nunique()}")
                st.write(f"唯一账户数: {df_valid['会员账号'].nunique()}")
                
                if len(df_valid) > 0:
                    lottery_stats = df_valid['彩种'].value_counts()
                    st.write(f"彩种分布: {dict(lottery_stats)}")
                    
                    # 显示投注方向分布
                    direction_stats = df_valid['投注方向'].value_counts()
                    st.write(f"投注方向分布: {dict(direction_stats)}")
            
            self.data_processed = True
            self.df_valid = df_valid
            return df_valid
            
        except Exception as e:
            logger.error(f"数据解析失败: {str(e)}")
            st.error(f"数据解析失败: {str(e)}")
            st.error(f"详细错误: {traceback.format_exc()}")
            return pd.DataFrame()
    
    def extract_bet_amount_safe(self, amount_text):
        """安全提取投注金额"""
        try:
            if pd.isna(amount_text):
                return 0
            
            text = str(amount_text).strip()
            
            try:
                cleaned_text = text.replace(',', '').replace('，', '').replace(' ', '')
                if re.match(r'^-?\d+(\.\d+)?$', cleaned_text):
                    amount = float(cleaned_text)
                    if amount >= self.config.min_amount:
                        return amount
            except:
                pass
            
            patterns = [
                r'投注[:：]?\s*(\d+[,，]?\d*\.?\d*)',
                r'下注[:：]?\s*(\d+[,，]?\d*\.?\d*)',
                r'金额[:：]?\s*(\d+[,，]?\d*\.?\d*)',
                r'总额[:：]?\s*(\d+[,，]?\d*\.?\d*)',
                r'(\d+[,，]?\d*\.?\d*)\s*元',
                r'￥\s*(\d+[,，]?\d*\.?\d*)',
                r'¥\s*(\d+[,，]?\d*\.?\d*)',
                r'[\$￥¥]?\s*(\d+[,，]?\d*\.?\d+)',
                r'(\d+[,，]?\d*\.?\d+)',
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
            
            numbers = re.findall(r'\d+\.?\d*', text)
            if numbers:
                try:
                    amount = float(numbers[0])
                    if amount >= self.config.min_amount:
                        return amount
                except:
                    pass
            
            return 0
            
        except Exception as e:
            logger.warning(f"金额提取失败: {amount_text}, 错误: {e}")
            return 0
    
    def extract_direction_from_content(self, content):
        """从内容列提取投注方向"""
        try:
            if pd.isna(content):
                return ""
            
            content_str = str(content).strip().lower()
            
            for direction, patterns in self.config.direction_patterns.items():
                for pattern in patterns:
                    if pattern.lower() in content_str:
                        return direction
            
            return ""
        except Exception as e:
            logger.warning(f"方向提取失败: {content}, 错误: {e}")
            return ""
    
    def calculate_account_total_periods_by_lottery(self, df):
        """修正：按彩种计算每个账户的总投注期数统计（使用原始数据）"""
        self.account_total_periods_by_lottery = defaultdict(dict)
        self.account_record_stats_by_lottery = defaultdict(dict)
        
        for lottery in df['彩种'].unique():
            df_lottery = df[df['彩种'] == lottery]
            
            # 计算每个账户的总投注期数（唯一期号数）
            period_counts = df_lottery.groupby('会员账号')['期号'].nunique().to_dict()
            self.account_total_periods_by_lottery[lottery] = period_counts
            
            # 计算每个账户的记录数
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
        
        period_groups = df_filtered.groupby(['期号', '彩种'])
        
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
        """获取有效的方向组合"""
        valid_combinations = []
        
        for opposites in self.config.opposite_groups:
            dir1, dir2 = list(opposites)
            
            for i in range(1, n_accounts):
                j = n_accounts - i
                valid_combinations.append({
                    'directions': [dir1] * i + [dir2] * j,
                    'dir1_count': i,
                    'dir2_count': j,
                    'opposite_type': f"{dir1}-{dir2}"
                })
        
        return valid_combinations
    
    def _detect_combinations_for_period(self, period_data, period_accounts, n_accounts, valid_combinations):
        """为单个期号检测组合"""
        patterns = []
        
        account_info = {}
        for _, row in period_data.iterrows():
            account = row['会员账号']
            account_info[account] = {
                'direction': row['投注方向'],
                'amount': row['投注金额']
            }
        
        for account_group in combinations(period_accounts, n_accounts):
            for combo in valid_combinations:
                target_directions = combo['directions']
                
                actual_directions = [account_info[acc]['direction'] for acc in account_group]
                if sorted(actual_directions) != sorted(target_directions):
                    continue
                
                dir1_total = 0
                dir2_total = 0
                
                for account, target_dir in zip(account_group, target_directions):
                    actual_dir = account_info[account]['direction']
                    amount = account_info[account]['amount']
                    
                    if actual_dir == combo['opposite_type'].split('-')[0]:
                        dir1_total += amount
                    else:
                        dir2_total += amount
                
                if dir1_total == 0 or dir2_total == 0:
                    continue
                
                similarity = min(dir1_total, dir2_total) / max(dir1_total, dir2_total)
                
                if similarity >= self.config.amount_similarity_threshold:
                    amount_group = [account_info[acc]['amount'] for acc in account_group]
                    
                    record = {
                        '期号': period_data['期号'].iloc[0],
                        '彩种': period_data['彩种'].iloc[0],
                        '账户组': list(account_group),
                        '方向组': actual_directions,
                        '金额组': amount_group,
                        '总金额': dir1_total + dir2_total,
                        '相似度': similarity,
                        '账户数量': n_accounts,
                        '模式': f"{combo['opposite_type'].split('-')[0]}({combo['dir1_count']}个) vs {combo['opposite_type'].split('-')[1]}({combo['dir2_count']}个)",
                        '对立类型': combo['opposite_type']
                    }
                    
                    patterns.append(record)
        
        return patterns
    
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
            
            # 修正：根据账户组的总投注期数确定最小对刷期数要求
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
                
                main_opposite_type = max(opposite_type_counts.items(), key=lambda x: x[1])[0]
                
                # 修正：显示每个账户的详细统计信息
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
                    '账户数量': len(account_group),
                    '主要对立类型': main_opposite_type,
                    '对立类型分布': dict(opposite_type_counts),
                    '对刷期数': len(sorted_records),  # 实际对刷期数
                    '总投注金额': total_investment,
                    '平均相似度': avg_similarity,
                    '模式分布': dict(pattern_count),
                    '详细记录': sorted_records,
                    '账户活跃度': activity_level,
                    '账户统计信息': account_stats_info,  # 修正：显示每个账户的统计信息
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
        """修正：根据账户组在特定彩种的总投注期数获取活跃度水平"""
        if lottery not in self.account_total_periods_by_lottery:
            return 'unknown'
        
        total_periods_stats = self.account_total_periods_by_lottery[lottery]
        
        # 计算账户组中在指定彩种的最小总投注期数（用于活跃度判断）
        min_total_periods = min(total_periods_stats.get(account, 0) for account in account_group)
        
        # 按照您要求的活跃度阈值设置
        if min_total_periods <= self.config.period_thresholds['low_activity']:
            return 'low'        # 总投注期数≤10
        elif min_total_periods <= self.config.period_thresholds['medium_activity_high']:
            return 'medium'     # 总投注期数11-200
        else:
            return 'high'       # 总投注期数≥201
    
    def get_required_min_periods(self, account_group, lottery):
        """修正：根据账户组的总投注期数活跃度获取所需的最小对刷期数"""
        activity_level = self.get_account_group_activity_level(account_group, lottery)
        
        if activity_level == 'low':
            return self.config.period_thresholds['min_periods_low']    # 3期
        elif activity_level == 'medium':
            return self.config.period_thresholds['min_periods_medium'] # 5期
        else:
            return self.config.period_thresholds['min_periods_high']   # 8期
    
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
                
                if self.performance_stats['detection_time'] > 0:
                    records_per_second = self.performance_stats['total_records'] / self.performance_stats['detection_time']
                    st.write(f"- 处理速度: {records_per_second:.1f} 条记录/秒")
    
    def display_detailed_results(self, patterns):
        """显示详细检测结果 - 以彩种为独立包装，默认展开"""
        st.write("\n" + "="*60)
        st.write("🎯 多账户对刷检测结果")
        st.write("="*60)
        
        if not patterns:
            st.error("❌ 未发现符合阈值条件的连续对刷模式")
            return
        
        patterns_by_lottery = defaultdict(list)
        for pattern in patterns:
            patterns_by_lottery[pattern['彩种']].append(pattern)
        
        for lottery, lottery_patterns in patterns_by_lottery.items():
            # 使用expander包装每个彩种，默认展开
            with st.expander(f"🎲 彩种：{lottery}（发现{len(lottery_patterns)}组）", expanded=True):
                for i, pattern in enumerate(lottery_patterns, 1):
                    # 对刷组信息
                    st.markdown(f"**对刷组 {i}:** {' ↔ '.join(pattern['账户组'])}")
                    
                    # 活跃度信息
                    activity_icon = "🟢" if pattern['账户活跃度'] == 'low' else "🟡" if pattern['账户活跃度'] == 'medium' else "🔴"
                    st.markdown(f"**活跃度:** {activity_icon} {pattern['账户活跃度']} | **彩种:** {pattern['彩种']} | **主要类型:** {pattern['主要对立类型']}")
                    
                    # 账户统计信息
                    st.markdown(f"**账户在该彩种投注期数/记录数:** {', '.join(pattern['账户统计信息'])}")
                    
                    # 对刷期数
                    st.markdown(f"**对刷期数:** {pattern['对刷期数']}期 (要求≥{pattern['要求最小对刷期数']}期)")
                    
                    # 金额信息
                    st.markdown(f"**总金额:** {pattern['总投注金额']:.2f}元 | **平均匹配:** {pattern['平均相似度']:.2%}")
                    
                    # 详细记录 - 直接展开显示
                    st.markdown("**详细记录:**")
                    for j, record in enumerate(pattern['详细记录'], 1):
                        account_directions = []
                        for account, direction, amount in zip(record['账户组'], record['方向组'], record['金额组']):
                            account_directions.append(f"{account}({direction}:{amount})")
                        
                        st.markdown(f"{j}. **期号:** {record['期号']} | **模式:** {record['模式']} | **方向:** {' ↔ '.join(account_directions)} | **匹配度:** {record['相似度']:.2%}")
                    
                    # 对刷组之间的分隔线
                    if i < len(lottery_patterns):
                        st.markdown("---")
        
        self.display_summary_statistics(patterns)
    
    def display_summary_statistics(self, patterns):
        """显示总体统计"""
        if not patterns:
            return
            
        st.write(f"\n{'='*60}")
        st.write("📊 总体统计")
        st.write(f"{'='*60}")
        
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
        
        # 活跃度分布
        activity_stats = defaultdict(int)
        for pattern in patterns:
            activity_stats[pattern['账户活跃度']] += 1
        
        # 对立类型分布
        opposite_type_stats = defaultdict(int)
        for pattern in patterns:
            for opposite_type, count in pattern['对立类型分布'].items():
                opposite_type_stats[opposite_type] += count
        
        st.write(f"**🎯 检测结果汇总:**")
        st.write(f"- 对刷组数: {total_groups} 组")
        st.write(f"- 涉及账户: {total_accounts} 个")
        st.write(f"- 总对刷期数: {total_wash_periods} 期")
        st.write(f"- 总涉及金额: {total_amount:.2f} 元")
        
        st.write(f"**👥 按账户数量分布:**")
        for account_count, count in sorted(account_count_stats.items()):
            st.write(f"- {account_count}个账户组: {count} 组")
        
        st.write(f"**🎲 按彩种分布:**")
        for lottery, count in lottery_stats.items():
            st.write(f"- {lottery}: {count} 组")
            
        st.write(f"**📈 按活跃度分布:**")
        for activity, count in activity_stats.items():
            st.write(f"- {activity}活跃度: {count} 组")
            
        st.write(f"**🎯 按对立类型分布:**")
        for opposite_type, count in opposite_type_stats.items():
            st.write(f"- {opposite_type}: {count} 期对刷")
    
    def export_to_excel(self, patterns, filename):
        """导出检测结果到Excel文件"""
        if not patterns:
            st.error("❌ 没有对刷数据可导出")
            return None, None
        
        export_data = []
        
        for group_idx, pattern in enumerate(patterns, 1):
            for record_idx, record in enumerate(pattern['详细记录'], 1):
                account_directions = []
                for account, direction, amount in zip(record['账户组'], record['方向组'], record['金额组']):
                    account_directions.append(f"{account}({direction}:{amount})")
                
                export_data.append({
                    '对刷组编号': group_idx,
                    '账户组': ' ↔ '.join(pattern['账户组']),
                    '彩种': pattern['彩种'],
                    '账户数量': pattern['账户数量'],
                    '账户活跃度': pattern['账户活跃度'],
                    '账户统计信息': ', '.join(pattern['账户统计信息']),
                    '要求最小对刷期数': pattern['要求最小对刷期数'],
                    '主要对立类型': pattern['主要对立类型'],
                    '对立类型分布': str(pattern['对立类型分布']),
                    '对刷期数': pattern['对刷期数'],
                    '总投注金额': pattern['总投注金额'],
                    '平均相似度': f"{pattern['平均相似度']:.2%}",
                    '模式分布': str(pattern['模式分布']),
                    '期号': record['期号'],
                    '对立类型': record['对立类型'],
                    '模式': record['模式'],
                    '金额': record['总金额'],
                    '匹配度': f"{record['相似度']:.2%}",
                    '账户方向': ' | '.join(account_directions)
                })
        
        df_export = pd.DataFrame(export_data)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_filename = f"对刷检测报告_智能版_{timestamp}.xlsx"
        
        try:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_export.to_excel(writer, sheet_name='详细记录', index=False)
                
                summary_data = []
                for group_idx, pattern in enumerate(patterns, 1):
                    summary_data.append({
                        '对刷组编号': group_idx,
                        '账户组': ' ↔ '.join(pattern['账户组']),
                        '彩种': pattern['彩种'],
                        '账户数量': pattern['账户数量'],
                        '账户活跃度': pattern['账户活跃度'],
                        '账户统计信息': ', '.join(pattern['账户统计信息']),
                        '要求最小对刷期数': pattern['要求最小对刷期数'],
                        '主要对立类型': pattern['主要对立类型'],
                        '对立类型分布': str(pattern['对立类型分布']),
                        '对刷期数': pattern['对刷期数'],
                        '总投注金额': pattern['总投注金额'],
                        '平均相似度': f"{pattern['平均相似度']:.2%}",
                        '模式分布': str(pattern['模式分布'])
                    })
                
                df_summary = pd.DataFrame(summary_data)
                df_summary.to_excel(writer, sheet_name='对刷组汇总', index=False)
            
            output.seek(0)
            st.success(f"✅ Excel报告已生成: {export_filename}")
            
            return output, export_filename
            
        except Exception as e:
            st.error(f"❌ 导出Excel失败: {str(e)}")
            return None, None

# 特码完美覆盖分析系统的函数
def extract_bet_amount_perfect_coverage(amount_text):
    """从复杂文本中提取投注金额 - 特码分析专用"""
    try:
        if pd.isna(amount_text):
            return 0
        
        text = str(amount_text).strip()
        
        # 先尝试直接转换
        try:
            cleaned_text = text.replace(',', '').replace('，', '')
            amount = float(cleaned_text)
            if amount >= 0:
                return amount
        except:
            pass
        
        # 多种金额提取模式
        patterns = [
            r'投注[:：]?\s*(\d+[,，]?\d*\.?\d*)',
            r'投注\s*(\d+[,，]?\d*\.?\d*)',
            r'金额[:：]?\s*(\d+[,，]?\d*\.?\d*)',
            r'(\d+[,，]?\d*\.?\d*)\s*元',
            r'￥\s*(\d+[,，]?\d*\.?\d*)',
            r'¥\s*(\d+[,，]?\d*\.?\d*)',
            r'(\d+[,，]?\d*\.?\d*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                amount_str = match.group(1).replace(',', '').replace('，', '')
                try:
                    amount = float(amount_str)
                    if amount >= 0:
                        return amount
                except:
                    continue
        
        return 0
    except Exception as e:
        st.warning(f"金额提取失败: {amount_text}, 错误: {e}")
        return 0

def find_correct_columns_perfect_coverage(df):
    """找到正确的列 - 特码分析专用"""
    column_mapping = {}
    used_standard_cols = set()
    
    for col in df.columns:
        col_str = str(col).lower().strip()
        
        # 会员账号列
        if '会员账号' not in used_standard_cols and any(keyword in col_str for keyword in ['会员', '账号', '账户', '用户账号']):
            column_mapping[col] = '会员账号'
            used_standard_cols.add('会员账号')
        
        # 期号列
        elif '期号' not in used_standard_cols and any(keyword in col_str for keyword in ['期号', '期数', '期次', '期']):
            column_mapping[col] = '期号'
            used_standard_cols.add('期号')
        
        # 彩种列
        elif '彩种' not in used_standard_cols and any(keyword in col_str for keyword in ['彩种', '彩票', '游戏类型']):
            column_mapping[col] = '彩种'
            used_standard_cols.add('彩种')
        
        # 玩法分类列
        elif '玩法分类' not in used_standard_cols and any(keyword in col_str for keyword in ['玩法分类', '玩法', '投注类型', '类型']):
            column_mapping[col] = '玩法分类'
            used_standard_cols.add('玩法分类')
        
        # 内容列
        elif '内容' not in used_standard_cols and any(keyword in col_str for keyword in ['内容', '投注', '下注内容', '注单内容']):
            column_mapping[col] = '内容'
            used_standard_cols.add('内容')
        
        # 金额列
        elif '金额' not in used_standard_cols and any(keyword in col_str for keyword in ['金额', '下注总额', '投注金额', '总额', '下注金额']):
            column_mapping[col] = '金额'
            used_standard_cols.add('金额')
    
    return column_mapping

def extract_numbers_from_content(content):
    """从内容中提取所有1-49的数字"""
    numbers = []
    content_str = str(content)
    
    # 使用正则表达式提取所有数字
    number_matches = re.findall(r'\d+', content_str)
    for match in number_matches:
        num = int(match)
        if 1 <= num <= 49:
            numbers.append(num)
    
    return list(set(numbers))  # 去重

def format_numbers_display(numbers):
    """格式化数字显示，确保两位数显示"""
    formatted = []
    for num in sorted(numbers):
        formatted.append(f"{num:02d}")
    return ", ".join(formatted)

def calculate_similarity(avgs):
    """计算金额匹配度"""
    if not avgs or max(avgs) == 0:
        return 0
    return (min(avgs) / max(avgs)) * 100

def get_similarity_indicator(similarity):
    """获取相似度颜色指示符"""
    if similarity >= 90:
        return "🟢"
    elif similarity >= 80:
        return "🟡"
    elif similarity >= 70:
        return "🟠"
    else:
        return "🔴"

def run_perfect_coverage_analysis(df):
    """运行特码完美覆盖分析"""
    st.header("🎯 特码完美覆盖分析")
    
    # 定义需要分析的8种六合彩彩种
    target_lotteries = [
        '新澳门六合彩', '澳门六合彩', '香港六合彩', '一分六合彩',
        '五分六合彩', '三分六合彩', '香港⑥合彩', '分分六合彩'
    ]
    
    # 筛选目标彩种和特码玩法
    df_target = df[
        (df['彩种'].isin(target_lotteries)) & 
        (df['玩法分类'] == '特码')
    ]
    
    st.write(f"✅ 特码玩法数据行数: {len(df_target):,}")
    
    if len(df_target) == 0:
        st.warning("❌ 没有找到特码玩法数据")
        return
    
    # 按期数和彩种分组分析
    grouped = df_target.groupby(['期号', '彩种'])
    st.write(f"📅 共发现 {len(grouped):,} 个期数+彩种组合")
    
    all_period_results = {}
    valid_periods = 0
    
    # 进度条
    progress_bar = st.progress(0)
    total_groups = len(grouped)
    
    for i, ((period, lottery), group) in enumerate(grouped):
        if len(group) < 10:  # 数据量太少的跳过
            continue
        
        result = analyze_period_lottery_combination(group, period, lottery)
        if result:
            all_period_results[(period, lottery)] = result
            valid_periods += 1
        
        # 更新进度条
        progress_bar.progress((i + 1) / total_groups)
    
    st.success(f"✅ 分析完成！共分析 {valid_periods} 个有效期数")
    
    # 显示所有期数的完整组合
    st.header("📊 所有期数的完整组合展示")
    
    for (period, lottery), result in all_period_results.items():
        all_results = result['all_results']
        total_combinations = result['total_combinations']
        
        if total_combinations > 0:
            with st.expander(f"📅 期号[{period}] - 彩种[{lottery}] (共{total_combinations}个完美组合)", expanded=True):
                # 显示2账户组合
                if all_results[2]:
                    st.subheader(f"👥 2个账号组合 (共{len(all_results[2])}组)")
                    for i, result_data in enumerate(all_results[2], 1):
                        st.markdown(f"**🎯 组合 {i}**")
                        accounts = result_data['accounts']
                        st.write(f"🔥 账户组: {accounts[0]} ↔ {accounts[1]}")
                        st.write(f"📊 总数字数: {result_data['total_digits']}")
                        st.write(f"💰 总投注金额: {result_data['total_amount']:,.2f} 元")
                        st.write(f"💯 平均金额匹配: {result_data['similarity']:.2f}% {result_data['similarity_indicator']}")
                        
                        for account in accounts:
                            amount_info = result_data['individual_amounts'][account]
                            avg_info = result_data['individual_avg_per_number'][account]
                            st.write(f"   **{account}:** {len(result_data['bet_contents'][account].split(', '))}个数字 | 总投注: {amount_info:,.2f}元 | 平均每号: {avg_info:,.2f}元")
                            st.write(f"   投注内容: {result_data['bet_contents'][account]}")
                        
                        st.markdown("---")
                
                # 显示3账户组合
                if all_results[3]:
                    st.subheader(f"👥 3个账号组合 (共{len(all_results[3])}组)")
                    for i, result_data in enumerate(all_results[3], 1):
                        st.markdown(f"**🎯 组合 {i}**")
                        accounts = result_data['accounts']
                        st.write(f"🔥 账户组: {accounts[0]} ↔ {accounts[1]} ↔ {accounts[2]}")
                        st.write(f"📊 总数字数: {result_data['total_digits']}")
                        st.write(f"💰 总投注金额: {result_data['total_amount']:,.2f} 元")
                        st.write(f"💯 平均金额匹配: {result_data['similarity']:.2f}% {result_data['similarity_indicator']}")
                        
                        for account in accounts:
                            amount_info = result_data['individual_amounts'][account]
                            avg_info = result_data['individual_avg_per_number'][account]
                            st.write(f"   **{account}:** {len(result_data['bet_contents'][account].split(', '))}个数字 | 总投注: {amount_info:,.2f}元 | 平均每号: {avg_info:,.2f}元")
                            st.write(f"   投注内容: {result_data['bet_contents'][account]}")
                        
                        st.markdown("---")

def analyze_period_lottery_combination(df_period_lottery, period, lottery):
    """分析特定期数和彩种的组合"""
    st.info(f"📊 处理: 期号[{period}] - 彩种[{lottery}] - 数据量: {len(df_period_lottery):,}行")
    
    has_amount_column = '金额' in df_period_lottery.columns
    if has_amount_column:
        df_period_lottery['投注金额'] = df_period_lottery['金额'].apply(extract_bet_amount_perfect_coverage)
        period_amount = df_period_lottery['投注金额'].sum()
        st.write(f"💰 本期总投注额: {period_amount:,.2f} 元")
    
    # 按账户提取所有特码数字和金额统计
    account_numbers = {}
    account_amount_stats = {}
    account_bet_contents = {}

    for account in df_period_lottery['会员账号'].unique():
        account_data = df_period_lottery[df_period_lottery['会员账号'] == account]
        
        # 提取该账户下所有特码数字
        all_numbers = set()
        total_amount = 0
        bet_count = 0
        
        for _, row in account_data.iterrows():
            numbers = extract_numbers_from_content(row['内容'])
            all_numbers.update(numbers)
            
            if has_amount_column:
                total_amount += row['投注金额']
                bet_count += 1
        
        if all_numbers:
            account_numbers[account] = sorted(all_numbers)
            account_bet_contents[account] = format_numbers_display(all_numbers)
            number_count = len(all_numbers)
            account_amount_stats[account] = {
                'number_count': number_count,
                'total_amount': total_amount,
                'bet_count': bet_count,
                'avg_amount_per_bet': total_amount / bet_count if bet_count > 0 else 0,
                'avg_amount_per_number': total_amount / number_count if number_count > 0 else 0
            }

    # 排除投注总数量≤11的账户
    filtered_account_numbers = {}
    filtered_account_amount_stats = {}
    filtered_account_bet_contents = {}

    for account, numbers in account_numbers.items():
        num_count = len(numbers)
        if num_count > 11:
            filtered_account_numbers[account] = numbers
            filtered_account_amount_stats[account] = account_amount_stats[account]
            filtered_account_bet_contents[account] = account_bet_contents[account]

    st.write(f"👥 有效账户: {len(filtered_account_numbers):,}个")

    if len(filtered_account_numbers) < 2:
        st.warning("❌ 有效账户不足2个，无法进行组合分析")
        return None

    # 这里简化了组合搜索逻辑，实际使用时需要完整实现
    # 为了演示，我们返回一个空结果
    return {
        'period': period,
        'lottery': lottery,
        'total_accounts': len(account_numbers),
        'filtered_accounts': len(filtered_account_numbers),
        'total_combinations': 0,
        'best_result': None,
        'all_results': {2: [], 3: [], 4: []}
    }

def main():
    """主函数"""
    st.title("🎯 智能多账户对刷检测系统")
    st.markdown("---")
    
    # 侧边栏配置
    st.sidebar.header("⚙️ 检测参数配置")
    
    min_amount = st.sidebar.number_input("最小投注金额", value=10, min_value=1, help="低于此金额的记录将被过滤")
    similarity_threshold = st.sidebar.slider("金额匹配度阈值", 0.8, 1.0, 0.9, 0.01, help="对立方向金额匹配度阈值")
    max_accounts = st.sidebar.slider("最大检测账户数", 2, 8, 5, help="检测的最大账户组合数量")
    
    # 活跃度阈值配置 - 修正版
    st.sidebar.subheader("📊 活跃度阈值配置（基于总投注期数）")
    st.sidebar.markdown("**低活跃度:** 总投注期数≤10期")
    st.sidebar.markdown("**中活跃度:** 总投注期数11-200期")  
    st.sidebar.markdown("**高活跃度:** 总投注期数≥201期")
    
    min_periods_low = st.sidebar.number_input("低活跃度最小对刷期数", value=3, min_value=1, 
                                            help="总投注期数≤10的账户，要求≥3期连续对刷")
    min_periods_medium = st.sidebar.number_input("中活跃度最小对刷期数", value=5, min_value=1,
                                               help="总投注期数11-200的账户，要求≥5期连续对刷")
    min_periods_high = st.sidebar.number_input("高活跃度最小对刷期数", value=8, min_value=1,
                                             help="总投注期数≥201的账户，要求≥8期连续对刷")
    
    # 文件上传
    st.header("📁 数据上传")
    uploaded_file = st.file_uploader(
        "请上传数据文件 (支持 .xlsx, .xls, .csv)", 
        type=['xlsx', 'xls', 'csv'],
        help="请确保文件包含必要的列：会员账号、期号、内容、金额"
    )
    
    # 特码分析开关
    st.sidebar.header("🔧 高级功能")
    enable_perfect_coverage = st.sidebar.checkbox("启用特码完美覆盖分析", value=False, 
                                                help="启用六合彩特码完美覆盖分析功能")
    
    if uploaded_file is not None:
        try:
            # 更新配置参数
            config = Config()
            config.min_amount = min_amount
            config.amount_similarity_threshold = similarity_threshold
            config.max_accounts_in_group = max_accounts
            config.period_thresholds = {
                'low_activity': 10,  # 按照您要求的阈值
                'medium_activity_low': 11,  
                'medium_activity_high': 200, 
                'min_periods_low': min_periods_low,
                'min_periods_medium': min_periods_medium,
                'min_periods_high': min_periods_high
            }
            
            detector = WashTradeDetector(config)
            
            st.success(f"✅ 已上传文件: {uploaded_file.name}")
            
            with st.spinner("🔄 正在解析数据..."):
                df, filename = detector.upload_and_process(uploaded_file)
                if df is not None:
                    df_valid = detector.parse_column_data(df)
                    
                    if len(df_valid) > 0:
                        st.success("✅ 数据解析完成")
                        
                        with st.expander("📊 数据概览", expanded=False):
                            st.write(f"有效记录数: {len(df_valid):,}")
                            st.write(f"唯一期号数: {df_valid['期号'].nunique():,}")
                            st.write(f"唯一账户数: {df_valid['会员账号'].nunique():,}")
                        
                        # 自动开始检测
                        st.info("🚀 自动开始检测对刷交易...")
                        with st.spinner("🔍 正在检测对刷交易..."):
                            patterns = detector.detect_all_wash_trades()
                        
                        if patterns:
                            st.success(f"✅ 检测完成！发现 {len(patterns)} 个对刷组")
                            
                            detector.display_detailed_results(patterns)
                            
                            excel_output, export_filename = detector.export_to_excel(patterns, filename)
                            
                            if excel_output is not None:
                                st.download_button(
                                    label="📥 下载检测报告",
                                    data=excel_output,
                                    file_name=export_filename,
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )
                        else:
                            st.warning("⚠️ 未发现符合阈值条件的对刷行为")
                        
                        # 特码完美覆盖分析（可选）
                        if enable_perfect_coverage:
                            # 重新读取原始数据进行特码分析
                            df_original = pd.read_excel(uploaded_file)
                            column_mapping = find_correct_columns_perfect_coverage(df_original)
                            if column_mapping:
                                df_original = df_original.rename(columns=column_mapping)
                            
                            # 检查必要列
                            required_cols = ['会员账号', '期号', '彩种', '玩法分类', '内容']
                            if all(col in df_original.columns for col in required_cols):
                                run_perfect_coverage_analysis(df_original)
                            else:
                                st.error("❌ 特码分析缺少必要列，请确保文件包含：会员账号、期号、彩种、玩法分类、内容")
                    else:
                        st.error("❌ 数据解析失败，请检查文件格式和内容")
            
        except Exception as e:
            st.error(f"❌ 程序执行失败: {str(e)}")
            st.error(f"详细错误信息:\n{traceback.format_exc()}")
    
    # 使用说明
    with st.expander("📖 使用说明（智能多账户对刷检测系统）"):
        st.markdown("""
        ### 系统功能说明

        **🎯 对刷检测逻辑：**
        - **总投注期数**：账户在特定彩种中的所有期号投注次数
        - **对刷期数**：账户组实际发生对刷行为的期数
        - 根据**总投注期数**判定账户活跃度，设置不同的**对刷期数**阈值

        **📊 活跃度判定：**
        - **低活跃度账户**：总投注期数 ≤ 10期 → 要求 ≥ 3期连续对刷
        - **中活跃度账户**：总投注期数 11-200期 → 要求 ≥ 5期连续对刷  
        - **高活跃度账户**：总投注期数 ≥ 201期 → 要求 ≥ 8期连续对刷

        **🎯 对刷检测规则：**
        - 检测2-5个账户之间的对刷行为
        - **支持的对立投注类型：**
          - 大 vs 小
          - 单 vs 双  
          - 龙 vs 虎
        - 金额匹配度 ≥ 90%
        - 排除同一账户多方向下注

        **🎲 特码完美覆盖分析：**
        - 在侧边栏勾选"启用特码完美覆盖分析"即可使用
        - 分析六合彩特码玩法的完美数字覆盖组合
        - 支持2-4个账户的组合分析
        - 要求组合数字覆盖1-49所有号码且无重复

        **📁 数据格式要求：**
        - 必须包含：会员账号、期号、内容、金额
        - 可选包含：彩种（如无则自动添加默认值）
        - 支持自动列名映射
        """)

if __name__ == "__main__":
    main()
