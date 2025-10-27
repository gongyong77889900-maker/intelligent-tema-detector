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
st.markdown("### 基于完整搜索算法的完美组合检测")

class OptimizedBettingAnalyzer:
    """优化版投注分析器 - 简化显示，专注结果"""
    
    def __init__(self):
        self.full_set = set(range(1, 50))
        
        # 完整的六合彩彩种列表
        self.target_lotteries = [
            '新澳门六合彩', '澳门六合彩', '香港六合彩', '一分六合彩',
            '五分六合彩', '三分六合彩', '香港⑥合彩', '分分六合彩',
            '台湾大乐透', '大发六合彩', '快乐6合彩'
        ]
    
    def find_correct_columns(self, df):
        """智能找到正确的列 - 兼容多种格式"""
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
    
    def extract_bet_amount(self, amount_text):
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
    
    def extract_numbers_from_content(self, content):
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
    
    def analyze_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析数据质量"""
        quality_info = {
            'total_records': len(df),
            'has_amount': '金额' in df.columns,
            'lottery_types': df['彩种'].value_counts().to_dict() if '彩种' in df.columns else {},
            'bet_types': df['玩法分类'].value_counts().to_dict() if '玩法分类' in df.columns else {},
            'periods': df['期号'].value_counts().to_dict() if '期号' in df.columns else {},
            'accounts': len(df['会员账号'].unique()) if '会员账号' in df.columns else 0
        }
        
        return quality_info
    
    def find_all_perfect_combinations(self, account_numbers, account_amount_stats, account_bet_contents):
        """完整搜索所有可能的完美组合（2-4个账户）"""
        all_results = {2: [], 3: [], 4: []}
        all_accounts = list(account_numbers.keys())
        
        # 预先计算数字集合以提高速度
        account_sets = {account: set(numbers) for account, numbers in account_numbers.items()}
        
        # 搜索2个账户的组合
        found_2 = 0
        total_pairs = len(all_accounts) * (len(all_accounts) - 1) // 2
        
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
                    similarity = self.calculate_similarity(avgs)
                    
                    result_data = {
                        'accounts': (acc1, acc2),
                        'account_count': 2,
                        'total_digits': 49,
                        'efficiency': 49/2,
                        'numbers': combined_set,
                        'total_amount': total_amount,
                        'avg_amount_per_number': avg_amount_per_number,
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
                        similarity = self.calculate_similarity(avgs)
                        
                        result_data = {
                            'accounts': (acc1, acc2, acc3),
                            'account_count': 3,
                            'total_digits': 49,
                            'efficiency': 49/3,
                            'numbers': combined_set,
                            'total_amount': total_amount,
                            'avg_amount_per_number': avg_amount_per_number,
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
                            similarity = self.calculate_similarity(avgs)
                            
                            result_data = {
                                'accounts': (acc1, acc2, acc3, acc4),
                                'account_count': 4,
                                'total_digits': 49,
                                'efficiency': 49/4,
                                'numbers': combined_set,
                                'total_amount': total_amount,
                                'avg_amount_per_number': avg_amount_per_number,
                                'similarity': similarity,
                                'similarity_indicator': self.get_similarity_indicator(similarity),
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
        
        return all_results

    def analyze_period_lottery_combination(self, group, period, lottery):
        """分析特定期数和彩种的组合 - 简化版，不显示过程"""
        has_amount_column = '金额' in group.columns
        
        # 按账户提取所有特码数字和金额统计
        account_numbers = {}
        account_amount_stats = {}
        account_bet_contents = {}

        for account in group['会员账号'].unique():
            account_data = group[group['会员账号'] == account]
            
            # 提取该账户下所有特码数字
            all_numbers = set()
            total_amount = 0
            bet_count = 0
            
            for _, row in account_data.iterrows():
                numbers = self.extract_numbers_from_content(row['内容'])
                all_numbers.update(numbers)
                
                if has_amount_column:
                    total_amount += row['投注金额']
                    bet_count += 1
            
            if all_numbers:
                account_numbers[account] = sorted(all_numbers)
                account_bet_contents[account] = ", ".join([f"{num:02d}" for num in sorted(all_numbers)])
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

        # 使用完整搜索算法
        all_results = self.find_all_perfect_combinations(
            filtered_account_numbers, 
            filtered_account_amount_stats, 
            filtered_account_bet_contents
        )

        total_combinations = sum(len(results) for results in all_results.values())

        if total_combinations > 0:
            # 合并所有组合并按效率排序
            all_combinations = []
            for results in all_results.values():
                all_combinations.extend(results)
            
            # 排序标准：先按账户数量，再按金额匹配度降序
            all_combinations.sort(key=lambda x: (x['account_count'], -x['similarity']))
            
            return {
                'period': period,
                'lottery': lottery,
                'total_accounts': len(account_numbers),
                'filtered_accounts': len(filtered_account_numbers),
                'total_combinations': total_combinations,
                'all_combinations': all_combinations,
                'best_result': all_combinations[0] if all_combinations else None
            }
        else:
            return None

def main():
    analyzer = OptimizedBettingAnalyzer()
    
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
            
            st.success(f"✅ 成功读取文件，共 {len(df):,} 条记录")
            
            # 智能列名映射
            column_mapping = analyzer.find_correct_columns(df)
            
            if column_mapping:
                df = df.rename(columns=column_mapping)
                st.write("✅ 列名映射完成")

            # 数据质量分析
            quality_info = analyzer.analyze_data_quality(df)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("总记录数", f"{quality_info['total_records']:,}")
            with col2:
                st.metric("唯一账户数", f"{quality_info['accounts']:,}")
            with col3:
                st.metric("彩种类型数", len(quality_info['lottery_types']))
            with col4:
                st.metric("期号数量", len(quality_info['periods']))

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

            if len(available_columns) >= 5:
                df_clean = df[available_columns].copy()
                
                # 移除空值
                df_clean = df_clean.dropna(subset=required_columns)
                
                # 数据类型转换
                for col in available_columns:
                    df_clean[col] = df_clean[col].astype(str).str.strip()
                
                # 如果有金额列，提取金额
                if has_amount_column:
                    df_clean['投注金额'] = df_clean['金额'].apply(analyzer.extract_bet_amount)

                # 筛选目标彩种和特码玩法
                df_target = df_clean[
                    (df_clean['彩种'].isin(analyzer.target_lotteries)) & 
                    (df_clean['玩法分类'] == '特码')
                ]
                
                st.write(f"✅ 特码玩法数据行数: {len(df_target):,}")

                # 按期数和彩种分组分析 - 使用进度条
                grouped = df_target.groupby(['期号', '彩种'])
                
                # 创建进度条
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                all_period_results = {}
                total_groups = len(grouped)
                
                # 分析每个期数+彩种组合
                for idx, ((period, lottery), group) in enumerate(grouped):
                    status_text.text(f"分析进度: {idx+1}/{total_groups} (期号: {period})")
                    progress_bar.progress((idx+1) / total_groups)
                    
                    if len(group) < 2:  # 数据量太少的跳过
                        continue
                    
                    result = analyzer.analyze_period_lottery_combination(group, period, lottery)
                    if result:
                        all_period_results[(period, lottery)] = result

                # 清除进度条
                progress_bar.empty()
                status_text.empty()

                # 显示结果
                st.header("🎉 分析结果")
                
                if all_period_results:
                    for (period, lottery), result in all_period_results.items():
                        total_combinations = result['total_combinations']
                        
                        if total_combinations > 0:
                            st.success(f"### 📊 期号[{period}] - 彩种[{lottery}] - 共找到 {total_combinations} 个完美组合")
                            
                            # 显示所有组合
                            for idx, combo in enumerate(result['all_combinations'], 1):
                                # 添加横线分隔符（除了第一个组合）
                                if idx > 1:
                                    st.markdown("---")
                                
                                accounts = combo['accounts']
                                
                                # 创建组合标题
                                if len(accounts) == 2:
                                    combo_title = f"**组合 {idx}: {accounts[0]} ↔ {accounts[1]}**"
                                elif len(accounts) == 3:
                                    combo_title = f"**组合 {idx}: {accounts[0]} ↔ {accounts[1]} ↔ {accounts[2]}**"
                                else:
                                    combo_title = f"**组合 {idx}: {', '.join(accounts)}**"
                                
                                st.markdown(combo_title)
                                
                                # 显示组合基本信息
                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    st.metric("账户数量", combo['account_count'])
                                with col2:
                                    st.metric("覆盖效率", f"{combo['efficiency']:.1f}")
                                with col3:
                                    if has_amount_column:
                                        st.metric("总金额", f"¥{combo['total_amount']:,.2f}")
                                with col4:
                                    similarity = combo['similarity']
                                    indicator = combo['similarity_indicator']
                                    st.metric("金额匹配度", f"{similarity:.1f}% {indicator}")
                                
                                # 显示各账户详情
                                with st.expander(f"📋 查看组合 {idx} 详情", expanded=(idx == 1)):
                                    st.write("**各账户详情:**")
                                    for account in accounts:
                                        amount_info = combo['individual_amounts'][account]
                                        avg_info = combo['individual_avg_per_number'][account]
                                        numbers_count = len(combo['bet_contents'][account].split(', '))
                                        st.write(f"- **{account}**: {numbers_count}个数字")
                                        if has_amount_column:
                                            st.write(f"  - 总投注: ¥{amount_info:,.2f}")
                                            st.write(f"  - 平均每号: ¥{avg_info:,.2f}")
                                        st.write(f"  - 投注内容: {combo['bet_contents'][account]}")
                else:
                    st.error("❌ 在所有期数中均未找到完美组合")
                    st.info("""
                    **可能原因:**
                    1. 有效账户数量不足
                    2. 账户投注号码无法形成完美覆盖
                    3. 数据质量需要检查
                    """)
            
            else:
                st.error(f"❌ 缺少必要列，可用列: {available_columns}")
            
        except Exception as e:
            st.error(f"❌ 处理文件时出错: {str(e)}")
    
    else:
        # 显示示例和使用说明
        st.info("💡 **优化版六合彩特码分析系统**")
        st.markdown("""
        ### 系统特性:
        - **简洁界面**: 只显示最终结果，隐藏分析过程
        - **完整组合**: 显示所有找到的完美组合
        - **清晰分隔**: 用横线分隔不同组合
        
        ### 数据要求:
        - 必须包含: 会员账号, 彩种, 期号, 玩法分类, 内容
        - 玩法分类必须为'特码'
        - 彩种必须是六合彩类型
        """)

if __name__ == "__main__":
    main()
