import streamlit as st
import pandas as pd
import datetime
import requests
import xml.etree.ElementTree as ET


# 설정: API 키, 매핑 정보
API_KEY = "0c25a284ecaa5cd995de76792b639d98"
GENRE_MAPPING = {
    "Film-Noir": "느와르",
    "Documentary": "다큐멘터리",
    "War": "전쟁",
    "Drama": "드라마",
    "Musical": "뮤지컬",
    "Crime": "범죄",
    "Animation": "애니메이션",
    "Mystery": "미스터리",
    "Romance": "멜로/로맨스",
    "Western": "서부",
    "Thriller": "스릴러",
    "Comedy": "코미디",
    "Fantasy": "판타지",
    "Adventure": "모험",
    "Children's": "아동",
    "Action": "액션",
    "Sci-Fi": "SF",
    "Horror": "호러"
}


# 함수: 데이터 불러오기
def load_data():
    """Load movies, ratings, and users datasets."""
    movies = pd.read_csv('movies.dat', sep='::', engine='python', header=None, 
                         names=['movieId', 'title', 'genres'], encoding='latin1')
    ratings = pd.read_csv('ratings.dat', sep='::', engine='python', header=None, 
                          names=['userId', 'movieId', 'rating', 'timestamp'], encoding='latin1')
    users = pd.read_csv('users.dat', sep='::', engine='python', header=None, 
                        names=['userId', 'gender', 'age', 'occupation', 'zip_code'], encoding='latin1')
    users = users[users['age'] != 1]  # 이상치 제거
    return movies, ratings, users # 데이터프레임 반환

# 함수: 연령대별 사용자 필터링
def get_age_group(age, users):
    """Filter users by age group."""
    age_groups = [(10, 20), (20, 30), (30, 40), (40, 50), (50, 60)] # 연령대 범위 설정
    for start_age, end_age in age_groups:
        if start_age <= age < end_age:
            return users[(users['age'] >= start_age) & (users['age'] < end_age)] # 연령대 필터링
    return None # 입력한 연령대에 맞는 정보가 없는 경우 None 반환

# 함수: 장르별 평점 계산
def calculate_genre_ratings(users_group, ratings, movies):
    users_data = users_group.merge(ratings, on='userId').merge(movies, on='movieId') # 연령별 사용자가 평가한 영화 데이터에 영화 정보 병합
    users_data['genres'] = users_data['genres'].str.split('|') # 장르 분리
    users_data = users_data.explode('genres')
    return users_data.groupby('genres')['rating'].mean() # 장르별 평균 평점 계산

# 함수: 영화 정보 가져오기
def fetch_box_office_data():
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y%m%d') # 날짜 가져오기
    url = "http://kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.xml" # API 호출 URL
    params = {"key": API_KEY, "targetDt": yesterday} # API 호출 매개변수
    response = requests.get(url, params=params) 

    if response.status_code != 200: # 응답 안된 경우 빈 프레임 반환
        return pd.DataFrame()

    data = []   # 데이터 저장 리스트
    root = ET.fromstring(response.text) # XML 데이터 파싱
    for item in root.findall('.//dailyBoxOffice'):  # 각 영화 정보 추출
        movie_code = item.find('movieCd').text  # 영화 코드
        movie_name = item.find('movieNm').text  # 영화 이름
        rank = item.find('rank').text   # 순위
        sales = item.find('salesAmt').text # 매출액

        genre = fetch_movie_genre(movie_code) # 장르 정보 가져오기
        if genre:   
            data.append({"영화 이름": movie_name, "순위": rank, "매출액": int(sales), "장르": genre})
    return pd.DataFrame(data)   # 영화 정보 프레임 반환

# 함수: 영화 장르 정보 가져오기
def fetch_movie_genre(movie_code):
    url = "http://kobis.or.kr/kobisopenapi/webservice/rest/movie/searchMovieInfo.xml"
    params = {"key": API_KEY, "movieCd": movie_code}
    response = requests.get(url, params=params)
    if response.status_code == 200: # 응답 성공
        root = ET.fromstring(response.text) # XML 데이터 파싱
        genre = root.find('.//genreNm') # 장르 정보 추출
        return genre.text if genre is not None else None # 장르 반환
    return None

# 함수: 추천 영화 테이블 생성
def create_recommendation_table(box_office_data, genre_ratings):
    # 영화 정보 데이터프레임 생성
    box_office_data['영문 장르'] = box_office_data['장르'].map( 
        lambda x: next((k for k, v in GENRE_MAPPING.items() if v == x), None))  # 장르 매핑 적용
    box_office_data['연령대 평균 평점'] = box_office_data['영문 장르'].map(genre_ratings) # 장르별 평균 평점 매핑
    sorted_data = box_office_data.sort_values(by=['연령대 평균 평점', '매출액'], ascending=False)   # 정렬

    sorted_data = sorted_data.reset_index(drop=True)  # 기존 인덱스 리셋
    sorted_data['추천 순위'] = sorted_data.index + 1  # 추천 순위 추가

    final_data = sorted_data[['추천 순위', '영화 이름', '순위', '매출액', '장르', '연령대 평균 평점']] # 최종 데이터프레임 생성
    final_data.rename(columns={'순위': '기존 순위'}, inplace=False) # 컬럼명 변경

    return final_data


# 메인 함수
def main():
    st.title('🎬연령별 영화 추천 시스템')

    # 사용자 정보 입력
    name = st.text_input('이름을 입력하세요.')
    age = st.number_input('나이를 입력하세요.', min_value=15, max_value=70, value=20, step=1)
    
    # 확인 버튼
    if st.button('확인'):
        if name and age:
            movies, ratings, users = load_data() # 데이터 불러오기
            users_group = get_age_group(age, users) # 연령대별 사용자 필터링

            if users_group is not None:
                genre_ratings = calculate_genre_ratings(users_group, ratings, movies) # 장르별 평점 계산
                sorted_genre_ratings = genre_ratings.sort_values(ascending=False)   # 정렬
                st.write(f"📊 {name} 님의 연령대가 선호하는 영화 장르:")
                st.bar_chart(sorted_genre_ratings)
                
                # 영화 추천 로직 추가
                box_office_data = fetch_box_office_data()   # 박스오피스 데이터 가져오기
                if not box_office_data.empty:
                    final_data = create_recommendation_table(box_office_data, genre_ratings) # 추천 영화 테이블 생성

                    st.success(f'{name} 님을 위한 추천 영화 목록입니다!')
                    st.dataframe(final_data)   # 추천 영화 테이블 출력

                    # 데이터 저장
                    final_data.to_csv('추천 영화.csv', index=False)
                else:
                    st.error("박스오피스 데이터를 가져오는 데 실패했습니다.") # 예외처리
            else:
                st.error("입력하신 연령대에 해당하는 데이터가 없습니다.") # 예외처리
        else:
            st.error("모든 필드를 입력해주세요.") # 예외처리

# 메인 함수 실행
if __name__ == "__main__":
    main()
