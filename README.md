# TOTO LOG — 로그인 없는 개인 해외 스포츠 베팅 기록장

Flask + PostgreSQL 기반의 1인용 경기별 기록 앱입니다. 로그인은 없으며, 베팅 기록은 `DATABASE_URL`에 연결한 PostgreSQL 서버에 저장됩니다.

## 기능
- 경기별 기록 추가/수정/삭제
- 총 베팅액, 환급액, 순손익, ROI, 미정산액 및 적중률
- 기간 조회와 월별 통계
- CSV 백업
- CSRF 보호 및 `/health` 상태 확인

## 무료 배포 권장 구성
- 앱 서버: Render Free Web Service
- 데이터베이스: Neon Free PostgreSQL
- Render의 무료 웹 서비스는 15분 동안 요청이 없으면 잠들 수 있고, 다시 접속할 때 깨어나는 데 약 1분 걸릴 수 있습니다. Render 무료 PostgreSQL은 생성 후 30일이 지나면 만료되므로, Render 무료 DB를 장기 데이터 저장소로 사용하지 마세요. 공식 안내: https://render.com/docs/free
- Neon 무료 플랜의 현재 용량/사용량은 가입 시 공식 플랜 안내에서 확인하세요: https://neon.com/pricing

## 배포 절차
1. 이 폴더의 파일을 GitHub 저장소에 업로드합니다.
2. https://console.neon.tech/ 에서 무료 프로젝트를 생성합니다.
3. Neon 대시보드에서 PostgreSQL 연결 문자열을 복사합니다. 가능하면 pooled connection string을 사용합니다. 비밀번호가 포함된 연결 문자열을 공개 저장소나 코드에 올리지 마세요.
4. https://dashboard.render.com/ 에서 **New + → Blueprint**를 선택하고 GitHub 저장소를 연결합니다. `render.yaml`은 무료 웹 서비스를 만듭니다.
5. Render 서비스의 **Environment** 설정에서 `DATABASE_URL`을 추가하고 Neon 연결 문자열을 붙여 넣습니다. 저장 후 재배포합니다.
6. Render가 발급한 `https://...onrender.com` 주소를 열고 `/health`가 `{"status":"ok"}`를 반환하는지 확인합니다. 가계부 첫 화면에서 테스트 기록을 추가하고 CSV 백업까지 확인하세요.

## 매우 중요한 공개 접근 주의사항
로그인을 제거했기 때문에 Render URL을 아는 사람은 누구나 기록을 열람하고 추가/수정/삭제할 수 있습니다. URL이 비공개라는 것은 접근 제어가 아닙니다. 개인 기록에 민감한 정보나 계정 정보를 적지 마세요. 로그인 없이 쓰려면 URL을 공유하지 말고, 가능하면 Cloudflare Access 등 별도 접근 보호를 추가하세요.

## 데이터 보존
- Render 무료 웹 서비스의 로컬 파일시스템은 임시 저장소입니다. SQLite 파일을 운영 DB로 사용하지 마세요.
- PostgreSQL에 저장된 기록은 앱 재배포 후에도 유지되지만, 무료 서비스에는 한도와 장애/정책 변경 위험이 있습니다. 정기적으로 CSV 백업을 내려받아 별도 보관하세요.
- 최초 실행 시 `db.create_all()`이 테이블을 만듭니다.

## 로컬 실행
Python 3.11+ 권장. `DATABASE_URL`을 설정하지 않으면 개발용 SQLite 파일을 사용합니다. 로컬 개발 데이터는 Render 배포 데이터와 별개입니다.

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

이 앱은 수동 기록/정산 관리용이며 외부 사이트의 베팅이나 결제를 자동화하지 않습니다.
