import pandas as pd
import numpy as np
import streamlit as st
import io
import itertools
import re
import base64
import tempfile
import os
from datetime import datetime

# 设置页面配置
st.set_page_config(
    page_title="特码完美覆盖分析系统",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

class SpecialCodeAnalysisSystem:
    """特码完美覆盖分析系统主类"""
    
    def __init__(self):
        self.target_lotteries = [
            '新澳门六合彩', '澳门六合彩', '香港六合彩', '一分六合彩',
            '五分六合彩', '三分六合彩', '香港⑥合彩', '分分六合彩'
        ]
        self.has_amount_column = False
        self.df_target = None
        self.all_period_results = {}
    
    def extract_bet_amount(self, amount_text):
        """从复杂文本中提取投注金额 - 完整保留原始逻辑"""
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
            
            # 多种金额提取模式 - 完整保留原始逻辑
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
    
    def find_correct_columns(self, df):
        """找到正确的列 - 兼容多种格式 - 完整保留原始逻辑"""
        column_mapping = {}
        used_standard_cols = set()
        
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
    
    def extract_numbers_from_content(self, content):
        """从内容中提取所有1-49的数字 - 完整保留原始逻辑"""
        numbers = []
        content_str = str(content)
        
        # 使用正则表达式提取所有数字
        number_matches = re.findall(r'\d+', content_str)
        for match in number_matches:
            num = int(match)
            if 1 <= num <= 49:
                numbers.append(num)
        
        return list(set(numbers))  # 去重
    
    def format_numbers_display(self, numbers):
        """格式化数字显示，确保两位数显示 - 完整保留原始逻辑"""
        formatted = []
        for num in sorted(numbers):
            formatted.append(f"{num:02d}")
        return ", ".join(formatted)
    
    def calculate_similarity(self, avgs):
        """计算金额匹配度 - 完整保留原始逻辑"""
        if not avgs or max(avgs) == 0:
            return 0
        return (min(avgs) / max(avgs)) * 100
    
    def get_similarity_indicator(self, similarity):
        """获取相似度颜色指示符 - 完整保留原始逻辑"""
        if similarity >= 90:
            return "🟢"
        elif similarity >= 80:
            return "🟡"
        elif similarity >= 70:
            return "🟠"
        else:
            return "🔴"
    
    def process_uploaded_file(self, uploaded_file):
        """处理上传的文件"""
        try:
            if uploaded_file is None:
                return None, "❌ 没有上传文件"
            
            # 读取文件内容
            file_content = uploaded_file.read()
            
            if uploaded_file.name.endswith('.csv'):
                # 尝试多种编码
                encodings = ['utf-8', 'gbk', 'gb2312', 'latin1']
                for encoding in encodings:
                    try:
                        df = pd.read_csv(io.BytesIO(file_content), encoding=encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    return None, "❌ 无法解码CSV文件，请检查文件编码"
            else:
                df = pd.read_excel(io.BytesIO(file_content))
            
            return df, f"✅ 已上传文件: {uploaded_file.name}"
            
        except Exception as e:
            return None, f"❌ 文件处理失败: {str(e)}"
    
    def preprocess_data(self, df):
        """数据预处理 - 完整保留原始逻辑"""
        try:
            # 列名标准化
            column_mapping = self.find_correct_columns(df)
            if column_mapping:
                df = df.rename(columns=column_mapping)
            
            # 检查必要列
            required_columns = ['会员账号', '彩种', '期号', '玩法分类', '内容']
            available_columns = []
            
            for col in required_columns:
                if col in df.columns:
                    available_columns.append(col)
            
            # 检查是否有金额列
            self.has_amount_column = '金额' in df.columns
            if self.has_amount_column:
                available_columns.append('金额')
            
            if len(available_columns) >= 5:
                df_clean = df[available_columns].copy()
                
                # 移除空值
                df_clean = df_clean.dropna(subset=required_columns)
                
                # 数据类型转换
                for col in available_columns:
                    df_clean[col] = df_clean[col].astype(str).str.strip()
                
                # 如果有金额列，提取金额
                if self.has_amount_column:
                    df_clean['投注金额'] = df_clean['金额'].apply(self.extract_bet_amount)
                
                # 筛选目标彩种和特码玩法
                self.df_target = df_clean[
                    (df_clean['彩种'].isin(self.target_lotteries)) & 
                    (df_clean['玩法分类'] == '特码')
                ]
                
                return True, "✅ 数据预处理完成"
            else:
                return False, f"❌ 缺少必要列，可用列: {available_columns}"
                
        except Exception as e:
            return False, f"❌ 数据预处理失败: {str(e)}"
    
    def analyze_period_lottery_combination(self, df_period_lottery, period, lottery):
        """分析特定期数和彩种的组合 - 完整保留原始逻辑"""
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
                numbers = self.extract_numbers_from_content(row['内容'])
                all_numbers.update(numbers)
                
                if self.has_amount_column:
                    total_amount += row['投注金额']
                    bet_count += 1
            
            if all_numbers:
                account_numbers[account] = sorted(all_numbers)
                account_bet_contents[account] = self.format_numbers_display(all_numbers)
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
            """完整搜索所有可能的完美组合（2-4个账户）- 完整保留原始逻辑"""
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
            return None
    
    def run_complete_analysis(self):
        """运行完整分析"""
        if self.df_target is None or len(self.df_target) == 0:
            return "❌ 没有有效的特码数据可供分析"
        
        # 按期数和彩种分组分析
        grouped = self.df_target.groupby(['期号', '彩种'])
        self.all_period_results = {}
        valid_periods = 0
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        total_groups = len(grouped)
        current_group = 0
        
        # 先收集所有期数的分析结果
        for (period, lottery), group in grouped:
            current_group += 1
            progress = current_group / total_groups
            progress_bar.progress(progress)
            status_text.text(f"分析进度: {current_group}/{total_groups} - 期号: {period}, 彩种: {lottery}")
            
            if len(group) < 10:  # 数据量太少的跳过
                continue
            
            result = self.analyze_period_lottery_combination(group, period, lottery)
            if result:
                self.all_period_results[(period, lottery)] = result
                valid_periods += 1
        
        progress_bar.empty()
        status_text.empty()
        
        return f"✅ 分析完成！共分析 {valid_periods} 个有效期数+彩种组合"
    
    def display_data_overview(self):
        """显示数据概览"""
        if self.df_target is None:
            return
        
        st.subheader("📊 数据概览")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("特码数据总行数", f"{len(self.df_target):,}")
        with col2:
            st.metric("唯一账户数", self.df_target['会员账号'].nunique())
        with col3:
            st.metric("唯一期号数", self.df_target['期号'].nunique())
        with col4:
            st.metric("彩种数量", self.df_target['彩种'].nunique())
        
        if self.has_amount_column:
            total_amount = self.df_target['投注金额'].sum()
            avg_amount = self.df_target['投注金额'].mean()
            col5, col6 = st.columns(2)
            with col5:
                st.metric("总投注金额", f"{total_amount:,.2f} 元")
            with col6:
                st.metric("平均每注金额", f"{avg_amount:,.2f} 元")
        
        # 显示数据分布
        col7, col8 = st.columns(2)
        
        with col7:
            st.write("🎲 彩种分布")
            st.dataframe(self.df_target['彩种'].value_counts(), use_container_width=True)
        
        with col8:
            st.write("📅 期号分布 (前10)")
            st.dataframe(self.df_target['期号'].value_counts().head(10), use_container_width=True)
    
    def display_all_combinations(self):
        """显示所有期数的完整组合"""
        if not self.all_period_results:
            st.warning("❌ 没有找到任何完美组合")
            return
        
        st.subheader("📊 所有期数的完整组合展示")
        
        for (period, lottery), result in self.all_period_results.items():
            all_results = result['all_results']
            total_combinations = result['total_combinations']
            
            if total_combinations > 0:
                with st.expander(f"📅 期号[{period}] - 彩种[{lottery}] - {total_combinations}个完美组合", expanded=False):
                    # 显示2账户组合
                    if all_results[2]:
                        st.write(f"👥 **2个账号组合** (共{len(all_results[2])}组)")
                        for i, result_data in enumerate(all_results[2], 1):
                            with st.container():
                                st.write(f"**组合 {i}**")
                                accounts = result_data['accounts']
                                st.write(f"🔥 账户组: `{accounts[0]}` ↔ `{accounts[1]}`")
                                st.write(f"🎯 组合 ({result_data['account_count']}个账户)")
                                st.write(f"总数字数: {result_data['total_digits']}")
                                
                                if self.has_amount_column:
                                    st.write(f"总投注金额: {result_data['total_amount']:,.2f} 元")
                                    st.write(f"💯 平均金额匹配: {result_data['similarity']:.2f}% {result_data['similarity_indicator']}")
                                    
                                    for account in accounts:
                                        numbers = result_data['numbers']
                                        amount_info = result_data['individual_amounts'][account]
                                        avg_info = result_data['individual_avg_per_number'][account]
                                        st.write(f"- `{account}`: {len([x for x in numbers if x in set(result_data['bet_contents'][account].split(', '))])}个数字 | 总投注: {amount_info:,.2f}元 | 平均每号: {avg_info:,.2f}元")
                                        st.write(f"  投注内容: `{result_data['bet_contents'][account]}`")
                                
                                st.write("---")
                    
                    # 显示3账户组合
                    if all_results[3]:
                        st.write(f"👥 **3个账号组合** (共{len(all_results[3])}组)")
                        for i, result_data in enumerate(all_results[3], 1):
                            with st.container():
                                st.write(f"**组合 {i}**")
                                accounts = result_data['accounts']
                                st.write(f"🔥 账户组: `{accounts[0]}` ↔ `{accounts[1]}` ↔ `{accounts[2]}`")
                                st.write(f"🎯 组合 ({result_data['account_count']}个账户)")
                                st.write(f"总数字数: {result_data['total_digits']}")
                                
                                if self.has_amount_column:
                                    st.write(f"总投注金额: {result_data['total_amount']:,.2f} 元")
                                    st.write(f"💯 平均金额匹配: {result_data['similarity']:.2f}% {result_data['similarity_indicator']}")
                                    
                                    for account in accounts:
                                        numbers = result_data['numbers']
                                        amount_info = result_data['individual_amounts'][account]
                                        avg_info = result_data['individual_avg_per_number'][account]
                                        st.write(f"- `{account}`: {len([x for x in numbers if x in set(result_data['bet_contents'][account].split(', '))])}个数字 | 总投注: {amount_info:,.2f}元 | 平均每号: {avg_info:,.2f}元")
                                        st.write(f"  投注内容: `{result_data['bet_contents'][account]}`")
                                
                                st.write("---")
    
    def display_best_combinations_summary(self):
        """显示各期最优组合汇总"""
        if not self.all_period_results:
            return
        
        st.subheader("🏆 各期最优组合汇总")
        
        # 按最优组合的账户数量排序
        sorted_periods = sorted(self.all_period_results.items(), 
                              key=lambda x: (x[1]['best_result']['account_count'], -x[1]['best_result']['similarity']))
        
        for (period, lottery), result in sorted_periods:
            best = result['best_result']
            accounts = best['accounts']
            
            with st.expander(f"📅 期号: {period} | 彩种: {lottery} | 账户数: {len(accounts)}", expanded=False):
                if len(accounts) == 2:
                    st.write(f"🔥 账户组: `{accounts[0]}` ↔ `{accounts[1]}`")
                elif len(accounts) == 3:
                    st.write(f"🔥 账户组: `{accounts[0]}` ↔ `{accounts[1]}` ↔ `{accounts[2]}`")
                else:
                    st.write(f"🔥 账户组: `{accounts[0]}` ↔ `{accounts[1]}` ↔ `{accounts[2]}` ↔ `{accounts[3]}`")
                    
                if self.has_amount_column:
                    st.write(f"💰 总投注金额: {best['total_amount']:,.2f} 元")
                    st.write(f"💯 平均金额匹配: {best['similarity']:.2f}% {best['similarity_indicator']}")
                    st.write(f"📊 平均每号金额: {best['avg_amount_per_number']:,.2f} 元")
                    st.write(f"🔍 组合详情:")
                    for account in accounts:
                        amount_info = best['individual_amounts'][account]
                        avg_info = best['individual_avg_per_number'][account]
                        numbers_count = len([x for x in best['numbers'] if x in set(best['bet_contents'][account].split(', '))])
                        st.write(f"- `{account}`: {numbers_count}个数字 | 总投注: {amount_info:,.2f}元 | 平均每号: {avg_info:,.2f}元")
                        st.write(f"  投注内容: `{best['bet_contents'][account]}`")
    
    def display_global_best_combination(self):
        """显示全局最优组合"""
        if not self.all_period_results:
            return
        
        st.subheader("🏅 全局最优组合（基于金额匹配度）")
        
        # 选择标准：优先金额匹配度最高的组合
        best_global = None
        best_period_key = None
        
        for (period, lottery), result in self.all_period_results.items():
            current_best = result['best_result']
            if best_global is None or current_best['similarity'] > best_global['similarity']:
                best_global = current_best
                best_period_key = (period, lottery)
        
        if best_global:
            accounts = best_global['accounts']
            
            st.success(f"🎯 **最佳匹配组合** - 期号: {best_period_key[0]} | 彩种: {best_period_key[1]}")
            
            if len(accounts) == 2:
                st.write(f"🔥 账户组: `{accounts[0]}` ↔ `{accounts[1]}`")
            elif len(accounts) == 3:
                st.write(f"🔥 账户组: `{accounts[0]}` ↔ `{accounts[1]}` ↔ `{accounts[2]}`")
            else:
                st.write(f"🔥 账户组: `{accounts[0]}` ↔ `{accounts[1]}` ↔ `{accounts[2]}` ↔ `{accounts[3]}`")
                
            st.write(f"🎯 最优组合 ({best_global['account_count']}个账户)")
            st.write(f"总数字数: {best_global['total_digits']}")
            
            if self.has_amount_column:
                st.write(f"总投注金额: {best_global['total_amount']:,.2f} 元")
                st.write(f"💯 平均金额匹配: {best_global['similarity']:.2f}% {best_global['similarity_indicator']}")
                
                for account in accounts:
                    amount_info = best_global['individual_amounts'][account]
                    avg_info = best_global['individual_avg_per_number'][account]
                    numbers_count = len([x for x in best_global['numbers'] if x in set(best_global['bet_contents'][account].split(', '))])
                    st.write(f"- `{account}`: {numbers_count}个数字 | 总投注: {amount_info:,.2f}元 | 平均每号: {avg_info:,.2f}元")
                    st.write(f"  投注内容: `{best_global['bet_contents'][account]}`")

def main():
    """主函数"""
    st.title("🎯 特码完美覆盖分析系统 - Streamlit完整版")
    st.markdown("按期数+彩种分别分析 + 完整组合展示 + 智能最优评选")
    
    # 初始化分析系统
    if 'analysis_system' not in st.session_state:
        st.session_state.analysis_system = SpecialCodeAnalysisSystem()
    
    # 侧边栏
    with st.sidebar:
        st.header("📁 上传数据文件")
        uploaded_file = st.file_uploader(
            "选择Excel或CSV文件",
            type=['xlsx', 'xls', 'csv'],
            help="支持包含会员账号、期号、彩种、玩法分类、内容等列的数据文件"
        )
        
        st.header("⚙️ 分析设置")
        if st.button("🚀 开始分析", type="primary", use_container_width=True):
            if uploaded_file is not None:
                with st.spinner("处理文件中..."):
                    # 处理上传文件
                    df, message = st.session_state.analysis_system.process_uploaded_file(uploaded_file)
                    if df is not None:
                        st.success(message)
                        
                        # 数据预处理
                        success, message = st.session_state.analysis_system.preprocess_data(df)
                        if success:
                            st.success(message)
                            
                            # 运行完整分析
                            result = st.session_state.analysis_system.run_complete_analysis()
                            st.success(result)
                        else:
                            st.error(message)
                    else:
                        st.error(message)
            else:
                st.error("❌ 请先上传数据文件")
        
        st.header("📋 功能说明")
        st.markdown("""
        ### 🔍 核心功能
        - **按期数+彩种分离分析**
        - **完整组合搜索展示**
        - **智能最优组合评选**
        - **金额匹配度分析**
        
        ### 🎯 分析目标
        - 2-4个账户的完美数字覆盖
        - 1-49个数字的完整覆盖
        - 高金额匹配度组合
        """)
    
    # 主内容区
    if uploaded_file is not None:
        # 显示数据概览
        st.session_state.analysis_system.display_data_overview()
        
        # 显示分析结果
        if st.session_state.analysis_system.all_period_results:
            tab1, tab2, tab3 = st.tabs(["📊 完整组合", "🏆 最优汇总", "🏅 全局最佳"])
            
            with tab1:
                st.session_state.analysis_system.display_all_combinations()
            
            with tab2:
                st.session_state.analysis_system.display_best_combinations_summary()
            
            with tab3:
                st.session_state.analysis_system.display_global_best_combination()
        else:
            st.info("👆 点击侧边栏的'开始分析'按钮运行分析")
    else:
        st.info("👆 请在侧边栏上传数据文件开始分析")
        
        # 显示使用说明
        st.markdown("""
        ### 📝 使用说明
        1. **上传** Excel/CSV格式的彩票数据文件
        2. **点击** "开始分析"按钮
        3. **查看** 各标签页的分析结果
        
        ### 🔧 数据格式要求
        文件应包含以下列（列名可以不同，系统会自动识别）：
        - **会员账号**: 用户账号信息
        - **彩种**: 彩票类型名称
        - **期号**: 彩票期次编号  
        - **玩法分类**: 投注的玩法类型（需要包含"特码"）
        - **内容**: 投注的具体内容
        - **金额**: 投注金额（可选）
        
        ### 🎲 支持彩种
        - 新澳门六合彩
        - 澳门六合彩
        - 香港六合彩
        - 一分六合彩
        - 五分六合彩
        - 三分六合彩
        - 香港⑥合彩
        - 分分六合彩
        """)

if __name__ == "__main__":
    main()
