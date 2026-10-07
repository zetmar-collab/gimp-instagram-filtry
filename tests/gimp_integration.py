# -*- coding: utf-8 -*-
"""
Test integracyjny w GIMP 3 (bez okna). Wtyczki muszą być zainstalowane.
  gimp-console-3.2.exe -i --batch-interpreter python-fu-eval ^
      -b "exec(open(r'...\\tests\\gimp_integration.py', encoding='utf-8').read())" --quit
Zmienne środowiskowe:
  TEST_PHOTO   – zdjęcie testowe (domyślnie tapeta Windows)
  TEST_OUT     – katalog na podglądy (domyślnie %TEMP%\\instagram-test)
"""
import os
import tempfile

import gi
gi.require_version("Gimp", "3.0")
gi.require_version("Gegl", "0.4")
from gi.repository import Gimp, Gegl, Gio

PHOTO = os.environ.get("TEST_PHOTO", r"C:\Windows\Web\Wallpaper\ThemeA\img20.jpg")
OUT = os.environ.get("TEST_OUT", os.path.join(tempfile.gettempdir(), "instagram-test"))
os.makedirs(OUT, exist_ok=True)
OK = Gimp.PDBStatusType.SUCCESS
results = []


def check(name, cond, info=""):
    results.append(bool(cond))
    print("%s  %s %s" % ("PASS" if cond else "FAIL", name, info), flush=True)


def run(proc_name, img, drawables, **props):
    proc = Gimp.get_pdb().lookup_procedure(proc_name)
    if proc is None:
        return None, "brak procedury"
    cfg = proc.create_config()
    cfg.set_property("run-mode", Gimp.RunMode.NONINTERACTIVE)
    cfg.set_property("image", img)
    cfg.set_core_object_array("drawables", drawables)
    for k, v in props.items():
        cfg.set_property(k, v)
    res = proc.run(cfg)
    return res.index(0), (res.index(1) if res.length() > 1 else None)


def save(img, path):
    Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, img, Gio.File.new_for_path(path), None)


src = Gimp.file_load(Gimp.RunMode.NONINTERACTIVE, Gio.File.new_for_path(PHOTO))
src.scale(900, int(src.get_height() * 900 / src.get_width()))
W, H = src.get_width(), src.get_height()

procs = sorted(p for p in Gimp.get_pdb().query_procedures(
    "python-fu-instagram-.*", "", "", "", "", "", "", "") )
check("22 filtry zarejestrowane", len(procs) == 22, len(procs))

thumbs = [("oryginał", src.duplicate())]
for name in procs:
    img = src.duplicate()
    base = img.get_layers()[0]
    n_before = len(img.get_layers())
    st, err = run(name, img, [base])
    top = img.get_layers()[0]
    ok = (st == OK and len(img.get_layers()) == n_before + 1
          and top.is_group_layer() and len(top.get_children()) >= 2
          and base.is_valid())
    check(name, ok, err or "%s, %d warstw w grupie" % (top.get_name(), len(top.get_children())))
    thumbs.append((name.replace("python-fu-instagram-", ""), img))

# Siatka podglądów (składana w GIMP-ie, bez zewnętrznych bibliotek)
TW = 300
TH = int(H * TW / W)
cols = 4
rows = (len(thumbs) + cols - 1) // cols
sheet = Gimp.Image.new(cols * TW, rows * TH, Gimp.ImageBaseType.RGB)
bg = Gimp.Layer.new(sheet, "tło", cols * TW, rows * TH, Gimp.ImageType.RGB_IMAGE,
                    100, Gimp.LayerMode.NORMAL)
sheet.insert_layer(bg, None, 0)
bg.fill(Gimp.FillType.WHITE)
for i, (label, img) in enumerate(thumbs):
    flat = img.flatten()
    img.scale(TW, TH)
    lay = Gimp.Layer.new_from_drawable(img.get_layers()[0], sheet)
    sheet.insert_layer(lay, None, 0)
    lay.set_offsets((i % cols) * TW, (i // cols) * TH)
    txt = Gimp.TextLayer.new(sheet, label, Gimp.context_get_font(), 16, Gimp.Unit.pixel())
    sheet.insert_layer(txt, None, 0)
    txt.set_color(Gegl.Color.new("yellow"))
    txt.set_offsets((i % cols) * TW + 6, (i // cols) * TH + 4)
    img.delete()
sheet.flatten()
save(sheet, os.path.join(OUT, "podglad.png"))
print("PODGLAD", os.path.join(OUT, "podglad.png"))

# Zaznaczenie użytkownika: filtr działa na całym obrazie, zaznaczenie wraca
img = src.duplicate()
img.select_rectangle(Gimp.ChannelOps.REPLACE, 10, 10, 100, 50)
st, err = run("python-fu-instagram-1977", img, [img.get_layers()[0]])
b = Gimp.Selection.bounds(img)
grp = img.get_layers()[0]
check("zaznaczenie przywrócone, warstwy pełnego rozmiaru",
      st == OK and tuple(b[1:]) == (True, 10, 10, 110, 60)
      and grp.get_children()[-1].get_width() == W, (b, err))
check("brak dodatkowych kanałów", len(img.get_channels()) == 0)
img.delete()

# Bez zaznaczonej warstwy -> czytelny błąd, nic nie zostaje
img = src.duplicate()
st, err = run("python-fu-instagram-gotham", img, [])
check("bez warstwy -> błąd", st != OK and len(img.get_layers()) == 1, err)
img.delete()

# Obramowanie tekstu
img = src.duplicate()
t = Gimp.TextLayer.new(img, "Test", Gimp.context_get_font(), 80, Gimp.Unit.pixel())
img.insert_layer(t, None, 0)
t.set_offsets(100, 100)
w0, h0 = t.get_width(), t.get_height()
red = Gegl.Color.new("red")
st, err = run("python-fu-text-border", img, [t], thickness=6, colour=red)
top = img.get_layers()[0]
check("obramowanie tekstu: SUCCESS, jedna warstwa o tej samej nazwie",
      st == OK and len(img.get_layers()) == 2 and top.get_name() == "Test", err)
check("obramowanie tekstu: warstwa większa o grubość",
      top.get_width() >= w0 and top.get_height() >= h0, (top.get_width(), w0))
img.delete()

src.delete()
print("WYNIK: %d/%d PASS" % (sum(results), len(results)), flush=True)
