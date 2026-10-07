#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Obramowanie tekstu – GIMP 3.x.

Port na GIMP 3 wtyczki „python_text_border” (© 2016 Rebecca Breu, GPLv3).
Tworzy obrys wokół zaznaczonej warstwy tekstowej (albo dowolnej warstwy
z przezroczystością) i scala go z tą warstwą.

Menu: Warstwa → Tekst → Dodaj obramowanie tekstu…

Licencja: GNU GPL v3 lub nowsza.
"""

import sys

import gi
gi.require_version("Gimp", "3.0")
gi.require_version("GimpUi", "3.0")
gi.require_version("Gegl", "0.4")
from gi.repository import Gimp, GimpUi, Gegl, GLib, GObject

PROC = "python-fu-text-border"


def _error(procedure, message):
    return procedure.new_return_values(Gimp.PDBStatusType.EXECUTION_ERROR,
                                       GLib.Error(message))


class TextBorder(Gimp.PlugIn):

    def do_query_procedures(self):
        return [PROC]

    def do_set_i18n(self, name):
        return False

    def do_create_procedure(self, name):
        Gegl.init(None)
        rw = GObject.ParamFlags.READWRITE
        procedure = Gimp.ImageProcedure.new(self, name, Gimp.PDBProcType.PLUGIN,
                                            self.run, None)
        procedure.set_image_types("RGB*")
        procedure.set_sensitivity_mask(Gimp.ProcedureSensitivityMask.DRAWABLE)
        procedure.set_menu_label("Dodaj obramowanie tekstu…")
        procedure.add_menu_path("<Image>/Layer/Text")
        procedure.set_documentation(
            "Tworzy obramowanie wokół tekstu.",
            "Tworzy obrys o zadanej grubości i kolorze wokół zaznaczonej "
            "warstwy tekstowej i scala go z nią.", None)
        procedure.set_attribution("Rebecca Breu (port GIMP 3: Marek Zettel)",
                                  "2016 Rebecca Breu, GPLv3", "2016")
        procedure.add_int_argument("thickness", "Grubość (px)",
                                   "Grubość obramowania w pikselach",
                                   1, 500, 5, rw)
        procedure.add_color_argument("colour", "Kolor", "Kolor obramowania",
                                     False, Gegl.Color.new("black"), rw)
        return procedure

    def run(self, procedure, run_mode, image, drawables, config, data):
        if run_mode == Gimp.RunMode.INTERACTIVE:
            GimpUi.init("text-border")
            dialog = GimpUi.ProcedureDialog(procedure=procedure, config=config,
                                            title="Obramowanie tekstu")
            dialog.fill(["thickness", "colour"])
            ok = dialog.run()
            dialog.destroy()
            if not ok:
                return procedure.new_return_values(Gimp.PDBStatusType.CANCEL,
                                                   None)

        if len(drawables) != 1 or not isinstance(drawables[0], Gimp.Layer):
            return _error(procedure, "Zaznacz dokładnie jedną warstwę tekstową.")
        text_layer = drawables[0]
        if text_layer.is_group_layer():
            return _error(procedure, "Wybrana warstwa jest grupą – zaznacz "
                                     "warstwę tekstową.")

        thickness = config.get_property("thickness")
        colour = config.get_property("colour")
        layer_name = text_layer.get_name()

        Gimp.context_push()
        image.undo_group_start()
        try:
            image.select_item(Gimp.ChannelOps.REPLACE, text_layer)
            Gimp.Selection.grow(image, thickness)

            border = Gimp.Layer.new(image, "border", image.get_width(),
                                    image.get_height(),
                                    Gimp.ImageType.RGBA_IMAGE, 100,
                                    Gimp.LayerMode.NORMAL)
            parent = text_layer.get_parent()
            position = image.get_item_position(text_layer)
            image.insert_layer(border, parent, position + 1)

            Gimp.context_set_foreground(colour)
            border.edit_fill(Gimp.FillType.FOREGROUND)
            Gimp.Selection.none(image)

            merged = image.merge_down(text_layer,
                                      Gimp.MergeType.EXPAND_AS_NECESSARY)
            merged.set_name(layer_name)
        except Exception as e:  # noqa – żadnych niezłapanych wyjątków
            return _error(procedure, "Nie udało się dodać obramowania: %s" % e)
        finally:
            image.undo_group_end()
            Gimp.context_pop()

        Gimp.displays_flush()
        return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, None)


if __name__ == "__main__":
    Gimp.main(TextBorder.__gtype__, sys.argv)
