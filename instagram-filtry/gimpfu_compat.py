# -*- coding: utf-8 -*-
"""
Warstwa zgodności: udaje moduł `gimpfu` z GIMP 2.x na potrzebie filtrów
Instagram (Marco Crippa, 2013), tłumacząc użyte w nich wywołania `pdb.*`
na API GIMP 3 (gi.repository.Gimp).

Obsługuje tylko te funkcje, których używają skrypty w katalogu `filtry/`.
Nieznane wywołanie kończy się czytelnym błędem, a nie cichym pominięciem.

Licencja: GNU GPL v3 lub nowsza (jak całość pakietu).
"""

import random

import gi
gi.require_version("Gimp", "3.0")
gi.require_version("Gegl", "0.4")
from gi.repository import Gimp, Gegl

__all__ = ["pdb", "register", "main", "gimp"]

# Numeracja z GIMP 2.8 -> enumy GIMP 3. Tryby *_LEGACY dają ten sam wygląd
# mieszania co w GIMP 2.8 (m.in. „Overlay” z 2.8, który działał jak Soft light).
_LAYER_MODES = {
    0: Gimp.LayerMode.NORMAL_LEGACY,
    1: Gimp.LayerMode.DISSOLVE,
    2: Gimp.LayerMode.BEHIND_LEGACY,
    3: Gimp.LayerMode.MULTIPLY_LEGACY,
    4: Gimp.LayerMode.SCREEN_LEGACY,
    5: Gimp.LayerMode.OVERLAY_LEGACY,
    6: Gimp.LayerMode.DIFFERENCE_LEGACY,
    7: Gimp.LayerMode.ADDITION_LEGACY,
    8: Gimp.LayerMode.SUBTRACT_LEGACY,
    9: Gimp.LayerMode.DARKEN_ONLY_LEGACY,
    10: Gimp.LayerMode.LIGHTEN_ONLY_LEGACY,
    11: Gimp.LayerMode.HSV_HUE_LEGACY,
    12: Gimp.LayerMode.HSV_SATURATION_LEGACY,
    13: Gimp.LayerMode.HSL_COLOR_LEGACY,
    14: Gimp.LayerMode.HSV_VALUE_LEGACY,
    15: Gimp.LayerMode.DIVIDE_LEGACY,
    16: Gimp.LayerMode.DODGE_LEGACY,
    17: Gimp.LayerMode.BURN_LEGACY,
    18: Gimp.LayerMode.HARDLIGHT_LEGACY,
    19: Gimp.LayerMode.SOFTLIGHT_LEGACY,
    20: Gimp.LayerMode.GRAIN_EXTRACT_LEGACY,
    21: Gimp.LayerMode.GRAIN_MERGE_LEGACY,
    22: Gimp.LayerMode.COLOR_ERASE_LEGACY,
}

# GIMP 2: 0 FG, 1 BG, 2 WHITE, 3 TRANSPARENT, 4 PATTERN.
# GIMP 3 wstawił CIELAB_MIDDLE_GRAY pod numer 2, więc trzeba przemapować.
_FILL_TYPES = {
    0: Gimp.FillType.FOREGROUND,
    1: Gimp.FillType.BACKGROUND,
    2: Gimp.FillType.WHITE,
    3: Gimp.FillType.TRANSPARENT,
    4: Gimp.FillType.PATTERN,
}


def _mode(m):
    return _LAYER_MODES[int(m)]


def _img(x):
    """Odpakowuje ImageProxy do Gimp.Image."""
    return getattr(x, "_image", x)


def _color(c):
    """Krotka (r, g, b) 0–255 albo Gegl.Color -> Gegl.Color."""
    if isinstance(c, Gegl.Color):
        return c
    # Uwaga: Gegl.Color.new("rgb(58,10,89)") czyta liczby jako 0–1, nie 0–255;
    # zapis szesnastkowy jest interpretowany jako 8-bitowe sRGB, jak w GIMP 2.
    r, g, b = (max(0, min(255, int(v))) for v in c[:3])
    return Gegl.Color.new("#%02x%02x%02x" % (r, g, b))


def _run_gegl(drawable, operation, **props):
    flt = Gimp.DrawableFilter.new(drawable, operation, "")
    cfg = flt.get_config()
    for k, v in props.items():
        cfg.set_property(k, v)
    flt.update()
    drawable.merge_filter(flt)


def _run_pdb(name, image, drawable):
    proc = Gimp.get_pdb().lookup_procedure(name)
    cfg = proc.create_config()
    cfg.set_property("run-mode", Gimp.RunMode.NONINTERACTIVE)
    cfg.set_property("image", image)
    cfg.set_core_object_array("drawables", [drawable])
    res = proc.run(cfg)
    if res.index(0) != Gimp.PDBStatusType.SUCCESS:
        raise RuntimeError("Procedura %s zakończyła się błędem" % name)


