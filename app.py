import streamlit as st
import pandas as pd
import openpyxl
from datetime import datetime, timedelta
import io
import re
from pdf2image import convert_from_bytes
import pytesseract

st.set_page_config(page_title="개인회생 채권자목록 자동 완성기", page_icon="⚖️", layout="centered")

st.title("⚖️ 개인회생 채권자목록 자동 완성기")
st.markdown("법원 제출용 엑셀 양식에 맞춰 부채증명서 내용을 자동으로 채워줍니다.")

st.subheader("1. 파일 업로드")
template_file = st.file_uploader("빈 양식 엑셀 파일 (변제계획안.xlsx 또는 채권자목록 양식)", type="xlsx")
pdf_files = st.file_uploader("부채증명서 PDF 파일 업로드 (여러 개 가능)", type="pdf", accept_multiple_files=True)

# 숫자 금액을 안전하게 추출하는 함수
def parse_amount(text, keyword):
    try:
        # 키워드 주변에서 콤마가 포함된 숫자 패턴 찾기
        patterns = [
            f"{keyword}.*?([0-9,]{{4,}})\\s*원",
            f"{keyword}.*?([0-9,]{{4,}})",
        ]
        for p in patterns:
            match = re.search(p, text.replace(" ", ""))
            if match:
                num_str = match.group(1).replace(",", "")
                return int(num_str)
        return 0
    except:
        return 0

if st.button("✨ 채권자목록 자동 작성 시작", type="primary"):
    if not template_file or not pdf_files:
        st.error("엑셀 양식과 부채증명서 PDF를 모두 업로드해 주세요.")
    else:
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        total_principal = 0
        total_interest = 0

        for i, pdf in enumerate(pdf_files):
            status_text.text(f"[{pdf.name}] 부채증명서 내용을 정밀 분석 중입니다... 🧐")
            
            try:
                # PDF를 이미지로 변환 후 OCR로 텍스트 추출
                images = convert_from_bytes(pdf.read())
                full_text = ""
                for img in images:
                    text = pytesseract.image_to_string(img, lang='kor')
                    full_text += text + "\n"
                
                # 데이터 기본 구조 생성
                data = {
                    "creditor_name": "확인필요",
                    "start_date": "",
                    "address": "",
                    "phone": "",
                    "cause": "신용카드사용채무 / 대출금",
                    "principal": 0,
                    "interest": 0,
                    "ref_date": "2025-10-28" # 기본 기준일
                }
                
                # 1. 채권자명 자동 인식
                if "현대카드" in full_text: 
                    data["creditor_name"] = "현대카드 주식회사"
                    data["address"] = "서울특별시 영등포구 의사당대로 3"
                    data["phone"] = "1577-6000"
                    data["cause"] = "신용카드대금"
                elif "삼성카드" in full_text: 
                    data["creditor_name"] = "삼성카드 주식회사"
                    data["address"] = "서울특별시 중구 세종대로 67"
                    data["phone"] = "1588-8700"
                    data["cause"] = "신용카드대금"
                elif "토스뱅크" in full_text or "TOSS" in full_text.upper(): 
                    data["creditor_name"] = "토스뱅크 주식회사"
                    data["address"] = "서울 강남구 테헤란로 131"
                    data["phone"] = "1661-7654"
                    data["cause"] = "대출금"
                elif "김창곤" in full_text:
                    data["creditor_name"] = "김창곤"
                    data["cause"] = "개인대여금"
                elif "김아림" in full_text:
                    data["creditor_name"] = "김아림"
                    data["cause"] = "개인대여금"

                # 2. 원금 및 이자 추출
                data["principal"] = parse_amount(full_text, "원금")
                if data["principal"] == 0:
                    data["principal"] = parse_amount(full_text, "잔액")
                
                data["interest"] = parse_amount(full_text, "이자")

                results.append(data)
                total_principal += data["principal"]
                total_interest += data["interest"]

            except Exception as e:
                st.error(f"⚠️ {pdf.name} 처리 중 오류 발생: {e}")
            
            progress_bar.progress((i + 1) / len(pdf_files))

        if results:
            status_text.text("✅ 분석 완료! 법원 양식 엑셀에 작성 중입니다...")
            
            try:
                wb = openpyxl.load_workbook(template_file)
                ws = wb['채권'] if '채권' in wb.sheetnames else wb.active

                # 상단 총합계 기재 (파일2 양식 기준 D4, D5)
                ws['D4'] = total_principal 
                ws['D5'] = total_interest

                start_row = 14  # 채권자별 데이터가 시작되는 행
                
                for idx, data in enumerate(results):
                    current_row = start_row + (idx * 6)
                    
                    # 파일2 양식의 6줄 규칙에 맞춰 셀 배치
                    ws.cell(row=current_row, column=1, value=idx + 1) # 채권번호
                    ws.cell(row=current_row, column=2, value=data['creditor_name']) # 채권자명
                    ws.cell(row=current_row, column=4, value=data['start_date']) # 발생일자
                    ws.cell(row=current_row, column=12, value=data['address']) # 주소
                    
                    ws.cell(row=current_row+1, column=4, value=data['cause']) # 채권 내용
                    ws.cell(row=current_row+1, column=12, value=data['phone']) # 전화번호
                    
                    ws.cell(row=current_row+2, column=4, value="원금 잔액")
                    ws.cell(row=current_row+2, column=6, value=data['principal'])
                    
                    ws.cell(row=current_row+3, column=4, value=data['ref_date']) # 산정기준일
                    
                    ws.cell(row=current_row+4, column=4, value=data['principal'])
                    ws.cell(row=current_row+4, column=8, value="부채확인서 참조")
                    
                    ws.cell(row=current_row+5, column=4, value=data['interest'])
                    ws.cell(row=current_row+5, column=8, value="부채확인서 참조")

                output = io.BytesIO()
                wb.save(output)
                processed_data = output.getvalue()
                
                st.success("🎉 채권자목록 엑셀 파일이 성공적으로 완성되었습니다!")
                st.download_button(
                    "📥 완성된 채권자목록 다운로드", 
                    data=processed_data, 
                    file_name="완성된_채권자목록.xlsx", 
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"엑셀 파일 기록 중 오류가 발생했습니다: {e}")
