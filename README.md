# TUIM - Jackob tu był

docker compose up --build

docker compose exec backend python manage.py migrate

docker compose exec backend python manage.py createsuperuser

#

nwm czy redis jest nam potrzebny, mi do ci/cd nie

w wolnej chwili ogarnę deployowanie sobie z githuba na dockera
-KB

Chcecie mieć własne branche i pchać na main, czy main na stabilną wersję i pchamy na development?
#