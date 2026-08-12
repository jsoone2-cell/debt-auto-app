import streamlit as st
import pandas as pd
import json
import os
import io
import re
from pdf2image import convert_from_bytes
import pytesseract

st.set_page_config(page_title="개인회생 스마트 규칙 축적 에디터", page_icon="🧠", layout="wide")

st.title("🧠 쓸수록 똑똑해지는 개인회생 채권자목록 에디터")
st.markdown("부채증명서를 올리고 수정하면, 프로그램이 그 규칙을 학습하여 다음부터 자동으로 완벽하게 채워줍니다!")

# 규칙을 저장할 파일 경로
RULE_FILE = "learned_rules.json"

# 저장된 규칙 불러오기 함수
def load_rules():
    if os.path.exists(RULE_FILE):
        with open(RULE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# 규칙 저장하기 함수
def save_rule(keyword, data):
    rules = load_rules()
    rules[keyword] = data
    with open(RULE_FILE, "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=4)

# 세션 상태 초기화
if 'creditors' not in st.session_state:
    st.session_state.creditors = []

st.subheader("1. 부채증명서 PDF 업로드")
uploaded_files = st.file_uploader("PDF 파일을 여러 개 업로드하세요.", type="pdf", accept_multiple_files=True)

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

if st.button("✨ 문서 분석 및 자동 매칭 시작", type="primary"):
    if not uploaded_files:
        st.warning("PDF 파일을 업로드해 주세요.")
    else:
        learned_rules = load_rules()
        new_creditors = []
        
        for pdf in uploaded_files:
            try:
                images = convert_from_bytes(pdf.read())
                full_text = ""
                for img in images:
                    full_text += pytesseract.image_to_string(img, lang='kor') + "\n"
                
                # 1. 이미 학습된 규칙이 있는지 확인
                matched_rule = None
                for key in learned_rules:
                    if key in full_text:
                        matched_rule = learned_rules[key]
                        break
                
                if matched_rule:
                    # 학습된 규칙이 있다면 곧바로 적용!
                    new_creditors.append(matched_rule.copy())
                else:
                    # 규칙이 없다면 기본 추출 시도 후 기본값 부여
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
                    elif "토스뱅크" in full_text:
                        c_name = "토스뱅크 주식회사"
                        addr = "서울 강남구 테헤란로 131"
                        phone = "1661-7654"
                        cause = "대출금"

                    prin = parse_amount(full_text, "원금")
                    if prin == 0: prin = parse_amount(full_text, "잔액")
                    inte = parse_amount(full_text, "이자")

                    new_creditors.append({
                        "rule_key": c_name, # 학습용 키워드
                        "name": c_name,
                        "person_type": "법인",
                        "start_date": "",
                        "cause": cause,
                        "address": addr,
                        "phone": phone,
                        "principal": prin,
                        "interest": inte,
                        "ref_date": "2025-10-28"
                    })
            except Exception as e:
                st.error(f"{pdf.name} 처리 중 오류: {e}")
        
        st.session_state.creditors = new_creditors
        st.success("분석 및 규칙 매칭이 완료되었습니다! 아래에서 내용을 확인하고 수정하세요.")

# 2. 화면에서 직접 확인하고 수정하는 폼 영역 + 학습 저장 버튼
if st.session_state.creditors:
    st.markdown("---")
    st.subheader("2. 채권자 정보 확인, 수정 및 규칙 학습 저장")
    
    total_prin = sum(c['principal'] for c in st.session_state.creditors)
    total_inte = sum(c['interest'] for c in st.session_state.creditors)
    total_sum = total_prin + total_inte
    
    col1, col2, col3 = st.columns(3)
    col1.metric("채권현재액 총합계", f"{total_sum:,} 원")
    col2.metric("원금 합계", f"{total_prin:,} 원")
    col3.metric("이자 합계", f"{total_inte:,} 원")
    
    st.markdown("---")

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

            # 🧠 이 버튼을 누르면 현재 수정된 내용이 이 기관의 '영구 규칙'으로 저장됨!
            if st.button(f"💾 이 수정 내용을 '{cred['name']}' 규칙으로 학습 저장하기", key=f"save_{idx}"):
                rule_key = cred['name']
                save_rule(rule_key, st.session_state.creditors[idx])
                st.success(f"'{rule_key}'의 데이터가 프로그램에 학습되었습니다! 다음부터는 이 양식이 들어오면 이 내용으로 자동 적용됩니다.")

    st.markdown("---")
    st.subheader("3. 최종 다운로드")
    
    df_export = pd.DataFrame(st.session_state.creditors)
    csv_data = df_export.to_csv(index=False).encode('text/csv' if False else 'utf-8-sig')
    
    st.download_button(
        label="📥 채권자목록 최종 다운로드 (CSV)",
        data=csv_data,
        file_name="채권자목록_학습형.csv",
        mime="text/csv",
        type="primary"
    )
