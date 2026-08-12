import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import io
import os
from pdf2image import convert_from_bytes

# 환경 설정: 다른 인증 정보가 API 키를 방해하지 않도록 강제로 비움
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = ""

st.set_page_config(page_title="개인회생 AI 시각 에디터", page_icon="✨", layout="wide")

st.title("✨ 구글 Gemini 시각 AI 기반 채권자목록 에디터")
st.markdown("부채증명서 PDF를 올리면, AI가 문서를 직접 눈으로 보고 표의 '원금'과 '이자'를 정확히 추출합니다!")

with st.sidebar:
    st.header("⚙️ 설정")
    gemini_api_key = st.text_input("Google Gemini API 키 (AIza...) 입력", type="password")
    st.markdown("---")
    st.markdown("💡 **Tip:** [Google AI Studio](https://aistudio.google.com/)에서 새로 발급받은 `AIza` 키를 입력하세요.")

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
        try:
            # 설정 강제 초기화
            genai.configure(api_key=gemini_api_key.strip())
            # 가장 안정적인 Flash 모델 사용
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            new_creditors = []
            progress_bar = st.progress(0)
            status_text = st.empty()

            for idx, pdf in enumerate(uploaded_files):
                status_text.text(f"[{pdf.name}] AI가 정밀 분석 중입니다...")
                
                # 이미지 변환
                images = convert_from_bytes(pdf.read(), first_page=1, last_page=1)
                if not images: continue
                img = images[0]

                # 구조 분석 요청
                prompt = """
                이 문서는 개인회생 부채증명서입니다. 이미지에서 다음 정보를 JSON 형태로 정확히 추출하세요. 
                절대 마크다운(```json)을 붙이지 말고 순수 JSON만 출력하세요.
                {
                    "creditor_name": "채권자명",
                    "person_type": "법인",
                    "start_date": "YYYY.MM.DD",
                    "cause": "채권의 원인",
                    "address": "주소",
                    "phone": "전화번호",
                    "principal": 원금(숫자만),
                    "interest": 이자(숫자만),
                    "ref_date": "산정기준일"
                }
                """
                response = model.generate_content([prompt, img])
                raw_res = response.text.strip().replace("```json", "").replace("```", "")
                data = json.loads(raw_res)

                new_creditors.append({
                    "name": data.get("creditor_name", "확인필요"),
                    "person_type": data.get("person_type", "법인"),
                    "start_date": data.get("start_date", ""),
                    "cause": data.get("cause", "대출금"),
                    "address": data.get("address", ""),
                    "phone": data.get("phone", ""),
                    "principal": int(data.get("principal", 0)),
                    "interest": int(data.get("interest", 0)),
                    "ref_date": data.get("ref_date", "2025.10.28")
                })
                progress_bar.progress((idx + 1) / len(uploaded_files))

            st.session_state.creditors = new_creditors
            status_text.text("✨ 분석 완료!")
            st.success(f"총 {len(new_creditors)}건 분석 완료.")

        except Exception as e:
            st.error(f"⚠️ 분석 오류: {str(e)}")

# 결과 출력 및 수정 폼
if st.session_state.creditors:
    st.markdown("---")
    st.subheader("2. 채권자 정보 확인 및 수정")
    for idx, cred in enumerate(st.session_state.creditors):
        with st.expander(f"📌 {idx+1}. {cred['name']}", expanded=True):
            c1, c2, c3, c4 = st.columns(4)
            st.session_state.creditors[idx]['name'] = c1.text_input(f"채권자명 #{idx+1}", value=cred['name'], key=f"name_{idx}")
            st.session_state.creditors[idx]['person_type'] = c2.selectbox(f"인격 #{idx+1}", ["법인", "자연인"], index=0 if cred['person_type']=="법인" else 1, key=f"ptype_{idx}")
            st.session_state.creditors[idx]['start_date'] = c3.text_input(f"발생일 #{idx+1}", value=cred['start_date'], key=f"sdate_{idx}")
            st.session_state.creditors[idx]['cause'] = c4.text_input(f"원인 #{idx+1}", value=cred['cause'], key=f"cause_{idx}")
            
            c5, c6 = st.columns(2)
            st.session_state.creditors[idx]['principal'] = c5.number_input(f"원금 #{idx+1}", value=int(cred['principal']), step=1000, key=f"prin_{idx}")
            st.session_state.creditors[idx]['interest'] = c6.number_input(f"이자 #{idx+1}", value=int(cred['interest']), step=100, key=f"inte_{idx}")

    if st.button("➕ 채권자 추가"):
        st.session_state.creditors.append({"name": "새 채권자", "person_type": "법인", "principal": 0, "interest": 0})
        st.rerun()

    st.subheader("3. 최종 다운로드")
    df_export = pd.DataFrame(st.session_state.creditors)
    st.download_button("📥 채권자목록 다운로드 (CSV)", df_export.to_csv(index=False).encode('utf-8-sig'), "채권자목록_최종.csv", "text/csv")
