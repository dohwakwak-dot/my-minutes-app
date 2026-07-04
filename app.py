import streamlit as st
from google import genai
from google.genai import types
from docx import Document
import io

# 웹 화면 레이아웃 설정
st.set_page_config(page_title="Gemini 스마트 회의록 시스템", layout="centered")

# 🔒 화면 왼쪽(사이드바)에서 각자 본인의 API 키를 입력하도록 설정하여 사용자 토큰을 방어합니다.
with st.sidebar:
    st.header("🔑 API Key 설정")
    st.write("구글 AI 스튜디오에서 발급받은 본인의 API Key를 입력하셔야 프로그램이 작동합니다.")
    # 사용자가 직접 입력하는 칸 (비밀번호처럼 숨겨져서 입력됨)
    GEMINI_API_KEY = st.text_input("Gemini API Key 입력", type="password", placeholder="AIzaSy...")
    st.markdown("[👉 무료 Gemini API Key 발급 링크](https://aistudio.google.com/)")
    st.write("---")
    st.caption("※ 본 프로그램은 사용자의 API Key를 저장하거나 수집하지 않으며, 입력된 계정의 토큰만 소모합니다.")

# 입력한 키로 구글 재미나이 가동하기
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None

# 웹 화면 메인 타이틀 꾸미기
st.title("🤖 안건별 Gemini 회의록 작성 자동화 시스템")
st.write("회의 녹음 파일과 참석자 정보를 입력하면 재미나이가 맞춤형 회의록을 만들어 드립니다.")

# 1단계: 참석자 정보 입력받기
st.subheader("👥 1단계: 참석자 명단 작성")
col1, col2 = st.columns(2)
with col1:
    user_count = st.number_input("회의 참석 인원 (명)", min_value=1, value=3, step=1)
with col2:
    member_list = st.text_input("참석자 명단 입력 (쉼표로 구분)", placeholder="홍길동, 김철수, 이영희")

# 2단계: 녹음 파일 업로드
st.subheader("🎵 2단계: 회의 녹음 파일 업로드")
uploaded_file = st.file_uploader("회의 파일(mp3, wav 등)을 올려주세요.", type=["mp3", "wav", "m4a", "wma"])

# 모든 정보가 입력되었을 때 작동 시작
if uploaded_file is not None and member_list:
    if client is None:
        st.warning("👈 왼쪽 사이드바에 본인의 Gemini API Key를 먼저 입력해 주세요!")
    elif st.button("🚀 회의록 자동 작성 시작"):
        
        # 1. 오디오 데이터 읽기 및 전처리
        with st.spinner("1단계: 음성 파일을 읽고 분석하는 중입니다..."):
            try:
                audio_bytes = uploaded_file.read()
                file_ext = uploaded_file.name.split('.')[-1].lower()
                mime_type = f"audio/{file_ext}" if file_ext in ['mp3', 'wav', 'm4a', 'wma'] else "audio/mp3"
                
                audio_part = types.Part.from_bytes(
                    data=audio_bytes,
                    mime_type=mime_type,
                )
                st.success("✅ 음성 파일 로드 완료!")
                
            except Exception as e:
                st.error(f"음성 파일 분석 중 오류가 발생했습니다: {e}")
                st.stop()

        # 2. 재미나이 서식 구조화 요약 요청
        with st.spinner("2단계: 재미나이가 안건별 요약 및 분야별 결론을 도출 중입니다..."):
            
            # 대화로 완성한 비즈니스 룰 프롬프트
            system_prompt = f"""
            너는 대기업의 전문 비서 요원이야. 아래 규칙에 맞게 회의록을 완벽하게 작성해줘.
            
            [입력된 정보]
            - 총 참석 인원: {user_count}명
            - 참석자 이름 명단: {member_list}
            
            [회의록 작성 규칙]
            1. 회의 내용은 반드시 '안건별'로 구조를 나누어 정리해줘. (예: 안건 1: 신제품 디자인 선정)
            2. 안건별 세부 내용은 반드시 항목을 하나씩 나열하는 '개조식(- 기호 사용)'으로 작성해줘.
            3. 각 문장 끝에는 해당 발언을 한 사람이 누구인지 입력된 참석자 명단({member_list}) 중에서 매칭하여 괄호 표기해줘. (예: - 디자인 시안 A가 가독성이 더 높음 (홍길동))
            4. 회의록 맨 마지막에는 [결론: 후속 진행 사항]을 만들어줘. 이때 반드시 '분야별(예: 개발팀, 마케팅팀, 디자인팀 등 회의 내용에 나온 분야)'로 나누어 작성해서 담당자들이 업무를 놓치지 않도록 세부 태스크를 정리해줘.
            5. 어조는 정중하고 전문적인 비즈니스 명사형 종결어미(-함, -임, - 바람) 또는 보고서용 어조를 사용해줘.
            """
            
            try:
                # 오디오 인식이 뛰어난 최신 gemini-2.5-flash 활용
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[
                        audio_part,
                        f"\n\n위 오디오 파일을 분석하여 지시사항에 맞춰 회의록을 작성해줘:\n{system_prompt}"
                    ]
                )
                final_minutes = response.text
                st.success("✅ 재미나이 회의록 작성 완료!")
                
                # 화면에 결과 출력
                st.subheader("📝 완성된 회의록 미리보기")
                st.markdown(final_minutes)
                
                st.subheader("💾 3단계: 파일 다운로드")
                
                # 3-1. 워드(Docx) 다운로드 파일 빌드
                doc = Document()
                doc.add_heading('📋 회의록 결과 보고서 (Gemini)', level=0)
                doc.add_paragraph(final_minutes)
                bio_docx = io.BytesIO()
                doc.save(bio_docx)
                
                # 3-2. 한글(HWPX) 다운로드 파일 빌드
                bio_hwpx = io.BytesIO()
                bio_hwpx.write(final_minutes.encode('utf-8'))
                
                # 다운로드 버튼 가로 정렬
                col_dl1, col_dl2 = st.columns(2)
                with col_dl1:
                    st.download_button(
                        label="💾 워드(Docx) 파일로 다운로드",
                        data=bio_docx.getvalue(),
                        file_name="Gemini_회의록.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                with col_dl2:
                    st.download_button(
                        label="👑 한글(Hwpx) 파일로 다운로드",
                        data=bio_hwpx.getvalue(),
                        file_name="Gemini_회의록.hwpx",
                        mime="application/octet-stream"
                    )
                
            except Exception as e:
                st.error(f"재미나이 회의록 생성 중 오류가 발생했습니다: {e}")
else:
    st.info("💡 왼쪽 사이드바에 API 키를 넣고, 참석자 정보를 채운 뒤 녹음 파일을 올려주세요!")