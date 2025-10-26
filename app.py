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
        
    except Exception as e:
        st.error(f"❌ 读取文件失败: {e}")
        st.stop()
    
    # 智能列识别
    def find_correct_columns(df):
        """找到正确的列 - 兼容多种格式"""
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

    column_mapping = find_correct_columns(df)
    
    if column_mapping:
        df = df.rename(columns=column_mapping)
    
    # 数据清理
    def extract_bet_amount(amount_text):
        """从复杂文本中提取投注金额 - 修复版，支持多种格式"""
        try:
            if pd.isna(amount_text):
                return 0
            
            text = str(amount_text).strip()
            
            # 先尝试直接转换数字
            try:
                # 移除常见的非数字字符，但保留小数点
                cleaned_text = re.sub(r'[^\d.]', '', text)
                if cleaned_text:
                    amount = float(cleaned_text)
                    if amount >= 0:
                        return amount
            except:
                pass
            
            # 处理带逗号的数字（如：1,000.50）
            try:
                cleaned_text = text.replace(',', '').replace('，', '')
                amount = float(cleaned_text)
                if amount >= 0:
                    return amount
            except:
                pass
            
            # 处理"投注：2.000 抵用：0 中奖：0.000"格式
            try:
                if '投注' in text:
                    # 提取投注部分
                    bet_match = re.search(r'投注[:：]\s*(\d+\.?\d*)', text)
                    if bet_match:
                        bet_amount = float(bet_match.group(1))
                        return bet_amount
            except:
                pass
            
            # 多种金额提取模式
            patterns = [
                r'投注[:：]\s*(\d+\.?\d*)',  # 专门匹配"投注：2.000"格式
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

    if len(available_columns) >= 5:
        df_clean = df[available_columns].copy()
        
        # 移除空值
        df_clean = df_clean.dropna(subset=required_columns)
        
        # 数据类型转换 - 修复可能的列名问题
        for col in available_columns:
            if col in df_clean.columns:
                df_clean[col] = df_clean[col].astype(str).str.strip()
        
        # 提取金额
        if has_amount_column:
            df_clean['投注金额'] = df_clean['金额'].apply(extract_bet_amount)
            total_bet_amount = df_clean['投注金额'].sum()
        
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
            (df_clean['玩法分类'] == '特码')
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
            
            # 所有期数的完整组合展示 - 默认展开
            st.header("📊 完整组合展示")
            
            for (period, lottery), result in all_period_results.items():
                all_results = result['all_results']
                total_combinations = result['total_combinations']
                
                if total_combinations > 0:
                    # 修改这里：将expanded设置为True，默认展开
                    with st.expander(f"📅 期号[{period}] - 彩种[{lottery}] - 共找到 {total_combinations} 个完美组合", expanded=True):
                        
                        # 显示2账户组合
                        if all_results[2]:
                            st.subheader(f"👥 2个账号组合 (共{len(all_results[2])}组)")
                            for i, result_data in enumerate(all_results[2], 1):
                                accounts = result_data['accounts']
                                
                                st.markdown(f"**组合 {i}**")
                                st.write(f"**账户**: {accounts[0]} ↔ {accounts[1]}")
                                st.write(f"**总数字数**: {result_data['total_digits']}")
                                
                                if has_amount_column:
                                    st.write(f"**总投注金额**: {result_data['total_amount']:,.2f} 元")
                                    st.write(f"**金额匹配度**: {result_data['similarity']:.2f}% {result_data['similarity_indicator']}")
                                
                                # 修改这里：使用紧凑的显示格式，减少行间距
                                for account in accounts:
                                    numbers_count = len([x for x in result_data['numbers'] if x in set(result_data['bet_contents'][account].split(', '))])
                                    amount_info = result_data['individual_amounts'][account]
                                    avg_info = result_data['individual_avg_per_number'][account]
                                    
                                    # 使用紧凑格式显示账户信息
                                    st.write(f"**{account}**: {numbers_count}个数字 | 总投注: {amount_info:,.2f}元 | 平均每号: {avg_info:,.2f}元")
                                    # 投注内容单独一行，但减少间距
                                    st.write(f"**投注内容**: {result_data['bet_contents'][account]}")
                                
                                st.markdown("---")
        
        else:
            st.warning("❌ 在所有期数中均未找到完美组合")
    
    else:
        st.error("❌ 数据清理失败，缺少必要列")

else:
    st.info("👆 请上传Excel文件开始分析")

# 页脚
st.markdown("---")
st.markdown("🎯 特码完美覆盖分析系统 - 任务完成")
