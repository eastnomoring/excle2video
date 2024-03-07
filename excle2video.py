import os
import shutil
import traceback
import urllib.request
import time
import tkinter as tk
import wave
from tkinter import ttk
from tkinter import filedialog
import pandas as pd
from openai import OpenAI
import re
import sqlite3
import json
import base64
import requests
import pyttsx3
from datetime import datetime

from Draft import Draft
from material import Material

# 全局变量用于存储novel_id
global_novel_id = None

global_novel_name = None

global_output_file = None
# 设置OpenAI API密钥  sk-aarqWvwUk7RglB5m22F07aD75b1f4d3c892590999fC9E263

openai_api_key = None

client = None
# 建立数据库连接
faconne = sqlite3.connect('novel.db')
global_cursor = faconne.cursor()

# 创建主表（仅在表不存在时创建）
global_cursor.execute('''
    CREATE TABLE IF NOT EXISTS novel_info (
        novel_id INTEGER PRIMARY KEY,
        novel_name TEXT,
        novel_link TEXT,
        novel_author TEXT,
        novel_category TEXT,
        keywords TEXT
    )
''')

# 创建子表（仅在表不存在时创建）
global_cursor.execute('''
    CREATE TABLE IF NOT EXISTS novel_scene (
        scene_id INTEGER PRIMARY KEY AUTOINCREMENT,
        novel_id INTEGER,
        original_description TEXT,
        visual_description TEXT,
        positive_words TEXT,
        negative_words TEXT,
        image_path TEXT,
        hr_image_path TEXT,
        audio_path TEXT,
        audio_duration TEXT,
        FOREIGN KEY (novel_id) REFERENCES novel_info (novel_id)
    )
''')

# 提交事务
faconne.commit()
# 关闭数据库连接
faconne.close()

max_token = 384  # 假设最大token数为4096
fixed_prompts = [
    "我希望你能扮演一个优秀的作家，你有很强的阅读能力，学习能力。我会给你一篇稿件，你会根据我提供的稿件保持原文不变，仅仅根据上下文对稿件进行分段，按顺序将稿件依据场景进行划分。如果你理解了这一点要求，请等待我发送下一点要求",
    "我想让你扮演插画师的角色，你可以以绘画、绘图或数字媒体等形式，用于补充或增强文字内容，通过图像来传达信息、故事情节、情感或概念。如果你理解了这一点要求，请等待我发送下一点要求",
    "我想让你对小说内容进行分镜，根据分镜后的原文描述推断出的场景；推断和补充缺失或隐含的信息，包括但不限于：人物衣服，人物发型，人物发色，人物脸色，人物五官特点，人物体态，人物情绪，人物肢体动作等）、风格描述（包括但不限于：年代描述、空间描述、时间段描述、地理环境描述、天气描述）、物品描述（包括但不限于：动物、植物、食物、水果、玩具）、画面视角（包括但不限于：人物比例、镜头深度描述、观察角度描述）。，但不要过度。通过镜头语言描述，描绘更丰富的人物情绪和情感状态，你理解后通过句子生成一段新的描述内容。如果你明白了，请等待我给你发送下一点要求",
    "请注意输出格式改为成组的原文描述对应画面描述，将原文跟据场景或语境（若干句）分组：第n组：原文描述：原文…… 画面描述：根据原文句子创做的剧情内容…… 等等 ，要根据原文分组，不要缩减原文内容。如果你理解了这一要求，请确认并记住输出格式，然后等待我给你发送小说文本，按照输出格式输出"
]
positive_words_prompts = [
    "我想让你充当Stable diffusion人工智能程序的提示生成器。你的工作是提供详细的、有创意的描述，以激发 AI 独特而有趣的图像。你会从我提供的语句找到生成画面的关键词，书写格式应遵循基本格式，主体描述 （人物或动物）——人物表情—— 人物动作——  背景或场景描述 —— 综合描述 （包括画风主体、整体氛围、天气季节、灯光光照、镜头角度），如果语句是对话，心理描述，成语，谚语等需要还原成上述基本格式来进行描述，同时要考虑环境场景道具对人物行为的影响，人物主体使用1man，1woman，1boy，1girl，1old woman，1old man等的词去描述。当文本未明确人物主体时，要根据外貌描述，行为举止等来判断人物主体并生成相对应的提示词。"
    "请注意只需要提取关键词即可，并按照关键词在场景里的重要程度从高到底进行排序且用逗号隔开结尾也用逗号，主体放最前面，动作描写接在后面，背景或者场景描述放在中间，整体修饰放最后面；我给你的主题可能是用中文描述，你给出的提示词只用英文。",
    "StableDiffusion是一款利用深度学习的文生图模型，支持通过使用提示词来产生新的图像，描述要包含或省略的元素。我在这里引入StableDiffusion算法中的Prompt概念，又被称为提示符。下面的prompt是用来指导AI绘画模型创作图像的。它们包含了图像的各种细节，如人物的外观、背景、颜色和光线效果，以及图像的主题和风格。这些prompt的格式经常包含括号内的加权数字，用于指定某些细节的重要性或强调。例如，\"(masterpiece:1.5)\"表示作品质量是非常重要的，多个括号也有类似作用。此外，如果使用中括号，如\"{blue hair:white hair:0.3}\"，这代表将蓝发和白发加以融合，蓝发占比为0.3。"
    "以下是用prompt帮助AI模型生成图像的例子：masterpiece,(bestquality),highlydetailed,ultra-detailed,cold,solo,(1girl),(detailedeyes),(shinegoldeneyes),(longliverhair),expressionless,(long sleeves),(puffy sleeves),(white wings),shinehalo,(heavymetal:1.2),(metaljewelry),cross-lacedfootwear (chain),(Whitedoves:1.2) 仿照例子，给出一套详细描述以下内容的prompt。直接开始给出prompt不需要用自然语言描述："
]

