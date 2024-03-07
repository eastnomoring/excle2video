import time
import util as util


def canvase():
    return {
        "album_image": "",
        "blur": 0.0,
        "color": "",
        "id": util.generate_id(),
        "image": "",
        "image_id": "",
        "image_name": "",
        "source_platform": 0,
        "team_id": "",
        "type": "canvas_color"
    }


def sound_channel_mapping():
    return {
        "audio_channel_mapping": 0,
        "id": util.generate_id(),
        "is_config_open": False,
        "type": "none"
    }


def speed():
    return {
        "curve_speed": None,
        "id": util.generate_id(),
        "mode": 0,
        "speed": 1.0,
        "type": "speed"
    }


def image():
    return {
        "create_time": "",
        "duration": 0,  # 动画持续时间
        "extra_info": "",  # 图片的名字
        "file_Path": "",  # 图片完整路劲
        "height": 512,  # 图片高度
        "id": "",  # 唯一ID
        "import_time": "",
        "import_time_ms": "",
        "item_source": 1,
        "md5": "",
        "metetype": "photo",  # 类型
        "roughcut_time_range": {
            "duration": -1,
            "start": -1
        },
        "sub_time_range": {
            "duration": -1,
            "start": -1
        },
        "type": 0,
        "width": 512  # 图片宽度
    }


def video():
    return {
        "audio_fade": None,
        "cartoon_path": "",
        "category_id": "",
        "category_name": "local",
        "check_flag": 63487,
        "crop": {
            "lower_left_x": 0.0,
            "lower_left_y": 1.0,
            "lower_right_x": 1.0,
            "lower_right_y": 1.0,
            "upper_left_x": 0.0,
            "upper_left_y": 0.0,
            "upper_right_x": 1.0,
            "upper_right_y": 0.0
        },
        "crop_ratio": "free",
        "crop_scale": 1.0,
        "duration": 0,
        "extra_type_option": 0,
        "formula_id": "",
        "freeze": None,
        "gameplay": None,
        "has_audio": True,
        "height": 0,
        "id": util.generate_id(),
        "intensifies_audio_path": "",
        "intensifies_path": "",
        "is_unified_beauty_mode": False,
        "local_id": "",
        "local_material_id": "",
        "material_id": "",
        "material_name": "",
        "material_url": "",
        "matting": {
            "flag": 0,
            "has_use_quick_brush": False,
            "has_use_quick_eraser": False,
            "interactiveTime": [],
            "path": "",
            "strokes": []
        },
        "media_path": "",
        "object_locked": None,
        "path": "",
        "picture_from": "none",
        "picture_set_category_id": "",
        "picture_set_category_name": "",
        "request_id": "",
        "reverse_intensifies_path": "",
        "reverse_path": "",
        "source_platform": 0,
        "stable": None,
        "team_id": "",
        "type": "",  # "photo"
        "video_algorithm": {
            "algorithms": [],
            "deflicker": None,
            "motion_blur_config": None,
            "noise_reduction": None,
            "path": "",
            "time_range": None
        },
        "width": 0
    }


def material():
    return {
        "create_time": int(time.time()),
        "duration": 0,
        "extra_info": "",
        "file_Path": "",
        "height": 0,
        "id": util.generate_id(),
        "import_time": int(time.time()),
        "import_time_ms": int(time.time()) * 10 ^ 6,
        "md5": "",
        "metetype": "",
        "roughcut_time_range": {"duration": 0, "start": 0},
        "sub_time_range": {"duration": -1, "start": -1},
        "type": 0,
        "width": 0
    }


def track():
    return {
        "attribute": 0,
        "flag": 0,
        "id": util.generate_id(),
        "segments": [],
        "type": ""
    }


def segment():
    return {
        "cartoon": False,
        "clip": {
            "alpha": 1.0,
            "flip": {"horizontal": False, "vertical": False},
            "rotation": 0.0,
            "scale": {"x": 1.0, "y": 1.0},
            "transform": {"x": 0.0, "y": 0.0}
        },
        "common_keyframes": [],
        "enable_adjust": True,
        "enable_color_curves": True,
        "enable_color_wheels": True,
        "enable_lut": True,
        "enable_smart_color_adjust": False,
        "extra_material_refs": [
        ],
        "group_id": "",
        "hdr_settings": {"intensity": 1.0, "mode": 1, "nits": 1000},
        "id": util.generate_id(),
        "intensifies_audio": False,
        "is_placeholder": False,
        "is_tone_modify": False,
        "keyframe_refs": [],
        "last_nonzero_volume": 1.0,
        "material_id": "",
        "render_index": 0,
        "reverse": False,
        "source_timerange": {"duration": 0, "start": 0},
        "speed": 1.0,
        "target_timerange": {"duration": 0, "start": 0},
        "template_id": "",
        "template_scene": "default",
        "track_attribute": 0,
        "track_render_index": 0,
        "visible": True,
        "volume": 1.0
    }


