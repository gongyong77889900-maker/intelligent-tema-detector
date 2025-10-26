import streamlit as st
import pandas as pd
import re

# 设置页面
st.set_page_config(
    page_title="特码完美覆盖分析系统",
    page_icon="🎯",
    layout="wide"
)

# 主标题
st.title("🎯 特码完美覆盖分析系统")
st.markdown("---")

# 文件上传
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
        
        # 简单的列识别
        def rename_columns_simple(df):
            """简单列重命名"""
            new_columns = {}
            for col in df.columns:
                col_lower = str(col).lower()
                if any(x in col_lower for x in ['会员', '账号', '账户']):
                    new_columns[col] = '会员账号'
                elif any(x in col_lower for x in ['彩种', '彩票']):
                    new_columns[col] = '彩种'
                elif any(x in col_lower for x in ['期号', '期数']):
                    new_columns[col] = '期号'
                elif any(x in col_lower for x in ['玩法', '分类']):
                    new_columns[col] = '玩法分类'
                elif any(x in col_lower for x in ['内容', '投注']):
                    new_columns[col] = '内容'
                elif any(x in col_lower for x in ['金额', '投注金额']):
                    new_columns[col] = '金额'
            return new_columns
        
        # 重命名列
        column_mapping = rename_columns_simple(df)
        if column_mapping:
            df = df.rename(columns=column_mapping)
        
        # 检查必要列
        required_cols = ['会员账号', '彩种', '期号', '玩法分类', '内容']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            st.error(f"❌ 缺少必要列: {', '.join(missing_cols)}")
            st.stop()
        
        # 简单数据清理
        df_clean = df[required_cols].copy()
        
        # 转换为字符串并清理
        for col in df_clean.columns:
            df_clean[col] = df_clean[col].fillna('').astype(str)
        
        # 提取金额（如果存在金额列）
        has_amount = '金额' in df.columns
        if has_amount:
            df_clean['金额'] = df['金额'].fillna('').astype(str)
            
            def simple_extract_amount(text):
                """简单金额提取"""
                try:
                    # 直接找数字
                    numbers = re.findall(r'\d+\.?\d*', str(text))
                    for num in numbers:
                        try:
                            amount = float(num)
                            if amount > 0:
                                return amount
                        except:
                            continue
                    return 0
                except:
                    return 0
            
            df_clean['投注金额'] = df_clean['金额'].apply(simple_extract_amount)
        
        # 筛选特码数据
        target_lotteries = ['新澳门六合彩', '澳门六合彩', '香港六合彩']
        df_target = df_clean[
            (df_clean['彩种'].isin(target_lotteries)) & 
            (df_clean['玩法分类'].str.contains('特码'))
        ]
        
        if len(df_target) == 0:
            st.error("❌ 未找到特码玩法数据")
            st.stop()
        
        # 显示基本信息
        st.header("🎯 特码分析概览")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("特码数据行数", f"{len(df_target):,}")
        with col2:
            st.metric("涉及期数", f"{df_target['期号'].nunique()}")
        with col3:
            st.metric("涉及账户", f"{df_target['会员账号'].nunique()}")
        
        if has_amount:
            total_amount = df_target['投注金额'].sum()
            st.metric("总投注金额", f"{total_amount:,.2f} 元")
        
        # 核心分析功能
        st.header("🔍 完美组合分析")
        
        def extract_numbers_simple(content):
            """简单数字提取"""
            numbers = []
            for match in re.findall(r'\d+', str(content)):
                num = int(match)
                if 1 <= num <= 49:
                    numbers.append(num)
            return list(set(numbers))
        
        # 按期号分析
        periods = df_target['期号'].unique()
        
        if len(periods) == 0:
            st.warning("❌ 没有可分析的期号数据")
            st.stop()
        
        # 选择期号进行分析
        selected_period = st.selectbox("选择期号进行分析", periods)
        
        if selected_period:
            period_data = df_target[df_target['期号'] == selected_period]
            
            # 按账户分组
            accounts_data = {}
            for account in period_data['会员账号'].unique():
                account_data = period_data[period_data['会员账号'] == account]
                all_numbers = set()
                total_bet = 0
                
                for _, row in account_data.iterrows():
                    numbers = extract_numbers_simple(row['内容'])
                    all_numbers.update(numbers)
                    if has_amount:
                        total_bet += row['投注金额']
                
                if len(all_numbers) > 11:  # 只考虑投注11个数字以上的账户
                    accounts_data[account] = {
                        'numbers': sorted(all_numbers),
                        'total_bet': total_bet,
                        'number_count': len(all_numbers)
                    }
            
            st.write(f"**期号 {selected_period} 的有效账户**: {len(accounts_data)}个")
            
            if len(accounts_data) < 2:
                st.warning("❌ 有效账户不足，无法形成组合")
                st.stop()
            
            # 查找完美组合
            accounts_list = list(accounts_data.keys())
            perfect_combinations = []
            
            # 检查2账户组合
            for i in range(len(accounts_list)):
                for j in range(i+1, len(accounts_list)):
                    acc1, acc2 = accounts_list[i], accounts_list[j]
                    set1 = set(accounts_data[acc1]['numbers'])
                    set2 = set(accounts_data[acc2]['numbers'])
                    
                    if len(set1 | set2) == 49:
                        total_amount = accounts_data[acc1]['total_bet'] + accounts_data[acc2]['total_bet']
                        perfect_combinations.append({
                            'accounts': [acc1, acc2],
                            'account_count': 2,
                            'total_amount': total_amount,
                            'numbers': set1 | set2
                        })
            
            # 检查3账户组合
            for i in range(len(accounts_list)):
                for j in range(i+1, len(accounts_list)):
                    for k in range(j+1, len(accounts_list)):
                        acc1, acc2, acc3 = accounts_list[i], accounts_list[j], accounts_list[k]
                        set1 = set(accounts_data[acc1]['numbers'])
                        set2 = set(accounts_data[acc2]['numbers'])
                        set3 = set(accounts_data[acc3]['numbers'])
                        
                        if len(set1 | set2 | set3) == 49:
                            total_amount = (accounts_data[acc1]['total_bet'] + 
                                          accounts_data[acc2]['total_bet'] + 
                                          accounts_data[acc3]['total_bet'])
                            perfect_combinations.append({
                                'accounts': [acc1, acc2, acc3],
                                'account_count': 3,
                                'total_amount': total_amount,
                                'numbers': set1 | set2 | set3
                            })
            
            # 显示结果
            if perfect_combinations:
                st.success(f"🎉 找到 {len(perfect_combinations)} 个完美组合")
                
                for i, combo in enumerate(perfect_combinations, 1):
                    with st.expander(f"组合 {i} - {combo['account_count']}个账户", expanded=True):
                        st.write(f"**账户**: {' + '.join(combo['accounts'])}")
                        st.write(f"**覆盖数字**: {len(combo['numbers'])}个")
                        
                        if has_amount:
                            st.write(f"**总投注金额**: {combo['total_amount']:,.2f} 元")
                        
                        for account in combo['accounts']:
                            acc_data = accounts_data[account]
                            st.write(f"**{account}**: {acc_data['number_count']}个数字 | 总投注: {acc_data['total_bet']:,.2f}元")
                            st.write(f"投注内容: {', '.join([f'{n:02d}' for n in acc_data['numbers']])}")
            else:
                st.warning("❌ 未找到完美覆盖组合")
    
    except Exception as e:
        st.error(f"❌ 处理数据时出错: {str(e)}")
        st.info("💡 请检查Excel文件格式是否正确，或联系技术支持")

else:
    st.info("👆 请上传Excel文件开始分析")

# 页脚
st.markdown("---")
st.markdown("🎯 特码完美覆盖分析系统")
