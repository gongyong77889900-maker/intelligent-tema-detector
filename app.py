import streamlit as st
import pandas as pd
import io
import itertools
import re
import numpy as np
from io import BytesIO

# 设置页面
st.set_page_config(
    page_title="特码完美覆盖分析系统",
    page_icon="🎯",
    layout="wide"
)

# 主标题
st.title("🎯 特码完美覆盖分析系统")
st.markdown("📊 支持按期数+彩种分别分析 + 完整组合展示 + 智能最优评选")

class ColumnMapper:
    """列名映射器 - 处理重复列名和列名识别"""
    
    def __init__(self):
        self.column_mappings = {
            '会员账号': ['会员账号', '会员账户', '账号', '账户', '用户账号'],
            '彩种': ['彩种', '彩票种类', '游戏类型'],
            '期号': ['期号', '期数', '期次', '期'],
            '玩法': ['玩法', '玩法分类', '投注类型', '类型'],
            '内容': ['内容', '投注内容', '下注内容', '注单内容'],
            '金额': ['金额', '下注总额', '投注金额', '总额', '下注金额']
        }
    
    def find_correct_columns(self, df):
        """智能识别列名并处理重复列名"""
        column_mapping = {}
        used_standard_cols = set()
        duplicate_suffix = 1
        
        # 处理重复列名
        original_columns = list(df.columns)
        cleaned_columns = []
        
        for col in original_columns:
            col_str = str(col).strip()
            if col_str in cleaned_columns:
                # 处理重复列名
                new_col_name = f"{col_str}_{duplicate_suffix}"
                cleaned_columns.append(new_col_name)
                duplicate_suffix += 1
            else:
                cleaned_columns.append(col_str)
        
        # 更新DataFrame列名
        df.columns = cleaned_columns
        
        # 列名映射
        for col in cleaned_columns:
            col_lower = col.lower()
            matched = False
            
            for standard_col, keywords in self.column_mappings.items():
                if standard_col not in used_standard_cols:
                    for keyword in keywords:
                        if keyword.lower() in col_lower:
                            column_mapping[col] = standard_col
                            used_standard_cols.add(standard_col)
                            matched = True
                            break
                if matched:
                    break
        
        return column_mapping, df

    def rename_columns(self, df, column_mapping):
        """重命名列"""
        if column_mapping:
            return df.rename(columns=column_mapping)
        return df

# 文件上传 - 步骤1
st.header("📁 步骤1：上传Excel文件")
uploaded_file = st.file_uploader("请上传Excel文件", type=['xlsx', 'xls'])