negative_prompts = "EasyNegative,(nsfw:1.5),verybadimagenegative_v1.3, ng_deepnegative_v1_75t, (ugly face:0.8),cross-eyed,sketches, (worst quality:2), (low quality:2), (normal quality:2), lowres, normal quality, ((monochrome)), ((grayscale)), skin spots, acnes, skin blemishes, bad anatomy, DeepNegative, facing away, tilted head, Multiple people, lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worstquality, low quality, normal quality, jpegartifacts, signature, watermark, username, blurry, bad feet, cropped, poorly drawn hands, poorly drawn face, mutation, deformed, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, extra fingers, fewer digits, extra limbs, extra arms,extra legs, malformed limbs, fused fingers, too many fingers, long neck, cross-eyed,mutated hands, polar lowres, bad body, bad proportions, gross proportions, text, error, missing fingers, missing arms, missing legs, extra digit, extra arms, extra leg, extra foot, ((repeating hair))"


def submit_post(url: str, data: dict):
    return requests.post(url, data=json.dumps(data))


def save_encoded_image(b64_image: str, output_path: str):
    with open(output_path, 'wb') as image_file:
        image_file.write(base64.b64decode(b64_image))


def insert_novel_name(novel_name):
    # 建立数据库连接
    conn = sqlite3.connect('novel.db')
    cursor = conn.cursor()

    # 插入小说名称到主表
    cursor.execute('INSERT INTO novel_info (novel_name) VALUES (?)', (novel_name,))
    novel_id = cursor.lastrowid  # 获取刚插入的小说ID
    # 提交事务
    conn.commit()
    # 关闭数据库连接
    conn.close()
    # 返回小说ID
    return novel_id


# 在适当的位置将原始描述和可视化描述插入数据库子表中
def process_novel_segments(novel_id, processed_segments):
    # 建立数据库连接
    conn = sqlite3.connect('novel.db')
    cursor = conn.cursor()
    # 处理 novel segments
    if not novel_id:
        global global_novel_id
        novel_id = global_novel_id
    # 插入到数据库子表中
    for segment in processed_segments:
        original_description = segment['original_description']
        visual_description = segment['visual_description']
        positive_word = segment['positive_word']  # 获取positive_word

        cursor.execute('''
            INSERT INTO novel_scene (novel_id, original_description, visual_description, positive_words)
            VALUES (?, ?, ?, ?)
        ''', (novel_id, original_description, visual_description, positive_word))
    # 提交事务
    conn.commit()
    # 关闭数据库连接
    conn.close()


