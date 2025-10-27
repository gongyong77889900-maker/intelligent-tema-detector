import streamlit as st
import pandas as pd
import numpy as np
import re
from typing import Dict, List, Set, Tuple, Any
import itertools
from collections import defaultdict
import time
from io import BytesIO

# 设置页面
st.set_page_config(
    page_title="六合彩特码完美覆盖分析系统",
    page_icon="🎯",
    layout="wide"
)

# 标题和说明
st.title("🎯 六合彩特码完美覆盖分析系统")
st.markdown("### 基于数学完备性的完美组合检测与汇总")

class StrictLotteryCoverageAnalyzer:
    """严格版六合彩覆盖分析器 - 精确列名匹配"""
    
    def __init__(self):
        self.full_set = set(range(1, 50))
        
        # 完整的六合彩彩种列表
        self.target_lotteries = [
            '新澳门六合彩', '澳门六合彩', '香港六合彩', '一分六合彩',
            '五分六合彩', '三分六合彩', '香港⑥合彩', '分分六合彩',
            '台湾大乐透', '大发六合彩', '快乐6合彩'
        ]
        
        # 严格的列名映射字典 - 只使用您提供的列名
        self.column_mappings = {
            '会员账号': ['会员账号', '会员账户', '账号', '账户', '用户账号'],
            '彩种': ['彩种', '彩票种类', '游戏类型'],
            '期号': ['期号', '期数', '期次', '期'],
            '玩法': ['玩法', '玩法分类', '投注类型', '类型'],
            '内容': ['内容', '投注内容', '下注内容', '注单内容'],
            '金额': ['金额', '下注总额', '投注金额', '总额', '下注金额']
        }
    
    def strict_column_mapping(self, df):
        """严格版列名映射 - 只精确匹配提供的列名"""
        column_mapping = {}
        used_standard_cols = set()
        
        # 对每个标准列名，只检查精确匹配的列名
        for standard_col, possible_names in self.column_mappings.items():
            if standard_col in used_standard_cols:
                continue
                
            found_column = None
            for possible_name in possible_names:
                # 精确匹配 - 只匹配完全相同的列名
                if possible_name in df.columns:
                    found_column = possible_name
                    break
            
            if found_column:
                column_mapping[found_column] = standard_col
                used_standard_cols.add(standard_col)
            else:
                st.warning(f"⚠️ 未找到标准列名: {standard_col}")
        
        # 检查必要列是否都已识别
        required_columns = ['会员账号', '彩种', '期号', '玩法', '内容']
        missing_columns = [col for col in required_columns if col not in used_standard_cols]
        
        if missing_columns:
            st.error(f"❌ 缺少必要列: {missing_columns}")
            return None
        
        return column_mapping
    
    def extract_bet_amount(self, amount_text):
        """金额提取函数"""
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
            return 0.0
    
    def extract_numbers_from_content(self, content):
        """从内容中提取数字"""
        numbers = []
        content_str = str(content)
        
        number_matches = re.findall(r'\d+', content_str)
        for match in number_matches:
            num = int(match)
            if 1 <= num <= 49:
                numbers.append(num)
        
        return list(set(numbers))
    
    def calculate_similarity(self, avgs):
        """计算金额匹配度"""
        if not avgs or max(avgs) == 0:
            return 0
        return (min(avgs) / max(avgs)) * 100
    
    def get_similarity_indicator(self, similarity):
        """获取相似度颜色指示符"""
        if similarity >= 90: return "🟢"
        elif similarity >= 80: return "🟡"
        elif similarity >= 70: return "🟠"
        else: return "🔴"
    
    def find_perfect_combinations(self, account_numbers, account_amount_stats, account_bet_contents, min_avg_amount):
        """寻找完美组合 - 增加平均金额阈值"""
        all_results = {2: [], 3: [], 4: []}
        all_accounts = list(account_numbers.keys())
        
        account_sets = {account: set(numbers) for account, numbers in account_numbers.items()}
        
        # 搜索2账户组合
        for i, acc1 in enumerate(all_accounts):
            count1 = len(account_numbers[acc1])
            for j in range(i+1, len(all_accounts)):
                acc2 = all_accounts[j]
                count2 = len(account_numbers[acc2])
                
                if count1 + count2 != 49:
                    continue
                
                combined_set = account_sets[acc1] | account_sets[acc2]
                if len(combined_set) == 49:
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
                        'avg_amount_per_number': total_amount / 49,
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
                    
                    if count1 + count2 + count3 != 49:
                        continue
                    
                    combined_set = account_sets[acc1] | account_sets[acc2] | account_sets[acc3]
                    if len(combined_set) == 49:
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
                            'avg_amount_per_number': total_amount / 49,
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
        """分析特定期数和彩种 - 增加阈值参数"""
        has_amount_column = '金额' in group.columns
        
        account_numbers = {}
        account_amount_stats = {}
        account_bet_contents = {}

        for account in group['会员账号'].unique():
            account_data = group[group['会员账号'] == account]
            
            all_numbers = set()
            total_amount = 0
            bet_count = 0
            
            for _, row in account_data.iterrows():
                numbers = self.extract_numbers_from_content(row['内容'])
                all_numbers.update(numbers)
                
                if has_amount_column:
                    amount = row['投注金额']
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
            min_avg_amount
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
                'total_combinations': total_combinations,
                'all_combinations': all_combinations,
                'filtered_accounts': len(filtered_account_numbers)
            }
        
        return None

