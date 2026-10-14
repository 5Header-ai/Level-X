# Ход работ

## Этап 0 — baseline

- Реализовано: отдельный репозиторий, зафиксирован upstream и предполагаемые точки интеграции.
- Проверено: SHA, VERSION, подключение DisplayPipe через DART в исходниках.
- Не проверено: сборка Inferno под Windows, загрузка iOS и физический iPhone.
- Блокеры: отсутствует актуальный source-only Level X и отдельный guest-стенд.
- Далее: аудит связанных проектов, переносимый C-модуль, тесты и opt-in патч.
- Коммит этапа: первый коммит этого репозитория; точный идентификатор доступен в `git log --reverse`.
- Файлы: `BASELINE.md`, `PROGRESS.md`, `.gitignore`, `.gitattributes`.

Полный GPU/Metal не реализован. Наличие scanout не будет считаться завершением проекта.

## Этап 1 — независимый код памяти и минимальная software-операция

- Реализовано: `include/levelx_scanout.h`, `src/levelx_scanout.c`, транзакционное
  чтение через DMA callback, ограничения размеров/адресов, reset, заполнение rect.
- Проверено: `tests/unit/test_scanout.c`, `tools/test.py`; 9 групп PASS на MSVC
  /W4 /WX /RTC1 и отдельно AddressSanitizer. 1960 граничных сочетаний и 1000
  циклов выделения/освобождения. Логи: `reports/unit-msvc*.json`.
- Не проверено: настоящий DART, QEMU MMIO, IRQ, гостевые очереди, Metal.
- Коммит: `feat: add bounded DMA scanout core and executable C tests` (см. git log).
- Что можно интегрировать: автономный C API; аппаратный протокол GPU отсутствует.
- Блокеры: full Inferno build требует отсутствующих GNU/MSYS2 и библиотек;
  аппаратные проверки требуют отдельного стенда. Самостоятельные задачи продолжаются.

## Этап 2 — аудит и архитектура

- Исследованы pinned исходники всех шести перечисленных проектов и история
  релевантных изменений; hashes и сравнения сохранены в docs/hardware.
- Факты: существующий display path и DART interfaces; QTest отсутствует.
- Гипотезы, не принятые как факт: reims-vgpu как A13 replacement; переносимость
  PCC handshake другой ветки; применимость Asahi firmware ABI к A13/iOS14.
- Изменены/добавлены: BASELINE, GPU-ARCHITECTURE, LICENSES, licenses,
  docs/hardware, docs/interfaces, docs/decisions, docs/experiments,
  tools/audit_baseline.py и reports/baseline-audit.json.
- Основной блокер: AGX protocol не восстановлен. Level1 остаётся PARTIAL.
- Коммиты ранее: baseline `2bce81ab11947d071f2f8768de012267a98adcc8`,
  C-модуль `0f4d944d78962b5b455333c2f6ae0cbaabb7c92f`.
- Коммит этапа: `docs: audit pinned graphics sources and define protocol boundaries`.

## Этап 3 — интеграционные patches и проверка переноса

- Реализованы: opt-in QOM flag, адаптер к прежнему DART AddressSpace и три trace events.
- Patch commits относительно upstream: `c45f2f5d5fbdc2e707ebdf227177fd9baa4cd3f9`
  и `9278a7d8e5d42a4d52d154ec25bf0368516347e0`.
- Проверено: clean git am/apply, exact standalone-source identity, whitelist
  5 путей, whitespace, обратное применение. `reports/transfer.json` — PASS.
- Штатный trace generator принял события. QEMU build и guest runtime — NOT RUN.
- Добавлены INTEGRATION.md, patches/inferno, tests/integration/verify_transfer.py,
  tests/qtest/README.md, reports/transfer.json.
- Интегрировать можно для review/build в отдельной копии; production merge не выполнен.
- Коммит этапа: `feat: package opt-in Inferno patches and verify transfer and rollback`.

## Этап 4 — собственная гостевая диагностика

- Добавлено `tests/integration/ios`: UIKit приложение, Metal compute (256 точных
  uint результатов), render clear + texture readback (64 pixels), JSON отчёт.
- Не подменяет Metal CPU-вычислением; CPU только проверяет ожидаемые значения.
- Проверены plist и shell syntax. Xcode compile, iPhone и VM: NOT RUN.
- Timeout ожидания command completion 10 секунд; отмена GPU work не обещается.
- Коммит этапа: `test: add native iOS Metal compute and render readback probe`.
- Дальше: база reuse-кандидатов, попытка полной сборки Inferno, manifest и export.

## Этап 5 — повторное использование и работа с трассами

- Создан REUSABLE-TECHNOLOGIES.md: pinned репозитории, просмотренные файлы,
  лицензии, зависимости, результаты авторов отдельно от наших проверок,
  решения по адаптации. Исследованы также открытые PR/issues и GitLab источники.
- Добавлен анализатор метаданных на штатном QEMU simpletrace, без собственного
  binary parser. Пять интеграционных synthetic fixture tests PASS.
- Новые файлы: registry, docs/hardware/reuse-search.json, tools/analyze_trace.py,
  tests/integration/test_trace_reader.py, reports/trace-reader.json,
  docs/experiments/trace-analysis.md.
- Прямой перенос APV page tables/guest protocol в AGX отклонён. metal2vulkan
  остаётся кандидатом backend, m1n1/Mesa — decoder/ABI reference.
- Коммит этапа: `feat: reuse QEMU trace reader and record pinned technology decisions`.
