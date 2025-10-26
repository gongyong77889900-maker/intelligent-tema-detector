import pandas as pd
import streamlit as st
import io
import re
import numpy as np
from itertools import combinations
import time
from collections import defaultdict

# Streamlit页面配置
st.set_page_config(
    page_title="智能特码对刷分析系统",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

class TeMaAnalysisSystem:
    def __init__(self):
        self.target_lotteries = [
            '新澳门六合彩', '澳门六合彩', '香港六合彩', '一分六合彩',
            '五分六合彩', '三分六合彩', '香港⑥合彩', '分分六合彩'
        ]
    
    def extract_bet_amount(self, amount_text):
        """从复杂文本中提取投注金额"""
        try:
            if pd.isna(amount_text):
                return 0
            
            # 确保输入是字符串
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

    def extract_numbers_from_content(self, content):
        """从内容中提取所有1-49的数字"""
        try:
            numbers = []
            # 确保content是字符串类型
            content_str = str(content) if not isinstance(content, str) else content
            
            # 使用正则表达式提取所有数字
            number_matches = re.findall(r'\d+', content_str)
            for match in number_matches:
                try:
                    num = int(match)
                    if 1 <= num <= 49:
                        numbers.append(num)
                except ValueError:
                    continue
            
            return list(set(numbers))  # 去重
        except Exception as e:
            st.warning(f"提取数字失败: {content}, 错误: {e}")
            return []

    def format_numbers_display(self, numbers):
        """格式化数字显示，确保两位数显示"""
        formatted = []
        for num in sorted(numbers):
            formatted.append(f"{num:02d}")
        return ", ".join(formatted)

    def calculate_similarity(self, avgs):
        """计算金额匹配度"""
        if not avgs or max(avgs) == 0:
            return 0
        return (min(avgs) / max(avgs)) * 100

    def get_similarity_indicator(self, similarity):
        """获取相似度颜色指示符"""
        if similarity >= 90:
            return "🟢"
        elif similarity >= 80:
            return "🟡"
        elif similarity >= 70:
            return "🟠"
        else:
            return "🔴"

    def find_column_mapping(self, df):
        """智能列名映射"""
        column_mapping = {}
        used_standard_cols = set()
        
        # 确保列名是字符串
        df_columns = [str(col) for col in df.columns]
        
        for col in df_columns:
            col_str = col.lower().strip()
            
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

    def safe_filter_data(self, df, condition):
        """安全的数据筛选方法，避免Series布尔值歧义"""
        try:
            # 使用query方法避免布尔Series歧义
            if isinstance(condition, str):
                return df.query(condition)
            else:
                # 如果是布尔Series，使用.loc
                return df.loc[condition]
        except:
            # 如果上述方法失败，使用传统方法但添加明确的条件
            mask = condition.copy()
            return df[mask]

    def process_data(self, df):
        """处理上传的数据"""
        try:
            # 智能列名映射
            column_mapping = self.find_column_mapping(df)
            
            if column_mapping:
                df = df.rename(columns=column_mapping)
                st.success(f"✅ 自动识别列名: {column_mapping}")
            else:
                st.warning("⚠️ 无法自动识别列名，使用原始列名")

            # 检查必要列
            required_columns = ['会员账号', '彩种', '期号', '玩法分类', '内容']
            available_columns = []

            for col in required_columns:
                if col in df.columns:
                    available_columns.append(col)

            has_amount_column = '金额' in df.columns
            if has_amount_column:
                available_columns.append('金额')
                st.success("💰 检测到金额列，将进行金额分析")
            else:
                st.warning("⚠️ 未检测到金额列，将只分析号码覆盖")

            if len(available_columns) >= 5:
                df_clean = df[available_columns].copy()
                
                # 移除空值
                df_clean = df_clean.dropna(subset=required_columns)
                
                # 数据类型转换 - 修复：确保所有列都是字符串类型
                for col in available_columns:
                    # 使用更安全的方式转换数据类型
                    df_clean[col] = df_clean[col].apply(lambda x: str(x).strip() if pd.notna(x) else '')
                
                # 如果有金额列，提取金额
                if has_amount_column:
                    try:
                        df_clean['投注金额'] = df_clean['金额'].apply(self.extract_bet_amount)
                        total_bet_amount = df_clean['投注金额'].sum()
                        avg_bet_amount = df_clean['投注金额'].mean()
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("💰 总投注额", f"{total_bet_amount:,.2f} 元")
                        with col2:
                            st.metric("📈 平均每注金额", f"{avg_bet_amount:,.2f} 元")
                    except Exception as e:
                        st.error(f"❌ 金额提取失败: {str(e)}")
                        df_clean['投注金额'] = 0
                
                # 显示数据概览
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("📊 总记录数", f"{len(df_clean):,}")
                with col2:
                    st.metric("🎲 彩种数量", df_clean['彩种'].nunique())
                with col3:
                    st.metric("📅 期号数量", df_clean['期号'].nunique())
                
                # 修复：安全筛选目标彩种和特码玩法
                try:
                    # 方法1：使用位运算符，但要确保每个条件都是明确的布尔Series
                    lottery_mask = df_clean['彩种'].isin(self.target_lotteries)
                    category_mask = (df_clean['玩法分类'] == '特码')
                    
                    # 明确使用位运算符组合条件
                    combined_mask = lottery_mask & category_mask
                    
                    # 使用.loc进行安全筛选
                    df_target = df_clean.loc[combined_mask].copy()
                    
                    st.success(f"✅ 筛选条件: 彩种包含目标彩种 + 玩法分类='特码'")
                    
                except Exception as e:
                    st.error(f"❌ 数据筛选失败: {str(e)}")
                    # 方法2：使用query方法
                    try:
                        target_lotteries_str = "', '".join(self.target_lotteries)
                        query_str = f"彩种 in ['{target_lotteries_str}'] and 玩法分类 == '特码'"
                        df_target = df_clean.query(query_str).copy()
                        st.success("✅ 使用query方法筛选成功")
                    except Exception as e2:
                        st.error(f"❌ query方法也失败: {str(e2)}")
                        return None
                
                if len(df_target) == 0:
                    st.error("❌ 未找到符合条件的特码数据")
                    st.info("请检查以下内容：")
                    st.info(f"- 彩种是否包含: {', '.join(self.target_lotteries)}")
                    st.info("- 玩法分类是否为'特码'")
                    
                    # 显示实际的数据分布
                    st.subheader("📊 实际数据分布")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**彩种分布:**")
                        st.write(df_clean['彩种'].value_counts().head(10))
                    with col2:
                        st.write("**玩法分类分布:**")
                        st.write(df_clean['玩法分类'].value_counts().head(10))
                    
                    return None
                
                st.success(f"✅ 特码玩法数据: {len(df_target):,} 行")
                
                # 显示筛选后的数据预览
                with st.expander("🔍 筛选后数据预览", expanded=False):
                    st.dataframe(df_target.head(10))
                    st.write(f"筛选后数据形状: {df_target.shape}")
                
                return df_target
            else:
                st.error(f"❌ 缺少必要列，可用列: {available_columns}")
                st.error(f"❌ 需要的列: {required_columns}")
                return None
                
        except Exception as e:
            st.error(f"❌ 数据处理过程中出错: {str(e)}")
            import traceback
            st.error(f"详细错误信息:\n{traceback.format_exc()}")
            return None

    def analyze_simple_patterns(self, df_target):
        """简化的特码分析模式"""
        try:
            st.header("🔍 特码分析结果")
            
            # 按期号和彩种分组
            period_lottery_groups = df_target.groupby(['期号', '彩种'])
            
            analysis_results = []
            
            for (period, lottery), group_data in period_lottery_groups:
                # 分析每个期号+彩种的组合
                result = self.analyze_single_period(group_data, period, lottery)
                if result:
                    analysis_results.append(result)
            
            if analysis_results:
                self.display_simple_results(analysis_results)
            else:
                st.warning("⚠️ 未找到明显的对刷模式")
                
        except Exception as e:
            st.error(f"❌ 分析过程中出错: {str(e)}")

    def analyze_single_period(self, df_period, period, lottery):
        """分析单个期号的数据"""
        try:
            # 统计每个账户的特码数量
            account_stats = {}
            
            for account in df_period['会员账号'].unique():
                account_data = df_period[df_period['会员账号'] == account]
                all_numbers = set()
                
                for _, row in account_data.iterrows():
                    numbers = self.extract_numbers_from_content(row['内容'])
                    all_numbers.update(numbers)
                
                if all_numbers:
                    account_stats[account] = {
                        'number_count': len(all_numbers),
                        'numbers': sorted(all_numbers),
                        'bet_count': len(account_data),
                        'total_amount': account_data['投注金额'].sum() if '投注金额' in account_data.columns else 0
                    }
            
            # 筛选特码数量较多的账户（>11个）
            filtered_accounts = {acc: stats for acc, stats in account_stats.items() 
                               if stats['number_count'] > 11}
            
            if len(filtered_accounts) >= 2:
                return {
                    'period': period,
                    'lottery': lottery,
                    'total_accounts': len(account_stats),
                    'filtered_accounts': len(filtered_accounts),
                    'account_stats': filtered_accounts
                }
            
            return None
            
        except Exception as e:
            st.warning(f"分析期号 {period} 时出错: {str(e)}")
            return None

    def display_simple_results(self, results):
        """显示简化版的分析结果"""
        st.subheader("📈 分析统计")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🎯 有效期数", len(results))
        with col2:
            total_filtered = sum(r['filtered_accounts'] for r in results)
            st.metric("👥 可疑账户", total_filtered)
        with col3:
            avg_numbers = np.mean([len(r['account_stats']) for r in results])
            st.metric("📊 平均账户数", f"{avg_numbers:.1f}")
        
        # 显示每个期号的详细结果
        st.subheader("📋 详细分析")
        
        for result in results:
            with st.expander(f"📅 期号: {result['period']} | 彩种: {result['lottery']} | 可疑账户: {result['filtered_accounts']}个", expanded=False):
                
                for account, stats in result['account_stats'].items():
                    col1, col2, col3, col4 = st.columns([2, 2, 2, 4])
                    
                    with col1:
                        st.write(f"**{account}**")
                    with col2:
                        st.write(f"{stats['number_count']}个特码")
                    with col3:
                        st.write(f"{stats['bet_count']}次投注")
                    with col4:
                        if stats['total_amount'] > 0:
                            st.write(f"总金额: {stats['total_amount']:,.0f}元")
                    
                    # 显示特码内容（前20个）
                    numbers_display = self.format_numbers_display(stats['numbers'][:20])
                    if len(stats['numbers']) > 20:
                        numbers_display += f" ... (共{len(stats['numbers'])}个)"
                    st.write(f"特码: `{numbers_display}`")

def main():
    st.title("🎯 智能特码对刷分析系统")
    st.markdown("---")
    
    # 系统介绍
    with st.expander("📖 系统介绍", expanded=True):
        st.markdown("""
        ### 系统功能
        - **智能检测**：自动识别六合彩特码对刷行为
        - **完美覆盖分析**：检测账户组合是否完美覆盖1-49所有号码
        - **金额匹配度**：分析对刷账户之间的金额匹配程度
        - **多维度统计**：提供详细的投注统计和模式分析

        ### 支持彩种
        - 新澳门六合彩、澳门六合彩、香港六合彩
        - 一分六合彩、五分六合彩、三分六合彩
        - 香港⑥合彩、分分六合彩

        ### 数据要求
        - 必须包含：会员账号、期号、玩法分类、内容
        - 可选包含：金额列（用于金额分析）
        """)
    
    # 文件上传
    st.header("📁 数据上传")
    uploaded_file = st.file_uploader(
        "请上传Excel文件 (支持 .xlsx, .xls)", 
        type=['xlsx', 'xls'],
        help="请确保文件包含必要的列：会员账号、期号、玩法分类、内容"
    )
    
    if uploaded_file is not None:
        try:
            # 读取文件
            df = pd.read_excel(uploaded_file)
            st.success(f"✅ 已上传文件: {uploaded_file.name}")
            
            # 显示数据预览
            with st.expander("📋 数据预览", expanded=False):
                st.dataframe(df.head(10))
                st.write(f"数据形状: {df.shape}")
                st.write("列名:", list(df.columns))
            
            # 初始化分析系统
            analyzer = TeMaAnalysisSystem()
            
            # 处理数据
            df_target = analyzer.process_data(df)
            
            if df_target is not None:
                st.success("✅ 数据预处理完成")
                
                if st.button("🚀 开始特码对刷分析", type="primary"):
                    with st.spinner("🔍 正在分析特码对刷模式..."):
                        analyzer.analyze_simple_patterns(df_target)
            
        except Exception as e:
            st.error(f"❌ 处理文件时出错: {str(e)}")
            import traceback
            st.error(f"详细错误信息:\n{traceback.format_exc()}")

if __name__ == "__main__":
    main()
