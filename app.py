import streamlit as st
import pandas as pd
import numpy as np
import io
import re
import logging
from collections import defaultdict
from datetime import datetime
from itertools import combinations
import warnings
import traceback

# 配置日志和警告
warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('MultiAccountWashTrade')

# Streamlit页面配置
st.set_page_config(
    page_title="智能多账户对刷检测系统",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

class Config:
    """配置参数类"""
    def __init__(self):
        self.min_amount = 10
        self.amount_similarity_threshold = 0.9
        self.min_continuous_periods = 3
        self.max_accounts_in_group = 5
        self.supported_file_types = ['.xlsx', '.xls', '.csv']

class WashTradeDetector:
    def __init__(self, config=None):
        self.config = config or Config()
        self.data_processed = False
        self.df_valid = None
        self.export_data = []
        self.performance_stats = {}
    
    def upload_and_process(self, uploaded_file):
        """上传并处理文件"""
        try:
            if uploaded_file is None:
                st.error("❌ 没有上传文件")
                return None, None
            
            filename = uploaded_file.name
            logger.info(f"✅ 已上传文件: {filename}")
            
            if not any(filename.endswith(ext) for ext in self.config.supported_file_types):
                st.error(f"❌ 不支持的文件类型: {filename}")
                return None, None
            
            if filename.endswith('.csv'):
                df = pd.read_csv(uploaded_file, encoding='utf-8')
            else:
                df = pd.read_excel(uploaded_file)
            
            logger.info(f"原始数据维度: {df.shape}")
            
            return df, filename
            
        except Exception as e:
            logger.error(f"文件处理失败: {str(e)}")
            st.error(f"文件处理失败: {str(e)}")
            return None, None
    
    def auto_detect_columns(self, df):
        """自动检测列名"""
        column_mapping = {}
        
        # 显示原始列名供参考
        st.write("📋 原始文件列名:", df.columns.tolist())
        
        # 自动检测逻辑
        for col in df.columns:
            col_lower = str(col).lower()
            
            # 检测会员账号列
            if any(keyword in col_lower for keyword in ['会员', '账号', '账户', '用户']):
                if '会员账号' not in column_mapping.values():
                    column_mapping[col] = '会员账号'
            
            # 检测期号列
            elif any(keyword in col_lower for keyword in ['期号', '期数', '期次', '期']):
                if '期号' not in column_mapping.values():
                    column_mapping[col] = '期号'
            
            # 检测内容列
            elif any(keyword in col_lower for keyword in ['内容', '投注', '下注']):
                if '内容' not in column_mapping.values():
                    column_mapping[col] = '内容'
            
            # 检测金额列
            elif any(keyword in col_lower for keyword in ['金额', '下注总额', '投注金额', '总额']):
                if '金额' not in column_mapping.values():
                    column_mapping[col] = '金额'
            
            # 检测彩种列
            elif any(keyword in col_lower for keyword in ['彩种', '彩票', '游戏']):
                if '彩种' not in column_mapping.values():
                    column_mapping[col] = '彩种'
        
        return column_mapping
    
    def parse_column_data(self, df):
        """解析列结构数据 - 简化版本"""
        try:
            # 自动检测列名
            column_mapping = self.auto_detect_columns(df)
            
            if not column_mapping:
                st.error("❌ 无法自动识别列名，请手动指定列名映射")
                return pd.DataFrame()
            
            st.success("✅ 自动识别到以下列名映射:")
            for orig, mapped in column_mapping.items():
                st.write(f"  {orig} → {mapped}")
            
            # 重命名列
            df_renamed = df.rename(columns=column_mapping)
            
            # 检查必要列
            required_cols = ['会员账号', '期号', '内容', '金额']
            missing_cols = [col for col in required_cols if col not in df_renamed.columns]
            
            if missing_cols:
                st.error(f"❌ 缺少必要列: {missing_cols}")
                return pd.DataFrame()
            
            # 添加彩种列（如果不存在）
            if '彩种' not in df_renamed.columns:
                df_renamed['彩种'] = '未知彩种'
            
            # 选择需要的列
            df_clean = df_renamed[['会员账号', '期号', '内容', '金额', '彩种']].copy()
            df_clean = df_clean.dropna(subset=['会员账号', '期号', '内容', '金额'])
            
            # 数据清理
            for col in ['会员账号', '期号', '内容', '彩种']:
                df_clean[col] = df_clean[col].astype(str).str.strip()
            
            # 提取金额和方向
            df_clean['投注金额'] = df_clean['金额'].apply(self.extract_bet_amount_safe)
            df_clean['投注方向'] = df_clean['内容'].apply(self.extract_direction_from_content)
            
            # 过滤有效记录
            df_valid = df_clean[
                (df_clean['投注方向'] != '') & 
                (df_clean['投注金额'] >= self.config.min_amount)
            ].copy()
            
            if len(df_valid) == 0:
                st.error("❌ 过滤后没有有效记录")
                return pd.DataFrame()
            
            # 显示数据概览
            with st.expander("📊 数据概览", expanded=False):
                st.write(f"总记录数: {len(df_clean)}")
                st.write(f"有效记录数: {len(df_valid)}")
                st.write(f"唯一期号数: {df_valid['期号'].nunique()}")
                st.write(f"唯一账户数: {df_valid['会员账号'].nunique()}")
                
                lottery_stats = df_valid['彩种'].value_counts()
                st.write(f"彩种分布: {dict(lottery_stats)}")
                
                direction_stats = df_valid['投注方向'].value_counts()
                st.write(f"投注方向分布: {dict(direction_stats)}")
            
            self.data_processed = True
            self.df_valid = df_valid
            return df_valid
            
        except Exception as e:
            logger.error(f"数据解析失败: {str(e)}")
            st.error(f"数据解析失败: {str(e)}")
            st.error(f"详细错误: {traceback.format_exc()}")
            return pd.DataFrame()
    
    def extract_bet_amount_safe(self, amount_text):
        """安全提取投注金额"""
        try:
            if pd.isna(amount_text):
                return 0
            
            text = str(amount_text).strip()
            
            # 直接尝试转换
            try:
                cleaned_text = text.replace(',', '').replace('，', '').replace(' ', '')
                amount = float(cleaned_text)
                if amount >= self.config.min_amount:
                    return amount
            except:
                pass
            
            # 尝试提取数字
            numbers = re.findall(r'\d+\.?\d*', text)
            if numbers:
                try:
                    amount = float(numbers[0])
                    if amount >= self.config.min_amount:
                        return amount
                except:
                    pass
            
            return 0
            
        except Exception as e:
            return 0
    
    def extract_direction_from_content(self, content):
        """从内容列提取投注方向"""
        try:
            if pd.isna(content):
                return ""
            
            content_str = str(content).strip().lower()
            
            direction_patterns = {
                '小': ['小', 'small', 'xia'],
                '大': ['大', 'big', 'da'], 
                '单': ['单', 'odd', 'dan'],
                '双': ['双', 'even', 'shuang'],
                '龙': ['龙', 'long', 'dragon'],
                '虎': ['虎', 'hu', 'tiger']
            }
            
            for direction, patterns in direction_patterns.items():
                for pattern in patterns:
                    if pattern in content_str:
                        return direction
            
            return ""
        except Exception as e:
            return ""
    
    def detect_all_wash_trades(self):
        """检测所有类型的对刷交易"""
        if not self.data_processed or self.df_valid is None or len(self.df_valid) == 0:
            st.error("❌ 没有有效数据可用于检测")
            return []
        
        self.performance_stats = {
            'start_time': datetime.now(),
            'total_records': len(self.df_valid),
            'total_periods': self.df_valid['期号'].nunique(),
            'total_accounts': self.df_valid['会员账号'].nunique()
        }
        
        # 排除同一账户多方向下注
        multi_direction_mask = (
            self.df_valid.groupby(['期号', '会员账号'])['投注方向']
            .transform('nunique') > 1
        )
        df_filtered = self.df_valid[~multi_direction_mask].copy()
        
        if len(df_filtered) == 0:
            st.error("❌ 过滤后无有效数据")
            return []
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        all_patterns = []
        
        # 检测2-3个账户的对刷模式
        for account_count in range(2, 4):
            status_text.text(f"🔍 检测{account_count}个账户对刷模式...")
            patterns = self.detect_n_account_patterns(df_filtered, account_count)
            all_patterns.extend(patterns)
            
            progress = (account_count - 1) / 2
            progress_bar.progress(progress)
        
        progress_bar.progress(1.0)
        status_text.text("✅ 检测完成")
        
        self.performance_stats['end_time'] = datetime.now()
        self.performance_stats['detection_time'] = (
            self.performance_stats['end_time'] - self.performance_stats['start_time']
        ).total_seconds()
        self.performance_stats['total_patterns'] = len(all_patterns)
        
        return all_patterns
    
    def detect_n_account_patterns(self, df_filtered, n_accounts):
        """检测N个账户对刷模式"""
        wash_records = []
        
        period_groups = df_filtered.groupby(['期号', '彩种'])
        
        for period_key, period_data in period_groups:
            period_accounts = period_data['会员账号'].unique()
            
            if len(period_accounts) < n_accounts:
                continue
            
            # 获取账户信息
            account_info = {}
            for _, row in period_data.iterrows():
                account = row['会员账号']
                account_info[account] = {
                    'direction': row['投注方向'],
                    'amount': row['投注金额']
                }
            
            # 检测所有组合
            for account_group in combinations(period_accounts, n_accounts):
                # 检查是否形成对立
                directions = [account_info[acc]['direction'] for acc in account_group]
                amounts = [account_info[acc]['amount'] for acc in account_group]
                
                # 简单对立检测：大小、单双、龙虎
                if self.is_opposite_directions(directions):
                    dir1_total = sum(amounts[i] for i, d in enumerate(directions) if d in ['大', '单', '龙'])
                    dir2_total = sum(amounts[i] for i, d in enumerate(directions) if d in ['小', '双', '虎'])
                    
                    if dir1_total > 0 and dir2_total > 0:
                        similarity = min(dir1_total, dir2_total) / max(dir1_total, dir2_total)
                        
                        if similarity >= self.config.amount_similarity_threshold:
                            record = {
                                '期号': period_data['期号'].iloc[0],
                                '彩种': period_data['彩种'].iloc[0],
                                '账户组': list(account_group),
                                '方向组': directions,
                                '金额组': amounts,
                                '总金额': dir1_total + dir2_total,
                                '相似度': similarity,
                                '账户数量': n_accounts
                            }
                            wash_records.append(record)
        
        return self.find_continuous_patterns(wash_records)
    
    def is_opposite_directions(self, directions):
        """检查方向是否对立"""
        opposites = [{'大', '小'}, {'单', '双'}, {'龙', '虎'}]
        
        for opp_set in opposites:
            if set(directions) == opp_set:
                return True
        
        return False
    
    def find_continuous_patterns(self, wash_records):
        """查找连续对刷模式"""
        if not wash_records:
            return []
        
        account_group_patterns = defaultdict(list)
        for record in wash_records:
            account_group_key = (tuple(sorted(record['账户组'])), record['彩种'])
            account_group_patterns[account_group_key].append(record)
        
        continuous_patterns = []
        
        for (account_group, lottery), records in account_group_patterns.items():
            sorted_records = sorted(records, key=lambda x: x['期号'])
            
            if len(sorted_records) >= self.config.min_continuous_periods:
                total_investment = sum(r['总金额'] for r in sorted_records)
                similarities = [r['相似度'] for r in sorted_records]
                avg_similarity = np.mean(similarities) if similarities else 0
                
                continuous_patterns.append({
                    '账户组': list(account_group),
                    '彩种': lottery,
                    '账户数量': len(account_group),
                    '对刷期数': len(sorted_records),
                    '总投注金额': total_investment,
                    '平均相似度': avg_similarity,
                    '详细记录': sorted_records
                })
        
        return continuous_patterns
    
    def display_detailed_results(self, patterns):
        """显示详细检测结果"""
        st.write("\n" + "="*60)
        st.write("🎯 多账户对刷检测结果")
        st.write("="*60)
        
        if not patterns:
            st.error("❌ 未发现符合阈值条件的连续对刷模式")
            return
        
        for i, pattern in enumerate(patterns, 1):
            st.markdown(f"**对刷组 {i}:** {' ↔ '.join(pattern['账户组'])}")
            st.markdown(f"**彩种:** {pattern['彩种']} | **对刷期数:** {pattern['对刷期数']}期")
            st.markdown(f"**总金额:** {pattern['总投注金额']:.2f}元 | **平均匹配:** {pattern['平均相似度']:.2%}")
            
            st.markdown("**详细记录:**")
            for j, record in enumerate(pattern['详细记录'], 1):
                account_info = []
                for account, direction, amount in zip(record['账户组'], record['方向组'], record['金额组']):
                    account_info.append(f"{account}({direction}:{amount})")
                
                st.markdown(f"{j}. **期号:** {record['期号']} | **方向:** {' ↔ '.join(account_info)} | **匹配度:** {record['相似度']:.2%}")
            
            if i < len(patterns):
                st.markdown("---")
    
    def export_to_excel(self, patterns, filename):
        """导出检测结果到Excel文件"""
        if not patterns:
            st.error("❌ 没有对刷数据可导出")
            return None, None
        
        export_data = []
        
        for group_idx, pattern in enumerate(patterns, 1):
            for record_idx, record in enumerate(pattern['详细记录'], 1):
                account_directions = []
                for account, direction, amount in zip(record['账户组'], record['方向组'], record['金额组']):
                    account_directions.append(f"{account}({direction}:{amount})")
                
                export_data.append({
                    '对刷组编号': group_idx,
                    '账户组': ' ↔ '.join(pattern['账户组']),
                    '彩种': pattern['彩种'],
                    '账户数量': pattern['账户数量'],
                    '对刷期数': pattern['对刷期数'],
                    '总投注金额': pattern['总投注金额'],
                    '平均相似度': f"{pattern['平均相似度']:.2%}",
                    '期号': record['期号'],
                    '金额': record['总金额'],
                    '匹配度': f"{record['相似度']:.2%}",
                    '账户方向': ' | '.join(account_directions)
                })
        
        df_export = pd.DataFrame(export_data)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_filename = f"对刷检测报告_{timestamp}.xlsx"
        
        try:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_export.to_excel(writer, sheet_name='详细记录', index=False)
            
            output.seek(0)
            st.success(f"✅ Excel报告已生成: {export_filename}")
            
            return output, export_filename
            
        except Exception as e:
            st.error(f"❌ 导出Excel失败: {str(e)}")
            return None, None

def run_simple_tema_analysis(df):
    """运行简化的特码分析"""
    try:
        st.header("🎯 特码分析（简化版）")
        
        # 检查必要列
        required_cols = ['会员账号', '期号', '彩种', '内容']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            st.error(f"❌ 特码分析缺少必要列: {missing_cols}")
            return
        
        # 数据概览
        st.write(f"📊 总数据量: {len(df):,} 行")
        st.write(f"👥 唯一账户数: {df['会员账号'].nunique():,}")
        st.write(f"📅 唯一期号数: {df['期号'].nunique():,}")
        
        # 彩种分布
        lottery_stats = df['彩种'].value_counts()
        st.write("🎲 彩种分布:")
        for lottery, count in lottery_stats.items():
            st.write(f"  - {lottery}: {count:,} 行")
        
        st.success("✅ 特码分析完成（基础统计信息）")
        
    except Exception as e:
        st.error(f"❌ 特码分析失败: {str(e)}")

def main():
    """主函数"""
    st.title("🎯 智能多账户对刷检测系统")
    st.markdown("---")
    
    # 侧边栏配置
    st.sidebar.header("⚙️ 检测参数配置")
    
    min_amount = st.sidebar.number_input("最小投注金额", value=10, min_value=1)
    similarity_threshold = st.sidebar.slider("金额匹配度阈值", 0.8, 1.0, 0.9, 0.01)
    min_continuous_periods = st.sidebar.number_input("最小连续对刷期数", value=3, min_value=1)
    
    # 文件上传
    st.header("📁 数据上传")
    uploaded_file = st.file_uploader(
        "请上传数据文件 (支持 .xlsx, .xls, .csv)", 
        type=['xlsx', 'xls', 'csv']
    )
    
    # 功能开关
    st.sidebar.header("🔧 功能开关")
    enable_tema_analysis = st.sidebar.checkbox("启用特码分析", value=False)
    
    if uploaded_file is not None:
        try:
            # 更新配置
            config = Config()
            config.min_amount = min_amount
            config.amount_similarity_threshold = similarity_threshold
            config.min_continuous_periods = min_continuous_periods
            
            detector = WashTradeDetector(config)
            
            st.success(f"✅ 已上传文件: {uploaded_file.name}")
            
            with st.spinner("🔄 正在解析数据..."):
                df, filename = detector.upload_and_process(uploaded_file)
                if df is not None:
                    df_valid = detector.parse_column_data(df)
                    
                    if len(df_valid) > 0:
                        st.success("✅ 数据解析完成")
                        
                        # 对刷检测
                        st.info("🚀 开始检测对刷交易...")
                        with st.spinner("🔍 正在检测对刷交易..."):
                            patterns = detector.detect_all_wash_trades()
                        
                        if patterns:
                            st.success(f"✅ 检测完成！发现 {len(patterns)} 个对刷组")
                            detector.display_detailed_results(patterns)
                            
                            # 导出功能
                            excel_output, export_filename = detector.export_to_excel(patterns, filename)
                            if excel_output is not None:
                                st.download_button(
                                    label="📥 下载检测报告",
                                    data=excel_output,
                                    file_name=export_filename,
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )
                        else:
                            st.warning("⚠️ 未发现符合阈值条件的对刷行为")
                        
                        # 特码分析
                        if enable_tema_analysis:
                            run_simple_tema_analysis(df_valid)
                    
                    else:
                        st.error("❌ 数据解析失败，请检查文件格式和内容")
            
        except Exception as e:
            st.error(f"❌ 程序执行失败: {str(e)}")
    
    # 使用说明
    with st.expander("📖 使用说明"):
        st.markdown("""
        ### 系统功能说明

        **🎯 对刷检测：**
        - 检测2-3个账户之间的对刷行为
        - 支持对立投注类型：大 vs 小、单 vs 双、龙 vs 虎
        - 金额匹配度 ≥ 90%
        - 最小连续对刷期数可配置

        **📁 数据格式要求：**
        - 文件必须包含：会员账号、期号、内容、金额
        - 可选包含：彩种
        - 支持Excel和CSV格式

        **🔧 使用步骤：**
        1. 上传数据文件
        2. 调整检测参数（可选）
        3. 系统自动解析数据并检测
        4. 查看检测结果并下载报告
        """)

if __name__ == "__main__":
    main()
