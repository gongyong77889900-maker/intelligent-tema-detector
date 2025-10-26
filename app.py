import streamlit as st
import pandas as pd
import io
import itertools
import re
import numpy as np
from collections import defaultdict

# Streamlit页面配置
st.set_page_config(
    page_title="特码完美覆盖分析系统 + 对刷检测",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 应用标题
st.title("🎯 特码完美覆盖分析系统 + 自动对刷检测")
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

class 自动对刷检测系统:
    def __init__(self):
        self.玩法规则 = self.初始化玩法规则()
        
    def 初始化玩法规则(self):
        """初始化各种玩法的对刷规则"""
        规则 = {
            '特码': {
                '检测方法': self.检测特码对刷,
                '相反玩法': ['特码A', '特码B']
            },
            '大小': {
                '检测方法': self.检测大小对刷,
                '相反玩法': ['大', '小']
            },
            '单双': {
                '检测方法': self.检测单双对刷,
                '相反玩法': ['单', '双']
            },
            '波色': {
                '检测方法': self.检测波色对刷,
                '相反玩法': ['红波', '蓝波', '绿波']
            },
            '尾数': {
                '检测方法': self.检测尾数对刷,
                '相反玩法': ['尾大', '尾小']
            }
        }
        return 规则
    
    def 检测特码对刷(self, 内容1, 内容2):
        """检测特码对刷 - 相同的号码但不同的投注方向"""
        try:
            # 提取数字号码
            号码1 = re.findall(r'\d+', str(内容1))
            号码2 = re.findall(r'\d+', str(内容2))
            
            if 号码1 and 号码2:
                return 号码1[0] == 号码2[0]
            return False
        except:
            return False
    
    def 检测大小对刷(self, 内容1, 内容2):
        """检测大小对刷"""
        大小映射 = {'大': '小', '小': '大'}
        内容1_clean = str(内容1).strip().replace(' ', '')
        内容2_clean = str(内容2).strip().replace(' ', '')
        
        return (内容1_clean in 大小映射 and 
                内容2_clean == 大小映射.get(内容1_clean, ''))
    
    def 检测单双对刷(self, 内容1, 内容2):
        """检测单双对刷"""
        单双映射 = {'单': '双', '双': '单'}
        内容1_clean = str(内容1).strip().replace(' ', '')
        内容2_clean = str(内容2).strip().replace(' ', '')
        
        return (内容1_clean in 单双映射 and 
                内容2_clean == 单双映射.get(内容1_clean, ''))
    
    def 检测波色对刷(self, 内容1, 内容2):
        """检测波色对刷 - 不同的波色组合"""
        波色组 = [['红波', '蓝波', '绿波']]
        内容1_clean = str(内容1).strip().replace(' ', '')
        内容2_clean = str(内容2).strip().replace(' ', '')
        
        for 组 in 波色组:
            if 内容1_clean in 组 and 内容2_clean in 组 and 内容1_clean != 内容2_clean:
                return True
        return False
    
    def 检测尾数对刷(self, 内容1, 内容2):
        """检测尾数对刷"""
        尾数映射 = {'尾大': '尾小', '尾小': '尾大'}
        内容1_clean = str(内容1).strip().replace(' ', '')
        内容2_clean = str(内容2).strip().replace(' ', '')
        
        return (内容1_clean in 尾数映射 and 
                内容2_clean == 尾数映射.get(内容1_clean, ''))
    
    def 检测对刷组合(self, df, 期号, 彩种):
        """检测特定期号和彩种的对刷组合"""
        对刷结果 = []
        
        # 按玩法分类分组
        for 玩法, group in df.groupby('玩法分类'):
            if 玩法 not in self.玩法规则:
                continue
                
            规则 = self.玩法规则[玩法]
            账户列表 = group['会员账号'].unique()
            
            # 检查所有账户对
            for i, 账户1 in enumerate(账户列表):
                账户1数据 = group[group['会员账号'] == 账户1]
                
                for j, 账户2 in enumerate(账户列表[i+1:], i+1):
                    账户2数据 = group[group['会员账号'] == 账户2]
                    
                    # 检查每对投注内容
                    for _, 行1 in 账户1数据.iterrows():
                        for _, 行2 in 账户2数据.iterrows():
                            if 规则['检测方法'](行1['内容'], 行2['内容']):
                                # 发现对刷
                                对刷结果.append({
                                    '期号': 期号,
                                    '彩种': 彩种,
                                    '玩法': 玩法,
                                    '账户1': 账户1,
                                    '账户2': 账户2,
                                    '内容1': 行1['内容'],
                                    '内容2': 行2['内容'],
                                    '金额1': 行1.get('投注金额', 0),
                                    '金额2': 行2.get('投注金额', 0),
                                    '时间1': 行1.get('投注时间', ''),
                                    '时间2': 行2.get('投注时间', '')
                                })
        
        return 对刷结果

def extract_bet_amount(amount_text):
    """从复杂文本中提取投注金额"""
    try:
        if pd.isna(amount_text):
            return 0
        
        # 确保是字符串类型
        text = str(amount_text)
        
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
    used_standard_cols = set()
    
    # 修复：确保对列名进行字符串处理
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

def extract_numbers_from_content(content):
    """从内容中提取所有1-49的数字"""
    numbers = []
    # 修复：确保内容是字符串
    content_str = str(content) if content is not None else ""
    
    # 使用正则表达式提取所有数字
    number_matches = re.findall(r'\d+', content_str)
    for match in number_matches:
        try:
            num = int(match)
            if 1 <= num <= 49:
                numbers.append(num)
        except:
            continue
    
    return list(set(numbers))

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

# 初始化对刷检测系统
对刷检测器 = 自动对刷检测系统()

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
                
                # 数据类型转换 - 修复：确保对Series使用str方法
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
                
                # 自动对刷检测
                st.header("🔍 自动对刷检测结果")
                
                # 定义需要分析的彩种
                target_lotteries = [
                    '新澳门六合彩', '澳门六合彩', '香港六合彩', '一分六合彩',
                    '五分六合彩', '三分六合彩', '香港⑥合彩', '分分六合彩'
                ]
                
                # 筛选目标彩种
                df_target = df_clean[df_clean['彩种'].isin(target_lotteries)]
                
                if len(df_target) > 0:
                    # 按期数和彩种进行对刷检测
                    所有对刷结果 = []
                    
                    # 进度条
                    progress_bar = st.progress(0)
                    grouped = df_target.groupby(['期号', '彩种'])
                    total_groups = len(grouped)
                    
                    for i, ((期号, 彩种), group) in enumerate(grouped):
                        if len(group) < 2:  # 至少需要2个账户才能检测对刷
                            continue
                        
                        对刷结果 = 对刷检测器.检测对刷组合(group, 期号, 彩种)
                        所有对刷结果.extend(对刷结果)
                        
                        # 更新进度条
                        progress_bar.progress((i + 1) / total_groups)
                    
                    # 显示对刷检测结果
                    if 所有对刷结果:
                        st.error(f"🚨 发现 {len(所有对刷结果)} 个可疑对刷组合!")
                        
                        # 转换为DataFrame便于显示
                        对刷df = pd.DataFrame(所有对刷结果)
                        
                        # 按玩法分类显示
                        for 玩法 in 对刷df['玩法'].unique():
                            玩法数据 = 对刷df[对刷df['玩法'] == 玩法]
                            st.subheader(f"🎯 {玩法}玩法对刷检测 ({len(玩法数据)}个)")
                            
                            for _, 行 in 玩法数据.iterrows():
                                with st.expander(f"期号:{行['期号']} | {行['账户1']} ↔ {行['账户2']}", expanded=False):
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        st.write(f"**账户1:** {行['账户1']}")
                                        st.write(f"内容: {行['内容1']}")
                                        if has_amount_column:
                                            st.write(f"金额: {行['金额1']:,.2f}元")
                                    with col2:
                                        st.write(f"**账户2:** {行['账户2']}")
                                        st.write(f"内容: {行['内容2']}")
                                        if has_amount_column:
                                            st.write(f"金额: {行['金额2']:,.2f}元")
                                    
                                    # 风险等级评估
                                    金额差异 = abs(行['金额1'] - 行['金额2'])
                                    金额比例 = min(行['金额1'], 行['金额2']) / max(行['金额1'], 行['金额2']) if max(行['金额1'], 行['金额2']) > 0 else 0
                                    
                                    if 金额比例 >= 0.8:
                                        st.error("🔴 高风险: 金额高度匹配!")
                                    elif 金额比例 >= 0.6:
                                        st.warning("🟡 中风险: 金额较为匹配")
                                    else:
                                        st.info("🟢 低风险: 金额差异较大")
                    else:
                        st.success("✅ 未发现明显的对刷行为")
                
                else:
                    st.warning("❌ 没有找到目标彩种数据")
            
            else:
                st.error("❌ 缺少必要列，无法继续分析")
    
    except Exception as e:
        st.error(f"❌ 程序执行失败: {str(e)}")
        import traceback
        st.error(f"详细错误信息:\n{traceback.format_exc()}")

# 使用说明
with st.expander("📖 使用说明（特码完美覆盖分析系统 + 对刷检测）"):
    st.markdown("""
    ### 系统功能说明

    **🎯 完美覆盖检测逻辑：**
    - 分析六合彩特码玩法的完美数字覆盖组合
    - 支持2-4个账户的组合分析
    - 要求组合数字覆盖1-49所有号码且无重复

    **🔍 对刷检测逻辑：**
    - **特码对刷**: 相同号码的不同投注方向
    - **大小对刷**: 大 vs 小
    - **单双对刷**: 单 vs 双  
    - **波色对刷**: 不同波色组合
    - **尾数对刷**: 尾大 vs 尾小

    **📊 风险等级评估：**
    - 🔴 高风险: 金额匹配度 ≥ 80%
    - 🟡 中风险: 金额匹配度 60%-80%
    - 🟢 低风险: 金额匹配度 < 60%

    **🎲 支持彩种：**
    - 新澳门六合彩、澳门六合彩、香港六合彩
    - 一分六合彩、五分六合彩、三分六合彩
    - 香港⑥合彩、分分六合彩

    **📁 数据格式要求：**
    - 必须包含：会员账号、期号、彩种、玩法分类、内容
    - 可选包含：金额（如有则进行金额分析）
    - 支持自动列名映射
    """)

st.markdown("---")
st.success("🎯 特码完美覆盖分析系统 + 自动对刷检测 - 就绪")
