#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Filtry Instagram dla GIMP 3.x.

22 filtry Marco Crippy (2013, pierwotnie dla GIMP 2.8 / gimpfu) uruchamiane
w GIMP 3 przez warstwę zgodności `gimpfu_compat.py`. Oryginalne skrypty leżą
bez zmian w katalogu `filtry/`; ten plik wczytuje je, zbiera wywołania
register() i rejestruje każdy filtr jako procedurę GIMP 3:

    Filtry → Instagram → 1977, Amaro, … , X-Pro II

Licencja: GNU GPL v3 lub nowsza. Filtry: © 2013 Marco Crippa, GPL v2+.
"""

import glob
import os
import re
import sys

import gi
gi.require_version("Gimp", "3.0")
from gi.repository import Gimp, GLib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import gimpfu_compat  # noqa: E402

# Skrypty robią `from gimpfu import *` – podstawiamy warstwę zgodności.
sys.modules["gimpfu"] = gimpfu_compat


def _load_filters():
    """Wykonuje skrypty z filtry/ i zwraca {nazwa_procedury: wpis}."""
    gimpfu_compat.REGISTERED.clear()
    for path in sorted(glob.glob(os.path.join(HERE, "filtry", "*.py"))):
        with open(path, encoding="utf-8") as f:
            code = compile(f.read(), path, "exec")
        exec(code, {"__name__": "filtr_" + os.path.basename(path)[:-3],
                    "__file__": path})
    filters = {}
    for entry in gimpfu_compat.REGISTERED:
        # gimp_instagram_XproII -> python-fu-instagram-xproii
        slug = re.sub(r"^gimp_instagram_", "", entry["name"]).lower()
        proc_name = "python-fu-instagram-" + re.sub(r"[^a-z0-9]+", "-", slug)
        filters[proc_name] = entry
    return filters


FILTERS = _load_filters()


def _error(procedure, message):
    return procedure.new_return_values(Gimp.PDBStatusType.EXECUTION_ERROR,
                                       GLib.Error(message))


class InstagramFiltry(Gimp.PlugIn):

    def do_query_procedures(self):
        return list(FILTERS.keys())

    def do_set_i18n(self, name):
        return False

    def do_create_procedure(self, name):
        entry = FILTERS[name]
        menu_dir, label = entry["menu_path"].rsplit("/", 1)
        procedure = Gimp.ImageProcedure.new(self, name,
                                            Gimp.PDBProcType.PLUGIN,
                                            self.run, None)
        procedure.set_image_types(entry["image_types"])
        procedure.set_sensitivity_mask(Gimp.ProcedureSensitivityMask.DRAWABLE)
        procedure.set_menu_label(label)
        procedure.add_menu_path(menu_dir)
        procedure.set_documentation(entry["blurb"], entry["help"], None)
        procedure.set_attribution(entry["author"], entry["copyright"],
                                  entry["date"])
        return procedure

    def run(self, procedure, run_mode, image, drawables, config, data):
        entry = FILTERS[procedure.get_name()]
        if len(drawables) != 1:
            return _error(procedure, "Zaznacz dokładnie jedną warstwę, "
                                     "do której ma zostać zastosowany filtr.")
        drawable = drawables[0]

        before = set(l.get_id() for l in image.get_layers())
        saved_sel = None
        Gimp.context_push()
        image.undo_group_start()
        try:
            # Filtry liczą rozmiar nowych warstw z granic zaznaczenia, więc
            # aktywne zaznaczenie psułoby wynik – zapamiętujemy je i czyścimy.
            if not Gimp.Selection.is_empty(image):
                saved_sel = Gimp.Selection.save(image)
                Gimp.Selection.none(image)

            entry["function"](gimpfu_compat.ImageProxy(image), drawable)
        except Exception as e:  # noqa – żadnych niezłapanych wyjątków
            for layer in image.get_layers():
                if layer.get_id() not in before:
                    image.remove_layer(layer)
            return _error(procedure, "Filtr %s nie powiódł się: %s"
                          % (entry["menu_path"].rsplit("/", 1)[1], e))
        finally:
            if saved_sel is not None and saved_sel.is_valid():
                image.select_item(Gimp.ChannelOps.REPLACE, saved_sel)
                image.remove_channel(saved_sel)
            image.undo_group_end()
            Gimp.context_pop()

        Gimp.displays_flush()
        return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, None)


if __name__ == "__main__":
    Gimp.main(InstagramFiltry.__gtype__, sys.argv)