class _Pdb(object):
    """Podzbiór `pdb` z gimpfu, przetłumaczony na GIMP 3."""

    # --- kontekst ---------------------------------------------------------
    def gimp_context_get_foreground(self):
        return Gimp.context_get_foreground()

    def gimp_context_set_foreground(self, c):
        Gimp.context_set_foreground(_color(c))

    def gimp_context_get_background(self):
        return Gimp.context_get_background()

    def gimp_context_set_background(self, c):
        Gimp.context_set_background(_color(c))

    def gimp_context_set_gradient(self, grad):
        Gimp.context_set_gradient(grad)

    # --- warstwy ----------------------------------------------------------
    def gimp_layer_group_new(self, img):
        return Gimp.GroupLayer.new(_img(img), None)

    def gimp_image_insert_layer(self, img, layer, parent, position):
        _img(img).insert_layer(layer, parent, int(position))

    def gimp_layer_new(self, img, w, h, layer_type, name, opacity, mode):
        return Gimp.Layer.new(_img(img), name, int(w), int(h),
                              Gimp.ImageType(int(layer_type)), float(opacity),
                              _mode(mode))

    def gimp_layer_new_from_drawable(self, drawable, img):
        return Gimp.Layer.new_from_drawable(drawable, _img(img))

    def gimp_item_set_name(self, item, name):
        item.set_name(name)

    gimp_layer_set_name = gimp_item_set_name

    def gimp_image_set_active_layer(self, img, layer):
        _img(img).set_selected_layers([layer])

    def gimp_layer_set_mode(self, layer, mode):
        layer.set_mode(_mode(mode))

    def gimp_layer_set_opacity(self, layer, opacity):
        layer.set_opacity(float(opacity))

    def gimp_image_merge_down(self, img, layer, merge_type):
        return _img(img).merge_down(layer, Gimp.MergeType(int(merge_type)))

    def gimp_layer_create_mask(self, layer, mask_type):
        return layer.create_mask(Gimp.AddMaskType(int(mask_type)))

    def gimp_layer_add_mask(self, layer, mask):
        layer.add_mask(mask)

    def gimp_image_get_layer_position(self, img, layer):
        return _img(img).get_item_position(layer)

    # --- zaznaczenie ------------------------------------------------------
    def gimp_selection_all(self, img):
        Gimp.Selection.all(_img(img))

    def gimp_selection_bounds(self, img):
        # GIMP 3: (ok, non_empty, x1, y1, x2, y2); gimpfu: (non_empty, x1, y1, x2, y2)
        return tuple(Gimp.Selection.bounds(_img(img))[1:])

    def gimp_selection_clear(self, img):
        Gimp.Selection.none(_img(img))

    def gimp_selection_invert(self, img):
        Gimp.Selection.invert(_img(img))

    def gimp_selection_shrink(self, img, steps):
        Gimp.Selection.shrink(_img(img), int(steps))

    def gimp_selection_grow(self, img, steps):
        Gimp.Selection.grow(_img(img), int(steps))

    def gimp_selection_feather(self, img, radius):
        Gimp.Selection.feather(_img(img), float(radius))

    def gimp_image_select_rectangle(self, img, op, x, y, w, h):
        _img(img).select_rectangle(Gimp.ChannelOps(int(op)), x, y, w, h)

    def gimp_image_select_ellipse(self, img, op, x, y, w, h):
        _img(img).select_ellipse(Gimp.ChannelOps(int(op)), x, y, w, h)

    def gimp_image_select_round_rectangle(self, img, op, x, y, w, h, rx, ry):
        _img(img).select_round_rectangle(Gimp.ChannelOps(int(op)),
                                         x, y, w, h, rx, ry)

    def gimp_image_select_item(self, img, op, item):
        _img(img).select_item(Gimp.ChannelOps(int(op)), item)

    # --- wypełnianie, schowek ----------------------------------------------
    def gimp_edit_fill(self, drawable, fill_type):
        drawable.edit_fill(_FILL_TYPES[int(fill_type)])

    def gimp_edit_copy(self, drawable):
        return Gimp.edit_copy([drawable])

    def gimp_edit_paste(self, drawable, paste_into):
        layers = Gimp.edit_paste(drawable, bool(paste_into))
        return layers[0] if layers else None

    def gimp_floating_sel_attach(self, layer, drawable):
        Gimp.floating_sel_attach(layer, drawable)

    def gimp_edit_blend(self, drawable, blend_mode, paint_mode, gradient_type,
                        opacity, offset, repeat, reverse, supersample,
                        max_depth, threshold, dither, x1, y1, x2, y2):
        # 0 FG->BG (RGB), 1 FG->BG (HSV), 2 FG->przezroczysty, 3 bieżący gradient
        if blend_mode == 0:
            Gimp.context_set_gradient_fg_bg_rgb()
        elif blend_mode == 1:
            Gimp.context_set_gradient_fg_bg_hsv_cw()
        elif blend_mode == 2:
            Gimp.context_set_gradient_fg_transparent()
        Gimp.context_set_paint_mode(_mode(paint_mode))
        Gimp.context_set_opacity(float(opacity))
        Gimp.context_set_gradient_repeat_mode(Gimp.RepeatMode(int(repeat)))
        Gimp.context_set_gradient_reverse(bool(reverse))
        drawable.edit_gradient_fill(Gimp.GradientType(int(gradient_type)),
                                    float(offset), bool(supersample),
                                    int(max_depth), float(threshold),
                                    bool(dither), x1, y1, x2, y2)

    # --- korekcje kolorów (wartości z GIMP 2 w skali 0–255) -----------------
    def gimp_curves_spline(self, drawable, channel, num_points, points):
        drawable.curves_spline(Gimp.HistogramChannel(int(channel)),
                               [p / 255.0 for p in points])

    def gimp_levels(self, drawable, channel, low_in, high_in, gamma,
                    low_out, high_out):
        drawable.levels(Gimp.HistogramChannel(int(channel)),
                        low_in / 255.0, high_in / 255.0, True, float(gamma),
                        low_out / 255.0, high_out / 255.0, True)

    def gimp_brightness_contrast(self, drawable, brightness, contrast):
        drawable.brightness_contrast(brightness / 127.0, contrast / 127.0)

    def gimp_hue_saturation(self, drawable, hue_range, hue_offset, lightness,
                            saturation):
        drawable.hue_saturation(Gimp.HueRange(int(hue_range)), float(hue_offset),
                                float(lightness), float(saturation), 0.0)

    def gimp_desaturate_full(self, drawable, mode):
        # GIMP 2.8: 0 lightness, 1 luminosity (= LUMA w GIMP 3), 2 average
        drawable.desaturate(Gimp.DesaturateMode(int(mode)))

    # --- gradienty ----------------------------------------------------------
    def gimp_gradient_new(self, name):
        return Gimp.Gradient.new(name)

    def gimp_gradient_delete(self, grad):
        grad.delete()

    def gimp_gradient_segment_set_left_color(self, grad, seg, color, opacity):
        c = _color(color).duplicate()
        r, g, b, _ = c.get_rgba()
        c.set_rgba(r, g, b, opacity / 100.0)
        grad.segment_set_left_color(int(seg), c)

    def gimp_gradient_segment_set_right_color(self, grad, seg, color, opacity):
        c = _color(color).duplicate()
        r, g, b, _ = c.get_rgba()
        c.set_rgba(r, g, b, opacity / 100.0)
        grad.segment_set_right_color(int(seg), c)

    def gimp_gradient_segment_range_split_midpoint(self, grad, start, end):
        grad.segment_range_split_midpoint(int(start), int(end))

    # --- filtry (wtyczki z GIMP 2 zastąpione operacjami GEGL) ----------------
    def plug_in_gradmap(self, img, drawable):
        _run_pdb("plug-in-gradmap", _img(img), drawable)

    def plug_in_rgb_noise(self, img, drawable, independent, correlated,
                          n1, n2, n3, n4):
        # Tak samo jak zgodność „plug-in-rgb-noise” w GIMP 2.10.
        _run_gegl(drawable, "gegl:noise-rgb",
                  independent=bool(independent), correlated=bool(correlated),
                  linear=True, gaussian=True,
                  red=float(n1), green=float(n2), blue=float(n3),
                  alpha=float(n4), seed=random.randint(0, 2 ** 31 - 1))

    def plug_in_mblur(self, img, drawable, blur_type, length, angle,
                      center_x, center_y):
        if int(blur_type) != 0:
            raise NotImplementedError("plug_in_mblur: obsługiwany tylko typ liniowy (0)")
        _run_gegl(drawable, "gegl:motion-blur-linear",
                  length=float(length), angle=float(angle))

    def __getattr__(self, name):
        raise AttributeError(
            "Warstwa zgodności GIMP 2 -> 3 nie obsługuje pdb.%s" % name)


class ImageProxy(object):
    """
    Obraz przekazywany do starych filtrów. disable_undo()/enable_undo()
    są puste – wtyczka sama otacza filtr jedną grupą cofania (w GIMP 2
    disable_undo kasowało historię cofania i efekt był nieodwracalny).
    """

    def __init__(self, image):
        self._image = image

    def disable_undo(self):
        pass

    def enable_undo(self):
        pass

    def __getattr__(self, name):
        return getattr(self._image, name)


pdb = _Pdb()
gimp = None  # skrypty Instagram nie używają modułu `gimp`

# Rejestr wypełniany przez register() wywoływane w skryptach filtrów.
REGISTERED = []


def register(proc_name, blurb, help_text, author, copyright, date, menu_path,
             image_types, params, results, function, **kwargs):
    REGISTERED.append({
        "name": proc_name, "blurb": blurb, "help": help_text,
        "author": author, "copyright": copyright, "date": date,
        "menu_path": menu_path, "image_types": image_types,
        "params": params, "function": function,
    })


def main():
    pass
