import streamlit as st
import pandas as pd
import datetime
import requests
import xml.etree.ElementTree as ET

# 설정: API 키와 파일 경로
KOBIS_API_KEY = "0c25a284ecaa5cd995de76792b639d98"

# 함수: 박스오피스 데이터 가져오기
def fetch_box_office_data(api_key, target_date):
    """KOBIS API를 사용하여 박스오피스 데이터를 가져옵니다."""
    url = "http://kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.xml"
    params = {"key": api_key, "targetDt": target_date}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return ET.fromstring(response.text)
    else:
        st.error(f"박스오피스 데이터를 가져오는 중 오류 발생: {response.status_code}")
        return None

# 함수: 영화 상세 정보 가져오기
def fetch_movie_details(api_key, movie_code):
    """KOBIS API를 사용하여 영화 상세 정보를 가져옵니다."""
    url = "http://kobis.or.kr/kobisopenapi/webservice/rest/movie/searchMovieInfo.xml"
    params = {"key": api_key, "movieCd": movie_code}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return ET.fromstring(response.text)
    else:
        st.error(f"영화 코드 {movie_code}의 상세 정보를 가져오는 중 오류 발생.")
        return None

# 함수: 장르별 평점 계산
def calculate_genre_ratings(users, ratings, movies, age_group):
    """장르별 평균 평점을 계산합니다."""
    users_filtered = users[(users['age'] >= age_group[0]) & (users['age'] < age_group[1])]
    if users_filtered.empty:
        return None
    merged_data = users_filtered.merge(ratings, on="userId").merge(movies, on="movieId")
    merged_data["genres"] = merged_data["genres"].str.split("|")
    merged_data = merged_data.explode("genres")
    return merged_data.groupby("genres")["rating"].mean().sort_values(ascending=False)

# 메인 함수
def main():
    st.title("🎥 연령별 영화 추천 시스템")
    
    # 사용자 입력
    name = st.text_input("이름을 입력하세요.")
    age = st.number_input("나이를 입력하세요.", min_value=15, max_value=80, value=20, step=1)

    # 확인 버튼
    if st.button("확인"):
        if name and age:
            # 데이터 불러오기
            movies = pd.read_csv('movies.dat', sep="::", engine="python", header=None, names=["movieId", "title", "genres"], encoding="latin1")
            ratings = pd.read_csv('ratings.dat', sep="::", engine="python", header=None, names=["userId", "movieId", "rating", "timestamp"], encoding="latin1")
            users = pd.read_csv('users.dat', sep="::", engine="python", header=None, names=["userId", "gender", "age", "occupation", "zip_code"], encoding="latin1")
            
            # 연령대 설정 및 평점 계산
            age_groups = [(10, 20), (20, 30), (30, 40), (40, 50), (50, 60)]
            user_age_group = next((group for group in age_groups if group[0] <= age < group[1]), None)

            if user_age_group:
                genre_ratings = calculate_genre_ratings(users, ratings, movies, user_age_group)
                if genre_ratings is not None:
                    st.write(f"🎬 {name} 님의 연령대({user_age_group[0]}대)가 선호하는 영화 장르:")
                    st.bar_chart(genre_ratings)

                    # 박스오피스 데이터 가져오기
                    target_date = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y%m%d")
                    box_office_data = fetch_box_office_data(KOBIS_API_KEY, target_date)

                    if box_office_data:
                        movie_list = []
                        for box_office in box_office_data.findall(".//dailyBoxOffice"):
                            movie_name = box_office.find("movieNm").text
                            movie_code = box_office.find("movieCd").text
                            movie_detail = fetch_movie_details(KOBIS_API_KEY, movie_code)
                            if movie_detail is not None:
                                genre = movie_detail.find(".//genreNm").text
                                movie_list.append({"영화 이름": movie_name, "장르": genre})

                        # 박스오피스 추천 출력
                        if movie_list:
                            movie_df = pd.DataFrame(movie_list)
                            st.write("📊 박스오피스 추천 영화:")
                            st.dataframe(movie_df)
                        else:
                            st.write("박스오피스 데이터가 없습니다.")
                else:
                    st.error("해당 연령대에 대한 평점 데이터를 찾을 수 없습니다.")
            else:
                st.error("유효한 연령대가 아닙니다.")
        else:
            st.error("모든 필드를 입력해주세요.")

# 실행
if __name__ == "__main__":
    main()
