import streamlit as st
import pandas as pd
import numpy as np
import re
from typing import Dict, List, Set, Tuple, Any
import itertools
from collections import defaultdict
import io

# 设置页面
st.set_page_config(
    page_title="智能特码完美覆盖分析系统",
    page_icon="🎯",
    layout="wide"
)

# 标题和说明
st.title("🎯 智能特码完美覆盖分析系统")

class EnhancedBettingAnalyzer:
    """增强版投注分析器"""
    
    def __init__(self):
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
            st.info("请确保文件包含以下列之一:")
            for col in missing_columns:
                st.write(f"- {col}: {COLUMN_MAPPINGS[col]}")
            return None
        
        return df_renamed
    
    def extract_amount(self, amount_str) -> float:
        """三层策略提取金额"""
        if pd.isna(amount_str):
            return 0.0
            
        # 转换为字符串处理
        amount_str = str(amount_str).strip()
        
        # 第一层：直接数值转换
        try:
            # 处理简单数字格式
            clean_str = re.sub(r'[,\uff0c]', '', amount_str)  # 移除逗号和全角逗号
            return float(clean_str)
        except:
            pass
        
        # 第二层：结构化文本匹配
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
        
        # 第三层：货币格式匹配
        currency_patterns = [
            r'[￥¥]\s*([\d,.]+)',
            r'([\d,.]+)\s*[￥¥]'
        ]
        
        for pattern in currency_patterns:
            match = re.search(pattern, amount_str)
            if match:
                try:
                    clean_str = re.sub(r'[,\uff0c]', '', match.group(1))
                    return float(clean_str)
                except:
                    continue
        
        # 如果都无法提取，返回0
        return 0.0
    
    def extract_numbers(self, content: str) -> Set[int]:
        """从投注内容中提取数字"""
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
        """计算金额匹配度 - 衡量资金分配的均衡性"""
        if not avgs or max(avgs) == 0:
            return 0
        return (min(avgs) / max(avgs)) * 100
    
    def get_similarity_indicator(self, similarity: float) -> str:
        """金额匹配度可视化指示器"""
        if similarity >= 90: 
            return "🟢"
        elif similarity >= 80: 
            return "🟡" 
        elif similarity >= 70: 
            return "🟠"
        else: 
            return "🔴"
    
    def analyze_accounts(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析账户数据"""
        # 提取金额列
        if '金额' in df.columns:
            df['投注金额'] = df['金额'].apply(self.extract_amount)
        else:
            df['投注金额'] = 0.0
        
        # 筛选特码玩法
        special_bets = df[df['玩法'].str.contains('特码|特别号', na=False)]
        
        # 按账户分组分析
        account_stats = {}
        
        for account, group in special_bets.groupby('会员账号'):
            all_numbers = set()
            total_amount = 0
            bet_count = len(group)
            
            for _, row in group.iterrows():
                numbers = self.extract_numbers(row['内容'])
                all_numbers.update(numbers)
                total_amount += row['投注金额']
            
            number_count = len(all_numbers)
            
            account_stats[account] = {
                'numbers': all_numbers,
                'number_count': number_count,
                'total_amount': total_amount,
                'bet_count': bet_count,
                'avg_amount_per_bet': total_amount / bet_count if bet_count > 0 else 0,
                'avg_amount_per_number': total_amount / number_count if number_count > 0 else 0
            }
        
        return account_stats
    
    def find_perfect_coverage_combinations(self, account_stats: Dict[str, Any]) -> List[Dict]:
        """寻找完美覆盖组合 - 增强版"""
        if not account_stats:
            return []
        
        accounts_list = list(account_stats.keys())
        all_combinations = []
        
        st.info(f"🔍 正在分析 {len(accounts_list)} 个账户的组合...")
        
        # 进度显示
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 分析2-4个账户的所有可能组合
        total_combinations = 0
        for r in range(2, min(5, len(accounts_list) + 1)):
            total_combinations += len(list(itertools.combinations(accounts_list, r)))
        
        processed = 0
        
        # 检查2-4个账户的组合
        for r in range(2, min(5, len(accounts_list) + 1)):
            for combo in itertools.combinations(accounts_list, r):
                processed += 1
                progress = processed / total_combinations
                progress_bar.progress(progress)
                status_text.text(f"正在检查 {r} 个账户的组合... ({processed}/{total_combinations})")
                
                # 检查是否覆盖1-49
                union_numbers = set()
                total_amount = 0
                avg_amounts = []
                
                for account in combo:
                    union_numbers.update(account_stats[account]['numbers'])
                    total_amount += account_stats[account]['total_amount']
                    avg_amounts.append(account_stats[account]['avg_amount_per_number'])
                
                # 检查是否完美覆盖
                if len(union_numbers) >= 49:  # 允许有重复，但至少要有49个不同的数字
                    missing_numbers = set(range(1, 50)) - union_numbers
                    coverage_percentage = (len(union_numbers) / 49) * 100
                    
                    # 计算金额匹配度
                    similarity = self.calculate_similarity(avg_amounts)
                    
                    combination_info = {
                        'accounts': list(combo),
                        'account_count': len(combo),
                        'total_amount': total_amount,
                        'avg_amount_per_number': total_amount / 49,
                        'similarity': similarity,
                        'similarity_indicator': self.get_similarity_indicator(similarity),
                        'coverage_percentage': coverage_percentage,
                        'covered_numbers': len(union_numbers),
                        'missing_numbers': list(missing_numbers) if missing_numbers else [],
                        'union_numbers': union_numbers
                    }
                    all_combinations.append(combination_info)
        
        progress_bar.empty()
        status_text.empty()
        
        # 按覆盖率和账户数量排序
        all_combinations.sort(key=lambda x: (x['coverage_percentage'], -x['account_count'], -x['similarity']), reverse=True)
        
        return all_combinations

    def analyze_coverage_quality(self, combinations: List[Dict]) -> Dict[str, Any]:
        """分析覆盖质量"""
        if not combinations:
            return {}
        
        best_combo = combinations[0]
        coverage_quality = {
            'best_coverage': best_combo['coverage_percentage'],
            'best_account_count': best_combo['account_count'],
            'total_combinations': len(combinations),
            'perfect_combinations': len([c for c in combinations if c['coverage_percentage'] == 100]),
            'good_combinations': len([c for c in combinations if c['coverage_percentage'] >= 95]),
            'average_similarity': np.mean([c['similarity'] for c in combinations]) if combinations else 0
        }
        
        return coverage_quality

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
    analyzer = EnhancedBettingAnalyzer()
    
    # 文件上传
    st.sidebar.header("📁 数据上传")
    uploaded_file = st.sidebar.file_uploader(
        "上传投注数据文件", 
        type=['csv', 'xlsx', 'xls'],
        help="支持CSV、Excel格式文件"
    )
    
    # 分析参数设置
    st.sidebar.header("⚙️ 分析参数")
    min_coverage = st.sidebar.slider("最小覆盖率 (%)", 80, 100, 95)
    max_accounts = st.sidebar.slider("最大账户数", 2, 6, 4)
    
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
                st.header("🔍 数据分析结果")
                
                # 按期号分析
                if '期号' in df_mapped.columns:
                    periods = df_mapped['期号'].unique()
                    
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        selected_period = st.selectbox("选择期号", periods)
                    
                    # 筛选当期数据
                    period_data = df_mapped[df_mapped['期号'] == selected_period]
                    
                    # 分析账户
                    account_stats = analyzer.analyze_accounts(period_data)
                    
                    # 显示账户统计
                    st.subheader("📈 账户统计")
                    if account_stats:
                        account_df = pd.DataFrame.from_dict(account_stats, orient='index')
                        account_df = account_df.reset_index().rename(columns={'index': '会员账号'})
                        
                        # 显示所有账户统计
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("总账户数", len(account_stats))
                        with col2:
                            avg_numbers = account_df['number_count'].mean()
                            st.metric("平均投注数字数", f"{avg_numbers:.1f}")
                        with col3:
                            if '投注金额' in period_data.columns:
                                total_bet = period_data['投注金额'].sum()
                                st.metric("总投注金额", f"¥{total_bet:,.2f}")
                        with col4:
                            valid_accounts = len(account_df[account_df['number_count'] > 0])
                            st.metric("有效账户数", valid_accounts)
                        
                        # 显示账户详情
                        with st.expander("📋 账户详情"):
                            st.dataframe(account_df)
                        
                        # 寻找覆盖组合
                        st.subheader("🎯 覆盖组合分析")
                        combinations = analyzer.find_perfect_coverage_combinations(account_stats)
                        
                        if combinations:
                            # 过滤符合条件的组合
                            filtered_combinations = [
                                c for c in combinations 
                                if c['coverage_percentage'] >= min_coverage 
                                and c['account_count'] <= max_accounts
                            ]
                            
                            if filtered_combinations:
                                # 分析覆盖质量
                                coverage_quality = analyzer.analyze_coverage_quality(filtered_combinations)
                                
                                st.success(f"🎉 找到 {len(filtered_combinations)} 个符合条件的覆盖组合")
                                
                                # 显示覆盖质量统计
                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    st.metric("完美覆盖组合", coverage_quality['perfect_combinations'])
                                with col2:
                                    st.metric("优质覆盖组合", coverage_quality['good_combinations'])
                                with col3:
                                    st.metric("最佳覆盖率", f"{coverage_quality['best_coverage']:.1f}%")
                                with col4:
                                    st.metric("平均匹配度", f"{coverage_quality['average_similarity']:.1f}%")
                                
                                # 显示最佳组合
                                best_combo = filtered_combinations[0]
                                st.subheader("🏆 最佳覆盖组合")
                                
                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    st.metric("账户数量", best_combo['account_count'])
                                with col2:
                                    st.metric("覆盖率", f"{best_combo['coverage_percentage']:.1f}%")
                                with col3:
                                    st.metric("总金额", f"¥{best_combo['total_amount']:,.2f}")
                                with col4:
                                    similarity = best_combo['similarity']
                                    indicator = best_combo['similarity_indicator']
                                    st.metric("金额匹配度", f"{similarity:.1f}% {indicator}")
                                
                                # 显示组合详情
                                with st.expander("📋 最佳组合详情"):
                                    st.write("**包含账户:**")
                                    for account in best_combo['accounts']:
                                        stats = account_stats[account]
                                        st.write(f"- **{account}**: {len(stats['numbers'])}个数字, "
                                               f"总金额 ¥{stats['total_amount']:,.2f}, "
                                               f"每号平均 ¥{stats['avg_amount_per_number']:,.2f}")
                                    
                                    if best_combo['missing_numbers']:
                                        st.warning(f"❌ 缺少号码: {best_combo['missing_numbers']}")
                                    else:
                                        st.success("✅ 完美覆盖所有1-49号码!")
                                
                                # 显示所有组合
                                with st.expander("📊 所有覆盖组合"):
                                    combo_df = pd.DataFrame(filtered_combinations)
                                    # 简化显示列
                                    display_cols = ['accounts', 'account_count', 'coverage_percentage', 
                                                  'total_amount', 'similarity', 'similarity_indicator']
                                    if 'missing_numbers' in combo_df.columns:
                                        display_cols.append('missing_numbers')
                                    st.dataframe(combo_df[display_cols])
                                
                                # 号码覆盖分析
                                with st.expander("🔢 号码覆盖分析"):
                                    if best_combo['coverage_percentage'] < 100:
                                        missing = best_combo['missing_numbers']
                                        st.write(f"**缺失号码 ({len(missing)}个):** {missing}")
                                    
                                    # 显示每个账户的号码分布
                                    st.write("**各账户号码分布:**")
                                    for account in best_combo['accounts']:
                                        numbers = account_stats[account]['numbers']
                                        st.write(f"- {account}: {sorted(list(numbers))}")
                                
                            else:
                                st.warning(f"⚠️ 未找到覆盖率 ≥{min_coverage}% 且账户数 ≤{max_accounts} 的组合")
                                st.info("""
                                **建议调整:**
                                - 降低最小覆盖率要求
                                - 增加最大账户数限制  
                                - 检查数据质量
                                """)
                        else:
                            st.warning("⚠️ 未找到任何覆盖组合")
                            st.info("""
                            **可能原因:**
                            - 账户投注号码重复度太高
                            - 单个账户覆盖号码太少
                            - 数据格式需要检查
                            """)
                    
                    else:
                        st.warning("⚠️ 未找到有效的特码投注数据")
                
                else:
                    st.warning("⚠️ 数据中未找到期号信息")
            
        except Exception as e:
            st.error(f"❌ 处理文件时出错: {str(e)}")
            st.info("请检查文件格式和数据内容是否正确")
    
    else:
        # 显示示例和使用说明
        st.info("💡 **使用说明**")
        st.markdown("""
        ### 上传文件要求:
        1. **文件格式**: CSV 或 Excel
        2. **必要列**: 必须包含会员账号、彩种、期号、玩法、内容
        3. **数据示例**:
           - 玩法列应包含"特码"或"特别号"
           - 内容列应包含1-49的数字
        
        ### 分析功能:
        - ✅ 自动识别各种列名格式
        - ✅ 智能提取投注金额
        - ✅ 检测2-4个账户的覆盖组合
        - ✅ 分析金额均衡性
        - ✅ 评估覆盖质量
        """)
        
        # 提供示例数据
        example_data = {
            '会员账号': ['user001', 'user002', 'user003', 'user004'],
            '彩种': ['六合彩', '六合彩', '六合彩', '六合彩'],
            '期号': ['2024001', '2024001', '2024001', '2024001'],
            '玩法': ['特码', '特码', '特码', '特码'],
            '内容': [
                '1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24',
                '13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34',
                '25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45',
                '35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,1,2,3,4,5,6,7,8,9,10'
            ],
            '金额': ['1000', '投注: 1200', '1500元', '￥2000']
        }
        
        example_df = pd.DataFrame(example_data)
        
        # 下载示例文件
        csv = example_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 下载示例CSV文件",
            data=csv,
            file_name="示例数据.csv",
            mime="text/csv"
        )

if __name__ == "__main__":
    main()
