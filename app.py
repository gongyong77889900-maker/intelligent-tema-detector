import pandas as pd
import numpy as np
import streamlit as st
import re
from collections import defaultdict
from itertools import combinations
import io

# 页面配置
st.set_page_config(
    page_title="彩票号码覆盖检测系统",
    page_icon="🎯",
    layout="wide"
)

# 系统标题
st.title("🎯 彩票号码覆盖检测系统")
st.markdown("---")

class LotteryCoverageSystem:
    def __init__(self):
        # 定义所有彩种的号码范围
        self.number_ranges = {
            '六合彩': list(range(1, 50)),      # 1-49
            '快三': list(range(3, 19)),        # 3-18  
            'PK拾': list(range(1, 11)),        # 1-10
            '时时彩': list(range(0, 10)),      # 0-9
            '3D': list(range(0, 10))           # 0-9
        }
        
        # 位置名称映射
        self.position_names = {
            # 六合彩位置
            '特码': '特码', '正码': '正码', '正码1': '正码1', '正码2': '正码2',
            '正码3': '正码3', '正码4': '正码4', '正码5': '正码5', '正码6': '正码6',
            '正1特': '正1特', '正2特': '正2特', '正3特': '正3特', '正4特': '正4特',
            '正5特': '正5特', '正6特': '正6特', '正特': '正特', '正码1-6': '正码1-6',
            
            # PK拾位置
            '定位胆': '定位胆', '冠军': '冠军', '亚军': '亚军', '第三名': '第三名',
            '第四名': '第四名', '第五名': '第五名', '第六名': '第六名', '第七名': '第七名',
            '第八名': '第八名', '第九名': '第九名', '第十名': '第十名', '前一': '冠军',
            '定位胆_第1~5名': '定位胆_第1~5名', '定位胆_第6~10名': '定位胆_第6~10名',
            '冠亚和': '冠亚和', '冠亚和_和值': '冠亚和',
            
            # 时时彩位置
            '第1球': '第1球', '第2球': '第2球', '第3球': '第3球', '第4球': '第4球', '第5球': '第5球',
            '万位': '第1球', '千位': '第2球', '百位': '第3球', '十位': '第4球', '个位': '第5球',
            
            # 3D位置
            '百位': '百位', '十位': '十位', '个位': '个位',
            '定位胆_百位': '百位', '定位胆_十位': '十位', '定位胆_个位': '个位',
            
            # 快三位置
            '和值': '和值', '和值_大小单双': '和值'
        }
        
        # 默认阈值设置
        self.default_settings = {
            '六合彩': {'最少号码数': 11, '最低每号金额': 10},
            '快三': {'最少号码数': 4, '最低每号金额': 5},
            'PK拾': {'最少号码数': 3, '最低每号金额': 5},
            '时时彩': {'最少号码数': 3, '最低每号金额': 5},
            '3D': {'最少号码数': 3, '最低每号金额': 5}
        }

    def identify_lottery_type(self, lottery_name):
        """智能识别彩种类型"""
        name_str = str(lottery_name).lower()
        
        if any(keyword in name_str for keyword in ['六合彩', 'lhc', '特码', '正码']):
            return '六合彩'
        elif any(keyword in name_str for keyword in ['快三', '快3', 'k3', '和值']):
            return '快三'
        elif any(keyword in name_str for keyword in ['pk10', 'pk拾', '飞艇', '赛车']):
            return 'PK拾'
        elif any(keyword in name_str for keyword in ['时时彩', 'ssc', '分分彩']):
            return '时时彩'
        elif any(keyword in name_str for keyword in ['3d', '福彩3d', '排列三']):
            return '3D'
        else:
            return '未知'

    def extract_numbers(self, content_text):
        """从内容中提取号码"""
        try:
            if pd.isna(content_text):
                return []
            
            text = str(content_text).strip()
            
            # 处理竖线格式 |1|2|3|
            if '|' in text:
                numbers = []
                parts = text.split('|')
                for part in parts:
                    part_clean = part.strip()
                    if part_clean.isdigit():
                        numbers.append(int(part_clean))
                return numbers
            
            # 处理逗号分隔 1,2,3
            if ',' in text:
                numbers = []
                parts = text.split(',')
                for part in parts:
                    part_clean = part.strip()
                    if part_clean.isdigit():
                        numbers.append(int(part_clean))
                return numbers
            
            # 处理空格分隔 1 2 3
            if ' ' in text:
                numbers = []
                parts = text.split()
                for part in parts:
                    part_clean = part.strip()
                    if part_clean.isdigit():
                        numbers.append(int(part_clean))
                return numbers
            
            # 处理单个数字
            if text.isdigit():
                return [int(text)]
            
            # 处理投注：1,2,3 格式
            if '投注' in text:
                # 提取投注后面的数字部分
                number_part = text.split('投注')[-1]
                # 移除非数字字符，只保留数字和逗号
                clean_part = re.sub(r'[^\d,]', '', number_part)
                if ',' in clean_part:
                    return [int(x) for x in clean_part.split(',') if x.isdigit()]
                elif clean_part.isdigit():
                    return [int(clean_part)]
            
            return []
            
        except Exception as e:
            return []

    def extract_amount(self, amount_text):
        """提取金额"""
        try:
            if pd.isna(amount_text):
                return 0
            
            text = str(amount_text).strip()
            
            # 处理 投注：100.00 抵用：0 格式
            if '投注：' in text and '抵用：' in text:
                try:
                    bet_part = text.split('投注：')[1].split('抵用：')[0]
                    # 提取数字
                    numbers = re.findall(r'\d+\.?\d*', bet_part)
                    if numbers:
                        return float(numbers[0])
                except:
                    pass
            
            # 直接提取所有数字，取第一个
            numbers = re.findall(r'\d+\.?\d*', text.replace(',', ''))
            if numbers:
                return float(numbers[0])
            
            return 0
        except:
            return 0

    def process_data(self, uploaded_file):
        """处理上传的数据文件"""
        try:
            # 读取Excel文件
            df = pd.read_excel(uploaded_file)
            
            # 检查必要列
            required_columns = ['会员账号', '彩种', '期号', '玩法', '内容', '金额']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                st.error(f"缺少必要列: {', '.join(missing_columns)}")
                return None
            
            # 数据清洗
            df = df.dropna(subset=required_columns)
            
            # 识别彩种类型
            df['彩种类型'] = df['彩种'].apply(self.identify_lottery_type)
            
            # 统一位置名称
            df['标准位置'] = df['玩法'].apply(lambda x: self.position_names.get(str(x), str(x)))
            
            # 提取号码
            df['投注号码'] = df.apply(
                lambda row: self.extract_numbers(row['内容']), 
                axis=1
            )
            
            # 提取金额
            df['投注金额'] = df['金额'].apply(self.extract_amount)
            
            # 计算号码数量
            df['号码数量'] = df['投注号码'].apply(len)
            
            return df
            
        except Exception as e:
            st.error(f"数据处理失败: {str(e)}")
            return None

    def detect_coverage_patterns(self, df, settings):
        """检测号码覆盖模式"""
        try:
            # 过滤有效记录
            df_valid = self.filter_valid_records(df, settings)
            
            if len(df_valid) == 0:
                return []
            
            # 按位置分组检测
            all_patterns = []
            grouped = df_valid.groupby(['期号', '彩种类型', '标准位置'])
            
            for (period, lottery, position), group in grouped:
                # 获取该位置的全集号码
                full_set = self.get_full_number_set(lottery, position)
                if not full_set:
                    continue
                
                # 检测2-4个账户的组合
                for account_count in [2, 3, 4]:
                    patterns = self.find_coverage_combinations(
                        group, full_set, account_count, period, lottery, position
                    )
                    all_patterns.extend(patterns)
            
            return all_patterns
            
        except Exception as e:
            st.error(f"检测失败: {str(e)}")
            return []

    def filter_valid_records(self, df, settings):
        """根据阈值过滤有效记录"""
        valid_rows = []
        
        for _, row in df.iterrows():
            lottery = row.get('彩种类型', '未知')
            numbers = row.get('投注号码', [])
            amount = row.get('投注金额', 0)
            number_count = len(numbers)
            
            # 跳过未知彩种
            if lottery not in settings:
                continue
            
            # 获取阈值
            min_numbers = settings[lottery]['最少号码数']
            min_amount = settings[lottery]['最低每号金额']
            
            # 计算平均每号金额
            if number_count > 0:
                avg_amount = amount / number_count
            else:
                avg_amount = 0
            
            # 应用阈值过滤
            if number_count >= min_numbers and avg_amount >= min_amount:
                valid_rows.append(row)
        
        return pd.DataFrame(valid_rows)

    def get_full_number_set(self, lottery, position):
        """获取完整的号码集合"""
        if lottery not in self.number_ranges:
            return None
        
        base_numbers = set(self.number_ranges[lottery])
        
        # 特殊处理冠亚和
        if position == '冠亚和' and lottery == 'PK拾':
            return set(range(3, 20))
        
        return base_numbers

    def find_coverage_combinations(self, group_data, full_set, account_count, period, lottery, position):
        """查找号码覆盖组合"""
        patterns = []
        
        # 构建账户数据
        account_data = {}
        for _, row in group_data.iterrows():
            account = row['会员账号']
            numbers = set(row['投注号码'])
            amount = row['投注金额']
            
            if account not in account_data:
                account_data[account] = {
                    'numbers': set(),
                    'total_amount': 0
                }
            
            account_data[account]['numbers'] |= numbers
            account_data[account]['total_amount'] += amount
        
        # 检查所有账户组合
        accounts = list(account_data.keys())
        if len(accounts) < account_count:
            return patterns
        
        for account_group in combinations(accounts, account_count):
            # 检查是否完美覆盖
            if self.check_perfect_coverage(account_group, account_data, full_set):
                pattern = self.analyze_coverage_pattern(
                    account_group, account_data, full_set, period, lottery, position, account_count
                )
                if pattern:
                    patterns.append(pattern)
        
        return patterns

    def check_perfect_coverage(self, account_group, account_data, full_set):
        """检查是否完美覆盖"""
        try:
            # 检查并集是否等于全集
            union_numbers = set()
            for account in account_group:
                union_numbers |= account_data[account]['numbers']
            
            if union_numbers != full_set:
                return False
            
            # 检查号码是否不重叠
            for i in range(len(account_group)):
                for j in range(i + 1, len(account_group)):
                    set1 = account_data[account_group[i]]['numbers']
                    set2 = account_data[account_group[j]]['numbers']
                    if set1 & set2:  # 有交集
                        return False
            
            return True
            
        except:
            return False

    def analyze_coverage_pattern(self, account_group, account_data, full_set, period, lottery, position, account_count):
        """分析覆盖模式"""
        try:
            coverage_details = []
            avg_amounts = []
            
            for account in account_group:
                data = account_data[account]
                numbers = data['numbers']
                total_amount = data['total_amount']
                number_count = len(numbers)
                
                if number_count > 0:
                    avg_amount = total_amount / number_count
                else:
                    avg_amount = 0
                
                avg_amounts.append(avg_amount)
                coverage_details.append({
                    '账户': account,
                    '号码数量': number_count,
                    '总金额': total_amount,
                    '平均每号金额': avg_amount,
                    '具体号码': sorted(list(numbers))
                })
            
            # 计算金额相似度
            if avg_amounts and max(avg_amounts) > 0:
                similarity = min(avg_amounts) / max(avg_amounts)
            else:
                similarity = 0
            
            # 确定相似度等级
            if similarity >= 0.9:
                level = "🟢 优秀"
            elif similarity >= 0.8:
                level = "🟡 良好"
            elif similarity >= 0.7:
                level = "🟠 一般"
            else:
                level = "🔴 较差"
            
            return {
                '期号': period,
                '彩种': lottery,
                '位置': position,
                '账户组': list(account_group),
                '账户数量': account_count,
                '全集大小': len(full_set),
                '全集号码': sorted(list(full_set)),
                '覆盖详情': coverage_details,
                '金额相似度': similarity,
                '相似度等级': level,
                '总投注金额': sum(data['total_amount'] for data in account_data.values())
            }
            
        except Exception as e:
            return None

