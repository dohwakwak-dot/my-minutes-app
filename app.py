import streamlit as st
from google import genai
from google.genai import types
from docx import Document
import io

# 웹 화면 레이아웃 설정
st.set_page_config(page_title="엔지니어링 스마트 회의록 시스템", layout="wide")

# 🔒 화면 왼쪽(사이드바)에서 각자 본인의 API 키를 입력하도록 설정하여 사용자 토큰을 방어합니다.
with st.sidebar:
    st.header("🔑 API Key 설정")
    GEMINI_API_KEY = st.text_input("Gemini API Key 입력", type="password", placeholder="AIzaSy...")
    
    # 💡 [요구사항 반영] 동료들을 위한 친절한 API 발급 방법 안내문 상시 노출
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
    st.caption("※ 본 프로그램은 입력된 Key를 수집하지 않으며, 해당 계정의 무료/유료 토큰만 소모합니다.")

# 입력한 키로 구글 재미나이 가동하기
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None

# 웹 화면 메인 타이틀 꾸미기
st.title("🏗️ 엔지니어링 맞춤형 스마트 회의록 자동화 시스템")
st.write("사실에만 입각한 안건별 요약, 분야별 Action Plan, 원본 녹취록 매칭까지 한 번에 해결합니다.")

# 1단계: 참석자 및 분야별 정보 입력받기
st.subheader("👥 1단계: 회의 참석자 및 분야별 업무 분담 작성")
st.info("💡 회의 참석 여부와 상관없이, 후속 업무 전달이 필요한 분야의 담당자 정보를 모두 입력해 주세요.")

user_count = st.number_input("정보를 입력할 총 인원수 (명)", min_value=1, value=3, step=1)

# 인원수만큼 동적으로 이름과 분야를 입력받는 칸 생성
member_data = []
fields_options = ["상하수도", "구조", "토질", "건축", "기계", "전기 및 계측제어", "조경", "인허가", "기타 분야"]

# 가로로 깔끔하게 배치하기 위해 반복문 사용
for i in range(int(user_count)):
    col_name, col_field = st.columns(2)
    with col_name:
        name = st.text_input(f"👤 인원 {i+1} 이름", key=f"name_{i}", placeholder="홍길동")
    with col_field:
        field = st.selectbox(f"⚙️ 인원 {i+1} 담당 분야", options=fields_options, key=f"field_{i}")
    if name:
        member_data.append({"이름": name, "분야": field})

# 정보 추출용 문자열 미리 생성
member_info_str = ", ".join([f"{m['이름']}({m['분야']})" for m in member_data])
member_names_only = ", ".join([m['이름'] for m in member_data])

st.write("---")

# 2단계: 회의 메모 사전 입력 (덤핑식)
st.subheader("📝 2단계: 회의 중 메모한 내용 입력")
st.caption("정리되지 않은 날것의 메모, 키워드, 중요 정황 등을 편하게 덤핑(무작위 입력)식으로 적어주세요. AI가 녹음본과 대조하여 사실 확인에 사용합니다.")
memo_input = st.text_area("회의 메모 덤핑 입력란", height=150, placeholder="예: 상하수도 홍길동 관경 변경 검토 요청함. 토질 이철수 지반조사 보고서 다음 주까지 완료 바람...")

st.write("---")

# 3단계: 녹음 파일 업로드
st.subheader("🎵 3단계: 회의 녹음 파일 업로드")
uploaded_file = st.file_uploader("회의 파일(mp3, wav 등)을 올려주세요.", type=["mp3", "wav", "m4a", "wma"])

st.write("---")

