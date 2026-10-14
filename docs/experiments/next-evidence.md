# Очередь экспериментов после передачи

1. Получить зафиксированный source-only Level X commit + diff локальных правок,
   конфигурацию сборки и карту DT узлов graphics/display/DART. Не нужны диски,
   учётные записи, ключи или pair records.
2. Повторить audit и пересмотреть patch anchors. Сначала собрать флаг off;
   проверить запуск SpringBoard, ввод, rotation/display, reset и shutdown.
3. На отдельном собственном fixture включить trace MMIO и checked scanout;
   сравнить pixels, DMA faults и последовательность DisplayPipe IRQ.
4. Собрать и подписать MetalProbe существующим процессом владельца, получить
   baseline JSON на физическом iPhone 11 и VM. Nil MTLDevice — результат FAIL,
   а не повод возвращать поддельный device.
5. Если AGX driver не привязывается, исследовать DT, driver matching и init до
   любых command queues. Фиксировать MMIO address/size/value, порядок IRQ,
   mapping permissions, timestamps и OS/build. Не распространять private RAM dumps.
6. Доказать packet boundary, resource ownership и completion/fault для одной
   операции; затем software reference, затем optional host acceleration.

Физический iPhone в этой сессии недоступен. Никаких сравнительных показателей
производительности или результатов приложений не получено.
