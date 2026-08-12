import streamlit as st
import pandas as pd
import json
import requests
import io
from pdf2image import convert_from_bytes

st.set_page_config(page_title="개인회생 AI 에디터", page_icon="✨", layout="wide")

st.title("✨ 구글 Gemini API 직접 연동 에디터")
st.markdown("API 인증 오류를 원천 차단한 최신 버전입니다.")

with st.sidebar:
    st.header("⚙️ 설정")
    gemini_api_key = st.text_input("Google Gemini API 키 입력", type="password")

if 'creditors' not in st.session_state:
    st.session_state.creditors = []

uploaded_files = st.file_uploader("부채증명서 PDF 업로드", type="pdf", accept_multiple_files=True)

if st.button("✨ 분석 시작"):
    if not gemini_api_key or not uploaded_files:
        st.error("API 키와 파일을 확인하세요.")
    else:
        # API 호출 함수 (라이브러리 없이 직접 통신)
        def call_gemini_api(img_bytes, api_key):
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            
            # 이미지를 Base64로 인코딩
            import base64
            img_b64 = base64.b64encode(img_bytes).decode('utf-8')
            
            payload = {
                "contents": [{
                    "parts": [
                        {"text": "이 부채증명서에서 채권자명, 원금(숫자), 이자(숫자)를 JSON으로 추출해. 다른 말 하지 마."},
                        {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
                    ]
                }]
            }
            
            response = requests.post(url, json=payload)
            if response.status_code != 200:
                raise Exception(f"API 호출 실패: {response.text}")
            
            res_json = response.json()
            text = res_json['candidates'][0]['content']['parts'][0]['text']
            return text.replace("```json", "").replace("```", "").strip()

        for pdf in uploaded_files:
            try:
                images = convert_from_bytes(pdf.read(), first_page=1, last_page=1)
                img_io = io.BytesIO()
                images[0].save(img_io, format='JPEG')
                
                result_json = call_gemini_api(img_io.getvalue(), gemini_api_key.strip())
                data = json.loads(result_json)
                
                st.session_state.creditors.append({
                    "name": data.get("creditor_name", "미확인"),
                    "principal": int(data.get("principal", 0)),
                    "interest": int(data.get("interest", 0))
                })
            except Exception as e:
                st.error(f"분석 오류: {e}")

if st.session_state.creditors:
    df = pd.DataFrame(st.session_state.creditors)
    st.dataframe(df)
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 다운로드", csv, "채권자목록.csv", "text/csv")
