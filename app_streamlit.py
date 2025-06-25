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
    # 预设问题（放在输入框上方，避免控件冲突）
    preset_questions = load_preset_questions()
    if preset_questions:
        st.markdown("<b>常见问题：</b>", unsafe_allow_html=True)
        for idx, q in enumerate(preset_questions):
            if st.button(q, key=f"preset_{idx}"):
                st.session_state["question_input"] = q  # 先赋值，后渲染输入框
    # 问题输入框（只用key，不传value参数，避免警告）
    question = st.text_area("问题内容", key="question_input", height=120)
    # 提交按钮
    submit = st.button("生成答案", use_container_width=True)

with col2:
    st.header("📑 答案展示")
    # 只有点击按钮且输入不为空时才显示答案
    if submit and question.strip():
        with st.spinner("正在检索并生成答案，请稍候..."):
            try:
                pipeline = get_pipeline()
                answer = pipeline.answer_single_question(question, kind="string")
                st.markdown(f"<div style='font-size:18px;'><b>❓ 问题：</b> {question}</div>", unsafe_allow_html=True)
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
                        pages = final_dict.get("relevant_pages", "")
                        final = final_dict.get("final_answer", final)
                    except Exception:
                        step = answer.get("step_by_step_analysis", "")
                        summary = answer.get("reasoning_summary", "")
                        pages = answer.get("relevant_pages", "")
                else:
                    step = answer.get("step_by_step_analysis", "")
                    summary = answer.get("reasoning_summary", "")
                    pages = answer.get("relevant_pages", "")
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
                # 引用页码流式输出（逐字）
                if pages:
                    pages_placeholder = st.empty()
                    pages_text = f"**【引用页码】**{pages}"
                    display = ""
                    for char in pages_text:
                        display += char
                        pages_placeholder.markdown(display)
                        time.sleep(0.05)
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