def chat_with_model(prompt):
    messages = [{"role": "user", "content": prompt}]
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.3,
    )
    return response.choices[0].message.content


def chat_with_model_keywords(prompt):
    messages = [{"role": "user", "content": prompt}]
    response = client.chat.completions.create(
        # model="gpt-4",
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.5,
    )
    return response.choices[0].message.content


def get_replies(prompts):
    replies = []
    for prompt in prompts:
        start_time = time.time()  # 记录开始时间
        reply = None
        while reply is None:
            reply = chat_with_model(prompt)
            if reply is None:
                elapsed_time = time.time() - start_time  # 计算已经过去的时间
                if elapsed_time >= 3:  # 如果超过3秒，则跳过请求
                    break
                time.sleep(0.5)  # 等待0.5秒后重试
        if reply is not None:
            replies.append(reply)

    return replies


def split_novel_into_paragraphs(novel_text, max_paragraph_length):
    paragraphs = []
    current_paragraph = ""
    processed_paragraphs = []

    for text in novel_text:
        stripped_text = text.strip()
        remaining_text = stripped_text

        if len(remaining_text) > 0:
            remaining_text = remaining_text + "。"
            if len(current_paragraph) + len(remaining_text) <= max_paragraph_length:
                current_paragraph += remaining_text
            else:
                paragraphs.append(current_paragraph)
                current_paragraph = remaining_text

    if current_paragraph:
        paragraphs.append(current_paragraph)

    # 发送固定的提问语句获取返回值
    fixed_reply = get_replies(fixed_prompts)
    if fixed_reply:
        # 进行下一步操作
        # 将固定的返回值添加到处理后的段落数组中
        for index, paragraph in enumerate(paragraphs):
            start_time = time.time()  # 记录开始时间
            reply = None
            while reply is None:
                reply = chat_with_model(fixed_prompts[3] + " 原文: " + paragraph)
                if reply is None:
                    elapsed_time = time.time() - start_time  # 计算已经过去的时间
                    if elapsed_time >= 4:  # 如果超过4秒，则跳过请求
                        break
                    time.sleep(0.5)  # 等待0.5秒后重试
            if reply is not None:
                processed_paragraphs.append(reply)
            # 更新进度条
            current_step = index + 1
            progress = (current_step / len(paragraphs)) * 100 * 0.1
            progress_bar['value'] = progress
            window.update_idletasks()
    return process_return_values(processed_paragraphs)


def process_return_values(return_values):
    data = []  # 存储所有组数据的列表

    for group in return_values:
        group_values = process_paragraphs(group)
        for group_data in group_values:
            # 将每组数据添加到列表中
            data.append(group_data)
    return data


def process_paragraphs(text):
    pattern = r'第(\d+|[一二三四五六七八九十]+)组：'
    paragraphs = re.split(pattern, text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]  # 去除空白段落

    descriptions = []
    for i in range(1, len(paragraphs), 2):
        original_description, visual_description = extract_descriptions(paragraphs[i])
        if original_description and visual_description:
            descriptions.append({
                'original_description': original_description,
                'visual_description': visual_description
            })

    return descriptions


def extract_descriptions(paragraph):
    delimiter = '\n画面描述：'
    segments = paragraph.split(delimiter)
    if len(segments) == 2:
        original_description = segments[0].replace('原文描述：', '').strip()
        visual_description = segments[1].strip()
        return original_description, visual_description
    return None, None


def select_file():
    file_path = filedialog.askopenfilename(title="选择要处理的文件", filetypes=[("Excel Files", "*.xlsx;*.xls")])
    # 从文件路径中提取文件名作为小说名称
    file_name = os.path.basename(file_path)
    novel_name = os.path.splitext(file_name)[0]

    file_entry.delete(0, tk.END)
    file_entry.insert(0, file_path)
    load_columns(file_path)
    # 将小说名称插入主表
    global global_novel_id
    global global_novel_name
    global global_output_file
    global_novel_name = novel_name
    global_novel_id = insert_novel_name(novel_name)
    global_output_file = os.path.dirname(file_path)


