import sqlite3

import template
import os
from pymediainfo import MediaInfo


class Material:
    media_type_mapping = {
        "video": "video",
        "audio": "music",
        "image": "photo"
    }

    def __init__(self, file) -> None:
        self._data = template.material()
        self.metetype = ''
        self.track_type = ''
        self.width = 0
        self.height = 0
        self.duration = 0
        self.extra_info = ''
        self.file_Path = ''
        self.id = self._data['id']
        self.content_material = {}

        if type(file) == str:
            if os.path.exists(file):
                self.to_material(file)
                if self.track_type == 'video':
                    self.content_material = self.video()
                elif self.track_type == 'audio':
                    self.content_material = self.audio()
                elif self.track_type == 'image':
                    self.content_material = self.image()
            else:
                self.metetype = 'text'
                self.track_type = 'text'
                self.content_material = self.text()
                self.content_material['content'] = self.content_material['content'].replace('默认文本', file)
        elif type(file) == dict:
            # 估计用不到
            self.load_material(file)
        else:
            pass  # 素材类型错误

    @property
    def data(self):
        self._data['metetype'] = self.metetype
        self._data['width'] = self.width
        self._data['height'] = self.height
        self._data['duration'] = self.duration
        self._data['extra_info'] = self.extra_info
        self._data['file_Path'] = self.file_Path
        return self._data

    @data.setter
    def data(self, value):
        self._data = value

    def to_material(self, file_path):
        """
            通过文件的方式去加载为素材
        """
        media_info = MediaInfo.parse(file_path).to_data()["tracks"][1]
        self.track_type = media_info['track_type'].lower()
        self.metetype = self.media_type_mapping[self.track_type]
        if "width" in media_info:
            self.width = media_info['width']
            self.height = media_info['height']
        if self.metetype == "video" or self.metetype == "music":
            self.duration = media_info['duration'] * 1000
        elif self.metetype == "photo":
            self.duration = int(self.get_photo_duration(file_path))
            if self.duration is not None:
                self.duration *= 1000
            else:
                self.duration = 5000000
        self.extra_info = file_path.split("/")[-1]
        self.extra_info = file_path.split("\\")[-1]
        self.file_Path = file_path

    def load_material(self, material):
        """
            将剪映的素材加载为素材类
        """
        self.metetype = material['metetype']
        self.width = material['width']
        self.height = material['height']
        self.duration = material['duration']
        self.extra_info = material['extra_info']
        self.file_Path = material['file_Path']
        self.id = material['id']

    def video(self):
        v = template.video()
        v["duration"] = self.duration
        v["height"] = self.height
        v["local_material_id"] = self.id
        v["material_name"] = self.extra_info
        v["path"] = self.file_Path
        v["type"] = self.metetype
        v["width"] = self.width
        return v

    def audio(self):
        a = template.audio()
        a["duration"] = self.duration
        a["local_material_id"] = self.id
        a["name"] = self.extra_info
        a["path"] = self.file_Path
        a["type"] = "extract_" + self.metetype
        return a

    def image(self):
        i = template.video()
        i["duration"] = self.duration
        i["height"] = self.height
        i["local_material_id"] = self.id
        i["material_name"] = self.extra_info
        i["path"] = self.file_Path
        i["type"] = "photo"
        i["width"] = self.width
        return i

    def text(self):
        t = template.text()
        return t

    def change_color(self, hex):
        self.content_material['text_color'] = hex
        r = int(hex[1:3], 16)
        g = int(hex[3:5], 16)
        b = int(hex[5:7], 16)
        color1 = "<color=(1.000000, 1.000000, 1.000000, 1.000000)>"
        color2 = F'<color=({round(r / 255, 6):.6f}, {round(g / 255, 6):.6f}, {round(b / 255, 6):.6f}, 1.000000)>'
        self.content_material['content'] = self.content_material['content'].replace(color1, color2)

    def get_photo_duration(self, png_path):
        # 从路径中提取出文件名（包含扩展名）
        file_name = os.path.basename(png_path)
        # 去除扩展名，得到文件名部分
        file_name_without_extension = os.path.splitext(file_name)[0]
        # 使用 "-" 分割文件名，获取 scene_id
        scene_id = file_name_without_extension.split("-")[0]
        # 连接到 SQLite 数据库
        db = sqlite3.connect('./novel.db')
        # 创建游标
        cursor = db.cursor()

        # 查询数据库获取 audio_duration
        query = f"SELECT audio_duration FROM novel_scene WHERE scene_id = '{scene_id}'"
        cursor.execute(query)
        result = cursor.fetchone()

        # 关闭游标和数据库连接
        cursor.close()
        db.close()

        if result:
            audio_duration = result[0]
            return audio_duration
        else:
            return None