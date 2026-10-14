# Сбор метаданных DisplayPipe

`tools/analyze_trace.py` использует **готовый parser `scripts/simpletrace.py`**
из выбранной доверенной копии Inferno. Парсер и формат не переписаны и не vendored.
Выбирайте checkout и `trace-events-all` именно той сборки, которая создала trace.
Импорт Python-модуля исполняет его код: путь должен указывать на ваш проверенный
исходный checkout. Формат binary simpletrace меняется между версиями QEMU.

При конфигурации добавьте `--enable-trace-backends=log,simple`. Патчи 1 и 2 нужны.
Создайте файл `levelx-events`:

```text
levelx_adp_mmio_read
levelx_adp_mmio_write
levelx_adp_scanout
```

К своей тестовой команде запуска добавьте:

```text
-trace events=levelx-events,file=levelx-trace.bin
-global apple-display-pipe-v4.levelx-checked-scanout=on
```

После штатного завершения процесса (чтобы trace buffer сбросился):

```sh
python tools/analyze_trace.py --inferno /path/to/Inferno \
  --events /path/to/build/trace-events-all --trace levelx-trace.bin \
  --output reports/local-trace.json
```

Отчёт содержит количества чтений/записей и offset/size, checked DMA outcomes
и размеры слоёв. Shadow address нормализуется ровно как в модели (одно вычитание
0x200000), raw offset сохраняется. IOVA, MMIO values и содержимое памяти в итоговом
JSON не сохраняются; исходный бинарный trace содержит все аргументы событий.
Для каждой таблицы ограничение 4096 различных групп; totals сохраняются даже
при переполнении, количество негруппированных событий указано отдельно.

`PARSED` означает прочитанные события, не исправную графику. `INCOMPLETE`
при dropped events, `NO_LEVELX_EVENTS` при отсутствии наших событий возвращают
exit 2. Повреждённый/несовместимый trace — exit 1, новый отчёт не создаётся
(старый output, если был, не является результатом неуспешного запуска).
Отсутствие checked-scanout event не доказывает отсутствие frames: off path,
compressed/unknown format могут не создавать это событие. Нет проверки IRQ,
фреймового изображения, очередей AGX или Metal.

Реально выполнен тест интеграции **со штатным parser** и собственными synthetic
binary fixtures: normal/rejected scanout, shadow MMIO, dropped/irrelevant events,
invalid header/truncated payload и bounded buckets. Команда:

```sh
python tests/integration/test_trace_reader.py /path/to/Inferno \
  --report reports/local-trace-reader.json
```

Пять тестов PASS. Реальный iOS trace здесь NOT RUN.
