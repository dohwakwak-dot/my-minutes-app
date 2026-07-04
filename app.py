import streamlit as st
from google import genai
from google.genai import types
from docx import Document
import io
import re

# 웹 화면 레이아웃 설정
st.set_page_config(page_title="엔지니어링 스마트 회의록 시스템", layout="wide")

# 🔒 화면 왼쪽(사이드바)에서 각자 본인의 API 키를 입력하도록 설정하여 사용자 토큰을 방어합니다.
with st.sidebar:
    st.header("🔑 API Key 설정")
    GEMINI_API_KEY = st.text_input("Gemini API Key 입력", type="password", placeholder="AIzaSy...")
    
    st.markdown("""
    ### 🔰 초간단 API Key 발급 방법
    1. [👉 구글 AI 스튜디오 바로가기](https://aistudio.google.com/) 클릭
    2. 소지하신 **구글 계정(Gmail)**으로 로그인
    3. 약관 창이 뜨면 모두 체크 후 **[Accept/Continue]** 클릭
    4. 좌측 상단의 파란색 **`[Get API key]`** 버튼 클릭
    5. **`[Create API key]`** ➡️ **`[Create API key in new project]`** 클릭
    6. 생성된 `AIzaSy...`로 시작하는 긴 키를 복사(`Copy`)해서 위 칸에 붙여넣기 하시면 됩니다!
    """)
    st.write("---")
    st.caption("※ 本 프로그램은 입력된 Key를 수집하지 않으며, 해당 계정의 무료/유료 토큰만 소모합니다.")

# 입력한 키로 구글 재미나이 가동하기
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None

# 웹 화면 메인 타이틀 꾸미기
st.title("🏗️ 엔지니어링 맞춤형 스마트 회의록 자동화 시스템")
st.write("1차 추출된 대화 내용을 눈으로 직접 확인하며 완벽하게 발언자를 매칭합니다.")

# 1단계: 참석자 및 분야별 정보 입력받기
st.subheader("👥 1단계: 회의 참석자 정보 입력")
user_count = st.number_input("정보를 입력할 참석 인원수 (명)", min_value=1, value=3, step=1)

member_data = []
for i in range(int(user_count)):
    col_name, col_field = st.columns(2)
    with col_name:
        name = st.text_input(f"👤 참석자 {i+1} 이름", key=f"name_{i}", placeholder="홍길동")
    with col_field:
        field = st.text_input(f"⚙️ 참석자 {i+1} 담당 분야/직급", key=f"field_{i}", placeholder="예: 상하수도, 구조부, 발주청 감독관 등")
    if name:
        member_data.append({"이름": name, "분야": field if field else "미지정"})

# 선택 박스용 실제 이름 목록 리스트 생성
member_names_list = [m['이름'] for m in member_data]

st.write("---")

# 2단계: 회의 메모 사전 입력 (덤핑식)
st.subheader("📝 2단계: 회의 중 메모한 내용 입력")
memo_input = st.text_area("회의 메모 덤핑 입력란", height=120, placeholder="예: 상하수도 관경 변경 검토 요청함. 발주청 지시사항으로 다음 주까지 공정표 제출 바람...")

st.write("---")

# 3단계: 녹음 파일 업로드 및 가생성
st.subheader("🎵 3단계: 회의 녹음 파일 업로드")
uploaded_file = st.file_uploader("회의 파일(mp3, wav 등)을 올려주세요.", type=["mp3", "wav", "m4a", "wma"])

st.write("---")

# 상태 저장을 위한 세션 설정
if "step1_done" not in st.session_state:
    st.session_state.step1_done = False
if "raw_transcript" not in st.session_state:
    st.session_state.raw_transcript = ""
if "detected_speakers" not in st.session_state:
    st.session_state.detected_speakers = []