def create_download_data(all_results):
    """创建下载数据"""
    download_data = []
    
    for (period, lottery), result in all_results.items():
        for combo in result['all_combinations']:
            row = {
                '期号': period,
                '彩种': lottery,
                '账户数量': combo['account_count'],
                '账户组合': ' ↔ '.join(combo['accounts']),
                '总投注金额': combo['total_amount'],
                '平均每号金额': combo['avg_amount_per_number'],
                '金额匹配度': f"{combo['similarity']:.1f}%",
                '匹配度等级': combo['similarity_indicator']
            }
            
            # 添加各账户详情
            for i, account in enumerate(combo['accounts'], 1):
                row[f'账户{i}'] = account
                row[f'账户{i}投注金额'] = combo['individual_amounts'][account]
                row[f'账户{i}平均每号'] = combo['individual_avg_per_number'][account]
                row[f'账户{i}投注内容'] = combo['bet_contents'][account]
            
            download_data.append(row)
    
    return pd.DataFrame(download_data)

def main():
    analyzer = StrictLotteryCoverageAnalyzer()
    
    # 侧边栏设置
    st.sidebar.header("⚙️ 分析参数设置")
    
    # 阈值设置
    min_number_count = st.sidebar.slider(
        "账户投注号码数量阈值", 
        min_value=1, 
        max_value=30, 
        value=11,
        help="只分析投注号码数量大于等于此值的账户"
    )
    
    min_avg_amount = st.sidebar.slider(
        "平均每号金额阈值", 
        min_value=0, 
        max_value=10, 
        value=2,
        step=1,
        help="只分析平均每号金额大于等于此值的账户"
    )
    
    st.sidebar.markdown("---")
    
    # 文件上传
    st.sidebar.header("📁 数据上传")
    uploaded_file = st.sidebar.file_uploader(
        "上传投注数据文件", 
        type=['csv', 'xlsx', 'xls']
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
            
            # 严格版列名映射 - 隐藏详细过程
            column_mapping = analyzer.strict_column_mapping(df)
            
            if column_mapping is None:
                st.error("❌ 列名映射失败，无法继续分析")
                return
            
            df = df.rename(columns=column_mapping)
            st.success("✅ 列名映射完成")

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
                
                if has_amount_column:
                    # 应用金额提取
                    df_clean['投注金额'] = df_clean['金额'].apply(analyzer.extract_bet_amount)
                    total_bet_amount = df_clean['投注金额'].sum()
                    valid_amount_count = (df_clean['投注金额'] > 0).sum()
                    
                    st.success(f"💰 金额提取完成: 总投注额 {total_bet_amount:,.2f} 元")
                    st.info(f"📊 有效金额记录: {valid_amount_count:,} / {len(df_clean):,}")

                # 显示数据预览
                with st.expander("📊 数据预览"):
                    st.dataframe(df_clean.head(10))
                    st.write(f"数据形状: {df_clean.shape}")
                    
                    # 显示彩种分布
                    if '彩种' in df_clean.columns:
                        st.write("🎲 彩种分布:")
                        st.write(df_clean['彩种'].value_counts())
                    
                    # 显示玩法分布
                    if '玩法' in df_clean.columns:
                        st.write("🎯 玩法分布:")
                        st.write(df_clean['玩法'].value_counts())
                    
                    # 显示金额分布
                    if has_amount_column:
                        st.write("💰 金额统计:")
                        st.write(f"- 总投注额: {total_bet_amount:,.2f} 元")
                        st.write(f"- 平均每注: {df_clean['投注金额'].mean():.2f} 元")
                        st.write(f"- 最大单注: {df_clean['投注金额'].max():.2f} 元")
                        st.write(f"- 最小单注: {df_clean['投注金额'].min():.2f} 元")

                # 筛选特码数据
                df_target = df_clean[
                    (df_clean['彩种'].isin(analyzer.target_lotteries)) & 
                    (df_clean['玩法'] == '特码')
                ]
                
                st.write(f"✅ 特码玩法数据行数: {len(df_target):,}")

                if len(df_target) == 0:
                    st.error("❌ 未找到特码玩法数据")
                    st.info("""
                    **可能原因:**
                    1. 彩种名称不匹配 - 当前支持的六合彩类型:
                       - 新澳门六合彩, 澳门六合彩, 香港六合彩
                       - 一分六合彩, 五分六合彩, 三分六合彩
                       - 香港⑥合彩, 分分六合彩, 台湾大乐透
                       - 大发六合彩, 快乐6合彩
                    
                    2. 玩法名称不是'特码'
                    3. 数据格式问题
                    """)
                    return

                # 分析数据
                grouped = df_target.groupby(['期号', '彩种'])
                all_period_results = {}
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                total_groups = len(grouped)
                
                for idx, ((period, lottery), group) in enumerate(grouped):
                    status_text.text(f"分析进度: {idx+1}/{total_groups} (期号: {period})")
                    progress_bar.progress((idx+1) / total_groups)
                    
                    if len(group) >= 2:
                        result = analyzer.analyze_period_lottery(
                            group, period, lottery, min_number_count, min_avg_amount
                        )
                        if result:
                            all_period_results[(period, lottery)] = result

                progress_bar.empty()
                status_text.empty()

                # 显示结果 - 采用合并的层级结构
                st.header("📊 完美覆盖组合检测结果")
                
                if all_period_results:
                    # 汇总统计
                    total_combinations = 0
                    total_filtered_accounts = 0
                    
                    for (period, lottery), result in all_period_results.items():
                        total_combinations += result['total_combinations']
                        total_filtered_accounts += result['filtered_accounts']
                    
                    # 显示汇总信息
                    st.subheader("📈 检测汇总")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("总完美组合数", total_combinations)
                    with col2:
                        st.metric("分析期数", len(all_period_results))
                    with col3:
                        st.metric("有效账户数", total_filtered_accounts)
                    with col4:
                        st.metric("涉及彩种", len(set([lottery for (_, lottery) in all_period_results.keys()])))
                    
                    # 按彩种和期号显示结果 - 合并层级
                    for (period, lottery), result in all_period_results.items():
                        total_combinations = result['total_combinations']
                        
                        # 创建折叠筐，默认展开，标题合并彩种和期号
                        with st.expander(
                            f"🎯 {lottery} - 期号: {period}（{total_combinations}组）", 
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
                                    if has_amount_column:
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
                                    if has_amount_column:
                                        st.write(f"  - 总投注: ¥{amount_info:,.2f}")
                                        st.write(f"  - 平均每号: ¥{avg_info:,.2f}")
                                    st.write(f"  - 投注内容: {numbers}")
                                
                                # 添加分隔线（除了最后一个）
                                if idx < len(result['all_combinations']):
                                    st.markdown("---")
                    
                    # 导表功能
                    st.markdown("---")
                    st.subheader("📥 数据导出")
                    
                    if st.button("📊 导出完美组合数据"):
                        download_df = create_download_data(all_period_results)
                        
                        # 转换为Excel
                        output = BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            download_df.to_excel(writer, index=False, sheet_name='完美组合数据')
                        
                        # 提供下载
                        st.download_button(
                            label="📥 下载Excel文件",
                            data=output.getvalue(),
                            file_name=f"六合彩完美组合分析_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        
                        st.success("✅ 数据导出准备完成！")
                
                else:
                    st.error("❌ 未找到完美覆盖组合")
                    st.info(f"""
                    **可能原因:**
                    - 有效账户数量不足（当前阈值: 号码数量 ≥ {min_number_count}, 平均金额 ≥ {min_avg_amount}）
                    - 账户投注号码无法形成完美覆盖
                    - 数据质量需要检查
                    
                    **建议:**
                    - 尝试降低阈值设置
                    - 检查数据质量
                    """)
            
            else:
                st.error(f"❌ 缺少必要数据列，可用列: {available_columns}")
                st.info("💡 请确保文件包含以下必要列:")
                for col in ['会员账号', '彩种', '期号', '玩法', '内容']:
                    st.write(f"- {col}: {analyzer.column_mappings[col]}")
        
        except Exception as e:
            st.error(f"❌ 处理文件时出错: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
    
    else:
        st.info("💡 **六合彩完美覆盖分析系统**")
        st.markdown("""
        ### 系统功能:
        - 🎯 **严格列名识别**: 只识别指定的列名格式
        - 💰 **金额提取**: 支持多种金额格式
        - ⚙️ **参数调节**: 可调节号码数量和金额阈值
        - 📊 **结果汇总**: 按彩种和期号分类显示检测结果
        - 📥 **数据导出**: 一键导出所有完美组合数据
        
        ### 支持的列名格式:
        """)
        
        for standard_col, possible_names in analyzer.column_mappings.items():
            st.write(f"- **{standard_col}**: {', '.join(possible_names)}")
        
        st.markdown("""
        ### 数据要求:
        - 必须包含: 会员账号, 彩种, 期号, 玩法, 内容
        - 玩法必须为'特码'
        - 彩种必须是六合彩类型
        """)

if __name__ == "__main__":
    main()
