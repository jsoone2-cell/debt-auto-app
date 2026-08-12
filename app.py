import streamlit as st
import google.generativeai as genai
import pdfplumber
import json
import re
import io
import time
import openpyxl
from datetime import datetime, timedelta

st.set_page_config(page_title="채권자목록 자동 완성기", page_icon="⚖️", layout="centered")

st.title("⚖️ 개인회생 채권자목록 자동 완성 AI")
st.markdown("빈 엑셀 양식과 부채증명서들을 올리면, 법원 제출용 양식에 맞춰 작성됩니다.")

with st.sidebar:
    st.header("⚙️ 설정")
    api_key = st.text_input("Google Gemini API 키", type="password")

st.subheader("1. 파일 업로드")
template_file = st.file_uploader("빈 양식 엑셀 파일 (변제계획안.xlsx)", type="xlsx")
pdf_files = st.file_uploader("부채증명서 PDF 파일 업로드", type="pdf", accept_multiple_files=True)

if st.button("✨ 자동 작성 시작", type="primary"):
    if not api_key or not template_file or not pdf_files:
        st.error("API 키, 엑셀 양식, 부채증명서 PDF를 모두 확인해 주세요.")
    else:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        total_principal = 0
        total_interest = 0

        for i, pdf in enumerate(pdf_files):
            status_text.text(f"[{pdf.name}] 문서 분석 중... 🧐")
            
            # 🔥 표 인식이 뛰어난 pdfplumber 사용
            text = ""
            with pdfplumber.open(pdf) as p:
                for page in p.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
            
            # 글자를 아예 못 읽은 경우 (스캔 이미지 파일일 확률 높음)
            if len(text.strip()) < 10:
                st.error(f"❌ {pdf.name} 파일에서 글자를 읽을 수 없습니다. (스캔된 이미지 파일인지 확인해주세요)")
                continue

            text = re.sub(r'\d{6}-\d{7}', '******-*******', text) # 보안 마스킹

            # 🔥 디버깅: 파이썬이 문서를 어떻게 읽었는지 화면에 보여줌
            with st.expander(f"👀 {pdf.name} 추출된 텍스트 확인 (클릭)"):
                st.text(text[:1000]) # 앞부분만 보여주기
            
            prompt = f"""
            당신은 개인회생 채권자 목록 작성 전문가입니다. 부채증명서에서 다음 정보를 찾아 JSON으로 답하세요.
            [추출 항목]
            - creditor_name: 채권자명
            - start_date: 최초대출일 또는 카드발급일 (예: 2022-08-26, 모르면 "")
            - address: 채권자 주소 (모르면 "")
            - phone: 채권자 대표전화번호 (모르면 "")
            - cause: 채권의 내용 (예: 발급받은신용카드사용채무, 신용대출 등)
            - principal: 원금 잔액 (숫자만, 0이면 0)
            - interest: 이자 잔액 (숫자만, 없으면 0)
            - ref_date: 채무액 산정기준일 (예: 2025-10-28)

            텍스트: {text[:4000]}
            """
            try:
                response = model.generate_content(prompt)
                ai_data = json.loads(response.text.replace('```json', '').replace('```', '').strip())
                
                results.append(ai_data)
                total_principal += int(ai_data['principal'])
                total_interest += int(ai_data['interest'])
            except Exception as e:
                st.warning(f"⚠️ {pdf.name} 데이터 추출 실패: AI가 양식을 파악하지 못했습니다.")
            
            progress_bar.progress((i + 1) / len(pdf_files))
            time.sleep(2)

        if results:
            status_text.text("✅ AI 분석 완료! 엑셀 양식에 입력합니다...")
            
            try:
                wb = openpyxl.load_workbook(template_file)
                ws = wb['채권'] if '채권' in wb.sheetnames else wb.active

                ws['D4'] = total_principal 
                ws['D5'] = total_interest

                start_row = 14
                
                for idx, data in enumerate(results):
                    current_row = start_row + (idx * 6)
                    ws.cell(row=current_row, column=1, value=idx + 1)
                    ws.cell(row=current_row, column=2, value=data.get('creditor_name', ''))
                    ws.cell(row=current_row, column=4, value=data.get('start_date', ''))
                    ws.cell(row=current_row, column=12, value=data.get('address', ''))
                    
                    ws.cell(row=current_row+1, column=4, value=data.get('cause', ''))
                    ws.cell(row=current_row+1, column=12, value=data.get('phone', ''))
                    
                    ws.cell(row=current_row+2, column=4, value="원금 잔액")
                    ws.cell(row=current_row+2, column=6, value=int(data.get('principal', 0)))
                    
                    try:
                        ref_dt = datetime.strptime(data.get('ref_date', '').replace('. ','-').replace('.','-'), "%Y-%m-%d")
                        next_dt = ref_dt + timedelta(days=1)
                        ws.cell(row=current_row+3, column=4, value=next_dt.strftime("%Y-%m-%d"))
                    except:
                        ws.cell(row=current_row+3, column=4, value=data.get('ref_date', ''))
                    
                    ws.cell(row=current_row+4, column=4, value=int(data.get('principal', 0)))
                    ws.cell(row=current_row+4, column=8, value=f"부채확인서 참조 (산정기준일: {data.get('ref_date', '')})")
                    
                    ws.cell(row=current_row+5, column=4, value=int(data.get('interest', 0)))
                    ws.cell(row=current_row+5, column=8, value=f"부채확인서 참조 (산정기준일: {data.get('ref_date', '')})")

                output = io.BytesIO()
                wb.save(output)
                processed_data = output.getvalue()
                
                st.success("🎉 작성이 완료되었습니다! 아래 버튼을 눌러 결과물을 확인하세요.")
                st.download_button("📥 완성된 채권자목록 다운로드", data=processed_data, file_name="완성본_변제계획안.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            except Exception as e:
                st.error(f"엑셀 파일 작성 중 오류가 발생했습니다: {e}")
