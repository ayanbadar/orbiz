.PHONY: up down build logs migrate superuser shell test restart

up:
	docker compose up --build -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f backend celery_worker celery_beat

migrate:
	docker compose exec backend python manage.py migrate

superuser:
	docker compose exec backend python manage.py createsuperuser

shell:
	docker compose exec backend python manage.py shell

test:
	docker compose exec backend python manage.py test

restart:
	docker compose restart backend celery_worker celery_beat
