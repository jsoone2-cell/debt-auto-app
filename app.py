import streamlit as st
import vertexai
from vertexai.generative_models import GenerativeModel, Part
import pandas as pd
import json
from pdf2image import convert_from_bytes

# Vertex AI 설정 (서버 환경 변수 활용)
PROJECT_ID = "YOUR_PROJECT_ID"  # 사용 중인 GCP 프로젝트 ID로 수정해주세요.
LOCATION = "us-central1"        # 모델이 배포된 리전

vertexai.init(project=PROJECT_ID, location=LOCATION)
model = GenerativeModel("gemini-1.5-flash")

st.set_page_config(page_title="개인회생 AI 에디터", layout="wide")
st.title("✨ Vertex AI 기반 채권자목록 에디터")

uploaded_files = st.file_uploader("부채증명서 PDF 업로드", type="pdf", accept_multiple_files=True)

if st.button("✨ 분석 시작"):
    if not uploaded_files:
        st.warning("파일을 업로드하세요.")
    else:
        new_creditors = []
        for pdf in uploaded_files:
            try:
                images = convert_from_bytes(pdf.read(), first_page=1, last_page=1)
                # 이미지를 바이트로 변환
                import io
                img_byte_arr = io.BytesIO()
                images[0].save(img_byte_arr, format='JPEG')
                img_bytes = img_byte_arr.getvalue()

                # 모델 호출
                response = model.generate_content([
                    Part.from_data(data=img_bytes, mime_type="image/jpeg"),
                    "부채증명서에서 채권자명, 원금(숫자), 이자(숫자)를 JSON 형식으로 추출해. 백틱 없이 JSON만 출력해."
                ])
                
                data = json.loads(response.text.strip())
                new_creditors.append({
                    "name": data.get("creditor_name", "미확인"),
                    "principal": int(data.get("principal", 0)),
                    "interest": int(data.get("interest", 0))
                })
            except Exception as e:
                st.error(f"분석 오류: {e}")
        
        st.session_state.creditors = new_creditors

# (이후 입력폼 및 CSV 다운로드 로직은 동일)
if 'creditors' in st.session_state and st.session_state.creditors:
    df = pd.DataFrame(st.session_state.creditors)
    st.dataframe(df)
