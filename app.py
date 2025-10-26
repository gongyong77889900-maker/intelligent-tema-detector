import streamlit as st
import pandas as pd
import re
import numpy as np

# 设置页面
st.set_page_config(
    page_title="特码完美覆盖分析系统",
    page_icon="🎯",
    layout="wide"
)

# 主标题
st.title("🎯 特码完美覆盖分析系统")
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
    """)

# 文件上传
st.header("📁 上传Excel文件")
uploaded_file = st.file_uploader("选择Excel文件", type=['xlsx', 'xls'])

if uploaded_file is not None:
    try:
        # 读取数据
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
        with st.expander("📊 数据预览", expanded=False):
            st.dataframe(df.head(), use_container_width=True)
        
        # 智能列识别
        def find_correct_columns(df):
            """智能识别列名"""
            column_mapping = {}
            
            for col in df.columns:
                col_str = str(col).lower().strip()
                
                # 会员账号列
                if any(keyword in col_str for keyword in ['会员', '账号', '账户']):
                    column_mapping[col] = '会员账号'
                # 彩种列
                elif any(keyword in col_str for keyword in ['彩种', '彩票']):
                    column_mapping[col] = '彩种'
                # 期号列
                elif any(keyword in col_str for keyword in ['期号', '期数']):
                    column_mapping[col] = '期号'
                # 玩法分类列
                elif any(keyword in col_str for keyword in ['玩法', '分类', '类型']):
                    column_mapping[col] = '玩法分类'
                # 内容列
                elif any(keyword in col_str for keyword in ['内容', '投注']):
                    column_mapping[col] = '内容'
                # 金额列
                elif any(keyword in col_str for keyword in ['金额', '投注金额']):
                    column_mapping[col] = '金额'
            
            return column_mapping

        column_mapping = find_correct_columns(df)
        
        if column_mapping:
            df = df.rename(columns=column_mapping)
            st.success("✅ 列名识别完成")
        
        # 数据清理函数 - 修复金额提取
        def extract_bet_amount(amount_text):
            """从复杂文本中提取投注金额 - 修复版"""
            try:
                if pd.isna(amount_text):
                    return 0
                
                text = str(amount_text).strip()
                
                # 调试信息
                st.write(f"调试金额文本: {text}")
                
                # 处理"投注: 100.000 抵用: 0 中奖: 0.000"格式
                if '投注' in text:
                    # 多种可能的投注格式
                    patterns = [
                        r'投注[:：]\s*(\d+\.\d+)',
                        r'投注[:：]\s*(\d+)',
                        r'投注\s*(\d+\.\d+)',
                        r'投注\s*(\d+)',
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, text)
                        if match:
                            bet_amount = float(match.group(1))
                            st.write(f"调试: 从 '{text}' 中提取到金额: {bet_amount}")
                            return bet_amount
                
                # 尝试直接提取数字
                numbers = re.findall(r'\d+\.?\d*', text)
                if numbers:
                    for num in numbers:
                        try:
                            amount = float(num)
                            if amount > 0:
                                st.write(f"调试: 直接提取到金额: {amount}")
                                return amount
                        except:
                            continue
                
                st.write(f"调试: 无法从 '{text}' 中提取金额，返回0")
                return 0
            except Exception as e:
                st.write(f"金额提取错误: {e}")
                return 0

        # 检查必要列
        required_cols = ['会员账号', '彩种', '期号', '玩法分类', '内容']
        available_cols = []
        
        for col in required_cols:
            if col in df.columns:
                available_cols.append(col)
            else:
                st.warning(f"⚠️ 未找到列: {col}")

        if len(available_cols) < 4:
            st.error("❌ 缺少必要的数据列")
            st.stop()
        
        # 创建清理后的数据框
        df_clean = df[available_cols].copy()
        
        # 安全地处理每一列
        for col in df_clean.columns:
            try:
                df_clean[col] = df_clean[col].astype(str).str.strip()
            except Exception as e:
                st.warning(f"⚠️ 处理列 {col} 时出错: {e}")
        
        # 如果有金额列，提取金额
        has_amount = '金额' in df_clean.columns
        if has_amount:
            st.info("🔍 正在提取金额信息...")
            df_clean['投注金额'] = df_clean['金额'].apply(extract_bet_amount)
            total_amount = df_clean['投注金额'].sum()
            st.success(f"💰 金额提取完成，总投注额: {total_amount:,.2f} 元")
        
        # 特码分析
        st.header("🎯 特码完美覆盖分析")
        
        # 定义目标彩种
        target_lotteries = [
            '新澳门六合彩', '澳门六合彩', '香港六合彩', '一分六合彩',
            '五分六合彩', '三分六合彩', '香港⑥合彩', '分分六合彩'
        ]
        
        # 筛选特码数据
        df_target = df_clean[
            (df_clean['彩种'].isin(target_lotteries)) & 
            (df_clean['玩法分类'].str.contains('特码'))
        ]
        
        if len(df_target) == 0:
            st.error("❌ 未找到特码玩法数据，请检查数据格式")
            st.stop()
        
        # 显示特码数据信息
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("特码数据行数", f"{len(df_target):,}")
        with col2:
            st.metric("涉及彩种数", f"{df_target['彩种'].nunique()}")
        with col3:
            st.metric("涉及期数", f"{df_target['期号'].nunique()}")
        
        if has_amount:
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
            
            # 提取所有数字
            number_matches = re.findall(r'\d+', content_str)
            for match in number_matches:
                num = int(match)
                if 1 <= num <= 49:
                    numbers.append(num)
            
            return list(set(numbers))  # 去重
        
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
                    
                    if has_amount:
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
            
            st.write(f"🔍 期号[{period}] - 有效账户: {len(filtered_account_numbers)}个")
            
            if len(filtered_account_numbers) < 2:
                return None
            
            def find_all_perfect_combinations(account_numbers, account_amount_stats, account_bet_contents):
                """完整搜索所有可能的完美组合"""
                all_results = {2: [], 3: []}
                all_accounts = list(account_numbers.keys())
                
                # 预先计算数字集合
                account_sets = {account: set(numbers) for account, numbers in account_numbers.items()}
                
                # 搜索2个账户的组合
                found_2 = 0
                for i, acc1 in enumerate(all_accounts):
                    set1 = account_sets[acc1]
                    
                    for j in range(i+1, len(all_accounts)):
                        acc2 = all_accounts[j]
                        set2 = account_sets[acc2]
                        
                        # 检查是否有重复数字
                        if len(set1 | set2) == 49:
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
                                'numbers': set1 | set2,
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
                                'individual_number_counts': {
                                    acc1: account_amount_stats[acc1]['number_count'],
                                    acc2: account_amount_stats[acc2]['number_count']
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
                    set1 = account_sets[acc1]
                    
                    for j in range(i+1, len(all_accounts)):
                        acc2 = all_accounts[j]
                        set2 = account_sets[acc2]
                        
                        for k in range(j+1, len(all_accounts)):
                            acc3 = all_accounts[k]
                            set3 = account_sets[acc3]
                            
                            # 检查是否有重复数字
                            if len(set1 | set2 | set3) == 49:
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
                                    'numbers': set1 | set2 | set3,
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
                                    'individual_number_counts': {
                                        acc1: account_amount_stats[acc1]['number_count'],
                                        acc2: account_amount_stats[acc2]['number_count'],
                                        acc3: account_amount_stats[acc3]['number_count']
                                    },
                                    'bet_contents': {
                                        acc1: account_bet_contents[acc1],
                                        acc2: account_bet_contents[acc2],
                                        acc3: account_bet_contents[acc3]
                                    }
                                }
                                all_results[3].append(result_data)
                                found_3 += 1
                
                st.write(f"🔍 找到2账户组合: {found_2}个, 3账户组合: {found_3}个")
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
        if total_groups > 0:
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
            
            # 所有期数的完整组合展示
            st.header("📊 完整组合展示")
            
            for (period, lottery), result in all_period_results.items():
                all_results = result['all_results']
                total_combinations = result['total_combinations']
                
                if total_combinations > 0:
                    with st.expander(f"📅 期号[{period}] - 彩种[{lottery}] - 共找到 {total_combinations} 个完美组合", expanded=True):
                        
                        # 显示2账户组合
                        if all_results[2]:
                            st.subheader(f"👥 2个账号组合 (共{len(all_results[2])}组)")
                            for i, result_data in enumerate(all_results[2], 1):
                                accounts = result_data['accounts']
                                
                                st.markdown(f"**组合 {i}**")
                                st.write(f"**账户**: {accounts[0]} ↔ {accounts[1]}")
                                st.write(f"**总数字数**: {result_data['total_digits']}")
                                
                                if has_amount:
                                    st.write(f"**总投注金额**: {result_data['total_amount']:,.2f} 元")
                                    st.write(f"**金额匹配度**: {result_data['similarity']:.2f}% {result_data['similarity_indicator']}")
                                
                                # 修复数字计数显示
                                for account in accounts:
                                    numbers_count = result_data['individual_number_counts'][account]
                                    amount_info = result_data['individual_amounts'][account]
                                    avg_info = result_data['individual_avg_per_number'][account]
                                    
                                    st.write(f"**{account}**: {numbers_count}个数字 | 总投注: {amount_info:,.2f}元 | 平均每号: {avg_info:,.2f}元")
                                    st.write(f"**投注内容**: {result_data['bet_contents'][account]}")
                                
                                st.markdown("---")
                        
                        # 显示3账户组合
                        if all_results[3]:
                            st.subheader(f"👥 3个账号组合 (共{len(all_results[3])}组)")
                            for i, result_data in enumerate(all_results[3], 1):
                                accounts = result_data['accounts']
                                
                                st.markdown(f"**组合 {i}**")
                                st.write(f"**账户**: {accounts[0]} ↔ {accounts[1]} ↔ {accounts[2]}")
                                st.write(f"**总数字数**: {result_data['total_digits']}")
                                
                                if has_amount:
                                    st.write(f"**总投注金额**: {result_data['total_amount']:,.2f} 元")
                                    st.write(f"**金额匹配度**: {result_data['similarity']:.2f}% {result_data['similarity_indicator']}")
                                
                                # 修复数字计数显示
                                for account in accounts:
                                    numbers_count = result_data['individual_number_counts'][account]
                                    amount_info = result_data['individual_amounts'][account]
                                    avg_info = result_data['individual_avg_per_number'][account]
                                    
                                    st.write(f"**{account}**: {numbers_count}个数字 | 总投注: {amount_info:,.2f}元 | 平均每号: {avg_info:,.2f}元")
                                    st.write(f"**投注内容**: {result_data['bet_contents'][account]}")
                                
                                st.markdown("---")
        
        else:
            st.warning("❌ 在所有期数中均未找到完美组合")
    
    except Exception as e:
        st.error(f"❌ 处理数据时出错: {str(e)}")
        import traceback
        st.code(traceback.format_exc())

else:
    st.info("👆 请上传Excel文件开始分析")

# 页脚
st.markdown("---")
st.markdown("🎯 特码完美覆盖分析系统 - 任务完成")
