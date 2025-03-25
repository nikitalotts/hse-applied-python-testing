# Тестирование

Для разделения домашних заданий №3 и №4 было создано два репозиторий. Данный репозиторий является наследником [этого](https://github.com/nikitalotts/hse-applied-python-fastapi/ ), код и логика проекта в нем точно такая же, добавлены только файлы для тестирования. Инструкцию по запуску всего проекта и описание эндпоинтов можно найти в `SERVICE_README.md`.

## Юнит и функциональные тесты

### Запуск

Для запуска тестов нужно проделать следующее (все делается в корневой директории проекта):

1. Установить зависимости
```pip install -r requirements.txt```

2. Создать файл `.env` в корневой директории проекта с содержанием:

```
DB_HOST = 'postgres'
DB_PASS = 'changeme'
DB_PORT = '5432'
DB_NAME = 'ShortUrlDB'
DB_USER = 'changeme'
JWT_SECRET_KEY = 'changeme'
PASSWORD_SECRET_KEY = 'changeme'
MESSAGE_BROKER_URL = 'redis://redis:6379'
LINK_TTL_IN_DAYS = 5
CODE_GENERATION_ATTEMPTS = 5
CODE_GENERATION_SECRET = 'changeme'
SHORT_CODE_LENGTH = '9'
SITE_IP = 'localhost'
```

3. Запустить тесты
```
# сперва обязательно нужно запустить тесты
coverage run -m pytest tests

# получить статистику по покрытию
coverage report

# экспорт статистики в html (итоговая уже лежит в htmlcov/index.html - нужно его просто открыть в браузере)
coverage html
```

Сами файлы юнит-тестов расположены в дирекотрии `tests/`.

### Покрытие

Получившиеся итоговое покрытие юнит-тестами составляет 97%:

```
Name                                     Stmts   Miss  Cover
------------------------------------------------------------
src\admin\router.py                         16      0   100%
src\auth\backend.py                         11      0   100%
src\auth\models.py                          16      0   100%
src\auth\router.py                           7      0   100%
src\auth\schemas.py                         11      0   100%
src\auth\users.py                           25      0   100%
src\config.py                               20      0   100%
src\database.py                             15      0   100%
src\links\dependencies.py                    6      0   100%
src\links\exception_handlers.py              7      0   100%
src\links\exceptions.py                     23      0   100%
src\links\models.py                         19      0   100%
src\links\router.py                         70     18    74%
src\links\schemes.py                        67      0   100%
src\links\service.py                       132     11    92%
src\links\utils.py                          26      0   100%
src\main.py                                 34      3    91%
src\tasks\app.py                             4      0   100%
src\tasks\tasks.py                          25      0   100%
tests\test_admin_router.py                  47      0   100%
tests\test_auth_backend.py                  47      0   100%
tests\test_auth_users.py                    36      1    97%
tests\test_database.py                      34      0   100%
tests\test_links_dependencies.py            17      0   100%
tests\test_links_exception.py               13      0   100%
tests\test_links_exception_handlers.py      30      0   100%
tests\test_links_router.py                 272      5    98%
tests\test_links_schemas.py                 50      0   100%
tests\test_links_service.py                189      1    99%
tests\test_links_utils.py                   94      0   100%
tests\test_main.py                          46      4    91%
tests\test_tasks_tasks.py                   42      0   100%
------------------------------------------------------------
TOTAL                                     1451     43    97%
```

Функциональные тесты покрывают все эндпоинты (CRUD, redirect и другие) с большинством возможных сценариев (корректные запросы и нет). Файл тестов расположен в `tests/test_links_router.py`.

## Нагрузочное тестирование

### Запуск

Для нагрузочного тестирования использовался Locust. Для того, чтобы его запустить, нужно:

1. Запустить докер:
`docker compose build && docker compose up -d`

2. Запустить Locust

`locust --host=http://127.0.0.1:8000 --only-summary --print-stat --headless -f tests/locustfile.py -u 100 -r 100 -t 3m`

### Результаты

У автора на его локальной машине получились следующие результаты:

С кэшированием запросов - 44.77 RPS: 
```
Type     Name                                                                          # reqs      # fails |    Avg     Min     Max    Med |   req/s  failures/s   
--------|----------------------------------------------------------------------------|-------|-------------|-------|-------|-------|-------|--------|-----------   
POST     /auth/jwt/login                                                                  100     0(0.00%) |   2732     212    9831   1600 |    0.56        0.00   
POST     /auth/register                                                                   100     0(0.00%) |   9156    1820   16279   8900 |    0.56        0.00   
GET      /health                                                                          195     0(0.00%) |     10       1     158      4 |    1.09        0.00   
DELETE   /links/[short_code]                                                              792     0(0.00%) |    124       9    5551     23 |    4.41        0.00   
GET      /links/[short_code]                                                             3189     1(0.03%) |     70       5    5858     13 |   17.76        0.01   
PUT      /links/[short_code]                                                              759     3(0.40%) |    120      12    7121     28 |    4.23        0.02   
GET      /links/[short_code]/stats                                                        373     0(0.00%) |     75       3    3545     15 |    2.08        0.00   
GET      /links/all                                                                       387     0(0.00%) |     94       6    2824     19 |    2.15        0.00   
GET      /links/my-statistics                                                             193     1(0.52%) |     75       8    1086     21 |    1.07        0.01   
GET      /links/search                                                                    193     1(0.52%) |     86       3    2634     16 |    1.07        0.01   
POST     /links/shorten                                                                  1760     1(0.06%) |    217       9    7368     21 |    9.80        0.01   
--------|----------------------------------------------------------------------------|-------|-------------|-------|-------|-------|-------|--------|-----------   
         Aggregated                                                                      8041     7(0.09%) |    259       1   16279     18 |   44.77        0.04   
```

Без кэширования - 35.58 RPS: 
```
Type     Name                                                                          # reqs      # fails |    Avg     Min     Max    Med |   req/s  failures/s   
--------|----------------------------------------------------------------------------|-------|-------------|-------|-------|-------|-------|--------|-----------   
POST     /auth/jwt/login                                                                  100     0(0.00%) |   4168     273   18071   2900 |    0.56        0.00   
POST     /auth/register                                                                   100     0(0.00%) |  16250    2423   28283  16000 |    0.56        0.00   
GET      /health                                                                          175     0(0.00%) |     59       1     675     22 |    0.98        0.00   
DELETE   /links/[short_code]                                                              619     6(0.97%) |    561      10    5353    370 |    3.46        0.03   
GET      /links/[short_code]                                                             2467     4(0.16%) |    352       4    6678    150 |   13.78        0.02   
PUT      /links/[short_code]                                                              594     5(0.84%) |    746       8   13051    490 |    3.32        0.03   
GET      /links/[short_code]/stats                                                        306     2(0.65%) |    373       5    4274    160 |    1.71        0.01   
GET      /links/all                                                                       309     0(0.00%) |    555      16    8118    360 |    1.73        0.00   
GET      /links/my-statistics                                                             147     0(0.00%) |    579       7    3637    320 |    0.82        0.00   
GET      /links/search                                                                    161     3(1.86%) |    453       5    6652    300 |    0.90        0.02   
POST     /links/shorten                                                                  1393     6(0.43%) |    817       7   14209    430 |    7.78        0.03   
--------|----------------------------------------------------------------------------|-------|-------------|-------|-------|-------|-------|--------|-----------   
         Aggregated                                                                      6371    26(0.41%) |    831       1   28283    260 |   35.58        0.15   
```

Таким образом, кэширование добавляет ~10 RPS.
