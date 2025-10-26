import streamlit as st
import pandas as pd
import io
import itertools
import re
import numpy as np
from collections import defaultdict

# Streamlit页面配置
st.set_page_config(
    page_title="特码完美覆盖分析系统",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 应用标题
st.title("🎯 特码完美覆盖分析系统")
st.markdown("---")

# 侧边栏配置
st.sidebar.header("⚙️ 分析参数配置")

# 文件上传
st.header("📁 数据上传")
uploaded_file = st.file_uploader(
    "请上传Excel文件 (支持 .xlsx, .xls)", 
    type=['xlsx', 'xls'],
    help="请确保文件包含必要的列：会员账号、期号、彩种、玩法分类、内容、金额"
)

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
        st.warning(f"金额提取失败: {amount_text}, 错误: {e}")
        return 0

def find_correct_columns(df):
    """找到正确的列 - 兼容多种格式"""
    column_mapping = {}
    used_standard_cols = set()  # 跟踪已使用的标准列名
    
    for col in df.columns:
        col_str = str(col).lower().strip()
        
        # 会员账号列
        if '会员账号' not in used_standard_cols and any(keyword in col_str for keyword in ['会员', '账号', '账户', '用户账号']):
            column_mapping[col] = '会员账号'
            used_standard_cols.add('会员账号')
        
        # 期号列 - 兼容期号和期数
        elif '期号' not in used_standard_cols and any(keyword in col_str for keyword in ['期号', '期数', '期次', '期']):
            column_mapping[col] = '期号'
            used_standard_cols.add('期号')
        
        # 彩种列
        elif '彩种' not in used_standard_cols and any(keyword in col_str for keyword in ['彩种', '彩票', '游戏类型']):
            column_mapping[col] = '彩种'
            used_standard_cols.add('彩种')
        
        # 玩法分类列 - 兼容玩法分类和玩法
        elif '玩法分类' not in used_standard_cols and any(keyword in col_str for keyword in ['玩法分类', '玩法', '投注类型', '类型']):
            column_mapping[col] = '玩法分类'
            used_standard_cols.add('玩法分类')
        
        # 内容列 - 兼容内容和投注内容
        elif '内容' not in used_standard_cols and any(keyword in col_str for keyword in ['内容', '投注', '下注内容', '注单内容']):
            column_mapping[col] = '内容'
            used_standard_cols.add('内容')
        
        # 金额列 - 兼容多种金额列名
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

def analyze_period_lottery_combination(df_period_lottery, period, lottery):
    """分析特定期数和彩种的组合"""
    st.info(f"📊 处理: 期号[{period}] - 彩种[{lottery}] - 数据量: {len(df_period_lottery):,}行")
    
    has_amount_column = '投注金额' in df_period_lottery.columns
    if has_amount_column:
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

    def find_all_perfect_combinations(account_numbers, account_amount_stats, account_bet_contents):
        """完整搜索所有可能的完美组合（2-4个账户）"""
        all_results = {2: [], 3: [], 4: []}
        all_accounts = list(account_numbers.keys())
        
        # 预先计算数字集合以提高速度
        account_sets = {account: set(numbers) for account, numbers in account_numbers.items()}
        
        # 搜索2个账户的组合
        found_2 = 0
        for i, acc1 in enumerate(all_accounts):
            count1 = len(account_numbers[acc1])
            
            for j in range(i+1, len(all_accounts)):
                acc2 = all_accounts[j]
                count2 = len(account_numbers[acc2])
                total_count = count1 + count2
                
                # 快速判断：数字数量之和必须等于49
                if total_count != 49:
                    continue
                
                # 检查是否有重复数字
                combined_set = account_sets[acc1] | account_sets[acc2]
                if len(combined_set) == 49:
                    # 计算组合的总金额
                    total_amount = account_amount_stats[acc1]['total_amount'] + account_amount_stats[acc2]['total_amount']
                    avg_amount_per_number = total_amount / 49
                    
                    # 计算金额匹配度
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
                    
                    # 快速判断：数字数量之和必须等于49
                    if total_count != 49:
                        continue
                    
                    # 检查是否有重复数字
                    combined_set = account_sets[acc1] | account_sets[acc2] | account_sets[acc3]
                    if len(combined_set) == 49:
                        # 计算组合的总金额
                        total_amount = (account_amount_stats[acc1]['total_amount'] + 
                                      account_amount_stats[acc2]['total_amount'] + 
                                      account_amount_stats[acc3]['total_amount'])
                        avg_amount_per_number = total_amount / 49
                        
                        # 计算金额匹配度
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
        
        # 搜索4个账户的组合
        found_4 = 0
        
        # 为了加快速度，只搜索数字数量在合理范围内的账户
        suitable_accounts = [acc for acc in all_accounts if 12 <= len(account_numbers[acc]) <= 35]
        
        for i, acc1 in enumerate(suitable_accounts):
            count1 = len(account_numbers[acc1])
            
            for j in range(i+1, len(suitable_accounts)):
                acc2 = suitable_accounts[j]
                count2 = len(account_numbers[acc2])
                
                for k in range(j+1, len(suitable_accounts)):
                    acc3 = suitable_accounts[k]
                    count3 = len(account_numbers[acc3])
                    
                    for l in range(k+1, len(suitable_accounts)):
                        acc4 = suitable_accounts[l]
                        count4 = len(account_numbers[acc4])
                        total_count = count1 + count2 + count3 + count4
                        
                        # 快速判断：数字数量之和必须等于49
                        if total_count != 49:
                            continue
                        
                        # 检查是否有重复数字
                        combined_set = account_sets[acc1] | account_sets[acc2] | account_sets[acc3] | account_sets[acc4]
                        if len(combined_set) == 49:
                            # 计算组合的总金额
                            total_amount = (account_amount_stats[acc1]['total_amount'] + 
                                          account_amount_stats[acc2]['total_amount'] + 
                                          account_amount_stats[acc3]['total_amount'] + 
                                          account_amount_stats[acc4]['total_amount'])
                            avg_amount_per_number = total_amount / 49
                            
                            # 计算金额匹配度
                            avgs = [
                                account_amount_stats[acc1]['avg_amount_per_number'],
                                account_amount_stats[acc2]['avg_amount_per_number'],
                                account_amount_stats[acc3]['avg_amount_per_number'],
                                account_amount_stats[acc4]['avg_amount_per_number']
                            ]
                            similarity = calculate_similarity(avgs)
                            
                            result_data = {
                                'accounts': (acc1, acc2, acc3, acc4),
                                'account_count': 4,
                                'total_digits': 49,
                                'efficiency': 49/4,
                                'numbers': combined_set,
                                'total_amount': total_amount,
                                'avg_amount_per_number': avg_amount_per_number,
                                'similarity': similarity,
                                'similarity_indicator': get_similarity_indicator(similarity),
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
                                },
                                'bet_contents': {
                                    acc1: account_bet_contents[acc1],
                                    acc2: account_bet_contents[acc2],
                                    acc3: account_bet_contents[acc3],
                                    acc4: account_bet_contents[acc4]
                                }
                            }
                            all_results[4].append(result_data)
                            found_4 += 1
        
        st.write(f"🔍 搜索完成: 2账户组合{found_2}个, 3账户组合{found_3}个, 4账户组合{found_4}个")
        return all_results

    # 使用完整搜索算法
    all_results = find_all_perfect_combinations(filtered_account_numbers, filtered_account_amount_stats, filtered_account_bet_contents)

    total_combinations = sum(len(results) for results in all_results.values())

    if total_combinations > 0:
        # 选择最优组合：优先账户数量少，然后金额匹配度高
        all_combinations = []
        for results in all_results.values():
            all_combinations.extend(results)
        
        # 排序标准：先按账户数量，再按金额匹配度降序
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
        st.warning("❌ 未找到完美覆盖组合")
        return None