# 파일이 올라왔을 때 작동
if uploaded_file is not None and member_data:
    if client is None:
        st.warning("👈 왼쪽 사이드바에 본인의 Gemini API Key를 먼저 입력해 주세요!")
    else:
        # 1차 분석 버튼
        if not st.session_state.step1_done:
            if st.button("🔍 1차 음성 분석 및 발언자 분리 시작"):
                with st.spinner("재미나이가 음성을 분석하여 목소리 그룹(발언자1, 발언자2...)을 식별하고 있습니다..."):
                    try:
                        audio_bytes = uploaded_file.read()
                        file_ext = uploaded_file.name.split('.')[-1].lower()
                        mime_type = f"audio/{file_ext}" if file_ext in ['mp3', 'wav', 'm4a', 'wma'] else "audio/mp3"
                        audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
                        
                        speaker_prompt = """
                        위 오디오 파일의 대화 원본을 토대로 녹취록을 작성해라. 
                        단, 발언자의 실제 이름을 절대 임의로 추측해서 적지 마라. 
                        목소리 톤과 순서에 따라 철저히 '발언자 1', '발언자 2', '발언자 3' 형태로만 구분하여 '발언자 X: 대화내용' 양식으로 대화록 원본 전체를 출력해라.
                        """
                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=[audio_part, speaker_prompt]
                        )
                        st.session_state.raw_transcript = response.text
                        
                        # 패턴 추출
                        finders = re.findall(r'(발언자\s*\d+)', st.session_state.raw_transcript)
                        st.session_state.detected_speakers = sorted(list(set([f.replace(" ", "") for f in finders])))
                        
                        if not st.session_state.detected_speakers:
                            st.session_state.detected_speakers = ["발언자1", "발언자2", "발언자3", "발언자4"]
                            
                        st.session_state.step1_done = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"음성 분석 중 에러가 발생했습니다: {e}")

        # 임시 분석 완료 후 사용자에게 매칭 창을 열어줌
        if st.session_state.step1_done:
            st.subheader("🔄 4단계: 대화 원본 확인 및 발언자 지정")
            st.success("✅ AI가 음성 대화록을 추출했습니다! 아래 대화 내용을 읽어보시면서, 각 발언자 번호가 실제 누구인지 짝지어 주세요.")
            
            st.write("📋 **1차 추출된 대화 내용 원본 (여기서 대화를 확인하세요):**")
            st.text_area("대화 내용 스크롤 확인창", value=st.session_state.raw_transcript, height=250, disabled=True)
            
            st.write("🔽 **위 내용을 참고하여 발언자 매칭을 완료해 주세요:**")
            
            mapping_results = {}
            cols = st.columns(min(len(st.session_state.detected_speakers), 3))
            for idx, speaker in enumerate(st.session_state.detected_speakers):
                with cols[idx % 3]:
                    mapping_results[speaker] = st.selectbox(
                        f"🔊 {speaker}의 실제 인물",
                        options=member_names_list,
                        key=f"map_{speaker}"
                    )
            
            st.write("---")
            st.subheader("🚀 5단계: 최종 사실 기반 회의록 최종 생성")
            
            if st.button("✨ 최종 회의록 및 한글 파일 발행"):
                with st.spinner("설정하신 이름 매칭 정보를 바탕으로 최종 완벽한 보고서를 작성 중입니다..."):
                    
                    mapping_str = "\n".join([f"- 변경 전: {k} -> 변경 후 실제 이름: {v}" for k, v in mapping_results.items()])
                    member_info_str = ", ".join([f"{m['이름']}({m['분야']})" for m in member_data])
                    
                    # 🛠️ 수정한 프롬프트 구간 (오타 유발 중괄호 처리 및 인쇄 가이드 수정 완료)
                    final_prompt = f"너는 엔지니어링 설계 회사의 베테랑 전문 비서 요원이야. 제공된 데이터와 규칙을 100% 준수하여 보고서용 회의록을 완성해줘.\n\n[제공된 데이터 자료]\n1. 1차 분리된 대화 원본:\n{st.session_state.raw_transcript}\n\n2. 화자 매칭 정보:\n{mapping_str}\n\n3. 전체 인원 및 소속 분야:\n{member_info_str}\n\n4. 회의 사전 메모:\n{memo_input}\n\n[작성 규칙]\n- '발언자 X'를 매칭 정보에 맞게 실제 이름으로 전부 치환해라.\n- 오직 대화 내용과 사전 메모에 명시된 사실로만 요약하고, 기술 제안이나 유추 등 주관적 의견은 절대 포함하지 마라.\n- 샵(#), 별표(**), 대시(---) 같은 마크다운 기호는 전면 금지하며 오직 명사형 종결어미(-함, -임, - 바람)로만 보고서 서식을 작성해라.\n\n[출력 구조]\n1. [회의 개요]\n- 참석자 명단 출력\n2. [주요 안건 및 논의 내용]\n- 안건별 단락을 명확히 나누고 대시(-) 기호로 개조식 요약하되 문장 끝에 실제 발언자 괄호 표기\n3. [결론: 분야별 후속 진행 사항]\n- 상하수도분야, 구조분야, 토질분야, 건축분야, 기계분야, 전기 및 계측제어분야, 인허가 분야, 기타분야, 발주청 리스트를 고려하여 후속 조치 업무 정리\n4. [회의 대화 내용 원본 (녹취록)]\n- 발언자 이름이 모두 한글 이름으로 치환된 전체 대화 원본을 '이름: 대화내용' 양식으로 그대로 출력"
                    
                    try:
                        final_response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=final_prompt
                        )
                        final_minutes = final_response.text
                        st.success("✅ 완벽하게 매칭된 최종 회의록이 발행되었습니다!")
                        
                        st.subheader("📝 최종 회의록 및 매칭 대화록 미리보기")
                        st.text_area("최종 결과물 창", value=final_minutes, height=400)
                        
                        # 파일 빌드
                        doc = Document()
                        doc.add_heading('📋 스마트 회의록 결과 보고서', level=0)
                        doc.add_paragraph(final_minutes)
                        bio_docx = io.BytesIO()
                        doc.save(bio_docx)
                        
                        bio_hwpx = io.BytesIO()
                        bio_hwpx.write(final_minutes.encode('utf-8'))
                        
                        col_dl1, col_dl2 = st.columns(2)
                        with col_dl1:
                            st.download_button("💾 워드(Docx) 파일로 다운로드", data=bio_docx.getvalue(), file_name="엔지니어링_최종회의록.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                        with col_dl2:
                            st.download_button("👑 한글(Hwpx) 파일로 다운로드", data=bio_hwpx.getvalue(), file_name="엔지니어링_최종회의록.hwpx", mime="application/octet-stream")
                            
                        if st.button("🔄 처음부터 다시 작성하기"):
                            st.session_state.step1_done = False
                            st.rerun()
                            
                    except Exception as e:
                        st.error(f"최종 조율 중 에러 발생: {e}")
else:
    st.info("💡 왼쪽 사이드바에 API 키를 넣고, 1~3단계 정보를 채우시면 분석 버튼이 나타납니다.")
    st.session_state.step1_done = False