def beat():
    return {
        "ai_beats": {
            "beats_path": "",
            "beats_url": "",
            "melody_path": "",
            "melody_percents": [0.0],
            "melody_url": ""
        },
        "enable_ai_beats": False,
        "gear": 404,
        "id": util.generate_id(),
        "mode": 404,
        "type": "beats",
        "user_beats": [],
        "user_delete_ai_beats": None
    }


def audio():
    return {
        "app_id": 0,
        "category_id": "",
        "category_name": "local",
        "check_flag": 1,
        "duration": 0,
        "effect_id": "",
        "formula_id": "",
        "id": util.generate_id(),
        "intensifies_path": "",
        "local_material_id": "",
        "music_id": util.generate_id(),
        "name": "Krubb Wenkroist - Bleach.mp3",
        "path": "D:/Music/Krubb Wenkroist - Bleach.mp3",
        "request_id": "",
        "resource_id": "",
        "source_platform": 0,
        "team_id": "",
        "text_id": "",
        "tone_category_id": "",
        "tone_category_name": "",
        "tone_effect_id": "",
        "tone_effect_name": "",
        "tone_speaker": "",
        "tone_type": "",
        "type": "extract_music",
        "video_id": "",
        "wave_points": []
    }


def text():
    return {
        "add_type": 0,
        "alignment": 2,
        "background_alpha": 1.0,
        "background_color": "",
        "background_height": 1.0,
        "background_horizontal_offset": 0.0,
        "background_round_radius": 0.0,
        "background_style": 0,
        "background_vertical_offset": 0.0,
        "background_width": 1.0,
        "bold_width": 0.0,
        "border_color": "",
        "border_width": 0.08,
        "check_flag": 7,
        "content": "<font id=\"\" path=\"D:/JianyingPro/4.2.0.10100/Resources/Font/SystemFont/zh-hans.ttf\"><color=(1.000000, 1.000000, 1.000000, 1.000000)><size=5.000000>[默认文本]</size></color></font>",
        "font_category_id": "",
        "font_category_name": "",
        "font_id": "",
        "font_name": "",
        "font_path": "D:/JianyingPro/4.2.0.10100/Resources/Font/SystemFont/zh-hans.ttf",
        "font_resource_id": "",
        "font_size": 10.0,
        "font_source_platform": 0,
        "font_team_id": "",
        "font_title": "none",
        "font_url": "",
        "fonts": [],
        "force_apply_line_max_width": False,
        "global_alpha": 1.0,
        "group_id": "",
        "has_shadow": False,
        "id": util.generate_id(),
        "initial_scale": 1.0,
        "is_rich_text": False,
        "italic_degree": 0,
        "ktv_color": "",
        "language": "",
        "layer_weight": 1,
        "letter_spacing": 0.0,
        "line_spacing": 0.02,
        "name": "",
        "preset_category": "",
        "preset_category_id": "",
        "preset_has_set_alignment": False,
        "preset_id": "",
        "preset_index": 0,
        "preset_name": "",
        "recognize_type": 0,
        "relevance_segment": [],
        "shadow_alpha": 0.8,
        "shadow_angle": -45.0,
        "shadow_color": "",
        "shadow_distance": 8.0,
        "shadow_point": {"x": 1.0182337649086284, "y": -1.0182337649086284},
        "shadow_smoothing": 1.0,
        "shape_clip_x": False,
        "shape_clip_y": False,
        "style_name": "",
        "sub_type": 0,
        "text_alpha": 1.0,
        "text_color": "＃FF69B4",
        "text_preset_resource_id": "",
        "text_size": 10,
        "text_to_audio_ids": [],
        "tts_auto_update": False,
        "type": "text",
        "typesetting": 0,
        "underline": False,
        "underline_offset": 0.22,
        "underline_width": 0.05,
        "use_effect_default_color": True,
        "words": []
    }


def material_animation():
    return {
        "animations": [],
        "id": util.generate_id(),
        "type": "sticker_animation"
    }
