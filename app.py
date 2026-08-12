import streamlit as st
import google.generativeai as genai
import json
import io
import time
import openpyxl
from datetime import datetime, timedelta
import tempfile
import os

st.set_page_config(page_title="채권자목록 자동 완성기", page_icon="⚖️", layout="centered")

st.title("⚖️ 개인회생 채권자목록 자동 완성 AI")
st.markdown("스캔된 부채증명서라도 문제없습니다! AI가 직접 눈으로 읽고 법원 양식을 작성합니다.")

with st.sidebar:
    st.header("⚙️ 설정")
    api_key = st.text_input("Google Gemini API 키", type="password")

st.subheader("1. 파일 업로드")
template_file = st.file_uploader("빈 양식 엑셀 파일 (변제계획안.xlsx)", type="xlsx")
pdf_files = st.file_uploader("부채증명서 PDF 파일 업로드 (스캔본 가능)", type="pdf", accept_multiple_files=True)

if st.button("✨ 시각(Vision) AI로 작성 시작", type="primary"):
    if not api_key or not template_file or not pdf_files:
        st.error("API 키, 엑셀 양식, 부채증명서 PDF를 모두 확인해 주세요.")
    else:
        genai.configure(api_key=api_key)
        # 이미지 인식 능력이 탁월한 모델 사용
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        total_principal = 0
        total_interest = 0

        for i, pdf in enumerate(pdf_files):
            status_text.text(f"[{pdf.name}] AI가 문서를 직접 읽고 있습니다... 🧐")
            
            # 1. 스트림릿에 올라온 파일을 임시 폴더에 저장 (Gemini 업로드용)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
                temp_pdf.write(pdf.read())
                temp_path = temp_pdf.name
            
            try:
                # 2. Gemini의 눈(Vision)에 파일 업로드
                uploaded_file = genai.upload_file(path=temp_path, display_name=pdf.name)
                
                # 3. AI에게 내리는 프롬프트 (파일과 함께 전달)
                prompt = """
                당신은 개인회생 채권자 목록 작성 전문가입니다. 첨부된 부채증명서 문서(스캔본 포함)를 직접 눈으로 분석하여 다음 정보를 JSON으로만 답하세요.
                [추출 항목]
                - creditor_name: 채권자명 (예: 현대카드(주), 김창곤 등)
                - start_date: 최초대출일, 차용일 또는 카드발급일 (예: 2022-08-26, 모르면 "")
                - address: 채권자 주소 (모르면 "")
                - phone: 채권자 대표전화번호 (모르면 "")
                - cause: 채권의 내용 (예: 발급받은신용카드사용채무, 신용대출, 개인대여금 등)
                - principal: 원금 잔액 (숫자만, 0이면 0)
                - interest: 이자 잔액 (숫자만, 없으면 0)
                - ref_date: 채무액 산정기준일 (예: 2025-10-28)
                """
                
                # 4. 분석 실행
                response = model.generate_content([prompt, uploaded_file])
                
                # 5. 결과 정리
                ai_data = json.loads(response.text.replace('```json', '').replace('```', '').strip())
                results.append(ai_data)
                total_principal += int(ai_data.get('principal', 0))
                total_interest += int(ai_data.get('interest', 0))
                
                # 서버에서 임시 파일들 삭제 (보안 및 정리)
                os.remove(temp_path)
                genai.delete_file(uploaded_file.name)
                
            except Exception as e:
                st.warning(f"⚠️ {pdf.name} 데이터 추출 실패: {e}")
                # 에러가 나도 임시 파일은 지워지도록 처리
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            
            progress_bar.progress((i + 1) / len(pdf_files))
            time.sleep(2) # 무료 API 속도 조절용

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
                
                st.success("🎉 시각 AI로 작성이 완료되었습니다! 아래 버튼을 눌러 결과물을 확인하세요.")
                st.download_button("📥 완성된 채권자목록 다운로드", data=processed_data, file_name="완성본_변제계획안.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            except Exception as e:
                st.error(f"엑셀 파일 작성 중 오류가 발생했습니다: {e}")
