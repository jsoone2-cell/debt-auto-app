import streamlit as st
import pandas as pd
import json
import os
import io
import re
from pdf2image import convert_from_bytes
import pytesseract

st.set_page_config(page_title="개인회생 위치 학습형 에디터", page_icon="🧠", layout="wide")

st.title("🧠 위치 패턴을 학습하는 채권자목록 에디터")
st.markdown("부채증명서의 '키워드 기준 상대적 위치(줄 간격)'를 학습하여 다음부터 정확한 위치의 숫자를 찾아냅니다!")

RULE_FILE = "position_rules.json"

# 저장된 위치 규칙 불러오기
def load_rules():
    if os.path.exists(RULE_FILE):
        with open(RULE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# 위치 규칙 저장하기 (키워드 기준 상대적 줄 오프셋 저장)
def save_position_rule(inst_key, rule_data):
    rules = load_rules()
    rules[inst_key] = rule_data
    with open(RULE_FILE, "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=4)

# 텍스트에서 특정 키워드 기준으로 상대 위치(오프셋)에 있는 숫자를 찾는 함수
def extract_by_position_rule(lines, rule):
    try:
        anchor = rule.get("anchor_keyword", "합계")
        offset = rule.get("line_offset", 0)
        
        anchor_idx = -1
        for idx, line in enumerate(lines):
            if anchor in line:
                anchor_idx = idx
                break
        
        if anchor_idx != -1 and 0 <= anchor_idx + offset < len(lines):
            target_line = lines[anchor_idx + offset]
            numbers = re.findall(r'[\d,]+', target_line)
            for num_str in numbers:
                clean = num_str.replace(',', '')
                if len(clean) >= 4:
                    return int(clean)
        return 0
    except:
        return 0

# 기본 스캔 및 위치 추적 함수
def smart_scan(full_text):
    lines = [line.strip() for line in full_text.split('\n') if line.strip()]
    
    # 기본 기관 판별
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

    # 기본값으로 대략적인 숫자 탐색
    prin, inte = 0, 0
    for idx, line in enumerate(lines):
        if "합계" in line and prin == 0:
            numbers = re.findall(r'[\d,]+', line)
            if numbers:
                prin = int(numbers[0].replace(',', ''))
        if ("이자" in line or "수수료" in line) and inte == 0:
            numbers = re.findall(r'[\d,]+', line)
            if numbers:
                inte = int(numbers[-1].replace(',', ''))

    return {
        "rule_key": c_name,
        "name": c_name,
        "person_type": "법인",
        "start_date": "",
        "cause": cause,
        "address": addr,
        "phone": phone,
        "principal": prin if prin > 0 else 0,
        "interest": inte if inte > 0 else 0,
        "ref_date": "2025.10.28",
        "_raw_lines": lines # 위치 학습을 위한 원본 라인 보관
    }

if 'creditors' not in st.session_state:
    st.session_state.creditors = []

st.subheader("1. 부채증명서 PDF 업로드")
uploaded_files = st.file_uploader("PDF 파일을 여러 개 업로드하세요.", type="pdf", accept_multiple_files=True)

if st.button("✨ 문서 분석 및 위치 규칙 적용", type="primary"):
    if not uploaded_files:
        st.warning("PDF 파일을 업로드해 주세요.")
    else:
        saved_rules = load_rules()
        new_creditors = []
        
        for pdf in uploaded_files:
            try:
                images = convert_from_bytes(pdf.read())
                full_text = ""
                for img in images:
                    full_text += pytesseract.image_to_string(img, lang='kor') + "\n"
                
                lines = [line.strip() for line in full_text.split('\n') if line.strip()]
                
                # 기관 식별
                inst_key = "기타기관"
                if "현대카드" in full_text: inst_key = "현대카드 주식회사"
                elif "삼성카드" in full_text: inst_key = "삼성카드 주식회사"
                elif "토스뱅크" in full_text: inst_key = "토스뱅크 주식회사"

                # 이미 학습된 '위치 규칙(오프셋)'이 있는지 확인
                if inst_key in saved_rules:
                    rule = saved_rules[inst_key]
                    prin = extract_by_position_rule(lines, rule.get("prin_rule", {}))
                    inte = extract_by_position_rule(lines, rule.get("inte_rule", {}))
                    
                    data = smart_scan(full_text)
                    if prin > 0: data["principal"] = prin
                    if inte > 0: data["interest"] = inte
                    data["rule_key"] = inst_key
                    new_creditors.append(data)
                else:
                    # 학습된 규칙이 없으면 기본 스캔 결과 사용
                    new_creditors.append(smart_scan(full_text))

            except Exception as e:
                st.error(f"{pdf.name} 처리 중 오류: {e}")
        
        st.session_state.creditors = new_creditors
        st.success("분석 완료! 아래에서 금액을 확인하고 수정하세요.")

# 2. 화면 수정 및 위치 패턴 학습 저장 영역
if st.session_state.creditors:
    st.markdown("---")
    st.subheader("2. 채권자 정보 확인, 수정 및 위치 패턴 학습 저장")
    
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

            # 🧠 핵심: 변호사님이 수정한 올바른 원금 숫자가 문서 내에서 '합계' 키워드로부터 몇 번째 줄에 있는지 역산하여 위치 규칙을 영구 저장!
            if st.button(f"💾 이 수정된 금액의 위치를 '{cred['name']}' 패턴으로 학습 저장하기", key=f"save_{idx}"):
                inst_key = cred['name']
                lines = cred.get("_raw_lines", [])
                
                # 변호사님이 입력한 올바른 원금 값
                target_prin = int(st.session_state.creditors[idx]['principal'])
                
                # 문서 라인 중 이 원금 숫자가 포함된 라인을 찾아 '합계' 키워드와의 줄 간격(오프셋) 계산
                anchor_idx = -1
                prin_line_idx = -1
                for l_idx, line in enumerate(lines):
                    if "합계" in line: anchor_idx = l_idx
                    if str(target_prin) in line.replace(',', ''): prin_line_idx = l_idx
                
                prin_offset = (prin_line_idx - anchor_idx) if (anchor_idx != -1 and prin_line_idx != -1) else 0

                position_rule = {
                    "prin_rule": {"anchor_keyword": "합계", "line_offset": prin_offset},
                    "inte_rule": {"anchor_keyword": "합계", "line_offset": prin_offset + 1} # 이자는 보통 바로 아랫줄
                }
                
                save_position_rule(inst_key, position_rule)
                st.success(f"성공! '{inst_key}'의 문서 위치 패턴(합계 기준 오프셋: {prin_offset}줄)이 완벽하게 학습되었습니다. 다음부터 이 양식은 이 위치를 찾아 자동으로 추출합니다!")

    st.markdown("---")
    st.subheader("3. 최종 다운로드")
    
    df_export = pd.DataFrame(st.session_state.creditors)
    csv_data = df_export.drop(columns=['_raw_lines'], errors='ignore').to_csv(index=False).encode('utf-8-sig')
    
    st.download_button(
        label="📥 채권자목록 최종 다운로드 (CSV)",
        data=csv_data,
        file_name="채권자목록_위치학습완료.csv",
        mime="text/csv",
        type="primary"
    )