if uploaded_file is not None:
    try:
        st.success(f"✅ 已上传文件: {uploaded_file.name}")
        
        with st.spinner("🔄 正在读取和分析数据..."):
            # 读取Excel文件
            df = pd.read_excel(uploaded_file)
            
            st.write(f"📈 数据维度: {df.shape[0]} 行 × {df.shape[1]} 列")
            st.write("📋 原始列名:", list(df.columns))
            
            # 自动识别列名
            column_mapping = find_correct_columns(df)
            st.write("🔄 自动识别的列映射:", column_mapping)
            
            if column_mapping:
                # 修复：使用正确的重命名方式
                df = df.rename(columns=column_mapping)
                st.write("✅ 重命名后的列名:", list(df.columns))
            else:
                st.warning("⚠️ 无法自动识别列名，使用原始列名")
            
            # 数据清理
            required_columns = ['会员账号', '彩种', '期号', '玩法分类', '内容']
            available_columns = []
            
            # 检查哪些必要列存在
            for col in required_columns:
                if col in df.columns:
                    available_columns.append(col)
            
            # 检查是否有金额列
            has_amount_column = '金额' in df.columns
            if has_amount_column:
                available_columns.append('金额')
                st.success("💰 ✅ 检测到金额列，将进行金额分析")
            else:
                st.warning("⚠️ 未检测到金额列，将只分析号码覆盖")
            
            st.write(f"📊 可用列: {available_columns}")
            
            if len(available_columns) >= 5:
                # 修复：确保只选择存在的列
                df_clean = df[available_columns].copy()
                
                # 移除空值
                for col in required_columns:
                    if col in df_clean.columns:
                        df_clean = df_clean.dropna(subset=[col])
                
                # 数据类型转换 - 修复：确保对Series使用str方法，而不是DataFrame
                for col in available_columns:
                    if col in df_clean.columns:
                        # 修复：对Series使用str方法，而不是DataFrame
                        df_clean[col] = df_clean[col].astype(str).str.strip()
                
                # 如果有金额列，提取金额
                if has_amount_column:
                    df_clean['投注金额'] = df_clean['金额'].apply(extract_bet_amount)
                    total_bet_amount = df_clean['投注金额'].sum()
                    avg_bet_amount = df_clean['投注金额'].mean()
                    st.write(f"💰 金额提取统计:")
                    st.write(f"   📊 总投注额: {total_bet_amount:,.2f} 元")
                    st.write(f"   📈 平均每注金额: {avg_bet_amount:,.2f} 元")
                
                st.write(f"✅ 清理后数据行数: {len(df_clean):,}")
                
                # 显示数据概览
                with st.expander("📊 数据概览", expanded=False):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write("🎲 彩种分布:")
                        # 修复：确保对Series使用value_counts
                        if '彩种' in df_clean.columns:
                            st.write(df_clean['彩种'].value_counts())
                    with col2:
                        st.write("📅 期号分布:")
                        if '期号' in df_clean.columns:
                            st.write(df_clean['期号'].value_counts().head(10))
                    with col3:
                        st.write("🎯 玩法分类分布:")
                        if '玩法分类' in df_clean.columns:
                            st.write(df_clean['玩法分类'].value_counts())
                
                # 按期数和彩种分别分析特码玩法
                st.header("🎯 特码完美覆盖分析")
                
                # 定义需要分析的8种六合彩彩种
                target_lotteries = [
                    '新澳门六合彩', '澳门六合彩', '香港六合彩', '一分六合彩',
                    '五分六合彩', '三分六合彩', '香港⑥合彩', '分分六合彩'
                ]
                
                # 筛选目标彩种和特码玩法
                df_target = df_clean[
                    (df_clean['彩种'].isin(target_lotteries)) & 
                    (df_clean['玩法分类'] == '特码')
                ]
                
                st.write(f"✅ 特码玩法数据行数: {len(df_target):,}")
                
                if len(df_target) > 0:
                    # 按期数和彩种分组分析
                    grouped = df_target.groupby(['期号', '彩种'])
                    st.write(f"📅 共发现 {len(grouped):,} 个期数+彩种组合")
                    
                    all_period_results = {}
                    valid_periods = 0
                    
                    # 进度条
                    progress_bar = st.progress(0)
                    total_groups = len(grouped)
                    
                    # 先收集所有期数的分析结果
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
                                        
                                        if has_amount_column:
                                            st.write(f"💰 总投注金额: {result_data['total_amount']:,.2f} 元")
                                            st.write(f"💯 平均金额匹配: {result_data['similarity']:.2f}% {result_data['similarity_indicator']}")
                                            
                                            for account in accounts:
                                                numbers = result_data['numbers']
                                                amount_info = result_data['individual_amounts'][account]
                                                avg_info = result_data['individual_avg_per_number'][account]
                                                st.write(f"   **{account}:** {len([x for x in numbers if x in set(result_data['bet_contents'][account].split(', '))])}个数字 | 总投注: {amount_info:,.2f}元 | 平均每号: {avg_info:,.2f}元")
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
                                        
                                        if has_amount_column:
                                            st.write(f"💰 总投注金额: {result_data['total_amount']:,.2f} 元")
                                            st.write(f"💯 平均金额匹配: {result_data['similarity']:.2f}% {result_data['similarity_indicator']}")
                                            
                                            for account in accounts:
                                                numbers = result_data['numbers']
                                                amount_info = result_data['individual_amounts'][account]
                                                avg_info = result_data['individual_avg_per_number'][account]
                                                st.write(f"   **{account}:** {len([x for x in numbers if x in set(result_data['bet_contents'][account].split(', '))])}个数字 | 总投注: {amount_info:,.2f}元 | 平均每号: {avg_info:,.2f}元")
                                                st.write(f"   投注内容: {result_data['bet_contents'][account]}")
                                        
                                        st.markdown("---")
                    
                    # 各期最优组合汇总
                    st.header("🏆 各期最优组合汇总")
                    
                    if all_period_results:
                        # 按最优组合的账户数量排序
                        sorted_periods = sorted(all_period_results.items(), 
                                              key=lambda x: (x[1]['best_result']['account_count'], -x[1]['best_result']['similarity']))
                        
                        for (period, lottery), result in sorted_periods:
                            best = result['best_result']
                            accounts = best['accounts']
                            
                            with st.expander(f"📅 期号: {period} | 彩种: {lottery} | 最优组合", expanded=False):
                                if len(accounts) == 2:
                                    st.write(f"🔥 账户组: {accounts[0]} ↔ {accounts[1]}")
                                elif len(accounts) == 3:
                                    st.write(f"🔥 账户组: {accounts[0]} ↔ {accounts[1]} ↔ {accounts[2]}")
                                else:
                                    st.write(f"🔥 账户组: {accounts[0]} ↔ {accounts[1]} ↔ {accounts[2]} ↔ {accounts[3]}")
                                    
                                if has_amount_column:
                                    st.write(f"💰 总投注金额: {best['total_amount']:,.2f} 元")
                                    st.write(f"💯 平均金额匹配: {best['similarity']:.2f}% {best['similarity_indicator']}")
                                    st.write(f"📊 平均每号金额: {best['avg_amount_per_number']:,.2f} 元")
                                    st.write(f"🔍 组合详情:")
                                    for account in accounts:
                                        amount_info = best['individual_amounts'][account]
                                        avg_info = best['individual_avg_per_number'][account]
                                        numbers_count = len([x for x in best['numbers'] if x in set(best['bet_contents'][account].split(', '))])
                                        st.write(f"   - **{account}:** {numbers_count}个数字 | 总投注: {amount_info:,.2f}元 | 平均每号: {avg_info:,.2f}元")
                                        st.write(f"     投注内容: {best['bet_contents'][account]}")
                        
                        # 全局最优组合
                        st.header("🏅 全局最优组合")
                        
                        # 选择标准：优先金额匹配度最高的组合
                        best_global = None
                        for (period, lottery), result in all_period_results.items():
                            current_best = result['best_result']
                            if best_global is None or current_best['similarity'] > best_global['similarity']:
                                best_global = current_best
                                best_period_key = (period, lottery)
                        
                        if best_global:
                            accounts = best_global['accounts']
                            
                            st.success(f"🏆 全局最优组合 - 期号: {best_period_key[0]} | 彩种: {best_period_key[1]}")
                            
                            if len(accounts) == 2:
                                st.write(f"🔥 账户组: {accounts[0]} ↔ {accounts[1]}")
                            elif len(accounts) == 3:
                                st.write(f"🔥 账户组: {accounts[0]} ↔ {accounts[1]} ↔ {accounts[2]}")
                            else:
                                st.write(f"🔥 账户组: {accounts[0]} ↔ {accounts[1]} ↔ {accounts[2]} ↔ {accounts[3]}")
                                
                            st.write(f"🎯 最优组合 ({best_global['account_count']}个账户)")
                            st.write(f"📊 总数字数: {best_global['total_digits']}")
                            
                            if has_amount_column:
                                st.write(f"💰 总投注金额: {best_global['total_amount']:,.2f} 元")
                                st.write(f"💯 平均金额匹配: {best_global['similarity']:.2f}% {best_global['similarity_indicator']}")
                                
                                for account in accounts:
                                    amount_info = best_global['individual_amounts'][account]
                                    avg_info = best_global['individual_avg_per_number'][account]
                                    numbers_count = len([x for x in best_global['numbers'] if x in set(best_global['bet_contents'][account].split(', '))])
                                    st.write(f"   **{account}:** {numbers_count}个数字 | 总投注: {amount_info:,.2f}元 | 平均每号: {avg_info:,.2f}元")
                                    st.write(f"   投注内容: {best_global['bet_contents'][account]}")
                
                else:
                    st.warning("❌ 没有找到特码玩法数据")
            
            else:
                st.error("❌ 缺少必要列，无法继续分析")
    
    except Exception as e:
        st.error(f"❌ 程序执行失败: {str(e)}")
        import traceback
        st.error(f"详细错误信息:\n{traceback.format_exc()}")

# 使用说明
with st.expander("📖 使用说明（特码完美覆盖分析系统）"):
    st.markdown("""
    ### 系统功能说明

    **🎯 检测逻辑：**
    - 分析六合彩特码玩法的完美数字覆盖组合
    - 支持2-4个账户的组合分析
    - 要求组合数字覆盖1-49所有号码且无重复

    **📊 分析规则：**
    - 只分析投注号码数量>11的账户
    - 支持按期数和彩种分别分析
    - 自动计算金额匹配度
    - 智能评选最优组合

    **🎲 支持彩种：**
    - 新澳门六合彩、澳门六合彩、香港六合彩
    - 一分六合彩、五分六合彩、三分六合彩
    - 香港⑥合彩、分分六合彩

    **📁 数据格式要求：**
    - 必须包含：会员账号、期号、彩种、玩法分类、内容
    - 可选包含：金额（如有则进行金额分析）
    - 支持自动列名映射

    **⚡ 分析流程：**
    1. 上传Excel文件
    2. 系统自动识别列名
    3. 按期数和彩种分别分析
    4. 展示所有完美组合
    5. 评选各期最优组合
    6. 评选全局最优组合
    """)

st.markdown("---")
st.success("🎯 特码完美覆盖分析系统 - 就绪")
