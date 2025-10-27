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
st.markdown("### 基于数学完备性的完美组合检测")

class PerfectCoverageAnalyzer:
    """完美覆盖分析器 - 基于数学完备性验证"""
    
    def __init__(self):
        self.full_set = set(range(1, 50))
        self.standard_columns = list(COLUMN_MAPPINGS.keys())
    
    def map_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """智能映射列名到标准格式"""
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
    
    def analyze_accounts(self, df: pd.DataFrame) -> Tuple[Dict, Dict, Dict]:
        """分析账户数据 - 返回三个字典"""
        # 提取金额
        if '金额' in df.columns:
            df['投注金额'] = df['金额'].apply(self.extract_amount)
        else:
            df['投注金额'] = 0.0
        
        # 筛选特码玩法
        special_bets = df[df['玩法'].str.contains('特码|特别号', na=False)]
        
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
            
            # 填充三个字典
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
            len(combined_set) == 49 and           # 恰好49个数字
            min(combined_set) == 1 and           # 最小值为1
            max(combined_set) == 49 and          # 最大值为49
            len(set(combined_set)) == 49         # 无重复数字
        )
    
    def search_2_account_combinations(self, accounts: List[str], account_sets: Dict, account_amount_stats: Dict) -> List[Dict]:
        """第一层：2账户组合搜索"""
        st.info("🔍 正在搜索2账户完美组合...")
        results = []
        all_accounts = accounts.copy()
        
        progress_bar = st.progress(0)
        total_pairs = len(all_accounts) * (len(all_accounts) - 1) // 2
        processed = 0
        
        for i, acc1 in enumerate(all_accounts):
            count1 = len(account_sets[acc1])
            for j in range(i+1, len(all_accounts)):
                acc2 = all_accounts[j]
                count2 = len(account_sets[acc2])
                
                processed += 1
                if processed % 100 == 0:  # 每100次更新一次进度
                    progress_bar.progress(min(processed / total_pairs, 1.0))
                
                # 快速预判：数字数量之和必须等于49
                if count1 + count2 != 49:
                    continue
                
                # 精确验证：并集是否恰好为49个不同数字
                combined_set = account_sets[acc1] | account_sets[acc2]
                if self.validate_perfect_coverage(combined_set):
                    # 计算金额指标
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
                        'numbers': combined_set,
                        'individual_amounts': {
                            acc1: account_amount_stats[acc1]['total_amount'],
                            acc2: account_amount_stats[acc2]['total_amount']
                        },
                        'individual_avg_per_number': {
                            acc1: account_amount_stats[acc1]['avg_amount_per_number'],
                            acc2: account_amount_stats[acc2]['avg_amount_per_number']
                        }
                    }
                    results.append(result_data)
        
        progress_bar.empty()
        return results
    
    def search_3_account_combinations(self, accounts: List[str], account_sets: Dict, account_amount_stats: Dict) -> List[Dict]:
        """第二层：3账户组合搜索"""
        st.info("🔍 正在搜索3账户完美组合...")
        results = []
        all_accounts = accounts.copy()
        
        progress_bar = st.progress(0)
        total_combinations = len(all_accounts) * (len(all_accounts)-1) * (len(all_accounts)-2) // 6
        processed = 0
        
        for i, acc1 in enumerate(all_accounts):
            count1 = len(account_sets[acc1])
            for j in range(i+1, len(all_accounts)):
                acc2 = all_accounts[j]
                count2 = len(account_sets[acc2])
                for k in range(j+1, len(all_accounts)):
                    acc3 = all_accounts[k]
                    count3 = len(account_sets[acc3])
                    
                    processed += 1
                    if processed % 100 == 0:
                        progress_bar.progress(min(processed / total_combinations, 1.0))
                    
                    # 快速预判
                    if count1 + count2 + count3 != 49:
                        continue
                    
                    # 精确验证
                    combined_set = account_sets[acc1] | account_sets[acc2] | account_sets[acc3]
                    if self.validate_perfect_coverage(combined_set):
                        total_amount = (account_amount_stats[acc1]['total_amount'] + 
                                      account_amount_stats[acc2]['total_amount'] + 
                                      account_amount_stats[acc3]['total_amount'])
                        avg_amounts = [
                            account_amount_stats[acc1]['avg_amount_per_number'],
                            account_amount_stats[acc2]['avg_amount_per_number'],
                            account_amount_stats[acc3]['avg_amount_per_number']
                        ]
                        similarity = self.calculate_similarity(avg_amounts)
                        
                        result_data = {
                            'accounts': [acc1, acc2, acc3],
                            'account_count': 3,
                            'total_digits': 49,
                            'efficiency': 49/3,
                            'total_amount': total_amount,
                            'avg_amount_per_number': total_amount / 49,
                            'similarity': similarity,
                            'similarity_indicator': self.get_similarity_indicator(similarity),
                            'numbers': combined_set,
                            'individual_amounts': {
                                acc1: account_amount_stats[acc1]['total_amount'],
                                acc2: account_amount_stats[acc2]['total_amount'],
                                acc3: account_amount_stats[acc3]['total_amount']
                            },
                            'individual_avg_per_number': {
                                acc1: account_amount_stats[acc1]['avg_amount_per_number'],
                                acc2: account_amount_stats[acc2]['avg_amount_per_number'],
                                acc3: account_amount_stats[acc3]['avg_amount_per_number']
                            }
                        }
                        results.append(result_data)
        
        progress_bar.empty()
        return results
    
    def search_4_account_combinations(self, accounts: List[str], account_sets: Dict, account_amount_stats: Dict) -> List[Dict]:
        """第三层：4账户组合搜索（带优化）"""
        st.info("🔍 正在搜索4账户完美组合...")
        results = []
        
        # 优化搜索范围：只选择数字数量在12-35之间的账户
        suitable_accounts = [acc for acc in accounts if 12 <= len(account_sets[acc]) <= 35]
        
        if len(suitable_accounts) < 4:
            return results
        
        progress_bar = st.progress(0)
        total_combinations = len(suitable_accounts) * (len(suitable_accounts)-1) * (len(suitable_accounts)-2) * (len(suitable_accounts)-3) // 24
        processed = 0
        
        for i, acc1 in enumerate(suitable_accounts):
            count1 = len(account_sets[acc1])
            for j in range(i+1, len(suitable_accounts)):
                acc2 = suitable_accounts[j]
                count2 = len(account_sets[acc2])
                for k in range(j+1, len(suitable_accounts)):
                    acc3 = suitable_accounts[k]
                    count3 = len(account_sets[acc3])
                    for l in range(k+1, len(suitable_accounts)):
                        acc4 = suitable_accounts[l]
                        count4 = len(account_sets[acc4])
                        
                        processed += 1
                        if processed % 100 == 0:
                            progress_bar.progress(min(processed / total_combinations, 1.0))
                        
                        # 快速预判
                        if count1 + count2 + count3 + count4 != 49:
                            continue
                        
                        # 精确验证
                        combined_set = account_sets[acc1] | account_sets[acc2] | account_sets[acc3] | account_sets[acc4]
                        if self.validate_perfect_coverage(combined_set):
                            total_amount = (account_amount_stats[acc1]['total_amount'] + 
                                          account_amount_stats[acc2]['total_amount'] + 
                                          account_amount_stats[acc3]['total_amount'] + 
                                          account_amount_stats[acc4]['total_amount'])
                            avg_amounts = [
                                account_amount_stats[acc1]['avg_amount_per_number'],
                                account_amount_stats[acc2]['avg_amount_per_number'],
                                account_amount_stats[acc3]['avg_amount_per_number'],
                                account_amount_stats[acc4]['avg_amount_per_number']
                            ]
                            similarity = self.calculate_similarity(avg_amounts)
                            
                            result_data = {
                                'accounts': [acc1, acc2, acc3, acc4],
                                'account_count': 4,
                                'total_digits': 49,
                                'efficiency': 49/4,
                                'total_amount': total_amount,
                                'avg_amount_per_number': total_amount / 49,
                                'similarity': similarity,
                                'similarity_indicator': self.get_similarity_indicator(similarity),
                                'numbers': combined_set,
                                'individual_amounts': {
                                    acc1: account_amount_stats[acc1]['total_amount'],
                                    acc2: account_amount_stats[acc2]['total_amount'],
                                    acc3: account_amount_stats[acc3]['total_amount'],
                                    acc4: account_amount_stats[acc4]['total_amount']
                                },
                                'individual_avg_per_number': {
                                    acc1: account_amount_stats[acc1]['avg_amount_per_number'],
                                    acc2: account_amount_stats[acc2]['avg_amount_per_number'],
                                    acc3: account_amount_stats[acc3]['avg_amount_per_number'],
                                    acc4: account_amount_stats[acc4]['avg_amount_per_number']
                                }
                            }
                            results.append(result_data)
        
        progress_bar.empty()
        return results
    
    def find_perfect_combinations(self, account_numbers: Dict, account_sets: Dict, account_amount_stats: Dict) -> Dict[str, List]:
        """多层搜索完美组合"""
        # 筛选有效账户（投注数字数量 > 11）
        valid_accounts = [acc for acc, numbers in account_numbers.items() 
                         if len(numbers) > 11]
        
        st.write(f"📊 有效账户分析: 总共 {len(account_numbers)} 个账户, 其中 {len(valid_accounts)} 个有效账户")
        
        if len(valid_accounts) < 2:
            st.error("❌ 有效账户不足2个，无法进行组合分析")
            return {'2': [], '3': [], '4': []}
        
        # 显示有效账户信息
        with st.expander("📋 有效账户详情"):
            for acc in valid_accounts:
                stats = account_amount_stats[acc]
                st.write(f"- **{acc}**: {len(account_sets[acc])}个数字, 总金额 ¥{stats['total_amount']:,.2f}")
        
        all_results = {'2': [], '3': [], '4': []}
        
        # 分层搜索
        if len(valid_accounts) >= 2:
            all_results['2'] = self.search_2_account_combinations(valid_accounts, account_sets, account_amount_stats)
        
        if len(valid_accounts) >= 3:
            all_results['3'] = self.search_3_account_combinations(valid_accounts, account_sets, account_amount_stats)
        
        if len(valid_accounts) >= 4:
            all_results['4'] = self.search_4_account_combinations(valid_accounts, account_sets, account_amount_stats)
        
        return all_results

