# Filtry Instagram dla GIMP 3

22 filtry w stylu Instagrama oraz wtyczka „Obramowanie tekstu”. Pierwotnie powstały dla GIMP 2.8 (`gimpfu`), tutaj zostały przeniesione na **GIMP 3.x**.

**Filtry → Instagram:** 1977, Amaro, Apollo, Brannan, Earlybird, Gotham, Hefe, Hudson, Inkwell, Lofi, Lord Kelvin, Mayfair, Nashville, Poprocket, Rise, Sierra, Sutro, Toaster, Valencia, Walden, Willow, X-Pro II.

**Warstwa → Tekst → Dodaj obramowanie tekstu…** dodaje obrys o wybranej grubości i kolorze wokół warstwy tekstowej.

Każdy filtr tworzy na górze obrazu grupę warstw „&lt;Nazwa&gt; Effect” i nie zmienia oryginalnej warstwy. Efekt można dopracować, zmieniając krycie warstw w grupie albo je ukrywając.

Przetestowano na GIMP 3.2.6 (Windows 11).

## Instalacja (Windows)

Pobierz ZIP z zakładki Releases, rozpakuj go i uruchom `install.ps1` (prawy przycisk → „Uruchom za pomocą programu PowerShell”). Skrypt sam znajdzie katalog GIMP 3.x:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

Możesz też zainstalować ręcznie: skopiuj foldery `instagram-filtry` i `text-border` do `%APPDATA%\GIMP\3.2\plug-ins\` (w GIMP 3.0 jest tam `3.0` zamiast `3.2`), a potem uruchom GIMP ponownie.

Linux/macOS: skopiuj foldery do `~/.config/GIMP/3.x/plug-ins/` i nadaj prawo wykonania:
`chmod +x instagram-filtry/instagram-filtry.py text-border/text-border.py`.

## Jak to działa

GIMP 3 nie ma już modułu `gimpfu`, a jego API Pythona jest zupełnie inne. Zamiast przepisywać ręcznie 22 filtry (łatwo przy tym zmienić ich wygląd), pakiet zawiera warstwę zgodności:

```
instagram-filtry/
  instagram-filtry.py   # wtyczka GIMP 3 – rejestruje wszystkie filtry
  gimpfu_compat.py      # udaje gimpfu: tłumaczy ~50 wywołań pdb.* z GIMP 2 na GIMP 3
  filtry/               # oryginalne skrypty Marco Crippy, bez zmian
text-border/
  text-border.py        # „Obramowanie tekstu” przepisane natywnie na GIMP 3
```

Nowy filtr w stylu GIMP 2 (z tymi samymi wywołaniami `pdb.*`) wystarczy wrzucić do `filtry/`, a pojawi się w menu.

Co tłumaczy warstwa zgodności:
- **Tryby warstw** z GIMP 2.8 są mapowane na tryby `*_LEGACY` w GIMP 3, więc mieszanie kolorów wygląda tak jak dawniej.
- **Krzywe, poziomy i jasność/kontrast** przelicza ze skali 0–255 na 0–1 używaną w GIMP 3.
- **Kolory** przekazuje jako 8-bitowe sRGB, w zapisie `#rrggbb`.
- **Typy wypełnienia** przemapowuje, bo GIMP 3 zmienił ich numerację.
- **`plug-in-rgb-noise` i `plug-in-mblur`**, których już nie ma, zastępuje filtrami GEGL `gegl:noise-rgb` i `gegl:motion-blur-linear`.

## Różnice względem wersji dla GIMP 2

- **Jedno Ctrl+Z cofa cały filtr.** W GIMP 2 skrypty wyłączały historię cofania i efektu nie dało się cofnąć.
- **Aktywne zaznaczenie nie psuje wyniku.** Oryginały liczyły rozmiar nowych warstw z granic zaznaczenia. Teraz filtr działa na całym obrazie, a zaznaczenie wraca na miejsce po zakończeniu.
- **Kolory pierwszego planu i tła zostają nietknięte.**
- **Komunikat zamiast cichego błędu.** Gdy nie zaznaczono żadnej warstwy, filtr wyświetla komunikat, a po nieudanym filtrze nie zostają żadne warstwy.
- **Szum i rozmycie ruchu** pochodzą z GEGL. Wynik jest bardzo podobny, ale nie identyczny co do piksela.
- **Grubość ramki może się różnić o 1 px.** Python 3 dzieli liczby inaczej niż Python 2, więc przy niektórych szerokościach zdjęcia ramka wychodzi o 1 px szersza.
- **Obramowanie tekstu** czyści zaznaczenie po wykonaniu. Oryginał zostawiał zaznaczony obrys.

## Testy

Test integracyjny uruchamia wszystkie filtry w GIMP-ie bez okna i zapisuje siatkę podglądów `podglad.png`:

```
"%LOCALAPPDATA%\Programs\GIMP 3\bin\gimp-console-3.2.exe" -i --batch-interpreter python-fu-eval -b "exec(open(r'C:\ścieżka\do\repo\tests\gimp_integration.py', encoding='utf-8').read())" --quit
```

Zmienne `TEST_PHOTO` i `TEST_OUT` wskazują zdjęcie testowe i katalog wyjściowy.

## Autorzy i licencja

- Filtry Instagram: © 2013 Marco Crippa, GNU GPL v2 lub nowsza.
- Obramowanie tekstu: © 2016 Rebecca Breu, GNU GPL v3.
- Port na GIMP 3 i warstwa zgodności: Marek Zettel, 2026.

Całość jest udostępniona na licencji **GNU GPL v3** (plik `LICENSE`).
