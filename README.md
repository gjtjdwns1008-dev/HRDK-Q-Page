# 국가기술자격 Q-Page 자격정보집

국가기술자격 652종목(검정형 545 · 과정평가형 107)의 응시·취득·취업·임금 통계를
종목당 한 화면으로 제공하는 대국민 채널.
다이렉트 링크 : https://gjtjdwns1008-dev.github.io/HRDK-Q-Page/

## 구조

```
index.html      단일 파일 사이트(외부용). 자료가 안에 박혀 있어 서버가 필요 없다.
pdf/            종목별 화면 PDF. 파일명 = 종목코드.pdf (외부용 시트 출력물만)
tools/
  pdf_to_png.py   pdf/ → PNG 변환기 (pdftoppm+pngquant, 없으면 PyMuPDF 폴백)
robots.txt      검색엔진 수집 차단(시범 기간). 공식 전환 때 삭제.
```

`dist/` 와 PNG는 **커밋하지 않는다.** GitHub Actions가 빌드할 때 만들어
Pages 산출물로 배포하므로 저장소 이력에 이미지가 쌓이지 않는다.
변환된 PNG 주소: `https://<계정>.github.io/<저장소>/sheets/종목코드.png`

## 연간 갱신 순서

1. 엑셀: 새 연도 파일 만들기 → 입력파일 내보내기 → 입력파일 불러오기 → 순위·평균 다시 계산
2. 리본에서 HTML 생성(Z33) → **외부용** HTML을 `index.html` 이름으로 이 폴더에 덮어쓰기
3. One-page(외부용) 시트에서 종목별 PDF를 뽑아 `pdf/` 에 종목코드.pdf 로 저장
4. 커밋(업로드) → Actions가 알아서 PNG 변환 + 배포
5. Actions 실행 화면의 "화면 PNG 변환" 요약에서 실패 0건인지 확인

## 사전 1회 설정

깃허브 웹에서 Settings → Pages → Source = **GitHub Actions** 로 지정.
그 외 설정·비밀키 없음.
