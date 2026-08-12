import streamlit as st
import pandas as pd
from datetime import datetime
import io
import re
from pdf2image import convert_from_bytes
import pytesseract

st.set_page_config(page_title="개인회생 채권자목록 작성 관리자", page_icon="📝", layout="wide")

st.title("📝 개인회생 채권자목록 자동 추출 및 편집기")
st.markdown("부채증명서 PDF를 올리면 아래 입력 폼에 내용이 자동으로 채워집니다. 화면에서 직접 수정하신 후 최종 다운로드하세요!")

# 세션 상태에 채권자 목록 데이터 저장 (화면 새로고침 시 유지용)
if 'creditors' not in st.session_state:
    st.session_state.creditors = []

# 파일 업로드 영역
st.subheader("1. 부채증명서 PDF 업로드")
uploaded_files = st.file_uploader("PDF 파일을 여러 개 업로드하세요.", type="pdf", accept_multiple_files=True)

# 금액 추출 헬퍼 함수
def parse_amount(text, keyword):
    try:
        patterns = [f"{keyword}.*?([0-9,]{{4,}})\\s*원", f"{keyword}.*?([0-9,]{{4,}})"]
        for p in patterns:
            match = re.search(p, text.replace(" ", ""))
            if match:
                return int(match.group(1).replace(",", ""))
        return 0
    except:
        return 0

if st.button("✨ 부채증명서 자동 읽기 및 입력 폼 생성", type="primary"):
    if not uploaded_files:
        st.warning("PDF 파일을 먼저 업로드해 주세요.")
    else:
        new_creditors = []
        for pdf in uploaded_files:
            try:
                images = convert_from_bytes(pdf.read())
                full_text = ""
                for img in images:
                    full_text += pytesseract.image_to_string(img, lang='kor') + "\n"
                
                # 기본값 설정
                c_name = "확인필요"
                addr = ""
                phone = ""
                cause = "신용카드사용채무 / 대출금"
                
                if "현대카드" in full_text:
                    c_name = "현대카드 주식회사"
                    addr = "서울특별시 영등포구 의사당대로 3"
                    phone = "1577-6000"
                    cause = "신용카드대금"
                elif "삼성카드" in full_text:
                    c_name = "삼성카드 주식회사"
                    addr = "서울특별시 중구 세종대로 67"
                    phone = "1588-8700"
                    cause = "신용카드대금"
                elif "토스뱅크" in full_text or "TOSS" in full_text.upper():
                    c_name = "토스뱅크 주식회사"
                    addr = "서울 강남구 테헤란로 131"
                    phone = "1661-7654"
                    cause = "대출금"
                elif "김창곤" in full_text:
                    c_name = "김창곤"
                    cause = "개인대여금"
                elif "김아림" in full_text:
                    c_name = "김아림"
                    cause = "개인대여금"

                prin = parse_amount(full_text, "원금")
                if prin == 0: prin = parse_amount(full_text, "잔액")
                inte = parse_amount(full_text, "이자")

                new_creditors.append({
                    "name": c_name,
                    "person_type": "법인" if "주식회사" in c_name or "카드" in c_name or "뱅크" in c_name else "자연인",
                    "start_date": "",
                    "cause": cause,
                    "address": addr,
                    "phone": phone,
                    "principal": prin,
                    "interest": inte,
                    "ref_date": "2025-10-28"
                })
            except Exception as e:
                st.error(f"{pdf.name} 분석 중 오류: {e}")
        
        st.session_state.creditors = new_creditors
        st.success(f"총 {len(new_creditors)}개의 채권자 정보가 아래 입력 폼에 쏙쏙 들어왔습니다!")

# 2. 화면에서 직접 확인하고 수정할 수 있는 입력 폼 영역
if st.session_state.creditors:
    st.markdown("---")
    st.subheader("2. 채권자 정보 확인 및 직접 수정 (첫 번째 사진 형태)")
    
    # 상단 요약 바 계산
    total_prin = sum(c['principal'] for c in st.session_state.creditors)
    total_inte = sum(c['interest'] for c in st.session_state.creditors)
    total_sum = total_prin + total_inte
    
    col1, col2, col3 = st.columns(3)
    col1.metric("채권현재액 총합계", f"{total_sum:,} 원")
    col2.metric("원금 합계", f"{total_prin:,} 원")
    col3.metric("이자 합계", f"{total_inte:,} 원")
    
    st.markdown("---")

    # 각 채권자별 수정 가능한 박스 생성
    for idx, cred in enumerate(st.session_state.creditors):
        with st.expander(f"📌 {idx+1}. {cred['name']} (원금: {cred['principal']:,}원)", expanded=True):
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.session_state.creditors[idx]['name'] = st.text_input(f"채권자명 #{idx+1}", value=cred['name'])
            with c2:
                st.session_state.creditors[idx]['person_type'] = st.selectbox(f"인격 구분 #{idx+1}", ["법인", "자연인"], index=0 if cred['person_type']=="법인" else 1)
            with c3:
                st.session_state.creditors[idx]['start_date'] = st.text_input(f"발생일자 (YYYY.MM.DD) #{idx+1}", value=cred['start_date'])
            with c4:
                st.session_state.creditors[idx]['cause'] = st.text_input(f"발생원인 #{idx+1}", value=cred['cause'])

            c5, c6 = st.columns(2)
            with c5:
                st.session_state.creditors[idx]['address'] = st.text_input(f"주소 #{idx+1}", value=cred['address'])
            with c6:
                st.session_state.creditors[idx]['phone'] = st.text_input(f"전화번호 #{idx+1}", value=cred['phone'])

            c7, c8, c9 = st.columns(3)
            with c7:
                st.session_state.creditors[idx]['principal'] = st.number_input(f"원금 #{idx+1}", value=int(cred['principal']), step=1000)
            with c8:
                st.session_state.creditors[idx]['interest'] = st.number_input(f"이자 #{idx+1}", value=int(cred['interest']), step=100)
            with c9:
                st.session_state.creditors[idx]['ref_date'] = st.text_input(f"산정기준일 #{idx+1}", value=cred['ref_date'])

    # 채권자 추가 버튼 등 확장 가능
    if st.button("➕ 채권자 수동으로 추가하기"):
        st.session_state.creditors.append({
            "name": "새 채권자", "person_type": "법인", "start_date": "", "cause": "대출금",
            "address": "", "phone": "", "principal": 0, "interest": 0, "ref_date": "2025-10-28"
        })
        st.rerun()

    st.markdown("---")
    st.subheader("3. 최종 다운로드")
    
    # 수정된 데이터를 CSV 또는 엑셀 형태로 변환하여 다운로드 제공
    df_export = pd.DataFrame(st.session_state.creditors)
    csv_data = df_export.to_csv(index=False).encode('utf-8-sig')
    
    st.download_button(
        label="📥 수정 완료된 채권자목록 CSV 다운로드",
        data=csv_data,
        file_name="최종_채권자목록.csv",
        mime="text/csv",
        type="primary"
    )
