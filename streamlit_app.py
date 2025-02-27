import streamlit as st
import pandas as pd
import altair as alt
import os
import re

##############################################
# 0. 모든 띄어쓰기를 제거하는 함수
##############################################
def remove_all_whitespace(name: str) -> str:
    """
    문자열에 있는 모든 공백(' ')을 제거.
    """
    if not isinstance(name, str):
        return name
    return name.replace(" ", "")

##############################################
# 1. MultiIndex 컬럼 평탄화 함수
##############################################
def flatten_cols(cols):
    flattened = []
    for col_tuple in cols:
        if not isinstance(col_tuple, tuple):
            flattened.append(col_tuple)
            continue
        parts = []
        for level_val in col_tuple:
            if pd.isna(level_val) or "Unnamed" in str(level_val):
                continue
            part_str = str(level_val).replace('\n', '').strip()
            if part_str:
                parts.append(part_str)
        if parts:
            flattened.append("_".join(parts))
        else:
            flattened.append("")
    return flattened

##############################################
# 2. 캠퍼스명 통합 및 대학명 표준화 함수
##############################################
def unify_campus_name(name: str) -> str:
    """예: 'OO대학교_제2캠퍼스' -> 'OO대학교'"""
    if not isinstance(name, str):
        return name
    return re.sub(r"_제\d+캠퍼스", "", name).strip()

def standardize_univ_name(name: str) -> str:
    """특정 대학명에 대해 표준화 규칙 적용"""
    if not isinstance(name, str):
        return name
    
    # 혹시 남아있을 수도 있는 공백 제거
    name = name.replace(" ", "")
    
    if "강릉원주대학교" in name and "국립강릉원주대학교" not in name:
        return "국립강릉원주대학교"
    elif "금오공과대학교" in name and "국립금오공과대학교" not in name:
        return "국립금오공과대학교"
    elif "안동대학교" in name and "국립경국대학교" not in name:
        return "국립경국대학교"
    elif ("동국대학교(경주)" in name) or ("동국대학교(WISE)" in name) or ("동국대학교(경주캠퍼스)" in name):
        return "동국대학교(WISE)_분교"
    else:
        return name

##############################################
# 3. 로컬 파일 경로에서 파일 찾기 함수
##############################################
def find_matching_file(year, data_dir, file_pattern):
    if not data_dir:
        st.error("❌ data_dir 설정이 되어 있지 않습니다.")
        return None
    if not os.path.exists(data_dir):
        st.error(f"❌ 데이터 디렉토리 '{data_dir}'가 존재하지 않습니다.")
        return None
    files = os.listdir(data_dir)
    for file in files:
        if str(year) in file and file_pattern in file:
            return os.path.join(data_dir, file)
    return None

##############################################
# 4. 대학코드 파일 로드 (대학코드.xlsx)
##############################################
@st.cache_data(show_spinner=False)
def load_univ_codes(path):
    df_univ = pd.read_excel(path)
    # "schlKrnNm"을 "학교"로 rename
    df_univ.rename(columns={"schlKrnNm": "학교"}, inplace=True)
    # 필요한 컬럼만 추출 (실제 상황에 맞게 조정)
    cols = ["학교", "경쟁대학_구분1", "대경사학_구분2", "본교_구분3"]
    existing_cols = [c for c in cols if c in df_univ.columns]
    df_univ = df_univ[existing_cols]
    
    # 1) 모든 띄어쓰기 제거
    df_univ["학교"] = df_univ["학교"].astype(str).apply(remove_all_whitespace)
    
    # 2) 캠퍼스명 통일
    df_univ["학교"] = df_univ["학교"].apply(unify_campus_name)
    
    # 3) 대학명 표준화
    df_univ["학교"] = df_univ["학교"].apply(standardize_univ_name)
    
    return df_univ

##############################################
# 5. 여러 구분 할당 함수 (리스트 반환)
##############################################
def assign_categories(row):
    """
    - '경쟁대학_구분1'에 '경쟁대학' 문자열이 포함되면 '경쟁대학' 카테고리
    - '대경사학_구분2'에 '대경사학' 문자열이 포함되면 '대경사학' 카테고리
    - '본교_구분3'에 '본교' 문자열이 포함되면 '본교' 카테고리
    """
    cats = []
    c1 = str(row.get("경쟁대학_구분1", "")).strip().lower()
    c2 = str(row.get("대경사학_구분2", "")).strip().lower()
    c3 = str(row.get("본교_구분3", "")).strip().lower()
    
    if "경쟁대학" in c1:
        cats.append("경쟁대학")
    if "대경사학" in c2:
        cats.append("대경사학")
    if "본교" in c3:
        cats.append("본교")
        
    return cats if cats else [None]

##############################################
# 6. 데이터 로드 함수
##############################################
@st.cache_data(show_spinner=False)
def load_data(path):
    return pd.read_excel(path)

##############################################
# 7. 대시보드 메인
##############################################

# -- (1) GitHub에서 사용하는 경우, 현재 디렉토리를 PROJECT_PATH로 설정 --
PROJECT_PATH = "."  # 현재 디렉토리

metrics = {
    "신입생충원율": "신입생충원율.xlsx",
    "재학률": "재학률.xlsx",
    "중도탈락률": "중도탈락률.xlsx",
    "현장실습참여학생비율": "현장실습참여학생비율.xlsx",
    "교수당국제저명논문수": "교수당국제저명논문수.xlsx",
    "학생창업실적": "학생창업실적.xlsx",
    "학생사회봉사참여실적": "학생100명당사회봉사참여실적.xlsx",
    "기금실적": "기금실적.xlsx",
    "세입중등록금비율": "세입중등록금비율.xlsx"
}

