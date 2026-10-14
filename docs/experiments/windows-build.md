# Проверка Windows-сборки

Среда развернута отдельно в workspace; системные PATH/Developer Mode не менялись.
Исходный Inferno после двух GPU patches имеет HEAD
`9278a7d8e5d42a4d52d154ec25bf0368516347e0`, tracked diff пуст.
MSYS2/UCRT64 GCC16.2.0, Meson1.12.1, Ninja1.13.2, Python3.14.8.
Полный список установленных пакетов: [msys2-packages](../../reports/msys2-packages.txt).
Он фиксирует использованную среду, но не обещает неизменность rolling mirrors.

MSYS2 base: `msys2-base-x86_64-20260927.tar.xz`, официальный
[архив](https://repo.msys2.org/distrib/x86_64/), SHA256 скачанного файла:
`ea2f31a0b6ade63914ce441ffb022f0f6aa96982bfefa2326460a26d5fb01322`.
Архив и toolchain не входят в source-поставку. Метод установки описан в
[MSYS2 documentation](https://www.msys2.org/docs/installer/);
QEMU [поддерживает MinGW/MSYS2](https://www.qemu.org/docs/master/about/build-platforms.html).

## Зависимости и исходники

В отдельном UCRT64 shell после штатного обновления MSYS2:

```sh
pacman -S --needed make git mingw-w64-ucrt-x86_64-gcc \
  mingw-w64-ucrt-x86_64-glib2 mingw-w64-ucrt-x86_64-pixman \
  mingw-w64-ucrt-x86_64-libpng mingw-w64-ucrt-x86_64-libtasn1 \
  mingw-w64-ucrt-x86_64-nettle mingw-w64-ucrt-x86_64-gnutls \
  mingw-w64-ucrt-x86_64-python mingw-w64-ucrt-x86_64-meson \
  mingw-w64-ucrt-x86_64-ninja mingw-w64-ucrt-x86_64-pkgconf
```

LZFSE отсутствовала в UCRT64 package repository. Использован официальный
[lzfse/lzfse](https://github.com/lzfse/lzfse) SHA
`e634ca58b4821d9f3d560cdc6df5dec02ffc93fd`, без изменений:

```sh
git -c core.autocrlf=false clone https://github.com/lzfse/lzfse.git lzfse
git -C lzfse checkout --detach e634ca58b4821d9f3d560cdc6df5dec02ffc93fd
make -C lzfse -j4
make -C lzfse install INSTALL_PREFIX=/ucrt64
```

Используйте отдельную MSYS2 root, если не хотите добавлять library в другую
рабочую среду. Для shell scripts исходники должны иметь LF. Новый Inferno clone
получен с `git -c core.autocrlf=false clone ...`, затем применены два патча.
`git submodule update --init util/mlib` получает записанный в baseline SHA
`d0fd65a8695218ffabf2aa543ce51ca3af69536f`. Meson получает pinned wraps:
dtc `b6910bec11614980a21e46fbccc35934b671bd81`,
keycodemapdb `f5772a62ec52591ff6870b7e8ef32482371f22c6`.

## Конфигурация и особенность этого хоста

В отдельном build directory внутри Inferno:

```sh
../configure --target-list=aarch64-softmmu --enable-pixman --enable-png \
  --enable-lzfse --enable-nettle --enable-gnutls --disable-guest-agent \
  --disable-werror --disable-tools --enable-trace-backends=log,simple
```

В этой ветке опция `--disable-docs` не существует. Она не включена в итоговую
команду. `--disable-werror` соответствует upstream CI; предупреждения baseline
не скрываются и не устраняются изменением посторонних подсистем.

Все dependency checks и генерация правил прошли. Последний postconf script
`scripts/symlink-install-tree.py` завершился ошибкой: на этом Windows-пользователе
недоступно создание symbolic links. Этот каталог нужен для run-from-build
install-tree. Отдельная проба `os.symlink` подтвердила WinError 1314.
Для компиляции C этот каталог не нужен. Обычный `ninja` повторяет неуспешный postconf.

Для **проверки компиляции** сохранены готовые правила под другим именем:

```sh
cp build.ninja build-compile.ninja
ninja -f build-compile.ninja -j4 qemu-system-aarch64.exe
ninja -f build-compile.ninja trace/trace-events-all
```

Исходники, compiler flags и generated rules не менялись. Это зафиксированный
снимок build graph без automatic regeneration; после изменений исходных build
описаний его нельзя продолжать использовать. Такой обход **не означает PASS
штатного configure/install workflow** и не подготавливает firmware lookup для
гостевого запуска. Он пригоден для source compilation и CLI registration tests.
После линковки неполный generated `qemu-bundle` переименован в
`qemu-bundle-incomplete` внутри этого build directory: иначе даже `--version`
завершался `Could not open .../qemu-bundle: Permission denied`. После переименования
все четыре CLI registration checks прошли, default flag действительно `off`.
Это только startup/help surfaces; устройство в VM не реализовывалось и iOS не запускалась.
В обычном окружении с symbolic links используйте успешный configure и `ninja`.

Фактический итог компиляции/линковки и runtime scope указан в
[build report](../../reports/windows-build.json). Бинарник с upstream artwork
не экспортируется. Guest fixture, production merge, iOS boot здесь отсутствуют.