def load_columns(file_path):
    try:
        df = pd.read_excel(file_path)
        column_listbox.delete(0, tk.END)
        for column in df.columns:
            column_listbox.insert(tk.END, column)
    except Exception as e:
        status_label.config(text=str(e))


def select_columns():
    selected_columns = [column_listbox.get(index) for index in column_listbox.curselection()]
    columns_entry.delete(0, tk.END)
    columns_entry.insert(0, ", ".join(selected_columns))


def add_positive_word(output_text):
    # chat_with_model(positive_words_prompts[0])
    total_text = len(output_text)
    current_text = 0
    if chat_with_model(positive_words_prompts[1]):
        for text in output_text:
            positive_word = chat_with_model_keywords(
                "使用英文回复，只需要提取关键词词组(Prompt)用于Stable diffusion绘画，以下是你需要处理的文本,请把关英文键词词组(Prompt)用逗号分割展示出来:" +
                text['visual_description'])
            text['positive_word'] = "4k,8k,best quality, masterpiece," + positive_word
            # 更新进度条
            current_text += 1
            progress = 10 + (current_text / total_text) * 100 * 0.1
            progress_bar['value'] = progress
            window.update_idletasks()
    return output_text


def process_file():
    input_file = file_entry.get()
    selected_columns = [column_listbox.get(index) for index in column_listbox.curselection()]
    if not input_file or not selected_columns:
        status_label.config(text="请选择文件和要提取的列！")
        return
    try:
        df = pd.read_excel(input_file)
        output_text = ""
        for column in selected_columns:
            if column in df.columns:
                output_text += df[column].astype(str) + "\n"
            else:
                status_label.config(text=f"列 '{column}' 不存在！")
                return
        # output_text = remove_newlines(output_text)
        # 分割小说文本为段落
        output_text = split_novel_into_paragraphs(output_text, max_token)
        output_text_with_positive_words = add_positive_word(output_text)
        global global_novel_id
        process_novel_segments(global_novel_id, output_text_with_positive_words)
        # save_path = filedialog.asksaveasfilename(title="选择保存位置", defaultextension=".txt",filetypes=[("Text Files", "*.txt")])

        global global_novel_name
        global global_output_file
        output_folder = os.path.join(global_output_file, global_novel_name)

        # 创建以小说名命名的文件夹
        folder_counter = 1
        while os.path.exists(output_folder):
            output_folder = f"{output_folder} ({folder_counter})"
            folder_counter += 1
        os.makedirs(output_folder)
        audio_folder = os.path.join(output_folder, "mp3")
        # 处理 "mp3" 子文件夹已存在的情况
        if os.path.exists(audio_folder):
            shutil.rmtree(audio_folder)
        # 创建新的 "mp3" 子文件夹
        os.makedirs(audio_folder)
        txt_folder = os.path.join(output_folder, f"{global_novel_name}.txt")
        with open(txt_folder, 'w', encoding='utf-8') as file:
            # file.write(output_text)
            for text in output_text:
                file.write(text['original_description'] + '\n')

        global_output_file = output_folder
        generate_audio()
        # generate_image()
        status_label.config(text="处理完成！")
        # 在5秒后调用close_window函数，销毁窗口
        # window.after(5000, close_window)

        # import_button.pack()  # 渲染导入剪映按钮

    except Exception as e:
        status_label.config(text=str(e))


