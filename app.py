import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import io
from pdf2image import convert_from_bytes

st.set_page_config(page_title="개인회생 AI 시각 에디터", page_icon="✨", layout="wide")

st.title("✨ 구글 Gemini 시각 AI 기반 채권자목록 에디터")
st.markdown("부채증명서 PDF를 올리면, AI가 문서를 직접 눈으로 보고 표의 '원금'과 '이자'를 정확히 추출하여 입력 폼에 채워줍니다!")

# 사이드바에 구글 API 키 입력
with st.sidebar:
    st.header("⚙️ 설정")
    gemini_api_key = st.text_input("Google Gemini API 키 (AIza...) 입력", type="password")
    st.markdown("---")
    st.markdown("💡 **Tip:** [Google AI Studio](https://aistudio.google.com/)에서 무료로 `AIza` 키를 발급받을 수 있습니다.")

if 'creditors' not in st.session_state:
    st.session_state.creditors = []

st.subheader("1. 부채증명서 PDF 업로드")
uploaded_files = st.file_uploader("부채증명서 PDF 파일을 여러 개 업로드하세요.", type="pdf", accept_multiple_files=True)

if st.button("✨ AI 시각 분석 시작", type="primary"):
    if not gemini_api_key:
        st.error("좌측 사이드바에 Google Gemini API 키(AIza...)를 입력해 주세요.")
    elif not uploaded_files:
        st.warning("PDF 파일을 하나 이상 업로드해 주세요.")
    else:
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        new_creditors = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        for idx, pdf in enumerate(uploaded_files):
            status_text.text(f"[{pdf.name}] AI가 문서를 눈으로 정밀 분석 중입니다... 🧐")
            
            try:
                images = convert_from_bytes(pdf.read(), first_page=1, last_page=1)
                if not images:
                    continue
                
                img = images[0]

                prompt = """
                당신은 개인회생 서류 작성 전문가입니다. 첨부된 부채증명서(금융거래 잔액 확인서 등) 이미지의 표 구조를 정밀하게 분석하여 다음 항목을 오직 순수 JSON 형식으로만 답하세요. 다른 설명이나 마크다운 백틱은 절대 출력하지 마세요.

                {
                    "creditor_name": "채권자명 (예: 현대카드 주식회사, 삼성카드 주식회사 등)",
                    "person_type": "법인 또는 자연인",
                    "start_date": "최초대출일 또는 카드발급일 (예: 2022.08.26 형식, 없으면 "")",
                    "cause": "채권의 내용/원인 (예: 신용카드대금, 대출금 등)",
                    "address": "주소 (없으면 "")",
                    "phone": "대표전화 (없으면 "")",
                    "principal": 원금 잔액 숫자만 (예: 3174260),
                    "interest": 이자 및 수수료 잔액 숫자만 (예: 87087),
                    "ref_date": "산정기준일 (예: 2025.10.28 형식)"
                }
                """

                response = model.generate
