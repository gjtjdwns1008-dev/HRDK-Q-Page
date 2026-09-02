# 국가기술자격 Q-Page 자격정보집

국가기술자격 652종목(검정형 545 · 과정평가형 107)의 응시·취득·취업·임금 통계를
종목당 한 화면으로 제공하는 대국민 채널.
다이렉트 링크 : <https://gjtjdwns1008-dev.github.io/HRDK-Q-Page/>

## 구조

```
q-page-outside_YYYY-MM-DD.html      외부공개 화면(단일 파일, 자료 내장).
                                    날짜가 가장 최신인 파일이 자동으로 홈(index)에 배포된다.
pdf/                                종목별 화면 PDF. 파일명 = 종목코드.pdf (외부용 시트 출력물만)
tools/
  pdf_to_png.py                     pdf/ → PNG 변환기 (pdftoppm+pngquant, 없으면 PyMuPDF 폴백)
robots.txt                          검색엔진 수집 차단(시범 기간). 공식 전환 때 삭제.
.github/workflows/build-qpage.yml   자동 배포 지시서(워크플로)
```

- `dist/` 와 PNG는 **커밋하지 않는다.** GitHub Actions가 빌드할 때 만들어
  Pages 산출물로 배포하므로 저장소 이력에 이미지가 쌓이지 않는다.
  변환된 PNG 주소: `https://<계정>.github.io/<저장소>/sheets/종목코드.png`
- 과거 날짜의 `q-page-outside_*.html` 은 지우지 않아도 된다.
  저장소에 남아 연도별 보관함이 되고, 웹에는 최신 1개만 노출된다.
- **안전장치**: `q-page-inside*` 또는 `*내부용*.html` 이 저장소에서 발견되면
  배포가 강제 중단된다(내부 자료 유출 방지). 실수로 올렸다면 삭제 커밋 후 재실행.

## 연간 갱신 순서

1. 엑셀: 새 연도 파일 만들기 → 입력파일 내보내기 → 입력파일 불러오기 → 순위·평균 다시 계산
2. 리본 **[외부공개 HTML]** → `out\q-page-outside_날짜.html` 생성
3. 그 파일을 이 저장소 **루트에 파일명 그대로** 업로드
4. One-page(외부용) 시트에서 종목별 PDF를 뽑아 `pdf/` 에 종목코드.pdf 로 저장
5. 커밋(업로드) → Actions가 알아서 PNG 변환 + 최신본 홈 배포
6. Actions 실행 화면의 요약에서 "홈(index)으로 배포된 파일"과 PNG 변환 실패 0건 확인

## 사전 1회 설정

깃허브 웹에서 Settings → Pages → Source = **GitHub Actions** 로 지정.
그 외 설정·비밀키 없음.