# 모든 정보가 입력되었을 때 작동 시작
if uploaded_file is not None and member_data:
    if client is None:
        st.warning("👈 왼쪽 사이드바에 본인의 Gemini API Key를 먼저 입력해 주세요!")
    elif st.button("🚀 사실 기반 회의록 작성 시작"):
        
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
        with st.spinner("2단계: 재미나이가 사실에 입각하여 회의록 및 원본 녹취록을 작성 중입니다..."):
            
            # [요구사항 대거 반영] 무조건 사실에만 입각하고, 분야별 담당자 매칭 및 원본 대화록을 출력하는 초강력 프롬프트
            system_prompt = f"""
            너는 엔지니어링 설계 회사의 베테랑 전문 비서 요원이야. 
            아래 제공된 [입력된 정보]와 [🚨 엄격한 작성 원칙]을 바탕으로 완벽한 회의록 보고서를 작성해줘.
            
            [입력된 정보]
            - 전체 명단 및 분야: {member_info_str}
            - 입력된 이름 목록: {member_names_only}
            - 작성자가 직접 입력한 회의 메모: {memo_input}
            
            [🚨 엄격한 작성 원칙 - 위반 시 감점]
            1. 오직 제공된 '오디오 파일 내용'과 '작성자가 직접 입력한 회의 메모'에 명시된 사실로만 작성해라.
            2. AI 너의 주관적인 아이디어, 권장 사항, 추가적인 기술 제안이나 예측 자료를 '절대' 포함하지 마라. 허구의 사실이나 유추는 철저히 배제하고 철저히 '사실에 입각(Fact-based)'해서만 적어라.
            3. 샾(#), 별표(**), 대시(---) 같은 마크다운 기호는 절대 사용하지 마라. 보고서용 텍스트 서식으로만 출력해라.
            4. 모든 문장의 끝은 전문적인 비즈니스 보고서용 명사형 종결어미(-함, -임, - 바람, - 결정됨)를 사용해라.

            [📋 회의록 작성 양식 가이드]
            아래 적어주는 대제목 구조를 유지하여 순서대로 작성해줘.

            [회의 개요]
            • 참석 및 관련자 명단: {member_info_str}

            [주요 안건 및 논의 내용]
            (회의 내용은 철저히 주요 안건별로 구조를 나누고, 세부 사항은 대시(-) 기호를 사용한 개조식으로 요약할 것.)
            (각 문장 끝에는 제공된 이름 목록({member_names_only})을 바탕으로 해당 발언자를 찾아 반드시 괄호 표기할 것. 예: - 관경 변경에 따른 수리계산서 재검토 바람 (홍길동))

            [결론: 분야별 후속 진행 사항]
            (회의 내용 및 메모를 바탕으로, 이후 진행해야 하는 태스크들을 입력된 담당자별/분야별로 명확히 쪼개서 정리할 것. 이를 통해 각 분야 담당자들이 본인의 업무를 놓치지 않게 가이드할 것.)
            • [분야명 / 담당자 이름] 세부 조치 사항 및 기한 정리 

            [회의 대화 내용 원본 (녹취록)]
            (오디오 파일에서 대화한 원본 내용을 그대로 받아 적어라. 이때 발언자가 누구인지 분석하여 제공된 이름 목록({member_names_only}) 중에서 매칭하여 반드시 '화자: 대화내용' 순서로 작성해라.)
            예시:
            홍길동: 이번 지반조사 결과 토질 상태가 생각보다 연약합니다.
            김철수: 그렇다면 구조물 기초 형식을 변경해야겠네요.
            """
            
            try:
                # 오디오와 덤핑 메모를 동시에 주입하여 상호 크로스체크 유도
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[
                        audio_part,
                        f"\n\n[추가 참고 메모]\n{memo_input}\n\n위 데이터들을 바탕으로 다음 지시사항에 맞춰 철저히 사실 기반의 회의록을 작성해줘:\n{system_prompt}"
                    ]
                )
                final_minutes = response.text
                st.success("✅ 재미나이 회의록 및 녹취록 작성 완료!")
                
                # 화면에 결과 미리보기 출력
                st.subheader("📝 완성된 회의록 및 원본 녹취록 미리보기")
                st.text_area("결과물 창 (복사 가능)", value=final_minutes, height=400)
                
                st.subheader("💾 4단계: 파일 다운로드")
                
                # 3-1. 워드(Docx) 다운로드 파일 빌드
                doc = Document()
                doc.add_heading('📋 스마트 회의록 결과 보고서', level=0)
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
                        file_name="엔지니어링_회의록.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                with col_dl2:
                    st.download_button(
                        label="👑 한글(Hwpx) 파일로 다운로드",
                        data=bio_hwpx.getvalue(),
                        file_name="엔지니어링_회의록.hwpx",
                        mime="application/octet-stream"
                    )
                
            except Exception as e:
                st.error(f"재미나이 회의록 생성 중 오류가 발생했습니다: {e}")
else:
    st.info("💡 왼쪽 사이드바에 API 키를 넣고, 1~3단계 정보를 채우시면 버튼이 활성화됩니다.")