if uploaded_file is not None:
    try:
        # 初始化列名映射器
        mapper = ColumnMapper()
        
        # 读取数据
        df = pd.read_excel(uploaded_file)
        st.success(f"✅ 已上传文件: {uploaded_file.name}")
        st.info(f"📈 数据维度: {df.shape}")
        
        # 显示原始列名
        st.write("📋 原始列名:", list(df.columns))
        
        # 智能列名识别和处理
        column_mapping, df_processed = mapper.find_correct_columns(df)
        df = mapper.rename_columns(df_processed, column_mapping)
        
        st.write("🔄 自动识别的列映射:", column_mapping)
        st.success("✅ 列名处理和重命名完成")
        st.write("🎯 处理后的列名:", list(df.columns))
        
        # 数据预览
        st.subheader("📊 数据预览")
        st.dataframe(df.head())
        
        # 数据清理 - 步骤2
        st.header("🔍 步骤2：数据清理与预处理")
        
        def extract_bet_amount(amount_text):
            """从复杂文本中提取投注金额"""
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
                return 0

        # 检查必要列
        required_columns = ['会员账号', '彩种', '期号', '玩法', '内容']
        available_columns = []
        
        for col in required_columns:
            if col in df.columns:
                available_columns.append(col)
        
        has_amount_column = '金额' in df.columns
        if has_amount_column:
            available_columns.append('金额')
            st.success("💰 ✅ 检测到金额列，将进行金额分析")
        else:
            st.warning("⚠️ 未检测到金额列，将只分析号码覆盖")
        
        if len(available_columns) >= 5:
            df_clean = df[available_columns].copy()
            
            # 移除空值
            initial_count = len(df_clean)
            df_clean = df_clean.dropna(subset=required_columns)
            after_count = len(df_clean)
            
            if initial_count != after_count:
                st.warning(f"⚠️ 移除了 {initial_count - after_count} 行空值数据")
            
            # 数据类型转换
            for col in available_columns:
                df_clean[col] = df_clean[col].astype(str).str.strip()
            
            # 提取金额
            if has_amount_column:
                df_clean['投注金额'] = df_clean['金额'].apply(extract_bet_amount)
                total_bet_amount = df_clean['投注金额'].sum()
                avg_bet_amount = df_clean['投注金额'].mean()
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("💰 总投注额", f"{total_bet_amount:,.2f} 元")
                with col2:
                    st.metric("📈 平均每注金额", f"{avg_bet_amount:,.2f} 元")
            
            st.success(f"✅ 清理后数据行数: {len(df_clean):,}")
            
            # 数据分布
            col1, col2, col3 = st.columns(3)
            with col1:
                st.subheader("🎲 彩种分布")
                st.write(df_clean['彩种'].value_counts())
            with col2:
                st.subheader("📅 期号分布")
                st.write(df_clean['期号'].value_counts().head(10))
            with col3:
                st.subheader("🎯 玩法分类分布")
                st.write(df_clean['玩法'].value_counts())
            
            # 特码分析 - 步骤3
            st.header("🎯 步骤3：特码完美覆盖分析")
            
            # 定义目标彩种
            target_lotteries = [
                '新澳门六合彩', '澳门六合彩', '香港六合彩', '一分六合彩',
                '五分六合彩', '三分六合彩', '香港⑥合彩', '分分六合彩'
            ]
            
            # 筛选特码数据
            df_target = df_clean[
                (df_clean['彩种'].isin(target_lotteries)) & 
                (df_clean['玩法'] == '特码')
            ]
            
            st.info(f"✅ 特码玩法数据行数: {len(df_target):,}")
            
            if len(df_target) == 0:
                st.error("❌ 未找到特码玩法数据，请检查：")
                st.write("1. 彩种是否包含:", target_lotteries)
                st.write("2. 玩法列是否包含'特码'")
                st.write("3. 数据样例:")
                st.write(df_clean[df_clean['彩种'].isin(target_lotteries)]['玩法'].value_counts())
                st.stop()
            
            if has_amount_column:
                total_target_amount = df_target['投注金额'].sum()
                avg_target_amount = df_target['投注金额'].mean()
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("🎯 特码总投注额", f"{total_target_amount:,.2f} 元")
                with col2:
                    st.metric("🎯 特码平均金额", f"{avg_target_amount:,.2f} 元")
            
            # 分析函数
            def extract_numbers_from_content(content):
                """从内容中提取所有1-49的数字"""
                numbers = []
                content_str = str(content)
                
                number_matches = re.findall(r'\d+', content_str)
                for match in number_matches:
                    try:
                        num = int(match)
                        if 1 <= num <= 49:
                            numbers.append(num)
                    except ValueError:
                        continue
                
                return list(set(numbers))
            
            def format_numbers_display(numbers):
                """格式化数字显示"""
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
                """获取相似度指示符"""
                if similarity >= 90:
                    return "🟢"
                elif similarity >= 80:
                    return "🟡"
                elif similarity >= 70:
                    return "🟠"
                else:
                    return "🔴"
            
            def analyze_period_lottery_combination(df_period_lottery, period, lottery):
                """分析特定期数和彩种的组合"""
                st.write(f"🔍 正在分析: 期号[{period}] - 彩种[{lottery}] - 数据量: {len(df_period_lottery)}行")
                
                # 按账户提取数据
                account_numbers = {}
                account_amount_stats = {}
                account_bet_contents = {}
                
                accounts = df_period_lottery['会员账号'].unique()
                
                for account in accounts:
                    account_data = df_period_lottery[df_period_lottery['会员账号'] == account]
                    
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
                
                # 过滤账户（投注数字>11）
                filtered_account_numbers = {}
                filtered_account_amount_stats = {}
                filtered_account_bet_contents = {}
                
                for account, numbers in account_numbers.items():
                    num_count = len(numbers)
                    if num_count > 11:  # 降低门槛到>11
                        filtered_account_numbers[account] = numbers
                        filtered_account_amount_stats[account] = account_amount_stats[account]
                        filtered_account_bet_contents[account] = account_bet_contents[account]
                
                st.write(f"👥 有效账户(数字>11): {len(filtered_account_numbers)}个")
                
                if len(filtered_account_numbers) < 2:
                    st.warning(f"❌ 期号[{period}]有效账户不足2个，无法进行组合分析")
                    return None
                
                # 搜索完美组合
                def find_perfect_combinations(account_numbers, account_amount_stats, account_bet_contents):
                    """搜索完美组合"""
                    all_results = {2: [], 3: []}
                    all_accounts = list(account_numbers.keys())
                    
                    # 搜索2账户组合
                    st.write("🔍 搜索2账户组合...")
                    found_2 = 0
                    
                    for i, acc1 in enumerate(all_accounts):
                        count1 = len(account_numbers[acc1])
                        
                        for j in range(i+1, len(all_accounts)):
                            acc2 = all_accounts[j]
                            count2 = len(account_numbers[acc2])
                            
                            # 检查组合
                            combined_numbers = set(account_numbers[acc1]) | set(account_numbers[acc2])
                            coverage_count = len(combined_numbers)
                            coverage_rate = (coverage_count / 49) * 100
                            
                            if coverage_count >= 45:  # 覆盖率超过90%
                                total_amount = account_amount_stats[acc1]['total_amount'] + account_amount_stats[acc2]['total_amount']
                                avg_amount_per_number = total_amount / coverage_count if coverage_count > 0 else 0
                                
                                avgs = [
                                    account_amount_stats[acc1]['avg_amount_per_number'],
                                    account_amount_stats[acc2]['avg_amount_per_number']
                                ]
                                similarity = calculate_similarity(avgs)
                                
                                result_data = {
                                    'accounts': (acc1, acc2),
                                    'account_count': 2,
                                    'total_digits': coverage_count,
                                    'coverage_rate': coverage_rate,
                                    'numbers': combined_numbers,
                                    'total_amount': total_amount,
                                    'avg_amount_per_number': avg_amount_per_number,
                                    'similarity': similarity,
                                    'similarity_indicator': get_similarity_indicator(similarity),
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
                                found_2 += 1
                    
                    st.write(f"✅ 找到2账户组合: {found_2}个")
                    
                    # 搜索3账户组合（简化）
                    if len(all_accounts) >= 3:
                        st.write("🔍 搜索3账户组合...")
                        found_3 = 0
                        
                        for i, acc1 in enumerate(all_accounts):
                            for j in range(i+1, len(all_accounts)):
                                acc2 = all_accounts[j]
                                for k in range(j+1, len(all_accounts)):
                                    acc3 = all_accounts[k]
                                    
                                    combined_numbers = (set(account_numbers[acc1]) | 
                                                      set(account_numbers[acc2]) | 
                                                      set(account_numbers[acc3]))
                                    coverage_count = len(combined_numbers)
                                    coverage_rate = (coverage_count / 49) * 100
                                    
                                    if coverage_count >= 45:
                                        total_amount = (account_amount_stats[acc1]['total_amount'] + 
                                                      account_amount_stats[acc2]['total_amount'] + 
                                                      account_amount_stats[acc3]['total_amount'])
                                        avg_amount_per_number = total_amount / coverage_count
                                        
                                        avgs = [
                                            account_amount_stats[acc1]['avg_amount_per_number'],
                                            account_amount_stats[acc2]['avg_amount_per_number'],
                                            account_amount_stats[acc3]['avg_amount_per_number']
                                        ]
                                        similarity = calculate_similarity(avgs)
                                        
                                        result_data = {
                                            'accounts': (acc1, acc2, acc3),
                                            'account_count': 3,
                                            'total_digits': coverage_count,
                                            'coverage_rate': coverage_rate,
                                            'numbers': combined_numbers,
                                            'total_amount': total_amount,
                                            'avg_amount_per_number': avg_amount_per_number,
                                            'similarity': similarity,
                                            'similarity_indicator': get_similarity_indicator(similarity),
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
                                        found_3 += 1
                        
                        st.write(f"✅ 找到3账户组合: {found_3}个")
                    
                    return all_results
                
                # 执行搜索
                all_results = find_perfect_combinations(filtered_account_numbers, filtered_account_amount_stats, filtered_account_bet_contents)
                total_combinations = sum(len(results) for results in all_results.values())
                
                if total_combinations > 0:
                    # 选择最优组合
                    all_combinations = []
                    for results in all_results.values():
                        all_combinations.extend(results)
                    
                    # 按覆盖率和匹配度排序
                    all_combinations.sort(key=lambda x: (-x['coverage_rate'], -x['similarity']))
                    best_result = all_combinations[0] if all_combinations else None
                    
                    return {
                        'period': period,
                        'lottery': lottery,
                        'total_accounts': len(account_numbers),
                        'filtered_accounts': len(filtered_account_numbers),
                        'total_combinations': total_combinations,
                        'best_result': best_result,
                        'all_results': all_results
                    }
                else:
                    st.warning(f"❌ 期号[{period}]未找到高覆盖率组合")
                    return None
            
            # 按期数和彩种分组分析
            st.subheader("📊 按期数和彩种分析")
            
            # 选择要分析的期数
            unique_periods = df_target['期号'].unique()
            if len(unique_periods) == 0:
                st.error("❌ 没有找到期号数据")
                st.stop()
            
            selected_periods = st.multiselect(
                "选择要分析的期号（可选，默认分析所有期号）",
                options=unique_periods,
                default=unique_periods[:min(10, len(unique_periods))]  # 默认选择前10个
            )
            
            if not selected_periods:
                st.warning("请选择至少一个期号进行分析")
                st.stop()
            
            # 过滤选中的期数
            df_filtered = df_target[df_target['期号'].isin(selected_periods)]
            
            # 分析参数设置
            col1, col2 = st.columns(2)
            with col1:
                min_coverage = st.slider("最小覆盖率(%)", 50, 100, 90)
            with col2:
                min_account_numbers = st.slider("每个账户最小数字数", 5, 20, 12)
            
            # 开始分析按钮
            if st.button("🚀 开始分析", type="primary"):
                grouped = df_filtered.groupby(['期号', '彩种'])
                all_period_results = {}
                
                total_groups = len(grouped)
                if total_groups == 0:
                    st.error("❌ 没有找到符合条件的期数数据")
                    st.stop()
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                groups_list = list(grouped)
                for idx, ((period, lottery), group) in enumerate(groups_list):
                    status_text.text(f"分析进度: {idx + 1}/{total_groups} - 期号: {period}")
                    progress_bar.progress((idx + 1) / total_groups)
                    
                    if len(group) >= 3:  # 降低数据量要求
                        result = analyze_period_lottery_combination(group, period, lottery)
                        if result and result['best_result']['coverage_rate'] >= min_coverage:
                            all_period_results[(period, lottery)] = result
                
                progress_bar.empty()
                status_text.empty()
                
                # 🏆 各期最优组合汇总 - 默认展开显示
                if all_period_results:
                    st.header("🏆 各期最优组合汇总")
                    st.success(f"🎉 分析完成！共找到 {len(all_period_results)} 个有效期数组合")
                    
                    # 显示所有结果，不使用expander，直接展开
                    for (period, lottery), result in all_period_results.items():
                        best = result['best_result']
                        accounts = best['accounts']
                        
                        # 创建卡片式显示
                        st.markdown("---")
                        st.subheader(f"📅 期号: {period} | 彩种: {lottery}")
                        
                        # 基本信息
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("🎯 号码覆盖率", f"{best['coverage_rate']:.1f}%")
                        with col2:
                            st.metric("👥 账户数量", len(accounts))
                        with col3:
                            if has_amount_column:
                                st.metric("💰 总投注金额", f"{best['total_amount']:,.2f} 元")
                        with col4:
                            st.metric("💯 金额匹配度", f"{best['similarity']:.1f}% {best['similarity_indicator']}")
                        
                        # 账户组信息
                        if len(accounts) == 2:
                            st.write(f"🔥 账户组: **{accounts[0]}** ↔ **{accounts[1]}**")
                        elif len(accounts) == 3:
                            st.write(f"🔥 账户组: **{accounts[0]}** ↔ **{accounts[1]}** ↔ **{accounts[2]}**")
                        
                        # 详细账户信息
                        st.write("### 🔍 组合详情")
                        for account in accounts:
                            with st.container():
                                col1, col2 = st.columns([1, 2])
                                with col1:
                                    st.write(f"**📋 账户: {account}**")
                                    numbers_count = len([x for x in best['numbers'] if x in set(best['bet_contents'][account].split(', '))])
                                    st.write(f"- 数字数量: {numbers_count}个")
                                    if has_amount_column:
                                        amount_info = best['individual_amounts'][account]
                                        avg_info = best['individual_avg_per_number'][account]
                                        st.write(f"- 总投注: {amount_info:,.2f}元")
                                        st.write(f"- 平均每号: {avg_info:,.2f}元")
                                with col2:
                                    st.text_area(
                                        f"投注内容 - {account}",
                                        best['bet_contents'][account],
                                        height=80,
                                        key=f"content_{period}_{lottery}_{account}",
                                        disabled=True
                                    )
                        
                        # 显示所有找到的组合
                        st.write("### 📊 所有找到的组合")
                        all_results = result['all_results']
                        for account_count, combinations in all_results.items():
                            if combinations:
                                st.write(f"**{account_count}个账户组合 (共{len(combinations)}组):**")
                                for i, combo in enumerate(combinations[:5], 1):  # 只显示前5个
                                    st.write(f"{i}. 账户: {', '.join(combo['accounts'])} - 覆盖率: {combo['coverage_rate']:.1f}% - 匹配度: {combo['similarity']:.1f}%")
                    
                    # 🏅 全局最优组合
                    st.header("🏅 全局最优组合")
                    best_global = None
                    best_period_key = None
                    
                    for (period, lottery), result in all_period_results.items():
                        current_best = result['best_result']
                        if best_global is None or (current_best['coverage_rate'] > best_global['coverage_rate']):
                            best_global = current_best
                            best_period_key = (period, lottery)
                    
                    if best_global:
                        accounts = best_global['accounts']
                        st.success(f"🎯 全局最优组合发现于: 期号[{best_period_key[0]}] - 彩种[{best_period_key[1]}]")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("🏆 最佳覆盖率", f"{best_global['coverage_rate']:.1f}%")
                        with col2:
                            st.metric("💯 金额匹配度", f"{best_global['similarity']:.1f}%")
                        with col3:
                            st.metric("👥 账户数量", len(accounts))
                        with col4:
                            if has_amount_column:
                                st.metric("💰 总投注金额", f"{best_global['total_amount']:,.2f} 元")
                        
                        if len(accounts) == 2:
                            st.write(f"🔥 最优账户组: **{accounts[0]}** ↔ **{accounts[1]}**")
                        elif len(accounts) == 3:
                            st.write(f"🔥 最优账户组: **{accounts[0]}** ↔ **{accounts[1]}** ↔ **{accounts[2]}**")
                else:
                    st.error("❌ 在选定的期数中未找到有效组合")
                    st.info("💡 建议：")
                    st.write("1. 降低最小覆盖率要求")
                    st.write("2. 检查数据格式是否正确")
                    st.write("3. 尝试选择更多期号")
        
        else:
            st.error("❌ 数据清理失败，缺少必要列")
            st.write("可用的列:", available_columns)
            st.write("需要的列:", required_columns)
    
    except Exception as e:
        st.error(f"❌ 处理文件时出错: {str(e)}")
        st.info("💡 如果遇到重复列名错误，系统已自动处理。请检查数据格式是否正确。")

else:
    st.info("📁 请上传Excel文件开始分析")

# 侧边栏信息
st.sidebar.title("🎯 使用说明")
st.sidebar.markdown("""
### 功能特点
- 📊 **按期数+彩种分别分析**
- 🔍 **完整组合搜索**
- 💰 **智能金额匹配**
- 🏆 **最优组合推荐**

### 支持彩种
- 新澳门六合彩
- 澳门六合彩  
- 香港六合彩
- 一分六合彩
- 五分六合彩
- 三分六合彩
- 香港⑥合彩
- 分分六合彩

### 数据要求
- ✅ 会员账号
- ✅ 期号
- ✅ 彩种
- ✅ 玩法分类
- ✅ 投注内容
- ✅ 金额（可选）

### 使用步骤
1. 📁 上传Excel文件
2. 🔍 系统自动识别列名
3. 🎯 选择分析期号
4. 🚀 开始分析
5. 📊 查看结果
""")

st.sidebar.info("💡 提示：系统会自动处理重复列名问题，确保数据格式正确")
