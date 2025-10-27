import streamlit as st
import pandas as pd
import numpy as np
import re
from typing import Dict, List, Set, Tuple, Any
import itertools
from collections import defaultdict
import time

# 设置页面
st.set_page_config(
    page_title="智能特码完美覆盖分析系统",
    page_icon="🎯",
    layout="wide"
)

# 标题和说明
st.title("🎯 智能特码完美覆盖分析系统")
st.markdown("### 精准识别六合彩特码玩法")

class EnhancedBettingAnalyzer:
    """增强版投注分析器 - 精准识别六合彩和特码"""
    
    def __init__(self):
        self.full_set = set(range(1, 50))
        
        # 六合彩彩种识别列表
        self.lottery_types = [
            '一分六合彩', '五分六合彩', '香港六合彩', '澳门六合彩', '快乐6合彩',
            '新澳门六合彩', '香港⑥合彩', '分分六合彩', '三分六合彩', 
            '台湾大乐透', '大发六合彩', '六合彩'
        ]
        
        # 特码玩法识别列表
        self.special_bet_types = [
            '特码', '特别号', '特肖', '特码生肖', '特码直选', '特码组选',
            '特码A', '特码B', '特码单双', '特码大小', '特码波色'
        ]
    
    def map_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """智能映射列名到标准格式"""
        COLUMN_MAPPINGS = {
            '会员账号': ['会员账号', '会员账户', '账号', '账户', '用户账号'],
            '彩种': ['彩种', '彩票种类', '游戏类型'],
            '期号': ['期号', '期数', '期次', '期'],
            '玩法': ['玩法', '玩法分类', '投注类型', '类型'],
            '内容': ['内容', '投注内容', '下注内容', '注单内容'],
            '金额': ['金额', '下注总额', '投注金额', '总额', '下注金额']
        }
        
        mapped_columns = {}
        
        for standard_col, possible_names in COLUMN_MAPPINGS.items():
            for possible_name in possible_names:
                if possible_name in df.columns:
                    mapped_columns[possible_name] = standard_col
                    break
        
        # 重命名列
        df_renamed = df.rename(columns=mapped_columns)
        
        # 检查必要列是否存在
        missing_columns = [col for col in ['会员账号', '彩种', '期号', '玩法', '内容'] 
                          if col not in df_renamed.columns]
        
        if missing_columns:
            st.error(f"缺少必要列: {missing_columns}")
            return None
        
        return df_renamed
    
    def is_lottery_type(self, lottery_str: str) -> bool:
        """判断是否为六合彩彩种"""
        if pd.isna(lottery_str):
            return False
        
        lottery_str = str(lottery_str).strip()
        
        # 检查是否包含六合彩关键词
        for lottery_type in self.lottery_types:
            if lottery_type in lottery_str:
                return True
        
        return False
    
    def is_special_bet(self, bet_type: str) -> bool:
        """判断是否为特码玩法"""
        if pd.isna(bet_type):
            return False
        
        bet_type = str(bet_type).strip()
        
        # 检查是否包含特码关键词
        for special_type in self.special_bet_types:
            if special_type in bet_type:
                return True
        
        return False
    
    def extract_amount(self, amount_str) -> float:
        """提取金额"""
        if pd.isna(amount_str):
            return 0.0
            
        amount_str = str(amount_str).strip()
        
        try:
            clean_str = re.sub(r'[,\uff0c]', '', amount_str)
            return float(clean_str)
        except:
            pass
        
        patterns = [
            r'投注\s*[:：]?\s*([\d,.]+)',
            r'金额\s*[:：]?\s*([\d,.]+)', 
            r'下注金额\s*([\d,.]+)',
            r'([\d,.]+)\s*元',
            r'([\d,.]+)\s*RMB'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, amount_str, re.IGNORECASE)
            if match:
                try:
                    clean_str = re.sub(r'[,\uff0c]', '', match.group(1))
                    return float(clean_str)
                except:
                    continue
        
        return 0.0
    
    def extract_numbers(self, content: str) -> Set[int]:
        """从投注内容中精确提取数字"""
        if pd.isna(content):
            return set()
        
        content_str = str(content)
        numbers = set()
        
        # 多种数字格式匹配
        number_matches = re.findall(r'\b\d{1,2}\b', content_str)
        for match in number_matches:
            num = int(match)
            if 1 <= num <= 49:
                numbers.add(num)
        
        return numbers
    
    def calculate_similarity(self, avgs: List[float]) -> float:
        """计算金额匹配度"""
        if not avgs or max(avgs) == 0:
            return 0
        return (min(avgs) / max(avgs)) * 100
    
    def get_similarity_indicator(self, similarity: float) -> str:
        """金额匹配度可视化指示器"""
        if similarity >= 90: return "🟢"
        elif similarity >= 80: return "🟡" 
        elif similarity >= 70: return "🟠"
        else: return "🔴"
    
    def analyze_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析数据质量"""
        quality_info = {
            'total_records': len(df),
            'has_amount': '金额' in df.columns,
            'lottery_types': df['彩种'].unique().tolist() if '彩种' in df.columns else [],
            'bet_types': df['玩法'].unique().tolist() if '玩法' in df.columns else [],
            'periods': df['期号'].unique().tolist() if '期号' in df.columns else [],
            'accounts': df['会员账号'].unique().tolist() if '会员账号' in df.columns else []
        }
        
        # 识别六合彩数据
        if '彩种' in df.columns:
            lottery_mask = df['彩种'].apply(self.is_lottery_type)
            quality_info['lottery_records'] = lottery_mask.sum()
            quality_info['non_lottery_records'] = (~lottery_mask).sum()
        
        # 识别特码玩法
        if '玩法' in df.columns:
            special_mask = df['玩法'].apply(self.is_special_bet)
            quality_info['special_bet_records'] = special_mask.sum()
            quality_info['non_special_records'] = (~special_mask).sum()
        
        return quality_info
    
    def analyze_accounts(self, df: pd.DataFrame) -> Tuple[Dict, Dict, Dict]:
        """分析账户数据 - 精准筛选六合彩特码玩法"""
        # 提取金额
        if '金额' in df.columns:
            df['投注金额'] = df['金额'].apply(self.extract_amount)
        else:
            df['投注金额'] = 0.0
        
        # 第一步：筛选六合彩数据
        lottery_mask = df['彩种'].apply(self.is_lottery_type)
        lottery_data = df[lottery_mask]
        
        st.write(f"🎯 六合彩数据筛选: {len(lottery_data)}/{len(df)} 条记录")
        
        if len(lottery_data) == 0:
            st.warning("未找到六合彩数据，请检查彩种名称")
            st.write("支持的六合彩类型:", self.lottery_types)
            return {}, {}, {}
        
        # 第二步：筛选特码玩法
        special_mask = lottery_data['玩法'].apply(self.is_special_bet)
        special_bets = lottery_data[special_mask]
        
        st.write(f"🎯 特码玩法筛选: {len(special_bets)}/{len(lottery_data)} 条记录")
        
        if len(special_bets) == 0:
            st.warning("未找到特码玩法数据，请检查玩法名称")
            st.write("支持的特码玩法:", self.special_bet_types)
            return {}, {}, {}
        
        # 显示筛选结果
        with st.expander("📋 数据筛选详情"):
            st.write("**六合彩类型分布:**")
            lottery_counts = lottery_data['彩种'].value_counts()
            st.write(lottery_counts)
            
            st.write("**特码玩法分布:**")
            bet_type_counts = special_bets['玩法'].value_counts()
            st.write(bet_type_counts)
        
        # 三个核心字典
        account_numbers = {}      # 账户 -> 数字列表
        account_sets = {}         # 账户 -> 数字集合
        account_amount_stats = {} # 账户 -> 金额统计
        
        for account, group in special_bets.groupby('会员账号'):
            all_numbers = set()
            total_amount = 0
            bet_count = len(group)
            
            for _, row in group.iterrows():
                numbers = self.extract_numbers(row['内容'])
                all_numbers.update(numbers)
                total_amount += row['投注金额']
            
            number_count = len(all_numbers)
            
            # 只记录有数字的账户
            if number_count > 0:
                account_numbers[account] = list(all_numbers)
                account_sets[account] = all_numbers
                account_amount_stats[account] = {
                    'number_count': number_count,
                    'total_amount': total_amount,
                    'bet_count': bet_count,
                    'avg_amount_per_bet': total_amount / bet_count if bet_count > 0 else 0,
                    'avg_amount_per_number': total_amount / number_count if number_count > 0 else 0
                }
        
        return account_numbers, account_sets, account_amount_stats
    
    def validate_perfect_coverage(self, combined_set: Set[int]) -> bool:
        """严格验证完美覆盖"""
        return (
            len(combined_set) == 49 and
            min(combined_set) == 1 and
            max(combined_set) == 49
        )
    
    def search_2_account_combinations(self, accounts: List[str], account_sets: Dict, account_amount_stats: Dict) -> List[Dict]:
        """2账户组合搜索"""
        results = []
        all_accounts = accounts.copy()
        
        if len(all_accounts) < 2:
            return results
        
        progress_bar = st.progress(0)
        total_pairs = len(all_accounts) * (len(all_accounts) - 1) // 2
        processed = 0
        
        for i, acc1 in enumerate(all_accounts):
            count1 = len(account_sets[acc1])
            for j in range(i+1, len(all_accounts)):
                acc2 = all_accounts[j]
                count2 = len(account_sets[acc2])
                
                processed += 1
                if processed % 10 == 0:
                    progress_bar.progress(min(processed / total_pairs, 1.0))
                
                # 精确验证
                combined_set = account_sets[acc1] | account_sets[acc2]
                if self.validate_perfect_coverage(combined_set):
                    total_amount = (account_amount_stats[acc1]['total_amount'] + 
                                  account_amount_stats[acc2]['total_amount'])
                    avg_amounts = [
                        account_amount_stats[acc1]['avg_amount_per_number'],
                        account_amount_stats[acc2]['avg_amount_per_number']
                    ]
                    similarity = self.calculate_similarity(avg_amounts)
                    
                    result_data = {
                        'accounts': [acc1, acc2],
                        'account_count': 2,
                        'total_digits': 49,
                        'efficiency': 49/2,
                        'total_amount': total_amount,
                        'avg_amount_per_number': total_amount / 49,
                        'similarity': similarity,
                        'similarity_indicator': self.get_similarity_indicator(similarity),
                        'numbers': combined_set
                    }
                    results.append(result_data)
        
        progress_bar.empty()
        return results
    
    def find_perfect_combinations(self, account_numbers: Dict, account_sets: Dict, account_amount_stats: Dict) -> Dict[str, List]:
        """寻找完美组合"""
        # 筛选有效账户（投注数字数量 >= 12）
        valid_accounts = [acc for acc, numbers in account_numbers.items() 
                         if len(numbers) >= 12]
        
        st.write(f"📊 有效账户分析: 总共 {len(account_numbers)} 个账户, 其中 {len(valid_accounts)} 个有效账户(数字≥12)")
        
        if len(valid_accounts) < 2:
            st.warning(f"有效账户不足2个，当前有 {len(valid_accounts)} 个有效账户")
            
            # 显示所有账户信息用于调试
            with st.expander("🔍 所有账户详情(用于调试)"):
                for acc, numbers in account_numbers.items():
                    stats = account_amount_stats[acc]
                    st.write(f"- **{acc}**: {len(numbers)}个数字, 总金额 ¥{stats['total_amount']:,.2f}")
                    st.write(f"  号码: {sorted(list(numbers))}")
            
            return {'2': [], '3': [], '4': []}
        
        # 显示有效账户信息
        with st.expander("📋 有效账户详情"):
            for acc in valid_accounts:
                stats = account_amount_stats[acc]
                numbers = account_sets[acc]
                st.write(f"- **{acc}**: {len(numbers)}个数字, 总金额 ¥{stats['total_amount']:,.2f}")
        
        all_results = {'2': [], '3': [], '4': []}
        
        # 搜索2账户组合
        st.info("🔍 正在搜索2账户完美组合...")
        all_results['2'] = self.search_2_account_combinations(valid_accounts, account_sets, account_amount_stats)
        
        return all_results

def main():
    analyzer = EnhancedBettingAnalyzer()
    
    # 文件上传
    st.sidebar.header("📁 数据上传")
    uploaded_file = st.sidebar.file_uploader(
        "上传投注数据文件", 
        type=['csv', 'xlsx', 'xls'],
        help="支持CSV、Excel格式文件"
    )
    
    if uploaded_file is not None:
        try:
            # 读取文件
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.success(f"✅ 成功读取文件，共 {len(df)} 条记录")
            
            # 数据质量分析
            st.header("📊 数据质量分析")
            quality_info = analyzer.analyze_data_quality(df)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("总记录数", quality_info['total_records'])
            with col2:
                st.metric("六合彩记录", quality_info.get('lottery_records', 0))
            with col3:
                st.metric("特码玩法记录", quality_info.get('special_bet_records', 0))
            with col4:
                st.metric("唯一账户数", len(quality_info['accounts']))
            
            # 显示原始数据
            with st.expander("📋 原始数据预览"):
                st.dataframe(df.head(10))
                st.write(f"数据形状: {df.shape}")
                st.write(f"彩种类型: {quality_info['lottery_types']}")
                st.write(f"玩法类型: {quality_info['bet_types']}")
            
            # 列名映射
            df_mapped = analyzer.map_column_names(df)
            
            if df_mapped is not None:
                st.success("✅ 列名映射完成")
                
                # 数据分析
                st.header("🔬 特码完美覆盖分析")
                
                # 按期号分析
                if '期号' in df_mapped.columns:
                    periods = df_mapped['期号'].unique()
                    
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        selected_period = st.selectbox("选择期号", periods)
                    
                    # 筛选当期数据
                    period_data = df_mapped[df_mapped['期号'] == selected_period]
                    
                    # 分析账户
                    account_numbers, account_sets, account_amount_stats = analyzer.analyze_accounts(period_data)
                    
                    if not account_numbers:
                        st.error("❌ 未找到有效的六合彩特码投注数据")
                        st.info("""
                        **可能原因:**
                        1. 彩种名称不匹配 - 当前支持的六合彩类型包括: {}
                        2. 玩法名称不匹配 - 当前支持的特码玩法包括: {}
                        3. 数据格式问题 - 请检查数据内容
                        """.format(analyzer.lottery_types, analyzer.special_bet_types))
                        return
                    
                    # 寻找完美组合
                    st.subheader("🎯 完美组合搜索")
                    all_results = analyzer.find_perfect_combinations(account_numbers, account_sets, account_amount_stats)
                    
                    # 汇总结果
                    total_perfect = len(all_results['2']) + len(all_results['3']) + len(all_results['4'])
                    
                    if total_perfect > 0:
                        st.success(f"🎉 找到 {total_perfect} 个完美覆盖组合!")
                        
                        # 显示最佳组合
                        all_combinations = all_results['2'] + all_results['3'] + all_results['4']
                        if all_combinations:
                            best_combo = all_combinations[0]
                            st.subheader("🏆 最佳完美组合")
                            
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("账户数量", best_combo['account_count'])
                            with col2:
                                st.metric("覆盖效率", f"{best_combo['efficiency']:.1f}")
                            with col3:
                                st.metric("总金额", f"¥{best_combo['total_amount']:,.2f}")
                            with col4:
                                similarity = best_combo['similarity']
                                indicator = best_combo['similarity_indicator']
                                st.metric("金额匹配度", f"{similarity:.1f}% {indicator}")
                            
                            # 显示组合详情
                            with st.expander("📋 组合详情"):
                                st.write("**包含账户:**")
                                for account in best_combo['accounts']:
                                    stats = account_amount_stats[account]
                                    numbers = account_sets[account]
                                    st.write(f"- **{account}**: {len(numbers)}个数字, "
                                           f"总金额 ¥{stats['total_amount']:,.2f}, "
                                           f"每号平均 ¥{stats['avg_amount_per_number']:,.2f}")
                                    st.write(f"  号码: {sorted(list(numbers))}")
                    
                    else:
                        st.warning("⚠️ 未找到完美覆盖组合")
                        
                        # 显示覆盖分析
                        if account_numbers:
                            st.info("🔍 覆盖情况分析")
                            all_numbers = set()
                            for numbers in account_sets.values():
                                all_numbers.update(numbers)
                            
                            missing_numbers = set(range(1, 50)) - all_numbers
                            coverage = len(all_numbers) / 49 * 100
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("已覆盖号码", f"{len(all_numbers)}/49")
                                st.metric("覆盖率", f"{coverage:.1f}%")
                            with col2:
                                st.metric("缺失号码数", len(missing_numbers))
                                if missing_numbers:
                                    st.write(f"缺失号码: {sorted(list(missing_numbers))}")
            
        except Exception as e:
            st.error(f"❌ 处理文件时出错: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
    
    else:
        # 显示示例和使用说明
        st.info("💡 **精准六合彩特码分析系统**")
        st.markdown("""
        ### 系统特性:
        - **精准彩种识别**: 支持多种六合彩变体
        - **特码玩法筛选**: 精准识别特码相关玩法
        - **完美覆盖检测**: 数学完备性验证
        
        ### 支持的六合彩类型:
        {}
        
        ### 支持的特码玩法:
        {}
        """.format(analyzer.lottery_types, analyzer.special_bet_types))

if __name__ == "__main__":
    main()
