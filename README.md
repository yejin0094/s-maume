# S-MAUMe 단계 5: PostgreSQL FAQ

FAQ 요청은 FastAPI가 PostgreSQL에서 직접 검색하며 AI Agent를 호출하지 않는다.
기존 AI Agent Echo 경로는 `/api/agent-test`로 그대로 유지된다.

## 최초 실행

모든 명령은 프로젝트 루트(`D:\projects\s-maume`)에서 실행한다.

```powershell
docker compose down
docker compose build
docker compose up -d
docker compose ps
```

Backend 컨테이너는 PostgreSQL healthcheck가 통과한 뒤 Alembic migration과
중복 방지 seed를 실행하고 FastAPI를 시작한다.

## 상태 및 API 확인

```powershell
curl.exe http://localhost:8000/health
curl.exe http://localhost:8001/health
curl.exe -X POST http://localhost:8000/api/agent-test `
  -H "Content-Type: application/json" `
  -d '{"message":"echo test"}'
curl.exe -X POST http://localhost:8000/api/faq/search `
  -H "Content-Type: application/json" `
  -d '{"question":"도서관 몇 시까지 해?"}'
```

PostgreSQL 준비 상태와 저장된 FAQ 수를 확인한다.

```powershell
docker compose exec postgres pg_isready -U smaume -d smaume
docker compose exec postgres psql -U smaume -d smaume -c "SELECT COUNT(*) FROM faqs;"
```

## Migration, seed, test

```powershell
docker compose exec backend alembic upgrade head
docker compose exec backend python seed.py
docker compose exec backend python seed.py
docker compose run --rm backend sh -c "pip install -r requirements-test.txt && pytest -q"
```

두 번째 seed 결과가 `0 row(s) created`이면 중복 방지가 정상이다.

## 로그와 데이터 영속성

```powershell
docker compose logs -f backend postgres ai-agent frontend
docker compose down
docker compose up -d
docker compose exec postgres psql -U smaume -d smaume -c "SELECT COUNT(*) FROM faqs;"
```

일반 `docker compose down`은 `postgres_data` 볼륨을 보존하므로 FAQ가 유지된다.
`docker compose down -v`는 이 볼륨까지 삭제하여 FAQ 데이터를 지울 수 있으므로
데이터를 의도적으로 초기화할 때만 사용한다.

React 테스트 화면은 <http://localhost:5173>에서 확인한다.