# 列名映射配置
COLUMN_MAPPINGS = {
    '会员账号': ['会员账号', '会员账户', '账号', '账户', '用户账号'],
    '彩种': ['彩种', '彩票种类', '游戏类型'],
    '期号': ['期号', '期数', '期次', '期'],
    '玩法': ['玩法', '玩法分类', '投注类型', '类型'],
    '内容': ['内容', '投注内容', '下注内容', '注单内容'],
    '金额': ['金额', '下注总额', '投注金额', '总额', '下注金额']
}

def main():
    analyzer = PerfectCoverageAnalyzer()
    
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
            
            # 显示原始数据
            with st.expander("📊 原始数据预览"):
                st.dataframe(df.head(10))
                st.write(f"原始列名: {list(df.columns)}")
                st.write(f"数据形状: {df.shape}")
            
            # 列名映射
            df_mapped = analyzer.map_column_names(df)
            
            if df_mapped is not None:
                st.success("✅ 列名映射完成")
                
                # 显示映射后的数据
                with st.expander("🔄 映射后数据预览"):
                    st.dataframe(df_mapped.head(10))
                    st.write(f"映射后列名: {list(df_mapped.columns)}")
                
                # 数据分析
                st.header("🔬 数学完备性分析")
                
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
                        st.warning("⚠️ 未找到有效的特码投注数据")
                        return
                    
                    # 寻找完美组合
                    st.subheader("🎯 完美组合搜索")
                    all_results = analyzer.find_perfect_combinations(account_numbers, account_sets, account_amount_stats)
                    
                    # 汇总结果
                    total_perfect = len(all_results['2']) + len(all_results['3']) + len(all_results['4'])
                    
                    if total_perfect > 0:
                        st.success(f"🎉 找到 {total_perfect} 个完美覆盖组合!")
                        
                        # 显示统计信息
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("2账户组合", len(all_results['2']))
                        with col2:
                            st.metric("3账户组合", len(all_results['3']))
                        with col3:
                            st.metric("4账户组合", len(all_results['4']))
                        with col4:
                            st.metric("总计", total_perfect)
                        
                        # 合并所有结果并按效率排序
                        all_combinations = all_results['2'] + all_results['3'] + all_results['4']
                        all_combinations.sort(key=lambda x: (x['account_count'], -x['similarity']))
                        
                        # 显示最佳组合
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
                            
                            # 显示所有组合
                            with st.expander("📊 所有完美组合"):
                                for combo in all_combinations:
                                    st.write(f"**{combo['account_count']}账户组合** (效率: {combo['efficiency']:.1f}, "
                                           f"匹配度: {combo['similarity']:.1f}% {combo['similarity_indicator']}):")
                                    st.write(f"账户: {combo['accounts']}")
                                    st.write(f"总金额: ¥{combo['total_amount']:,.2f}")
                                    st.write("---")
                    
                    else:
                        st.warning("⚠️ 未找到完美覆盖组合")
                        st.info("""
                        **数学分析结果:**
                        - 当前数据无法形成1-49的完美覆盖
                        - 可能原因: 账户号码分布重叠过多
                        - 建议: 检查数据质量或调整投注策略
                        """)
                
                else:
                    st.warning("⚠️ 数据中未找到期号信息")
            
        except Exception as e:
            st.error(f"❌ 处理文件时出错: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
    
    else:
        # 显示示例和使用说明
        st.info("💡 **数学完备性分析系统**")
        st.markdown("""
        ### 完美组合定义:
        - **数学完备**: 账户组合的数字并集恰好等于 {1,2,3,...,49}
        - **无重复无缺失**: 恰好49个不重复数字
        - **效率优先**: 账户数量越少越好
        
        ### 搜索策略:
        1. **2账户组合**: 数字数量之和=49，且并集=全集
        2. **3账户组合**: 数字数量之和=49，且并集=全集  
        3. **4账户组合**: 数字数量之和=49，且并集=全集
        
        ### 数据要求:
        - 必须包含特码玩法的投注记录
        - 每个账户投注数字数量 > 11
        - 数字范围严格在1-49之间
        """)
        
        # 提供完美组合示例
        st.subheader("🎲 完美组合示例")
        example_data = {
            '2账户组合': {
                '账户A': list(range(1, 25)),      # 1-24
                '账户B': list(range(25, 50))     # 25-49
            },
            '3账户组合': {
                '账户A': list(range(1, 17)),      # 1-16
                '账户B': list(range(17, 33)),     # 17-32  
                '账户C': list(range(33, 50))      # 33-49
            }
        }
        
        for combo_type, accounts in example_data.items():
            with st.expander(f"{combo_type}示例"):
                for acc, numbers in accounts.items():
                    st.write(f"- {acc}: {len(numbers)}个数字")
                union_set = set()
                for numbers in accounts.values():
                    union_set.update(numbers)
                st.write(f"✅ 并集验证: {len(union_set)}个不重复数字，完美覆盖: {union_set == set(range(1,50))}")

if __name__ == "__main__":
    main()
