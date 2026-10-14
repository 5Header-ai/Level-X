# Собственная диагностика Metal

Состояние: **NOT RUN** — нет macOS/Xcode/iOS-стенда. Исходники подготовлены;
компиляция Objective-C и запуск пока не подтверждены.

На Mac с Xcode: `sh tests/integration/ios/build.sh`. Либо создайте в Xcode iOS App
Objective-C с deployment target 14.0, замените исходники на `MetalProbe.m`,
используйте этот Info.plist без scene manifest, подключите Metal.framework.
Подпись и установку выполняйте своим существующим процессом; приватные ключи
не входят в репозиторий и не должны передаваться автору модуля.

Приложение автоматически выполняет один прогон вне UI-потока:

1. Записывает OS build и machine type, результат создания MTLDevice.
2. Компилирует собственный compute shader, выполняет 256 целочисленных операций.
3. После завершения команды сравнивает **все 256** результатов с CPU-эталоном.
4. Очищает private RGBA8 texture цветом magenta, копирует её GPU blit-командой
   в shared buffer и проверяет каждый пиксель 8×8 после completion.
5. Сохраняет `Documents/metal-probe.json`, показывает его и пишет в NSLog.

Отсутствие устройства, ошибка компиляции/очереди, timeout или неверные данные
никогда не дают PASS. Нет CPU fallback. Для каждого command buffer предел
ожидания 10 секунд. Timeout не отменяет команду GPU; завершите приложение
перед повтором. Системный зависший драйвер этим пользовательским таймаутом
не устраняется. Shader compilation сама по себе синхронная и не имеет
гарантированного таймаута в этом прототипе.

Выполните одинаковый app build на физическом iPhone 11 и отдельной VM, сначала
без патча, затем с флагом off/on. Сохраняйте отчёты вместе с SHA движка и
конфигурацией запуска; одинаковый MTLDevice name не доказывает эмуляцию.
Два PASS означают только конкретные compute/clear/readback операции, а не
полную совместимость Metal, CoreAnimation, коммерческих приложений или GPU ISA.

Источники API: [Apple compute sample](https://developer.apple.com/documentation/metal/performing-calculations-on-a-gpu),
[command model](https://developer.apple.com/library/archive/documentation/Miscellaneous/Conceptual/MetalProgrammingGuide/Cmd-Submiss/Cmd-Submiss.html).
