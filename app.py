import streamlit as st
import pandas as pd
import json
import os
import io
import re
from pdf2image import convert_from_bytes
import pytesseract

st.set_page_config(page_title="개인회생 스마트 채권자목록 에디터", page_icon="⚖️", layout="wide")

st.title("⚖️ 개인회생 채권자목록 스마트 자동 추출기")
st.markdown("부채증명서를 올리면 AI가 문서의 '원금'과 '이자' 패턴을 정밀하게 분석하여 채권자목록을 채워줍니다!")

# 정밀 금액 추출 함수 (키워드 근처의 숫자를 정확히 타겟팅)
def parse_smart_amount(text, target_keyword):
    try:
        lines = text.split('\n')
        for line in lines:
            if target_keyword in line:
                # 해당 줄에서 숫자와 콤마 패턴 추출
                numbers = re.findall(r'[\d,]+', line)
                for num_str in numbers:
                    clean_num = num_str.replace(',', '')
                    # 너무 작은 숫자(연도, 페이지 등)는 제외하고 4자리 이상 금액만 인정
                    if len(clean_num) >= 4:
                        return int(clean_num)
        return 0
    except:
        return 0

# 세션 상태 초기화
if 'creditors' not in st.session_state:
    st.session_state.creditors = []

st.subheader("1. 부채증명서 PDF 업로드")
uploaded_files = st.file_uploader("부채증명서 PDF 파일을 여러 개 업로드하세요.", type="pdf", accept_multiple_files=True)

if st.button("✨ 문서 정밀 분석 시작", type="primary"):
    if not uploaded_files:
        st.warning("PDF 파일을 업로드해 주세요.")
    else:
        new_creditors = []
        
        for pdf in uploaded_files:
            try:
                images = convert_from_bytes(pdf.read())
                full_text = ""
                for img in images:
                    full_text += pytesseract.image_to_string(img, lang='kor') + "\n"
                
                # 기본 정보 세팅
                c_name = "확인필요"
                addr = ""
                phone = ""
                cause = "신용카드사용채무 / 대출금"
                start_dt = ""
                
                # 기관별 기본 정보 매핑
                if "현대카드" in full_text:
                    c_name = "현대카드 주식회사"
                    addr = "서울특별시 영등포구 의사당대로 3"
                    phone = "1577-6000"
                    cause = "신용카드대금"
                    start_dt = "2022.08.26" # 사진 상단 손글씨/기준 참고용 기본값
                elif "삼성카드" in full_text:
                    c_name = "삼성카드 주식회사"
                    addr = "서울특별시 중구 세종대로 67"
                    phone = "1588-8700"
                    cause = "신용카드대금"
                elif "토스뱅크" in full_text:
                    c_name = "토스뱅크 주식회사"
                    addr = "서울 강남구 테헤란로 131"
                    phone = "1661-7654"
                    cause = "대출금"

                # 🧠 정밀 패턴으로 원금 및 이자 추출
                # 현대카드 등의 양식에서 '합계' 행 또는 '원금' 행의 금액 탐색
                prin = parse_smart_amount(full_text, "합계")
                if prin == 0:
                    prin = parse_smart_amount(full_text, "원금")
                if prin == 0:
                    prin = parse_smart_amount(full_text, "잔액")

                inte = parse_smart_amount(full_text, "수수료/이자")
                if inte == 0:
                    inte = parse_smart_amount(full_text, "이자")

                new_creditors.append({
                    "name": c_name,
                    "person_type": "법인",
                    "start_date": start_dt,
                    "cause": cause,
                    "address": addr,
                    "phone": phone,
                    "principal": prin,
                    "interest": inte,
                    "ref_date": "2025.10.28"
                })
            except Exception as e:
                st.error(f"{pdf.name} 처리 중 오류: {e}")
        
        st.session_state.creditors = new_creditors
        st.success("정밀 분석 완료! 아래에서 금액이 정확히 들어왔는지 확인해 보세요.")

# 2. 화면에서 직접 확인하고 수정하는 폼 영역
if st.session_state.creditors:
    st.markdown("---")
    st.subheader("2. 채권자 정보 확인 및 수정")
    
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
        label="📥 채권자목록 최종 다운로드 (CSV)",
        data=csv_data,
        file_name="채권자목록_정밀추출.csv",
        mime="text/csv",
        type="primary"
    )
