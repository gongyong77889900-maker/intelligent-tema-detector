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
st.subheader("按期数彩种分离优化版")
st.markdown("---")

# 侧边栏说明
with st.sidebar:
    st.header("📋 使用说明")
    st.markdown("""
    ### 功能特点：
    - 📊 按期数+彩种分别分析
    - 🔍 完整组合展示
    - 🎯 智能最优评选
    - 💰 金额匹配度分析
    
    ### 支持彩种：
    - 新澳门六合彩
    - 澳门六合彩  
    - 香港六合彩
    - 一分六合彩
    - 五分六合彩
    - 三分六合彩
    - 香港⑥合彩
    - 分分六合彩
    
    ### 数据要求：
    - Excel文件格式
    - 包含：会员账号、期号、彩种、玩法分类、内容等列
    - 玩法分类需包含"特码"
    """)

# 文件上传
st.header("📁 步骤1：上传Excel文件")
uploaded_file = st.file_uploader("选择Excel文件", type=['xlsx', 'xls'])

if uploaded_file is not None:
    # 读取数据
    try:
        df = pd.read_excel(uploaded_file)
        st.success(f"✅ 成功读取文件: {uploaded_file.name}")
        
        # 显示基本信息
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("数据行数", f"{len(df):,}")
        with col2:
            st.metric("数据列数", f"{len(df.columns)}")
        with col3:
            st.metric("文件大小", f"{uploaded_file.size / 1024:.1f} KB")
        
        # 显示数据预览
        with st.expander("📊 数据预览", expanded=True):
            st.dataframe(df.head(10), use_container_width=True)
            st.write(f"**原始列名:** {list(df.columns)}")
        
    except Exception as e:
        st.error(f"❌ 读取文件失败: {e}")
        st.stop()
    
    # 智能列识别 - 使用提供的列名映射配置
    def find_correct_columns(df):
        """找到正确的列 - 使用配置的列名映射"""
        column_mappings = {
            '会员账号': ['会员账号', '会员账户', '账号', '账户', '用户账号'],
            '彩种': ['彩种', '彩票种类', '游戏类型'],
            '期号': ['期号', '期数', '期次', '期'],
            '玩法分类': ['玩法', '玩法分类', '投注类型', '类型'],
            '内容': ['内容', '投注内容', '下注内容', '注单内容'],
            '金额': ['金额', '下注总额', '投注金额', '总额', '下注金额']
        }
        
        column_mapping = {}
        used_standard_cols = set()
        
        for standard_col, possible_names in column_mappings.items():
            if standard_col in used_standard_cols:
                continue
                
            for col in df.columns:
                col_str = str(col).lower().strip()
                # 检查当前列是否匹配该标准列的任一可能名称
                if any(possible_name.lower() in col_str for possible_name in possible_names):
                    column_mapping[col] = standard_col
                    used_standard_cols.add(standard_col)
                    break
        
        return column_mapping

    column_mapping = find_correct_columns(df)
    
    if column_mapping:
        df = df.rename(columns=column_mapping)
        st.success(f"✅ 自动识别列名完成: {column_mapping}")
        
        # 显示重命名后的列名
        with st.expander("🔄 重命名后的列名", expanded=False):
            st.write(f"**新列名:** {list(df.columns)}")
    else:
        st.warning("⚠️ 无法自动识别列名，使用原始列名")
    
    # 数据清理 - 使用提供的金额提取函数
    def extract_bet_amount(amount_text):
        """从复杂文本中提取投注金额 - 使用提供的代码"""
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
        
        # 数据类型转换
        for col in available_columns:
            df_clean[col] = df_clean[col].astype(str).str.strip()
        
        # 提取金额
        if has_amount_column:
            df_clean['投注金额'] = df_clean['金额'].apply(extract_bet_amount)
            total_bet_amount = df_clean['投注金额'].sum()
            avg_bet_amount = df_clean['投注金额'].mean()
            
            # 显示金额提取统计
            col1, col2 = st.columns(2)
            with col1:
                st.metric("总投注金额", f"{total_bet_amount:,.2f} 元")
            with col2:
                st.metric("平均每注金额", f"{avg_bet_amount:,.2f} 元")
        
        # 显示清理后信息
        st.header("🔍 步骤2：数据概览")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("清理后数据行数", f"{len(df_clean):,}")
        with col2:
            st.metric("彩种数量", f"{df_clean['彩种'].nunique()}")
        with col3:
            st.metric("期号数量", f"{df_clean['期号'].nunique()}")
        
        # 显示数据分布
        with st.expander("📊 数据分布详情", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.write("**彩种分布:**")
                st.write(df_clean['彩种'].value_counts())
            with col2:
                st.write("**玩法分类分布:**")
                st.write(df_clean['玩法分类'].value_counts())
        
        # 特码分析
        st.header("🎯 步骤3：特码完美覆盖分析")
        
        # 定义目标彩种
        target_lotteries = [
            '新澳门六合彩', '澳门六合彩', '香港六合彩', '一分六合彩',
            '五分六合彩', '三分六合彩', '香港⑥合彩', '分分六合彩'
        ]
        
        # 筛选特码数据
        df_target = df_clean[
            (df_clean['彩种'].isin(target_lotteries)) & 
            (df_clean['玩法分类'] == '特码')
        ]
        
        if len(df_target) == 0:
            st.error("❌ 未找到特码玩法数据，请检查数据格式")
            st.stop()
        
        # 显示特码数据信息
        st.success(f"✅ 找到 {len(df_target):,} 行特码数据")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("特码数据行数", f"{len(df_target):,}")
        with col2:
            st.metric("涉及彩种数", f"{df_target['彩种'].nunique()}")
        with col3:
            st.metric("涉及期数", f"{df_target['期号'].nunique()}")
        
        if has_amount_column:
            total_target_amount = df_target['投注金额'].sum()
            avg_target_amount = df_target['投注金额'].mean()
            col1, col2 = st.columns(2)
            with col1:
                st.metric("特码总投注额", f"{total_target_amount:,.2f} 元")
            with col2:
                st.metric("平均每注金额", f"{avg_target_amount:,.2f} 元")
        
        # 分析函数
        def extract_numbers_from_content(content):
            """从内容中提取所有1-49的数字"""
            numbers = []
            content_str = str(content)
            
            number_matches = re.findall(r'\d+', content_str)
            for match in number_matches:
                num = int(match)
                if 1 <= num <= 49:
                    numbers.append(num)
            
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
            """获取相似度颜色指示符"""
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
            
            # 按账户提取所有特码数字和金额统计
            account_numbers = {}
            account_amount_stats = {}
            account_bet_contents = {}
            
            accounts = df_period_lottery['会员账号'].unique()
            
            for account in accounts:
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
            
            if len(filtered_account_numbers) < 2:
                return None
            
            def find_all_perfect_combinations(account_numbers, account_amount_stats, account_bet_contents):
                """完整搜索所有可能的完美组合"""
                all_results = {2: [], 3: [], 4: []}
                all_accounts = list(account_numbers.keys())
                
                # 预先计算数字集合
                account_sets = {account: set(numbers) for account, numbers in account_numbers.items()}
                
                # 搜索2个账户的组合
                found_2 = 0
                for i, acc1 in enumerate(all_accounts):
                    count1 = len(account_numbers[acc1])
                    
                    for j in range(i+1, len(all_accounts)):
                        acc2 = all_accounts[j]
                        count2 = len(account_numbers[acc2])
                        total_count = count1 + count2
                        
                        if total_count != 49:
                            continue
                        
                        combined_set = account_sets[acc1] | account_sets[acc2]
                        if len(combined_set) == 49:
                            total_amount = account_amount_stats[acc1]['total_amount'] + account_amount_stats[acc2]['total_amount']
                            avg_amount_per_number = total_amount / 49
                            
                            avgs = [
                                account_amount_stats[acc1]['avg_amount_per_number'],
                                account_amount_stats[acc2]['avg_amount_per_number']
                            ]
                            similarity = calculate_similarity(avgs)
                            
                            result_data = {
                                'accounts': (acc1, acc2),
                                'account_count': 2,
                                'total_digits': 49,
                                'efficiency': 49/2,
                                'numbers': combined_set,
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
                
                # 搜索3个账户的组合
                found_3 = 0
                for i, acc1 in enumerate(all_accounts):
                    count1 = len(account_numbers[acc1])
                    
                    for j in range(i+1, len(all_accounts)):
                        acc2 = all_accounts[j]
                        count2 = len(account_numbers[acc2])
                        
                        for k in range(j+1, len(all_accounts)):
                            acc3 = all_accounts[k]
                            count3 = len(account_numbers[acc3])
                            total_count = count1 + count2 + count3
                            
                            if total_count != 49:
                                continue
                            
                            combined_set = account_sets[acc1] | account_sets[acc2] | account_sets[acc3]
                            if len(combined_set) == 49:
                                total_amount = (account_amount_stats[acc1]['total_amount'] + 
                                              account_amount_stats[acc2]['total_amount'] + 
                                              account_amount_stats[acc3]['total_amount'])
                                avg_amount_per_number = total_amount / 49
                                
                                avgs = [
                                    account_amount_stats[acc1]['avg_amount_per_number'],
                                    account_amount_stats[acc2]['avg_amount_per_number'],
                                    account_amount_stats[acc3]['avg_amount_per_number']
                                ]
                                similarity = calculate_similarity(avgs)
                                
                                result_data = {
                                    'accounts': (acc1, acc2, acc3),
                                    'account_count': 3,
                                    'total_digits': 49,
                                    'efficiency': 49/3,
                                    'numbers': combined_set,
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
                
                return all_results
            
            # 执行分析
            all_results = find_all_perfect_combinations(filtered_account_numbers, filtered_account_amount_stats, filtered_account_bet_contents)
            total_combinations = sum(len(results) for results in all_results.values())
            
            if total_combinations > 0:
                # 选择最优组合
                all_combinations = []
                for results in all_results.values():
                    all_combinations.extend(results)
                
                all_combinations.sort(key=lambda x: (x['account_count'], -x['similarity']))
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
                return None
        
        # 按期数和彩种分组分析
        st.info(f"📊 开始分析 {len(df_target):,} 行特码数据...")
        
        # 按期数和彩种分组
        grouped = df_target.groupby(['期号', '彩种'])
        
        all_period_results = {}
        valid_periods = 0
        
        # 进度条
        total_groups = len(grouped)
        progress_bar = st.progress(0, text="正在分析各期数据...")
        
        for idx, ((period, lottery), group) in enumerate(grouped):
            if len(group) < 10:
                continue
            
            result = analyze_period_lottery_combination(group, period, lottery)
            if result:
                all_period_results[(period, lottery)] = result
                valid_periods += 1
            
            progress_bar.progress((idx + 1) / total_groups, text=f"正在分析各期数据... ({idx+1}/{total_groups})")
        
        progress_bar.empty()
        
        # 显示结果
        if all_period_results:
            st.success(f"🎉 分析完成！在 {valid_periods} 个期数中发现完美组合")
            
            # 完整组合展示 - 优化显示紧凑性
            st.header("📊 完整组合展示")
            
            for (period, lottery), result in all_period_results.items():
                all_results = result['all_results']
                total_combinations = result['total_combinations']
                
                if total_combinations > 0:
                    with st.expander(f"📅 期号[{period}] - 彩种[{lottery}] - 共找到 {total_combinations} 个完美组合", expanded=True):
                        
                        # 显示2账户组合 - 紧凑布局
                        if all_results[2]:
                            st.subheader(f"👥 2个账号组合 (共{len(all_results[2])}组)")
                            for i, result_data in enumerate(all_results[2], 1):
                                accounts = result_data['accounts']
                                
                                # 使用紧凑的两列布局
                                col1, col2 = st.columns([1, 2])
                                with col1:
                                    st.markdown(f"**组合 {i}**")
                                    st.write(f"**账户**: {accounts[0]} ↔ {accounts[1]}")
                                    st.write(f"**总数字数**: {result_data['total_digits']}")
                                    
                                    if has_amount_column:
                                        st.write(f"**总投注**: {result_data['total_amount']:,.2f}元")
                                        st.write(f"**匹配度**: {result_data['similarity']:.2f}% {result_data['similarity_indicator']}")
                                
                                with col2:
                                    for account in accounts:
                                        numbers_count = len([x for x in result_data['numbers'] if x in set(result_data['bet_contents'][account].split(', '))])
                                        amount_info = result_data['individual_amounts'][account]
                                        avg_info = result_data['individual_avg_per_number'][account]
                                        
                                        # 紧凑显示
                                        st.write(f"**{account}**")
                                        st.write(f"- 数字: {numbers_count}个 | 总投注: {amount_info:,.2f}元 | 平均: {avg_info:,.2f}元/号")
                                        st.write(f"- 内容: {result_data['bet_contents'][account]}")
                                
                                st.markdown("---")
                        
                        # 显示3账户组合 - 紧凑布局
                        if all_results[3]:
                            st.subheader(f"👥 3个账号组合 (共{len(all_results[3])}组)")
                            for i, result_data in enumerate(all_results[3], 1):
                                accounts = result_data['accounts']
                                
                                col1, col2 = st.columns([1, 2])
                                with col1:
                                    st.markdown(f"**组合 {i}**")
                                    st.write(f"**账户**: {accounts[0]} ↔ {accounts[1]} ↔ {accounts[2]}")
                                    st.write(f"**总数字数**: {result_data['total_digits']}")
                                    
                                    if has_amount_column:
                                        st.write(f"**总投注**: {result_data['total_amount']:,.2f}元")
                                        st.write(f"**匹配度**: {result_data['similarity']:.2f}% {result_data['similarity_indicator']}")
                                
                                with col2:
                                    for account in accounts:
                                        numbers_count = len([x for x in result_data['numbers'] if x in set(result_data['bet_contents'][account].split(', '))])
                                        amount_info = result_data['individual_amounts'][account]
                                        avg_info = result_data['individual_avg_per_number'][account]
                                        
                                        st.write(f"**{account}**")
                                        st.write(f"- 数字: {numbers_count}个 | 总投注: {amount_info:,.2f}元 | 平均: {avg_info:,.2f}元/号")
                                        st.write(f"- 内容: {result_data['bet_contents'][account]}")
                                
                                st.markdown("---")
            
            # 各期最优组合汇总 - 紧凑显示
            st.header("🏆 各期最优组合汇总")
            
            # 按最优组合的账户数量排序
            sorted_periods = sorted(all_period_results.items(), 
                                  key=lambda x: (x[1]['best_result']['account_count'], -x[1]['best_result']['similarity']))
            
            for (period, lottery), result in sorted_periods:
                best = result['best_result']
                accounts = best['accounts']
                
                with st.expander(f"📅 期号: {period} | 彩种: {lottery} | 账户数: {len(accounts)} | 匹配度: {best['similarity']:.2f}% {best['similarity_indicator']}", expanded=False):
                    
                    # 紧凑布局
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        if len(accounts) == 2:
                            st.write(f"**账户组**: {accounts[0]} ↔ {accounts[1]}")
                        elif len(accounts) == 3:
                            st.write(f"**账户组**: {accounts[0]} ↔ {accounts[1]} ↔ {accounts[2]}")
                        
                        if has_amount_column:
                            st.metric("总投注金额", f"{best['total_amount']:,.2f} 元")
                            st.metric("平均每号金额", f"{best['avg_amount_per_number']:,.2f} 元")
                            st.metric("金额匹配度", f"{best['similarity']:.2f}%")
                    
                    with col2:
                        st.write("**组合详情:**")
                        for account in accounts:
                            amount_info = best['individual_amounts'][account]
                            avg_info = best['individual_avg_per_number'][account]
                            numbers_count = len([x for x in best['numbers'] if x in set(best['bet_contents'][account].split(', '))])
                            
                            # 紧凑显示
                            st.write(f"**{account}**")
                            st.write(f"- 数字: {numbers_count}个 | 总投注: {amount_info:,.2f}元 | 平均: {avg_info:,.2f}元/号")
                            st.write(f"- 内容: {best['bet_contents'][account]}")
                            st.write("")
            
            # 全局最优组合 - 紧凑显示
            st.header("🏅 全局最优组合")
            
            best_global = None
            best_period_key = None
            
            for (period, lottery), result in all_period_results.items():
                current_best = result['best_result']
                if best_global is None or current_best['similarity'] > best_global['similarity']:
                    best_global = current_best
                    best_period_key = (period, lottery)
            
            if best_global:
                accounts = best_global['accounts']
                
                st.success(f"🎯 最优组合来自: 期号[{best_period_key[0]}] - 彩种[{best_period_key[1]}]")
                
                # 紧凑的两列布局
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.write("**组合信息**")
                    if len(accounts) == 2:
                        st.write(f"**账户组**: {accounts[0]} ↔ {accounts[1]}")
                    elif len(accounts) == 3:
                        st.write(f"**账户组**: {accounts[0]} ↔ {accounts[1]} ↔ {accounts[2]}")
                    
                    st.write(f"**账户数量**: {best_global['account_count']}")
                    st.write(f"**总数字数**: {best_global['total_digits']}")
                    
                    if has_amount_column:
                        st.metric("总投注金额", f"{best_global['total_amount']:,.2f} 元")
                        st.metric("平均每号金额", f"{best_global['avg_amount_per_number']:,.2f} 元")
                        st.metric("金额匹配度", f"{best_global['similarity']:.2f}%")
                
                with col2:
                    st.write("**账户详情**")
                    for account in accounts:
                        amount_info = best_global['individual_amounts'][account]
                        avg_info = best_global['individual_avg_per_number'][account]
                        numbers_count = len([x for x in best_global['numbers'] if x in set(best_global['bet_contents'][account].split(', '))])
                        
                        # 紧凑显示每个账户信息
                        st.write(f"**{account}**")
                        st.write(f"- **数字数量**: {numbers_count}")
                        st.write(f"- **总投注**: {amount_info:,.2f}元")
                        st.write(f"- **平均每号**: {avg_info:,.2f}元")
                        st.write(f"**投注内容**: {best_global['bet_contents'][account]}")
        
        else:
            st.warning("❌ 在所有期数中均未找到完美组合")
    
    else:
        st.error("❌ 数据清理失败，缺少必要列")

else:
    st.info("👆 请上传Excel文件开始分析")

# 页脚
st.markdown("---")
st.markdown("🎯 特码完美覆盖分析系统 - 任务完成")