def generate_audio():
    try:
        # 初始化pyttsx3引擎
        engine = pyttsx3.init()
        # 设置语速
        engine.setProperty('rate',250)
        # 设置音频输出格式为MP3
        engine.setProperty('audio', 'audio/mp3')
        # 连接到 SQLite 数据库
        db = sqlite3.connect('novel.db')
        # 创建游标
        cursor = db.cursor()
        count_query = f"SELECT COUNT(*) FROM novel_scene WHERE novel_id = '{global_novel_id}'"
        cursor.execute(count_query)
        record_count = cursor.fetchone()[0]
        print(f"记录数量：{record_count}")
        # 查询 novel_scene 表中 novel_id 等于 global_novel_id 的场景下的原文
        query = f"SELECT scene_id, original_description FROM novel_scene WHERE novel_id = '{global_novel_id}'"
        cursor.execute(query)
        output_directory = os.path.join(global_output_file, "mp3")
        os.makedirs(output_directory, exist_ok=True)
        try:
            current_step = 0
            for (scene_id, original_description) in cursor:
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                output_file = os.path.join(output_directory, f"{scene_id}-{timestamp}.mp3")
                # 将文本转换为语音
                engine.save_to_file(original_description, output_file)
                engine.runAndWait()
                # 更新进度条
                current_step = current_step + 1
                progress = 20 + (current_step / record_count) * 100 * 0.2
                progress_bar['value'] = progress
                window.update_idletasks()
        except Exception as ex:
            # 发生异常，回滚事务
            db.rollback()
            raise ex
    except Exception as ex:
        # 处理其他异常
        print(f"生成音频时出现异常：{ex}")
    finally:
        # 关闭游标和数据库连接
        cursor.close()
        db.close()
        process_mp3_files(output_directory)


def get_audio_duration(audio_path):
    with wave.open(audio_path, 'rb') as audio_file:
        frames = audio_file.getnframes()
        rate = audio_file.getframerate()
        duration = frames / float(rate)
        duration_ms = int(duration * 1000)
        return duration_ms


def process_mp3_files(audio_directory):
    # 连接到 SQLite 数据库
    db = sqlite3.connect('novel.db')
    # 创建游标
    cursor = db.cursor()
    for filename in os.listdir(audio_directory):
        if filename.endswith(".mp3"):
            # 解析出 scene_id
            scene_id = filename.split("-")[0]

            # 查询数据库获取 original_description
            query = f"SELECT original_description,visual_description,positive_words FROM novel_scene WHERE scene_id = '{scene_id}'"
            cursor.execute(query)
            result = cursor.fetchone()
            if result:
                original_description = result[0]
                visual_description = result[1]
                positive_words = result[2]

                # 生成字幕文件路径和名称
                audio_path = os.path.join(audio_directory, filename)
                subtitles_filename = os.path.splitext(filename)[0] + ".srt"
                subtitles_file = os.path.join(audio_directory, subtitles_filename)
                txt_subtitles_filename = os.path.splitext(filename)[0] + ".txt"
                txt_subtitles_file = os.path.join(audio_directory, txt_subtitles_filename)
                # 获取音频文件的时长（毫秒）
                duration = get_audio_duration(audio_path)
                # 获取音频文字的字数 original_description的字数
                word_count = len(original_description)
                # 每个字平均时间
                # 计算每个字平均时间
                average_time_per_word = int(duration / word_count)

                # 生成 SRT 字幕内容
                subtitles_content = generate_srt_content(original_description, average_time_per_word)

                # 将字幕内容写入字幕文件
                with open(subtitles_file, 'w') as f:
                    f.write(subtitles_content)

                # 将txt字幕内容写入txt字幕文件
                with open(txt_subtitles_file, 'w') as f:
                    f.write(original_description + '\n')
                    f.write(visual_description + '\n')
                    f.write(positive_words + '\n')

                # 更新数据库中的 audio_path 字段
                update_query = "UPDATE novel_scene SET audio_path = ? , audio_duration = ? WHERE scene_id = ?"
                cursor.execute(update_query, (os.path.abspath(audio_path), duration, scene_id))
                db.commit()

    # 关闭游标和数据库连接
    cursor.close()
    db.close()
    generate_image()


def generate_srt_content(original_description, average_time_per_word):
    subtitle_index = 1
    start_time = 0
    end_time = 0
    subtitles_content = ""

    # 按句号分割原始描述文本
    sentences = original_description.split("。")

    for sentence in sentences:
        # 去除空白字符
        sentence = sentence.strip()

        if sentence:
            # 分割句子中的字
            characters = list(sentence)

            # 计算当前句子的开始时间和结束时间
            start_time = end_time
            end_time = start_time + (average_time_per_word * len(characters))

            # 将时间转换为 SRT 格式
            start_time_srt = milliseconds_to_srt_time(start_time)
            end_time_srt = milliseconds_to_srt_time(end_time)

            # 添加字幕内容到字幕文件
            subtitles_content += f"{subtitle_index}\n{start_time_srt} --> {end_time_srt}\n{sentence}\n\n"

            subtitle_index += 1

    return subtitles_content


