# План интеграционных прогонов

Все перечисленные runtime-прогоны **NOT RUN**. Не подключать production fixture.

1. Записать точный SHA + dirty diff, configure flags, компилятор, зависимости,
   OS build, synthetic/owner-approved DT reg/interrupts/SID. Проверить build.
2. Pristine upstream и patched/off на одинаковом fixture: boot SpringBoard,
   UIKit, input, frame hashes, IRQ sequence, 10 reset/stop/start. Отсутствие
   визуальной разницы само по себе не заменяет проверку DMA/IRQ.
3. Patched/on: тот же прогон; 828×1792 и действительные смены размеров, обе GP,
   row padding, unknown/compressed format, max cap, адрес на границе 32-bit.
4. Реальная DART: discontiguous pages, fault на второй странице, read protection,
   invalidation, смена mapping; никаких identity-map fallback. Проверить status
   и fault IRQ, отсутствие partial frame. Подробные сценарии в tests/qtest.
5. Reset во время pending BH; повторная инициализация и уничтожение устройства
   под sanitizer/leak checker. Off/on VMState migration проверять с одинаковым
   значением feature flag; не объявлять migration поддержанной заранее.
6. Xcode build MetalProbe; physical iPhone11 и VM, одинаковый app artifact.
   Сохранить JSON с build/machine/device/compute/render status. При timeout
   завершить приложение; не запускать бесконечные попытки.
7. Только после Level4: textured triangles, depth/blend, buffer reuse, fences,
   multiple queues, stress и performance. Каждый сценарий с известным oracle.

Сохраняйте отдельные PASS/FAIL/NOT RUN/BLOCKED по сценарию и командами воспроизведения.
Физическое устройство и виртуальный стенд сравниваются как разные среды;
report не должен включать credentials, private keys, pair records или диски.