UNIV_CODE_FILE = os.path.join(PROJECT_PATH, "대학코드.xlsx")

st.title("대학 지표 대시보드 (GitHub / 로컬 실행)")

# 사이드바: 지표 선택
selected_metric = st.sidebar.selectbox("보고자 하는 지표 선택", list(metrics.keys()))

# 조사연도 목록을 추출하는 함수
@st.cache_data(show_spinner=False)
def get_years(path):
    df_temp = pd.read_excel(path)
    if "조사연도" in df_temp.columns:
        years = sorted(df_temp["조사연도"].dropna().astype(str).unique().tolist())
        return years
    return []

file_path = os.path.join(PROJECT_PATH, metrics[selected_metric])
available_years = get_years(file_path)
if not available_years:
    available_years = [str(y) for y in [2021, 2022, 2023, 2024]]  # fallback

st.sidebar.markdown("### 연도 선택")
selected_years = []
for y in available_years:
    if st.sidebar.checkbox(y, value=True, key=f"year_{y}"):
        selected_years.append(y)
if not selected_years:
    selected_years = available_years

# 지표 파일 로드
if not os.path.exists(file_path):
    st.error(f"{metrics[selected_metric]} 파일을 찾을 수 없습니다. \n\n"
             f"다음 경로에 파일이 있는지 확인하세요: {file_path}")
    st.stop()
else:
    df = load_data(file_path)

    # 1) '대학코드' 컬럼은 표시에서 제외
    df_display = df.drop(columns=["대학코드"], errors="ignore")

    # 2) 연도 필터 적용
    if "조사연도" in df.columns:
        df["조사연도"] = df["조사연도"].astype(str)
        df = df[df["조사연도"].isin(selected_years)]
    else:
        st.info("데이터에 '조사연도' 열이 없습니다.")
    
    # 3) "학교" 컬럼 전처리 (메인 지표 데이터)
    if "학교" in df.columns:
        # (가) 모든 띄어쓰기 제거
        df["학교"] = df["학교"].astype(str).apply(remove_all_whitespace)
        # (나) 캠퍼스명 통일
        df["학교"] = df["학교"].apply(unify_campus_name)
        # (다) 대학명 표준화
        df["학교"] = df["학교"].apply(standardize_univ_name)
    else:
        st.info("데이터에 '학교' 열이 없습니다.")

    st.subheader(f"{selected_metric} 데이터")
    st.dataframe(df_display)

    # 사이드바: 학교 체크박스 필터 (체크된 학교만 사용)
    if "학교" in df.columns:
        schools = sorted(df["학교"].unique().tolist())
        st.sidebar.markdown("### 학교 선택")
        selected_schools = [school for school in schools if st.sidebar.checkbox(school, value=False, key=f"school_{school}")]
        if not selected_schools:
            selected_schools = schools
        df_school = df[df["학교"].isin(selected_schools)]
    else:
        df_school = df

    # 개별 꺾은선 그래프: 학교별 추세
    if not df_school.empty and "학교" in df_school.columns and selected_metric in df_school.columns and "조사연도" in df_school.columns:
        chart1 = alt.Chart(df_school).mark_line(point=True).encode(
            x=alt.X("조사연도:O", title="조사연도"),
            y=alt.Y(f"{selected_metric}:Q", title=selected_metric),
            color=alt.Color("학교:N", title="학교"),
            tooltip=["학교", "조사연도", selected_metric]
        ).interactive()
        st.altair_chart(chart1, use_container_width=True)
    else:
        st.info("개별 그래프를 표시할 데이터가 없습니다.")

    # CSV 다운로드 버튼
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("CSV로 데이터 다운로드", data=csv, file_name=f"{selected_metric}.csv", mime="text/csv")

    ##############################################
    # 구분별 평균 추세 그래프 (경쟁대학, 대경사학, 본교)
    ##############################################
    if os.path.exists(UNIV_CODE_FILE):
        df_univ = load_univ_codes(UNIV_CODE_FILE)

        # 머지: df와 df_univ를 "학교" 기준으로 연결
        if "학교" in df.columns:
            df_merged = pd.merge(df, df_univ, on="학교", how="left")
        else:
            st.info("데이터에 '학교' 열이 없습니다. 구분별 통계 그래프 생성 불가.")
            df_merged = df.copy()

        # 각 행에 대해 여러 구분을 리스트로 할당
        df_merged["구분_list"] = df_merged.apply(assign_categories, axis=1)

        # explode로 행 분리
        df_exploded = df_merged.explode("구분_list")
        df_exploded = df_exploded[df_exploded["구분_list"].notnull()]

        if not df_exploded.empty and selected_metric in df_exploded.columns:
            group_df = df_exploded.groupby(["조사연도", "구분_list"])[selected_metric].mean().reset_index()

            chart2 = alt.Chart(group_df).mark_line(point=True).encode(
                x=alt.X("조사연도:O", title="조사연도"),
                y=alt.Y(f"{selected_metric}:Q", title=f"{selected_metric} 평균"),
                color=alt.Color("구분_list:N", title="구분"),
                tooltip=["구분_list", "조사연도", f"{selected_metric}"]
            ).interactive()

            st.markdown("### 구분별 평균 추세 (경쟁대학, 대경사학, 본교)")
            st.altair_chart(chart2, use_container_width=True)
        else:
            st.warning("구분별 통계를 표시할 데이터가 없습니다.")
    else:
        st.info("대학코드 파일(대학코드.xlsx)을 찾을 수 없습니다. 구분별 통계 그래프를 생성할 수 없습니다.")
