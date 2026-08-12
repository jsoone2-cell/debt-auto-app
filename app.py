import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import os
from pdf2image import convert_from_bytes

st.set_page_config(page_title="개인회생 AI 에디터", layout="wide")

st.title("✨ AI 채권자목록 에디터 (인증 강화 버전)")

with st.sidebar:
    gemini_api_key = st.text_input("Google Gemini API 키 (AIza...)", type="password")

if st.button("✨ 분석 시작"):
    if not gemini_api_key or len(gemini_api_key.strip()) < 30:
        st.error("API 키가 올바르지 않습니다. AIza로 시작하는 키인지 확인하세요.")
    else:
        try:
            # [검토 1, 2] 인증 정보 강제 오버라이드
            os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
            os.environ["GOOGLE_API_KEY"] = gemini_api_key.strip()
            genai.configure(api_key=gemini_api_key.strip())
            
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            st.write("분석 중...")
            # (파일 처리 로직은 동일)
            # ... (아래는 핵심 분석 로직만 요약) ...
            
            # (중략)
            st.success("완료")
        except Exception as e:
            st.error(f"결정적 오류: {e}")