def milliseconds_to_srt_time(milliseconds):
    seconds = int(milliseconds // 1000)
    minutes = int(seconds // 60)
    hours = int(minutes // 60)

    milliseconds %= 1000
    seconds %= 60
    minutes %= 60

    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def timestamp():
    return datetime.fromtimestamp(time.time()).strftime("%Y%m%d%H%M%S")


def encode_file_to_base64(path):
    with open(path, 'rb') as file:
        return base64.b64encode(file.read()).decode('utf-8')


def decode_and_save_base64(base64_str, save_path):
    with open(save_path, "wb") as file:
        file.write(base64.b64decode(base64_str))


def call_api(api_endpoint, **payload):
    data = json.dumps(payload).encode('utf-8')
    request = urllib.request.Request(
        f'{webui_server_url}/{api_endpoint}',
        headers={'Content-Type': 'application/json'},
        data=data,
    )
    response = urllib.request.urlopen(request)
    return json.loads(response.read().decode('utf-8'))


def call_txt2img_api(filename, out_dir_t2i, **payload):
    response = call_api('sdapi/v1/txt2img', **payload)
    for index, image in enumerate(response.get('images')):
        save_path = os.path.join(out_dir_t2i, f'{filename}-{timestamp()}.png')
        decode_and_save_base64(image, save_path)


def call_img2img_api(filename, out_dir_i2i, **payload):
    response = call_api('sdapi/v1/img2img', **payload)
    for index, image in enumerate(response.get('images')):
        save_path = os.path.join(out_dir_i2i, f'{filename}-{timestamp()}-{index}.png')
        decode_and_save_base64(image, save_path)

def update_image_paths(item, image_directory):
    # 连接到 SQLite 数据库
    db = sqlite3.connect('novel.db')
    # 创建游标
    cursor = db.cursor()
    for filename in os.listdir(image_directory):
        if filename.endswith(".png"):
            # 解析出scene_id
            scene_id = filename.split("-")[0]
            image_path = os.path.join(image_directory, filename)
            # 更新数据库中的image_path字段
            if item == "image_path":
                update_query = "UPDATE novel_scene SET image_path = ? WHERE scene_id = ?"
            elif item == "hr_image_path":
                update_query = "UPDATE novel_scene SET hr_image_path = ? WHERE scene_id = ?"
            cursor.execute(update_query, (os.path.abspath(image_path), scene_id))
            db.commit()
    # 关闭游标和数据库连接
    cursor.close()
    db.close()
def generate_image():
    out_dir = global_output_file
    os.makedirs(out_dir, exist_ok=True)

    try:
        # 连接到 SQLite 数据库
        with sqlite3.connect('novel.db') as db:
            # 创建游标
            cursor = db.cursor()
            count_query = f"SELECT COUNT(*) FROM novel_scene WHERE novel_id = '{global_novel_id}'"
            cursor.execute(count_query)
            record_count = cursor.fetchone()[0]

            # 查询 novel_scene 表中 novel_id 等于 global_novel_id 的场景下的原文
            query = f"SELECT scene_id, visual_description, positive_words, negative_words FROM novel_scene WHERE novel_id = '{global_novel_id}'"
            cursor.execute(query)

            current_step = 0

            for (scene_id, visual_description, positive_words, negative_words) in cursor:
                negative_prompt = negative_prompts if not negative_words else negative_words

                payload = {
                    "prompt": positive_words,
                    "negative_prompt": negative_prompt,
                    "seed": 1,
                    "steps": 20,
                    "width": 616,
                    "height": 464,
                    "restore_faces": "true",
                    "cfg_scale": 7,
                    "sampler_name": "DPM++ 2M Karras",
                    "n_iter": 1,
                    "batch_size": 1,
                }

                if not webui_server_url.startswith("http://localhost") and not webui_server_url.startswith(
                        "http://127.0.0.1"):
                    payload["enable_hr"] = "true"
                    payload["hr_upscaler"] = "Latent"
                    payload["hr_scale"] = 4
                    payload["hr_resize_x"] = 2464
                    payload["hr_resize_y"] = 1856
                    payload["hr_sampler_name"] = "Euler"
                    payload["hr_second_pass_steps"] = 10
                    payload["denoising_strength"] = 0.7

                call_txt2img_api(scene_id, out_dir, **payload)

                # 更新进度条
                current_step += 1
                progress = 40 + (current_step / record_count) * 100 * 0.3
                progress_bar['value'] = progress
                window.update_idletasks()

        update_image_paths("image_path", out_dir)
        process_generated_images(out_dir)

    except Exception as ex:
        print(f"出现异常：{ex}")





def process_generated_images(image_directory):
    img2img_directory = os.path.join(image_directory, "img2img")
    os.makedirs(img2img_directory, exist_ok=True)
    total_images = len([filename for filename in os.listdir(image_directory) if filename.endswith(".png")])
    current_image = 0
    # 连接到 SQLite 数据库
    db = sqlite3.connect('novel.db')
    # 创建游标
    cursor = db.cursor()
    for filename in os.listdir(image_directory):
        if filename.endswith(".png"):
            # 解析出 scene_id
            scene_id = filename.split("-")[0]
            image_path = os.path.join(image_directory, filename)
            # 查询数据库获取相关信息
            query = f"SELECT scene_id, positive_words,negative_words FROM novel_scene WHERE scene_id = '{scene_id}'"
            cursor.execute(query)
            result = cursor.fetchone()
            if result:
                scene_id, positive_words, negative_words = result
                init_images = [
                    encode_file_to_base64(image_path),
                    # encode_file_to_base64(r"B:\path\to\img_2.png"),
                    # "https://image.can/also/be/a/http/url.png",
                ]
                batch_size = 1
                payload = {
                    "prompt": positive_words,
                    "seed": 1,
                    "steps": 20,
                    "width": 616,
                    "height": 464,
                    "denoising_strength": 0.2,
                    "n_iter": 1,
                    "init_images": init_images,
                    "image_cfg_scale": 0,
                    # "batch_size": batch_size if len(init_images) == 1 else len(init_images),
                    "batch_size": batch_size,
                    "script_name": "SD upscale",
                    "script_args": ["None", 64, "R-ESRGAN 4x+", 4],
                    # "mask": encode_file_to_base64(r"mask.png")

                }
                # if len(init_images) > 1 then batch_size should be == len(init_images)
                # else if len(init_images) == 1 then batch_size can be any value int >= 1
                call_img2img_api(scene_id, img2img_directory, **payload)
                # 更新数据库中的 image_path 字段
                '''
                update_query = "UPDATE novel_scene SET image_path = ? WHERE scene_id = ?"
                cursor.execute(update_query, (os.path.abspath(image_path), scene_id))
                db.commit()
                '''
                # 更新进度条
                current_image += 1
                progress = 70 + (current_image / total_images) * 100 * 0.3
                progress_bar['value'] = progress
                window.update_idletasks()

    # 关闭游标和数据库连接
    cursor.close()
    db.close()
    update_image_paths("hr_image_path", img2img_directory)
    import_to_jianying()


def import_to_jianying():
    try:
        # 连接到 SQLite 数据库
        with sqlite3.connect('novel.db') as db:
            # 创建游标
            cursor = db.cursor()
            # 查询 novel_scene 表中 novel_id 等于 global_novel_id 的场景
            query = f"SELECT scene_id, original_description, image_path, hr_image_path, audio_path, audio_duration FROM novel_scene WHERE novel_id = '{global_novel_id}'"
            cursor.execute(query)

            newdraft = Draft(global_novel_name)

            for (scene_id, original_description, image_path, hr_image_path, audio_path, audio_duration) in cursor:
                photo = Material(hr_image_path)
                audio = Material(audio_path)
                newdraft.add_media_to_materials(photo)
                newdraft.add_media_to_materials(audio)
                newdraft.add_media_to_track(photo)
                newdraft.add_media_to_track(audio)

                word_count = len(original_description)
                average_time_per_word = int(audio_duration) / word_count
                sentences = original_description.split("。")
                sentences = [sentence.strip() for sentence in sentences if sentence.strip()]
                total_duration = 0

                for i, sentence in enumerate(sentences):
                    if sentence:
                        sentence_duration = average_time_per_word * len(sentence)

                        if i == len(sentences) - 1:
                            remaining_duration = int(audio_duration) - total_duration
                            sentence_duration = remaining_duration if remaining_duration > 0 else 0

                        else:
                            sentence_duration = round(sentence_duration)

                        total_duration += sentence_duration
                        sentence = sentence.strip()
                        newdraft.add_media_to_track(sentence, duration=int(sentence_duration * 1000))

        newdraft.save()
    except Exception as ex:
        print(f"出现异常：{ex}")
        traceback.print_exc()

# OpenAI API密钥设置按钮
def set_api_key():
    api_key = api_key_entry.get()

    if api_key:
        # 在这里将api_key用于设置OpenAI API密钥
        # 将API密钥保存到文件中
        with open("openai_api_key.txt", "w") as api_key_file:
            api_key_file.write(api_key)
        global client
        client = OpenAI(
            api_key=api_key,
            base_url='https://api.gpt-ai.live/v1'
        )


def toggle_selection(event):
    selected_item = column_listbox.curselection()
    if selected_item:
        index = selected_item[0]
        if column_listbox.selection_includes(index):
            column_listbox.selection_set(index)
        else:
            column_listbox.selection_clear(index)

def close_window():
    window.destroy()

# 创建主窗口
window = tk.Tk()
window.title("Excel列转换为草稿")
window.geometry("600x500")
# 本地SD的api
webui_server_url = ""
default_webui_server_url = 'http://127.0.0.1:7860'
try:
    with open('./webui_server_url.txt', 'r') as file:
        webui_server_url = file.read().strip()
except FileNotFoundError:
    webui_server_url = default_webui_server_url

if not webui_server_url:
    webui_server_url = default_webui_server_url
# 测试webui_server_url是否联通
try:
    response = requests.get(webui_server_url)
    if response.status_code != 200:
        webui_server_url = default_webui_server_url
except requests.exceptions.RequestException:
    webui_server_url = default_webui_server_url

# OpenAI API密钥输入框
api_key_label = tk.Label(window, text="OpenAI API密钥:")
api_key_label.pack()
api_key_entry = tk.Entry(window, width=40)
api_key_entry.pack()
api_key_button = tk.Button(window, text="设置API密钥", command=set_api_key)
api_key_button.pack()

# 从文件中读取API密钥值
try:
    with open("openai_api_key.txt", "r") as file:
        saved_api_key = file.read().strip()

        if saved_api_key:
            api_key_entry.insert(0, saved_api_key)
            openai_api_key = saved_api_key
            client = OpenAI(
                api_key=openai_api_key,
                base_url='https://api.gpt-ai.live/v1'
            )
except FileNotFoundError:
    pass

# 选择文件按钮和输入框
file_label = tk.Label(window, text="选择要处理的文件:")
file_label.pack()
file_entry = tk.Entry(window, width=40)
file_entry.pack()
file_button = tk.Button(window, text="选择文件", command=select_file)
file_button.pack()

# 列选择部分
columns_label = tk.Label(window, text="选择要提取的列（多选）:")
columns_label.pack()
column_listbox = tk.Listbox(window, selectmode=tk.MULTIPLE)
column_listbox.pack()

scrollbar = tk.Scrollbar(window)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
column_listbox.config(yscrollcommand=scrollbar.set)
scrollbar.config(command=column_listbox.yview)

column_listbox.bind('<<ListboxSelect>>', toggle_selection)

# 处理按钮和状态提示
select_button = tk.Button(window, text="选择列", command=select_columns)
select_button.pack()

columns_entry = tk.Entry(window, width=40)
columns_entry.pack()

progress_bar = ttk.Progressbar(window, length=300, mode='determinate')
progress_bar.pack()

process_button = tk.Button(window, text="处理文件", command=process_file)
process_button.pack()

# import_button = tk.Button(window, text="导入剪映", command=import_to_jianying)
# import_button.pack()

status_label = tk.Label(window, text="")
status_label.pack()

# 运行主循环
if __name__ == "__main__":
    window.mainloop()
