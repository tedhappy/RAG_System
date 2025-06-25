# -*- coding: utf-8 -*-
"""
Streamlit企业知识库问答系统主界面（左侧有预设问题按钮，点击可自动填充输入框）
"""
import streamlit as st
from pathlib import Path
import sys
import os
import json
import time
import base64

# 设置根目录，确保可以import src
BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / 'src'
sys.path.append(str(SRC_DIR))

from pipeline import Pipeline, RunConfig

# 数据根目录（根据实际情况修改）
DATA_ROOT = BASE_DIR / 'data' / 'stock_data'
QUESTIONS_PATH = DATA_ROOT / 'questions.json'

# 读取预设问题
def load_preset_questions():
    try:
        with open(QUESTIONS_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return [item['text'] for item in data]
    except Exception:
        return []

# 初始化Pipeline（只初始化一次，避免重复加载）
@st.cache_resource(show_spinner=False)
def get_pipeline():
    run_config = RunConfig()  # 可根据需要自定义参数
    return Pipeline(DATA_ROOT, run_config=run_config)

# Streamlit页面设置
st.set_page_config(
    page_title="爱鱼网RAG系统",
    page_icon="🐟",
    layout="wide"
)

# 隐藏Streamlit顶部工具栏、菜单和页脚，并去除顶部所有空白区域
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .st-emotion-cache-18ni7ap {display: none;}
    .st-emotion-cache-1avcm0n {display: none;} /* 兼容新版Streamlit顶部栏 */
    .stApp [data-testid="stDecoration"] {display: none !important;}
    .stApp [data-testid="stHeader"] {height: 0; min-height: 0;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# 顶部标题区
st.markdown(
    """
    <div style='background: linear-gradient(90deg, #7b5cff 0%, #4e8cff 100%); border-radius: 32px; padding: 24px 0 10px 0; margin-bottom: 18px;'>
        <h2 style='color: white; text-align: center; margin: 0;'>🐟 爱鱼网RAG系统</h2>
        <div style='color: #e0e0ff; text-align: center; font-size: 16px; margin-top: 6px;'>企业智能知识库 | 向量检索+LLM推理</div>
    </div>
    """,
    unsafe_allow_html=True
)

# 主体布局
col1, col2 = st.columns([1, 2])

with col1:
    st.header("🔍 请输入您的问题")
    
    # 预设问题（必须放在输入框上方，以避免 Streamlit 状态更新冲突）
    preset_questions = load_preset_questions()
    if preset_questions:
        st.markdown("<b>常见问题：</b>", unsafe_allow_html=True)
        # 默认选择第一个问题，或者从 session_state 获取
        question_text = st.session_state.get("question_input", preset_questions[0])
        
        for idx, q in enumerate(preset_questions):
            if st.button(q, key=f"preset_{idx}"):
                question_text = q # 更新要显示的问题
                st.session_state["question_input"] = q # 更新 state
    else:
        question_text = ""

    # 问题输入框
    question = st.text_area("问题内容", value=question_text, key="question_input_area", height=120, label_visibility="collapsed")
    
    # 提交按钮
    submit = st.button("生成答案", use_container_width=True)

with col2:
    st.header("📑 答案展示")
    
    # 获取最终要处理的问题
    final_question = question
    if submit and final_question.strip():
        with st.spinner("正在检索并生成答案，请稍候..."):
            try:
                pipeline = get_pipeline()
                answer = pipeline.answer_single_question(final_question, kind="string")
                st.markdown(f"<div style='font-size:18px;'><b>❓ 问题：</b> {final_question}</div>", unsafe_allow_html=True)
                
                # 确保 answer 是 dict
                if isinstance(answer, str):
                    try:
                        answer = json.loads(answer)
                    except Exception:
                        answer = {"final_answer": answer}
                # 如果final_answer本身是json字符串，也要解析
                final = answer.get("final_answer", "")
                if isinstance(final, str) and final.strip().startswith("{"):
                    try:
                        final_dict = json.loads(final)
                        step = final_dict.get("step_by_step_analysis", "")
                        summary = final_dict.get("reasoning_summary", "")
                        pages = final_dict.get("relevant_pages", "") # 兼容旧版
                        final = final_dict.get("final_answer", final)
                    except Exception:
                        step = answer.get("step_by_step_analysis", "")
                        summary = answer.get("reasoning_summary", "")
                        pages = answer.get("relevant_pages", "") # 兼容旧版
                else:
                    step = answer.get("step_by_step_analysis", "")
                    summary = answer.get("reasoning_summary", "")
                    pages = answer.get("relevant_pages", "") # 兼容旧版
                
                # 分步推理流式输出（逐字）
                if step:
                    step_placeholder = st.empty()
                    step_text = ""
                    for char in f"**【分步推理】**\n{step}\n\n":
                        step_text += char
                        step_placeholder.markdown(step_text)
                        time.sleep(0.05)
                
                # 推理结论流式输出（逐字）
                if summary:
                    summary_placeholder = st.empty()
                    summary_text = ""
                    for char in f"**【推理结论】**\n{summary}\n\n":
                        summary_text += char
                        summary_placeholder.markdown(summary_text)
                        time.sleep(0.05)
                
                # 最终答案流式输出（逐字）
                if final:
                    final_placeholder = st.empty()
                    final_text = ""
                    for char in f"**【最终答案】**\n{final}\n\n":
                        final_text += char
                        final_placeholder.markdown(final_text)
                        time.sleep(0.05)
                
                # 来源信息处理与展示
                source_chunks = answer.get("source_chunks")
                
                # 引用来源展示
                if source_chunks:
                    sources_placeholder = st.empty()
                    # 按文档名聚合页码
                    doc_pages = {}
                    for chunk in source_chunks:
                        doc_name = chunk.get('document_name', '未知文档').replace('.json', '.md')
                        line_num = chunk.get('line_from') # 改为获取行号
                        if line_num is not None:
                            if doc_name not in doc_pages:
                                doc_pages[doc_name] = set()
                            doc_pages[doc_name].add(line_num) # 添加行号
                    
                    # 构建引用来源文本
                    sources_text_parts = []
                    for doc_name, line_set in doc_pages.items(): # 变量名改为line_set
                        sorted_lines = sorted(list(line_set)) # 变量名改为sorted_lines
                        sources_text_parts.append(f"《{doc_name}》 (行: {sorted_lines})")
                    
                    if sources_text_parts:
                        full_sources_text = f"**【引用来源】** " + ", ".join(sources_text_parts)
                        display_text = ""
                        for char in full_sources_text:
                            display_text += char
                            sources_placeholder.markdown(display_text)
                            time.sleep(0.05)
                
                # 详细来源信息
                if source_chunks:
                    st.markdown("---") # 添加分割线
                    st.markdown("#### 来源信息")
                    for i, chunk in enumerate(source_chunks[:3]): # 只取前3个
                        doc_name = chunk.get('document_name', '未知文档').replace('.json', '.md')
                        line_num = chunk.get('line_from', 'N/A') # 改为获取行号
                        with st.expander(f"来源 {i+1}: {doc_name} (行号: {line_num})"):
                            st.text(chunk.get('text', ''))

            except Exception as e:
                st.error(f"发生错误：{e}")
    else:
        st.info("请在左侧输入您的问题并点击【生成答案】")

# 读取本地图标并转为base64
beian_icon_path = 'data/stock_data/img/icon.png'  # 修改为新的本地路径
beian_icon_base64 = ''
try:
    with open(beian_icon_path, 'rb') as f:
        beian_icon_base64 = base64.b64encode(f.read()).decode('utf-8')
except Exception:
    beian_icon_base64 = ''
# 先拼好img标签
beian_img_html = (
    f'<img src="data:image/png;base64,{beian_icon_base64}" style="vertical-align:middle;width:20px;height:20px;margin-right:3px;" />'
    if beian_icon_base64 else ''
)
# 备案信息HTML
beian_html = f"""
<div style='text-align:center; color:#aaa; font-size:13px; margin-top:30px;'>
    <div>
        <a href='https://beian.miit.gov.cn' target='_blank' style='color:#aaa; text-decoration:none;'>蜀ICP备2025139299号</a>
    </div>
    <div style='margin-top:2px;'>
        {beian_img_html}
        <a href='https://beian.mps.gov.cn/#/query/webSearch?code=51010602002838' rel='noreferrer' target='_blank' style='color:#aaa; text-decoration:none;'>川公网安备51010602002838号</a>
    </div>
</div>
"""
st.markdown(beian_html, unsafe_allow_html=True)