# 创建系统实例
system = LotteryCoverageSystem()

# 侧边栏配置
with st.sidebar:
    st.header("📁 数据上传")
    uploaded_file = st.file_uploader(
        "选择Excel文件", 
        type=['xlsx', 'xls'],
        help="请上传包含投注数据的Excel文件"
    )
    
    st.header("⚙️ 检测参数设置")
    
    # 各彩种阈值设置
    settings = {}
    for lottery in ['六合彩', '快三', 'PK拾', '时时彩', '3D']:
        st.subheader(f"{lottery}设置")
        
        min_numbers = st.number_input(
            f"{lottery}最少号码数", 
            min_value=1, 
            max_value=50,
            value=system.default_settings[lottery]['最少号码数'],
            key=f"min_num_{lottery}"
        )
        
        min_amount = st.number_input(
            f"{lottery}最低每号金额", 
            min_value=1, 
            max_value=20,
            value=system.default_settings[lottery]['最低每号金额'],
            key=f"min_amt_{lottery}"
        )
        
        settings[lottery] = {
            '最少号码数': min_numbers,
            '最低每号金额': min_amount
        }

# 主界面
if uploaded_file is not None:
    # 显示文件信息
    st.success(f"✅ 已上传文件: {uploaded_file.name}")
    
    # 处理数据
    with st.spinner("🔄 正在处理数据..."):
        processed_data = system.process_data(uploaded_file)
    
    if processed_data is not None:
        st.success("✅ 数据预处理完成")
        
        # 显示数据概览
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总记录数", f"{len(processed_data):,}")
        with col2:
            st.metric("唯一期号", f"{processed_data['期号'].nunique():,}")
        with col3:
            st.metric("唯一账户", f"{processed_data['会员账号'].nunique():,}")
        with col4:
            st.metric("彩种类型", f"{processed_data['彩种类型'].nunique()}")
        
        # 数据预览
        with st.expander("📋 数据预览", expanded=False):
            st.dataframe(processed_data.head(20))
        
        # 开始检测
        st.info("🔍 开始检测号码覆盖模式...")
        with st.spinner("正在分析号码覆盖情况..."):
            patterns = system.detect_coverage_patterns(processed_data, settings)
        
        if patterns:
            st.success(f"🎉 检测完成！共发现 {len(patterns)} 个覆盖模式")
            
            # 显示总体统计
            st.subheader("📊 总体统计")
            
            total_groups = len(patterns)
            total_accounts = sum(p['账户数量'] for p in patterns)
            total_amount = sum(p['总投注金额'] for p in patterns)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("覆盖组数", total_groups)
            with col2:
                st.metric("涉及账户", total_accounts)
            with col3:
                st.metric("总金额", f"¥{total_amount:,.0f}")
            with col4:
                avg_similarity = np.mean([p['金额相似度'] for p in patterns])
                st.metric("平均相似度", f"{avg_similarity:.1%}")
            
            # 按彩种统计
            st.subheader("🎲 按彩种统计")
            lottery_stats = {}
            for pattern in patterns:
                lottery = pattern['彩种']
                if lottery not in lottery_stats:
                    lottery_stats[lottery] = {'count': 0, 'amount': 0}
                lottery_stats[lottery]['count'] += 1
                lottery_stats[lottery]['amount'] += pattern['总投注金额']
            
            # 创建彩种统计列
            lottery_cols = st.columns(len(lottery_stats))
            for i, (lottery, stats) in enumerate(lottery_stats.items()):
                with lottery_cols[i]:
                    st.metric(
                        label=lottery,
                        value=stats['count'],
                        delta=f"¥{stats['amount']:,.0f}"
                    )
            
            # 详细结果
            st.subheader("🔍 详细检测结果")
            
            for i, pattern in enumerate(patterns, 1):
                with st.expander(
                    f"模式{i}: {pattern['彩种']} - {pattern['位置']} | {pattern['相似度等级']} | {pattern['账户数量']}个账户", 
                    expanded=True
                ):
                    # 基本信息
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**期号:** {pattern['期号']}")
                        st.write(f"**位置:** {pattern['位置']}")
                        st.write(f"**全集号码:** {len(pattern['全集号码'])}个")
                        st.write(f"**账户数量:** {pattern['账户数量']}个")
                    
                    with col2:
                        st.write(f"**总投注金额:** ¥{pattern['总投注金额']:,.2f}")
                        st.write(f"**金额相似度:** {pattern['金额相似度']:.1%}")
                        st.write(f"**相似度等级:** {pattern['相似度等级']}")
                        st.write(f"**全集:** {pattern['全集号码']}")
                    
                    # 账户详情
                    st.write("**账户投注详情:**")
                    for detail in pattern['覆盖详情']:
                        st.write(f"- **{detail['账户']}**: "
                                f"{detail['号码数量']}个号码, "
                                f"总金额¥{detail['总金额']:,.2f}, "
                                f"平均每号¥{detail['平均每号金额']:,.2f}")
                        st.write(f"  投注号码: {detail['具体号码']}")
                    
                    st.markdown("---")
            
            # 导出结果
            st.subheader("📤 结果导出")
            if st.button("生成检测报告"):
                # 创建报告数据
                report_data = []
                for pattern in patterns:
                    for detail in pattern['覆盖详情']:
                        report_data.append({
                            '期号': pattern['期号'],
                            '彩种': pattern['彩种'],
                            '位置': pattern['位置'],
                            '账户': detail['账户'],
                            '号码数量': detail['号码数量'],
                            '总金额': detail['总金额'],
                            '平均每号金额': detail['平均每号金额'],
                            '投注号码': str(detail['具体号码']),
                            '全集号码': str(pattern['全集号码']),
                            '金额相似度': pattern['金额相似度'],
                            '相似度等级': pattern['相似度等级'],
                            '账户组': str(pattern['账户组'])
                        })
                
                report_df = pd.DataFrame(report_data)
                
                # 生成Excel文件
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    report_df.to_excel(writer, sheet_name='检测结果', index=False)
                
                st.download_button(
                    label="📥 下载检测报告",
                    data=output.getvalue(),
                    file_name=f"号码覆盖检测报告_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.ms-excel"
                )
                
        else:
            st.warning("⚠️ 未发现符合条件的号码覆盖模式")
            
