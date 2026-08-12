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
        # 무료 티어에서 가장 안정적인 시각 지원 모델 사용
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        new_creditors = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        for idx, pdf in enumerate(uploaded_files):
            status_text.text(f"[{pdf.name}] AI가 문서를 눈으로 정밀 분석 중입니다... 🧐")
            
            try:
                # PDF를 이미지로 변환 (첫 페이지만 추출)
                images = convert_from_bytes(pdf.read(), first_page=1, last_page=1)
                if not images:
                    continue
                
                img = images[0]

                # AI에게 내리는 엄격한 표 구조 분석 지시서
                prompt = """
                당신은 개인회생 서류 작성 전문가입니다. 첨부된 부채증명서(금융거래 잔액 확인서 등) 이미지의 표 구조를 정밀하게 분석하여 다음 항목을 오직 순수 JSON 형식으로만 답하세요. (다른 설명이나 마크다운 백틱 ```json 등은 절대 출력하지 마세요)
                
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

                response = model.generate_content([prompt, img])
                raw_res = response.text.strip()
                
                # JSON 파싱 정제
                clean_json_str = raw_res.replace('```json', '').replace('```', '').strip()
                data = json.loads(clean_json_str)

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

            except Exception as e:
                st.error(f"⚠️ {pdf.name} 분석 중 오류 발생: {e}")
            
            progress_bar.progress((idx + 1) / len(uploaded_files))

        st.session_state.creditors = new_creditors
        status_text.text("✨ 분석 완료!")
        st.success(f"총 {len(new_creditors)}개의 채권자 정보가 정확하게 추출되어 아래 입력 폼에 채워졌습니다.")

# 2. 웹 화면에서 직접 확인하고 수정하는 폼 영역
if st.session_state.creditors:
    st.markdown("---")
    st.subheader("2. 채권자 정보 확인 및 직접 수정")
    
    total_prin = sum(c['principal'] for c in st.session_state.creditors)
    total_inte = sum(c['interest'] for c in st.session_state.creditors)
    total_sum = total_prin + total_inte
    
    col1, col2, col3 = st.columns(3)
    col1.metric("채권현재액 총합계", f"{total_sum:,} 원")
    col2.metric("원금 합계", f"{total_prin:,} 원")
    col3.metric("이자 합계", f"{total_inte:,} 원")
    
    st.markdown("---")

    for idx, cred in enumerate(st.session_state.creditors):
        with st.expander(f"📌 {idx+1}. {cred['name']} (원금: {cred['principal']:,}원 / 이자: {cred['interest']:,}원)", expanded=True):
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.session_state.creditors[idx]['name'] = st.text_input(f"채권자명 #{idx+1}", value=cred['name'], key=f"name_{idx}")
            with c2:
                st.session_state.creditors[idx]['person_type'] = st.selectbox(f"인격 구분 #{idx+1}", ["법인", "자연인"], index=0 if cred['person_type']=="법인" else 1, key=f"ptype_{idx}")
            with c3:
                st.session_state.creditors[idx]['start_date'] = st.text_input(f"발생일자 (YYYY.MM.DD) #{idx+1}", value=cred['start_date'], key=f"sdate_{idx}")
            with c4:
                st.session_state.creditors[idx]['cause'] = st.text_input(f"발생원인 #{idx+1}", value=cred['cause'], key=f"cause_{idx}")

            c5, c6 = st.columns(2)
            with c5:
                st.session_state.creditors[idx]['address'] = st.text_input(f"주소 #{idx+1}", value=cred['address'], key=f"addr_{idx}")
            with c6:
                st.session_state.creditors[idx]['phone'] = st.text_input(f"전화번호 #{idx+1}", value=cred['phone'], key=f"phone_{idx}")

            c7, c8, c9 = st.columns(3)
            with c7:
                st.session_state.creditors[idx]['principal'] = st.number_input(f"원금 #{idx+1}", value=int(cred['principal']), step=1000, key=f"prin_{idx}")
            with c8:
                st.session_state.creditors[idx]['interest'] = st.number_input(f"이자 #{idx+1}", value=int(cred['interest']), step=100, key=f"inte_{idx}")
            with c9:
                st.session_state.creditors[idx]['ref_date'] = st.text_input(f"산정기준일 #{idx+1}", value=cred['ref_date'], key=f"rdate_{idx}")

    if st.button("➕ 채권자 수동으로 추가하기"):
        st.session_state.creditors.append({
            "name": "새 채권자", "person_type": "법인", "start_date": "", "cause": "대출금",
            "address": "", "phone": "", "principal": 0, "interest": 0, "ref_date": "2025.10.28"
        })
        st.rerun()

    st.markdown("---")
    st.subheader("3. 최종 다운로드")
    
    df_export = pd.DataFrame(st.session_state.creditors)
    csv_data = df_export.to_csv(index=False).encode('utf-8-sig')
    
    st.download_button(
        label="📥 수정 완료된 채권자목록 다운로드 (CSV)",
        data=csv_data,
        file_name="개인회생_채권자목록_최종.csv",
        mime="text/csv",
        type="primary"
    )
