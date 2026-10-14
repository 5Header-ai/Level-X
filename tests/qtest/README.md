# QTest — BLOCKED / NOT RUN

В точном baseline `cc4302a99167abec69b714cfd00c38caece7e7de` нет файлов qtest,
директории tests, qtest accelerator или параметра `-qtest` в проверенных исходниках.
Это существенно отличается от обычного upstream QEMU. Проверка воспроизводима:

```sh
git ls-tree -r --name-only cc4302a99167abec69b714cfd00c38caece7e7de
python tools/audit_baseline.py /path/to/Inferno --output reports/baseline-audit.json
```

Пустые stub-тесты, возвращающие PASS, не добавлены. Восстановление всей QTest
инфраструктуры не включено в локальные изменения графики. После получения
Level X baseline нужно выяснить, содержит ли он пригодный QTest harness;
если нет — отдельный коммит зависимости с обоснованием и ревью.

Спецификация будущих тестов реального устройства:

| Проверка | Действия и ожидаемое наблюдение |
|---|---|
| Инициализация | Synthetic DT + RAM + DART + ADP; CONTROL_VERSION = 0x70045, FRAME_SIZE = заданный размер |
| MMIO | Aligned 32-bit read/write GP0/GP1 stride/dimensions, INT_ENABLE; readback, отсутствие изменения соседнего GP |
| Shadow | Те же подтверждённые регистры через +0x200000; identical readback |
| Invalid MMIO | Невыровненные/1/2/8-byte обращения не должны повреждать состояние; фактический QEMU access result зафиксировать |
| DMA | Две несмежные RAM-страницы через реальную DART таблицу, совпадение scanout bytes |
| Fault | Unmapped/read-protected вторая страница: нет представления частично прочитанного кадра, fault DART регистр/IRQ |
| IRQ | В существующей модели IRQ0 = (int_status & int_enable) != 0; masked/unmasked/W1C |
| Reset | Pending display BH, reset, повторный кадр; отсутствие старых указателей и утечек |
| Shutdown | Повторный create/reset/destroy, проверка таймеров/BH/mutex под sanitizers |
| Очереди AGX | BLOCKED: контракт command packets/fences/completion не установлен |

Не подменять эти тесты тестами C callback. Абсолютные MMIO/IRQ/SID должны
поступать из synthetic fixture либо согласованного source-only DT описания.