else:
    # 系统介绍
    st.info("👈 请在左侧上传Excel文件开始分析")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎯 系统功能")
        st.markdown("""
        **支持的彩种:**
        - 🎲 六合彩: 1-49个号码
        - 🎯 快三和值: 3-18个和值  
        - 🚗 PK拾: 1-10个号码
        - ⏰ 时时彩: 0-9个号码
        - 🔢 3D: 0-9个号码
        
        **检测能力:**
        - 2个账户完美互补覆盖
        - 3个账户三方互补覆盖
        - 4个账户四方互补覆盖
        - 自动计算金额相似度
        """)
    
    with col2:
        st.subheader("📊 相似度标准")
        st.markdown("""
        **金额相似度等级:**
        - 🟢 优秀: 90%及以上
        - 🟡 良好: 80%-89%  
        - 🟠 一般: 70%-79%
        - 🔴 较差: 70%以下
        
        **默认阈值:**
        - 六合彩: ≥11号码, ≥10元/号
        - 和值类: ≥4号码, ≥5元/号
        - 定位类: ≥3号码, ≥5元/号
        """)
    
    with st.expander("📖 使用说明", expanded=True):
        st.markdown("""
        ### 使用步骤
        
        1. **准备数据**: 确保Excel文件包含以下列：
           - 会员账号
           - 彩种  
           - 期号
           - 玩法
           - 内容
           - 金额
        
        2. **上传文件**: 在左侧边栏选择Excel文件
        
        3. **设置参数**: 调整各彩种的检测阈值
        
        4. **开始检测**: 系统自动分析号码覆盖情况
        
        5. **查看结果**: 浏览检测到的覆盖模式
        
        6. **导出报告**: 下载详细的检测结果
        
        ### 检测原理
        
        系统会检查同一期号、同一彩种、同一位置的多个账户投注是否满足：
        - 所有账户投注的号码合并后正好是该位置的全部号码
        - 各个账户投注的号码没有重复
        - 每个账户的投注金额满足阈值要求
        
        这样的模式表明可能存在协调性的对刷行为。
        """)
