import os
import shutil
import traceback
import urllib
from urllib import request, error
import time
import tkinter as tk
import wave
from tkinter import ttk
from tkinter import filedialog

import gradio_client
import pandas as pd
from openai import OpenAI
import re
import sqlite3
import json
import base64
import requests
import pyttsx3
from datetime import datetime

from AppState import AppState
from Draft import Draft
from material import Material

from gradio_client import Client, file

# 全局变量
app_state = AppState()

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


def close_local_model():
    """关闭本地模型进程"""
    if app_state.local_model_process:
        app_state.local_model_process.terminate()
        app_state.local_model_process = None


def chat_with_local_model(prompt, model_name="deepseek-r1:32b"):
    try:
        payload = {"model": model_name, "prompt": prompt}
        response = requests.post(app_state.OLLAMA_URL, json=payload, timeout=30, stream=True)

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        print(f"[{timestamp}] Response status code: {response.status_code}")

        response.raise_for_status()
        result_content = []

        for line in response.iter_lines():
            if line.strip():
                try:
                    json_data = json.loads(line.decode("utf-8"))
                    response_text = json_data.get("response", "")
                    if response_text:
                        result_content.append(response_text)

                    if json_data.get("done", False):
                        break
                except json.JSONDecodeError:
                    return "解析本地模型响应时发生错误"

        # 合并内容后去除思考链
        full_content = "".join(result_content)
        processed_content = re.sub(
            r'<think>.*?</think>',  # 非贪婪匹配
            '',
            full_content,
            flags=re.DOTALL  # 允许.匹配换行符
        ).strip()

        return processed_content if processed_content else "本地模型返回了空内容"

    except requests.exceptions.RequestException as e:
        return f"本地模型请求失败: {e}"

    finally:
        if 'response' in locals():
            response.close()


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
        novel_id = app_state.global_novel_id
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


def chat_with_model(user_prompt, system_prompt=None):
    """根据选择调用不同模型"""
    if app_state.use_local_model:
        return chat_with_local_model(user_prompt, system_prompt)
    else:
        # 构建消息列表（支持动态系统消息）
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        try:
            response = app_state.client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=0.7,
                max_tokens=1024,
                stream=True
            )

            # 流式响应处理
            full_response = []
            for chunk in response:
                if chunk.choices[0].delta.content:
                    full_response.append(chunk.choices[0].delta.content)
            return "".join(full_response)

        except Exception as e:
            return handle_deepseek_error(e)


def handle_deepseek_error(e):
    error_mapping = {
        401: "无效API密钥，请检查控制台",
        429: "请求过于频繁，请稍后重试",
        500: "服务器内部错误，请联系技术支持"
    }
    if hasattr(e, 'status_code'):
        return f"DeepSeek API错误: {error_mapping.get(e.status_code, '未知错误')}"
    return f"网络连接异常: {str(e)}"


def chat_with_model_keywords(user_prompt, system_prompt=None):
    """根据选择调用不同模型"""
    if app_state.use_local_model:
        return chat_with_local_model(user_prompt, system_prompt)
    else:
        # 构建消息列表（支持动态系统消息）
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        try:
            response = app_state.client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=0.7,
                max_tokens=1024,
                stream=True
            )

            # 流式响应处理
            full_response = []
            for chunk in response:
                if chunk.choices[0].delta.content:
                    full_response.append(chunk.choices[0].delta.content)
            return "".join(full_response)

        except Exception as e:
            return handle_deepseek_error(e)


def get_replies(prompts):
    replies = []
    for prompt in prompts:
        start_time = time.time()  # 记录开始时间
        reply = None
        while reply is None:
            reply = chat_with_model("", prompt)
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
    if app_state.current_interface == "douyin":
        sentence_end = "。"
        for text in novel_text:
            stripped_text = text.strip()
            remaining_text = stripped_text

            if len(remaining_text) > 0:
                remaining_text += sentence_end if not re.search(r'[。！？]$', remaining_text) else ''
                if len(current_paragraph) + len(remaining_text) <= max_paragraph_length:
                    current_paragraph += remaining_text
                else:
                    paragraphs.append(current_paragraph)
                    current_paragraph = remaining_text
        if current_paragraph:
            paragraphs.append(current_paragraph)

        # 发送固定的提问语句获取返回值
        fixed_reply = get_replies(app_state.fixed_prompts)
        if fixed_reply:
            # 进行下一步操作
            # 将固定返回值添加到处理后的段落数组中
            for index, paragraph in enumerate(paragraphs):
                start_time = time.time()  # 记录开始时间
                reply = None
                while reply is None:
                    reply = chat_with_model(app_state.fixed_prompts[3], " 原文: " + paragraph)
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
                app_state.progress_bar['value'] = progress
                window.update_idletasks()

    else:
        sentence_end = "."
        max_paragraph_count = 2
        paragraph_count = 0
        for text in novel_text:
            stripped_text = text.strip()
            remaining_text = stripped_text

            if len(remaining_text) > 0:
                remaining_text += sentence_end if not re.search(r"[.!?'\']$", remaining_text) else ''
                if paragraph_count <= max_paragraph_count:
                    paragraph_count = paragraph_count + 1
                    current_paragraph += remaining_text
                else:
                    paragraphs.append(current_paragraph)
                    current_paragraph = remaining_text
                    paragraph_count = 0

        if current_paragraph:
            paragraphs.append(current_paragraph)

        if paragraphs:
            # 进行下一步操作
            # 将固定返回值添加到处理后的段落数组中
            fixed_reply = chat_with_model('', app_state.fixed_prompts_tiktok[0])
            if fixed_reply:
                for index, paragraph in enumerate(paragraphs):
                    start_time = time.time()  # 记录开始时间
                    reply = None
                    while reply is None:
                        reply = chat_with_model(" 原文如下: " + paragraph, app_state.fixed_prompts_tiktok[0])
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
                    app_state.progress_bar['value'] = progress
                    window.update_idletasks()

    return process_return_values(processed_paragraphs, paragraphs)


def process_return_values(return_values, paragraphs):
    data = []  # 存储所有组数据的列表

    # 根据不同的业务场景（抖音 vs TikTok）执行不同的处理逻辑
    if app_state.current_interface == "douyin":
        # 抖音业务：直接处理段落
        for group in return_values:
            group_values = process_paragraphs(group)
            for group_data in group_values:
                data.append(group_data)
    elif app_state.current_interface == "TikTok":
        # TikTok业务：处理原文和修改后的对照
        for original, processed in zip(paragraphs, return_values):
            # 对每一组原文和处理后的段落生成对照
            data.append({
                'original_description': original,
                'visual_description': processed
            })
    else:
        # 如果不在抖音或TikTok业务中，可以处理一个默认逻辑，或者抛出异常
        raise ValueError("Unsupported interface type")

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


def load_columns(file_path):
    try:
        df = pd.read_excel(file_path)
        app_state.column_listbox.delete(0, tk.END)
        for column in df.columns:
            app_state.column_listbox.insert(tk.END, column)
    except Exception as e:
        app_state.status_label.config(text=str(e))


def add_positive_word(output_text):
    # chat_with_model(positive_words_prompts[0])
    total_text = len(output_text)
    current_text = 0
    if chat_with_model('', app_state.positive_words_prompts[0]):
        for text in output_text:
            scene_words = chat_with_model_keywords("以下是你需要处理的文本:" + text['visual_description'],
                                                   app_state.scene_words_prompts[5])
            if scene_words is not None:
                positive_word = chat_with_model_keywords(scene_words, app_state.positive_words_prompts[0])
                text['positive_word'] = "4k,8k,best quality, masterpiece," + positive_word

            # 更新进度条
            current_text += 1
            progress = 10 + (current_text / total_text) * 100 * 0.1
            app_state.progress_bar['value'] = progress
            window.update_idletasks()
    return output_text


def process_file():
    input_file = app_state.file_entry.get()
    selected_columns = [app_state.column_listbox.get(index) for index in app_state.column_listbox.curselection()]
    if not input_file or not selected_columns:
        app_state.status_label.config(text="请选择文件和要提取的列！")
        return
    try:
        df = pd.read_excel(input_file)
        output_text = ""
        for column in selected_columns:
            if column in df.columns:
                output_text += df[column].astype(str) + "\n"
            else:
                app_state.status_label.config(text=f"列 '{column}' 不存在！")
                return
        # output_text = remove_newlines(output_text)
        # 分割小说文本为段落
        output_text = split_novel_into_paragraphs(output_text, app_state.max_token)
        output_text_with_positive_words = add_positive_word(output_text)
        process_novel_segments(app_state.global_novel_id, output_text_with_positive_words)
        # save_path = filedialog.asksaveasfilename(title="选择保存位置", defaultextension=".txt",filetypes=[("Text Files", "*.txt")])

        output_folder = os.path.join(app_state.global_output_file, app_state.global_novel_name)

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
        txt_folder = os.path.join(output_folder, f"{app_state.global_novel_name}.txt")
        with open(txt_folder, 'w', encoding='utf-8') as file:
            # file.write(output_text)
            for text in output_text:
                file.write(text['original_description'] + '\n')

        app_state.global_output_file = output_folder
        # 根据当前的音频模型选择合适的音频生成函数
        if app_state.current_audio_model == "gpt_sovits":
            generate_audio_with_gpt_sovits()
        else:
            generate_audio()
        # generate_image()
        app_state.status_label.config(text="处理完成！")
        # 在5秒后调用close_window函数，销毁窗口
        # window.after(5000, close_window)

        # import_button.pack()  # 渲染导入剪映按钮

    except Exception as e:
        app_state.status_label.config(text=str(e))


def generate_audio_from_text(text):
    if app_state.current_interface == "Douyin":
        text_lang = "中文"
        prompt_lang = "中文"
        text_split_method = "按中文句号。切"  # 切割文本方式为中文句号
    elif app_state.current_interface == "TikTok":
        text_lang = "英文"
        prompt_lang = "英文"
        text_split_method = "按英文句号.切"  # 切割文本方式为英文句号
    else:
        # 如果当前界面未知或没有设置，则使用默认值
        text_lang = "中文"
        prompt_lang = "中文"
        text_split_method = "按中文句号。切"
    try:
        # 调用 API 生成音频
        result = app_state.gradioclient.predict(
            text=text,  # 需要合成的文本
            text_lang=text_lang,  # 需要合成的语言
            ref_audio_path=gradio_client.handle_file(app_state.ref_audio_path),  # 参考音频文件路径
            aux_ref_audio_paths=[],
            prompt_text=app_state.prompt_text,  # 可以选择添加提示文本，如果不需要可以为空
            prompt_lang=prompt_lang,  # 参考音频的语言
            top_k=15,  # GPT采样参数
            top_p=1,
            temperature=1,
            text_split_method=text_split_method,  # 切割文本方式
            batch_size=20,
            speed_factor=1,
            ref_text_free=False,  # 是否开启无参考文本模式
            split_bucket=True,
            fragment_interval=0.3,
            seed=-1,
            keep_random=True,
            parallel_infer=True,
            repetition_penalty=1.35,
            api_name="/inference"
        )
        temp_audio_path = result
        # 如果 temp_audio_path 是元组，取出路径
        if isinstance(temp_audio_path, tuple):
            temp_audio_path = temp_audio_path[0]  # 假设文件路径在元组的第一个位置

        # 检查路径是否是字符串类型
        if isinstance(temp_audio_path, str) and os.path.exists(temp_audio_path):
            return temp_audio_path
        else:
            print(f"临时音频文件不存在: {temp_audio_path}")
            return None
    except Exception as e:
        print(f"生成音频时出现错误：{e}")
        return None


def generate_audio_with_gpt_sovits():
    if app_state.current_interface == "Douyin":
        text_lang = "中文"
        prompt_language = "中文"
    elif app_state.current_interface == "TikTok":
        text_lang = "英文"
        prompt_language = "英文"
    else:
        # 如果当前界面未知或没有设置，则使用默认值
        text_lang = "中文"
        prompt_language = "中文"
    try:
        # 连接到 SQLite 数据库
        db = sqlite3.connect('novel.db')
        cursor = db.cursor()

        # 获取当前小说的记录数量
        count_query = f"SELECT COUNT(*) FROM novel_scene WHERE novel_id = '{app_state.global_novel_id}'"
        cursor.execute(count_query)
        record_count = cursor.fetchone()[0]
        print(f"记录数量：{record_count}")

        # 查询 novel_scene 表中 novel_id 等于 global_novel_id 的场景下的原文
        query = f"SELECT scene_id, original_description FROM novel_scene WHERE novel_id = '{app_state.global_novel_id}'"
        cursor.execute(query)

        output_directory = os.path.join(app_state.global_output_file, "mp3")
        os.makedirs(output_directory, exist_ok=True)
        # 创建 Gradio 客户端
        app_state.gradioclient = Client("http://localhost:9872/")

        change_choices_result = app_state.gradioclient.predict(
            api_name="/change_choices"
        )
        # 提取 'choices' 中的路径
        choices_1 = [choice[0] for choice in change_choices_result[0]['choices']]
        choices_2 = [choice[0] for choice in change_choices_result[1]['choices']]

        hange_sovits_weights_result = app_state.gradioclient.predict(
            sovits_path=choices_1[1],
            prompt_language=prompt_language,
            text_language=text_lang,
            api_name="/change_sovits_weights"
        )
        init_t2s_weights_result = app_state.gradioclient.predict(
            weights_path=choices_2[1],
            api_name="/init_t2s_weights"
        )
        # 获取参考音频文件路径
        ref_audio_path = app_state.audio_file_entry.get()
        # 如果是元组类型，强制转换为字符串
        if isinstance(ref_audio_path, tuple):
            ref_audio_path = str(ref_audio_path[0])  # 假设文件路径在元组的第一个位置

        # 确保 ref_audio_path 是字符串类型
        if not isinstance(ref_audio_path, str):
            print("ref_audio_path 应该是一个有效的字符串路径，但当前值是：{}".format(type(ref_audio_path)))
        # 使用 replace 方法将双引号转为单引号
        app_state.ref_audio_path = ref_audio_path.replace('"', "'")
        # 获取TXT文件内容
        txt_file_path = app_state.audiotxt_file_entry.get()
        with open(txt_file_path, 'r', encoding='utf-8') as txt_file:
            prompt_text = txt_file.read()  # 读取TXT文件内容
        app_state.prompt_text = prompt_text.replace('"', "'")
        try:
            current_step = 0
            for (scene_id, original_description) in cursor:
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                output_file = os.path.join(output_directory, f"{scene_id}-{timestamp}.wav")

                audio_path = generate_audio_from_text(original_description)

                if audio_path:
                    # 将音频保存为 MP3 文件
                    audio_data = open(audio_path, 'rb').read()  # 读取生成的音频文件

                    # 保存音频文件
                    with open(output_file, 'wb') as audio_file:
                        audio_file.write(audio_data)

                    # 更新进度条
                    current_step += 1
                    progress = 20 + (current_step / record_count) * 100 * 0.2
                    app_state.progress_bar['value'] = progress
                    window.update_idletasks()
                else:
                    print(f"生成音频失败，场景 {scene_id}")
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


def generate_audio():
    try:
        # 初始化pyttsx3引擎
        engine = pyttsx3.init()
        # 设置语速
        engine.setProperty('rate', 250)
        # 设置音频输出格式为MP3
        engine.setProperty('audio', 'audio/mp3')
        # 连接到 SQLite 数据库
        db = sqlite3.connect('novel.db')
        # 创建游标
        cursor = db.cursor()
        count_query = f"SELECT COUNT(*) FROM novel_scene WHERE novel_id = '{app_state.global_novel_id}'"
        cursor.execute(count_query)
        record_count = cursor.fetchone()[0]
        print(f"记录数量：{record_count}")
        # 查询 novel_scene 表中 novel_id 等于 global_novel_id 的场景下的原文
        query = f"SELECT scene_id, original_description FROM novel_scene WHERE novel_id = '{app_state.global_novel_id}'"
        cursor.execute(query)
        output_directory = os.path.join(app_state.global_output_file, "mp3")
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
                app_state.progress_bar['value'] = progress
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
        if filename.endswith(".mp3") or filename.endswith(".wav"):  # 支持mp3和wav
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
                with open(subtitles_file, 'w', encoding='utf-8') as f:
                    f.write(subtitles_content)

                # 将txt字幕内容写入txt字幕文件
                with open(txt_subtitles_file, 'w', encoding='utf-8') as f:
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
    # data = urllib.parse.urlencode(payload).encode('utf-8')
    requester = urllib.request.Request(
        f'{app_state.webui_server_url}/{api_endpoint}',
        headers={'Content-Type': 'application/json'},
        data=data,
        method='POST'
    )
    try:
        with urllib.request.urlopen(requester) as response:
            return json.loads(response.read().decode('utf-8'))
    except error.URLError as ex:
        print(f"出现异常：{ex}")


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
    out_dir = app_state.global_output_file
    os.makedirs(out_dir, exist_ok=True)

    try:
        # 连接到 SQLite 数据库
        with sqlite3.connect('novel.db') as db:
            # 创建游标
            cursor = db.cursor()
            count_query = f"SELECT COUNT(*) FROM novel_scene WHERE novel_id = '{app_state.global_novel_id}'"
            cursor.execute(count_query)
            record_count = cursor.fetchone()[0]

            # 查询 novel_scene 表中 novel_id 等于 global_novel_id 的场景下的原文
            query = f"SELECT scene_id, visual_description, positive_words, negative_words FROM novel_scene WHERE novel_id = '{app_state.global_novel_id}'"
            cursor.execute(query)

            current_step = 0

            for (scene_id, visual_description, positive_words, negative_words) in cursor:
                negative_prompt = app_state.negative_prompts if not negative_words else negative_words

                payload = {
                    "prompt": positive_words,
                    "negative_prompt": negative_prompt,
                    "seed": -1,
                    "steps": 20,
                    "width": 1232,
                    "height": 928,
                    "restore_faces": "true",
                    "cfg_scale": 7,
                    "sampler_name": "DPM++ 2M",
                    "n_iter": 1,
                    "batch_size": 1,
                }

                if not app_state.webui_server_url.startswith(
                        "http://localhost") and not app_state.webui_server_url.startswith(
                    "http://127.0.0.1"):
                    payload["enable_hr"] = "true"
                    payload["hr_upscaler"] = "Latent"
                    payload["hr_scale"] = 2
                    payload["hr_resize_x"] = 2464
                    payload["hr_resize_y"] = 1856
                    payload["hr_sampler_name"] = "Euler a"
                    payload["hr_second_pass_steps"] = 10
                    payload["denoising_strength"] = 0.7

                call_txt2img_api(scene_id, out_dir, **payload)

                # 更新进度条
                current_step += 1
                progress = 40 + (current_step / record_count) * 100 * 0.3
                app_state.progress_bar['value'] = progress
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
                    "seed": -1,
                    "steps": 20,
                    "width": 1232,
                    "height": 928,
                    "denoising_strength": 0.2,
                    "n_iter": 1,
                    "init_images": init_images,
                    "image_cfg_scale": 0,
                    # "batch_size": batch_size if len(init_images) == 1 else len(init_images),
                    "batch_size": batch_size,
                    "script_name": "SD upscale",
                    "script_args": ["None", 64, "R-ESRGAN 4x+", 2],
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
                app_state.progress_bar['value'] = progress
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
            query = f"SELECT scene_id, original_description, image_path, hr_image_path, audio_path, audio_duration FROM novel_scene WHERE novel_id = '{app_state.global_novel_id}'"
            cursor.execute(query)

            newdraft = Draft(app_state.global_novel_name)

            for (scene_id, original_description, image_path, hr_image_path, audio_path, audio_duration) in cursor:
                photo = Material(hr_image_path)
                audio = Material(audio_path)
                newdraft.add_media_to_materials(photo)
                newdraft.add_media_to_materials(audio)
                newdraft.add_media_to_track(photo)
                newdraft.add_media_to_track(audio)

                word_count = len(original_description)
                average_time_per_word = int(audio_duration) / word_count
                # sentences = original_description.split("。")
                # sentences = [sentence.strip() for sentence in sentences if sentence.strip()]
                sentences = []

                # 根据 current_interface 判断句子的分割方式
                if app_state.current_interface == "douyin":
                    # 对于抖音，按中文句号“。”分割
                    sentences = [sentence.strip() for sentence in original_description.split("。") if sentence.strip()]
                elif app_state.current_interface == "TikTok":
                    # 对于 TikTok，按所有英文标点符号分割
                    sentences = [sentence.strip() for sentence in re.split(r'[.!?;:]+', original_description) if
                                 sentence.strip()]
                else:
                    # 对其他接口的处理，默认按英文标点分割
                    sentences = [sentence.strip() for sentence in re.split(r'[.!?;:]+', original_description) if
                                 sentence.strip()]

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
    app_state.api_key = app_state.api_key_entry.get()

    if app_state.api_key:
        with open(".env", "w") as f:
            f.write(f"DEEPSEEK_API_KEY={app_state.api_key}")
        os.environ["DEEPSEEK_API_KEY"] = app_state.api_key
        app_state.client = OpenAI(
            base_url="https://api.deepseek.com",
            api_key=app_state.api_key
        )


def toggle_selection(event):
    selected_item = app_state.column_listbox.curselection()
    if selected_item:
        index = selected_item[0]
        if app_state.column_listbox.selection_includes(index):
            app_state.column_listbox.selection_set(index)
        else:
            app_state.column_listbox.selection_clear(index)


def close_window():
    window.destroy()


# 创建主窗口
window = tk.Tk()
window.title("转为剪映草稿")
window.geometry("900x800")
window.config(bg="#f0f0f0")  # 设置背景颜色

# 创建两个Frame：一个用于抖音页面，另一个用于TikTok页面
# 创建Frame用于抖音页面
frame_douyin = tk.Frame(window, bg="#f0f0f0")
frame_douyin.grid(row=0, column=0, sticky="nsew")
frame_douyin.grid_forget()  # 默认不显示抖音页面

# 创建Frame用于TikTok页面
frame_tiktok = tk.Frame(window, bg="#f0f0f0")
frame_tiktok.grid(row=0, column=0, sticky="nsew")
frame_tiktok.grid_forget()  # 默认不显示TikTok页面

# 设置窗口布局，使得frame_douyin和frame_tiktok可以扩展
window.grid_rowconfigure(0, weight=1)
window.grid_columnconfigure(0, weight=1)

# 创建按钮框架
button_frame = tk.Frame(window, bg="#f0f0f0")
button_frame.grid(row=1, column=0, pady=20)

# 页面切换按钮，横向排列
button_douyin = tk.Button(button_frame, text="切换到抖音", command=lambda: toggle_page("douyin"), font=("Arial", 14),
                          relief="solid", width=15)
button_douyin.grid(row=0, column=0, padx=20)

button_tiktok = tk.Button(button_frame, text="切换到TikTok", command=lambda: toggle_page("tiktok"), font=("Arial", 14),
                          relief="solid", width=15)
button_tiktok.grid(row=0, column=1, padx=20)


# 切换模型的函数
def toggle_model_usage():
    """切换模型使用模式"""
    app_state.use_local_model = not app_state.use_local_model

    # 更新模型状态标签
    app_state.model_status_label.config(
        text=f"当前模型: {'本地模型 (Ollama)' if app_state.use_local_model else 'OpenAI API'}"
    )

    # 切换时根据模型状态隐藏或显示API密钥设置框
    if app_state.use_local_model:
        # 隐藏API密钥设置框
        app_state.api_key_label.grid_forget()
        app_state.api_key_entry.grid_forget()
        app_state.api_key_button.grid_forget()
    else:
        # 显示API密钥设置框
        app_state.api_key_label.grid(row=2, column=1, padx=5, pady=5)
        app_state.api_key_entry.grid(row=2, column=2, padx=5, pady=5)
        app_state.api_key_button.grid(row=2, column=3, padx=5, pady=5)


# 切换音频模型
def toggle_audio_model():
    if app_state.current_audio_model == "pyttsx3":
        app_state.current_audio_model = "gpt_sovits"
        app_state.audio_model_status_label.config(text="当前音频模型: gpt_sovits")
        app_state.audio_file_entry.grid(row=4, column=1, columnspan=2, pady=5)
        app_state.audio_file_button.grid(row=4, column=3, padx=5, pady=5)
        app_state.audiotxt_model_status_label.grid(row=5, column=0, padx=5, pady=5, sticky="w")
        app_state.audiotxt_file_entry.grid(row=5, column=1, columnspan=2, pady=5)
        app_state.audiotxt_file_button.grid(row=5, column=3, padx=5, pady=5, sticky="w")

    else:
        app_state.current_audio_model = "pyttsx3"
        app_state.audio_model_status_label.config(text="当前音频模型: pyttsx3")
        app_state.audio_file_entry.grid_forget()
        app_state.audio_file_button.grid_forget()
        app_state.audiotxt_model_status_label.grid_forget()
        app_state.audiotxt_file_entry.grid_forget()
        app_state.audiotxt_file_button.grid_forget()


# 设置API密钥
def set_api_key():
    entered_key = app_state.api_key_entry.get()
    if entered_key:
        # 更新环境变量
        os.environ["DEEPSEEK_API_KEY"] = entered_key
        # 更新客户端实例
        app_state.client = OpenAI(
            base_url="https://api.deepseek.com/",
            api_key=entered_key
        )
        # 保存到文件（可选）
        with open("deepseek_api_key.txt", "w") as f:
            f.write(entered_key)


def select_file():
    file_path = filedialog.askopenfilename(title="选择要处理的文件", filetypes=[("Excel Files", "*.xlsx;*.xls")])
    # 从文件路径中提取文件名作为小说名称
    file_name = os.path.basename(file_path)
    novel_name = os.path.splitext(file_name)[0]

    app_state.file_entry.delete(0, tk.END)
    app_state.file_entry.insert(0, file_path)
    load_columns(file_path)
    # 将小说名称插入主表

    app_state.global_novel_name = novel_name
    app_state.global_novel_id = insert_novel_name(novel_name)
    app_state.global_output_file = os.path.dirname(file_path)


def select_wav_file():
    """选择WAV文件"""
    file_path = filedialog.askopenfilename(filetypes=[("WAV Files", "*.wav")])
    if file_path:
        app_state.audio_file_entry.delete(0, tk.END)
        app_state.audio_file_entry.insert(0, file_path)


def select_txt_file():
    """选择TXT文件"""
    file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
    if file_path:
        app_state.audiotxt_file_entry.delete(0, tk.END)
        app_state.audiotxt_file_entry.insert(0, file_path)


# 本地SD的API配置
def load_webui_server_url():
    try:
        # 尝试读取配置文件中的webui_server_url
        with open('./webui_server_url.txt', 'r') as file:
            app_state.webui_server_url = file.read().strip()
    except FileNotFoundError:
        # 文件未找到时，使用默认值
        app_state.webui_server_url = app_state.default_webui_server_url

    # 如果没有获取到有效的URL，使用默认URL
    if not app_state.webui_server_url:
        app_state.webui_server_url = app_state.default_webui_server_url

    # 测试webui_server_url是否联通，并设置超时保护
    try:
        response = requests.get(app_state.webui_server_url, timeout=5)  # 设置超时5秒
        if response.status_code != 200:
            # 如果状态码不是200，使用默认URL
            app_state.webui_server_url = app_state.default_webui_server_url
    except requests.exceptions.RequestException:
        # 处理请求异常，如连接超时、DNS解析错误等
        app_state.webui_server_url = app_state.default_webui_server_url
    return app_state.webui_server_url


# 公共函数：用于添加模型切换按钮、状态标签等
def add_model_toggle_and_status(frame):
    # 切换模型按钮
    app_state.model_toggle_button = tk.Button(frame, text=f"切换文字模型", command=toggle_model_usage,
                                              font=("Arial", 12),
                                              relief="solid", width=20)
    app_state.model_toggle_button.grid(row=1, column=0, columnspan=4, pady=10)

    # 状态标签
    app_state.model_status_label = tk.Label(frame, text=f"当前文字模型: OpenAI API", font=("Arial", 12), bg="#f0f0f0")
    app_state.model_status_label.grid(row=2, column=0, padx=5, pady=5, sticky="w")

    # OpenAI API密钥输入框部分，设置它们在同一行显示
    app_state.api_key_label = tk.Label(frame, text="OpenAI API密钥:", font=("Arial", 12), bg="#f0f0f0")
    app_state.api_key_label.grid(row=2, column=1, padx=5, pady=5, sticky="w")

    app_state.api_key_entry = tk.Entry(frame, width=40, font=("Arial", 12))
    app_state.api_key_entry.grid(row=2, column=2, padx=5, pady=5)

    # 设置默认值（新增代码）
    try:
        with open('deepseek_api_key.txt', 'r') as f:
            default_key = f.read().strip()
    except FileNotFoundError:
        default_key = os.getenv("DEEPSEEK_API_KEY", "")
    app_state.api_key_entry.insert(0, default_key)  # 插入默认值

    app_state.api_key_button = tk.Button(frame, text="设置API密钥", command=set_api_key, font=("Arial", 12),
                                         relief="solid", width=20)
    app_state.api_key_button.grid(row=2, column=3, padx=5, pady=5)
    # 如果初始状态是本地模型，主动隐藏组件
    if app_state.use_local_model:
        app_state.api_key_label.grid_remove()
        app_state.api_key_entry.grid_remove()
        app_state.api_key_button.grid_remove()

    return app_state.model_status_label


def add_audio_toggle_and_status(frame):
    # 增加切换音频模型按钮
    app_state.audio_model_toggle_button = tk.Button(frame, text="切换音频模型", command=toggle_audio_model,
                                                    font=("Arial", 12),
                                                    relief="solid", width=20)
    app_state.audio_model_toggle_button.grid(row=3, column=0, columnspan=4, pady=10)

    # 增加状态标签
    app_state.audio_model_status_label = tk.Label(frame, text="当前音频模型: gpt_sovits", font=("Arial", 12),
                                                  bg="#f0f0f0")
    app_state.audio_model_status_label.grid(row=4, column=0, padx=5, pady=5, sticky="w")

    # 音频文件选择部分

    app_state.audio_file_entry = tk.Entry(frame, width=40, font=("Arial", 12))
    app_state.audio_file_entry.grid(row=4, column=1, columnspan=2, pady=5)

    app_state.audio_file_button = tk.Button(frame, text="选择WAV文件", command=select_wav_file, font=("Arial", 12),
                                            relief="solid",
                                            width=20)
    app_state.audio_file_button.grid(row=4, column=3, padx=5, pady=5, sticky="w")
    # 增加状态标签

    app_state.audiotxt_model_status_label = tk.Label(frame, text="音频模型参考TXT:", font=("Arial", 12), bg="#f0f0f0")
    app_state.audiotxt_model_status_label.grid(row=5, column=0, padx=5, pady=5, sticky="w")

    # 音频文件选择部分

    app_state.audiotxt_file_entry = tk.Entry(frame, width=40, font=("Arial", 12))
    app_state.audiotxt_file_entry.grid(row=5, column=1, columnspan=2, pady=5)

    app_state.audiotxt_file_button = tk.Button(frame, text="选择参考TXT文件", command=select_txt_file,
                                               font=("Arial", 12),
                                               relief="solid",
                                               width=20)
    app_state.audiotxt_file_button.grid(row=5, column=3, padx=5, pady=5, sticky="w")

    return app_state.audio_model_status_label


def add_file_select_and_column_select(frame):
    # 文件选择部分
    app_state.file_label = tk.Label(frame, text="选择要处理的文件:", font=("Arial", 12), bg="#f0f0f0")
    app_state.file_label.grid(row=6, column=0, padx=5, pady=5, sticky="w")

    app_state.file_entry = tk.Entry(frame, width=40, font=("Arial", 12))
    app_state.file_entry.grid(row=6, column=1, columnspan=2, pady=5)

    app_state.file_button = tk.Button(frame, text="选择文件", command=select_file, font=("Arial", 12), relief="solid",
                                      width=20)
    app_state.file_button.grid(row=6, column=3, padx=5, pady=5)

    # 列选择部分
    app_state.columns_label = tk.Label(frame, text="选择要提取的列（多选）:", font=("Arial", 12), bg="#f0f0f0")
    app_state.columns_label.grid(row=7, column=0, padx=5, pady=5, sticky="w")

    app_state.column_listbox = tk.Listbox(frame, selectmode=tk.MULTIPLE, font=("Arial", 12))
    app_state.column_listbox.grid(row=7, column=1, columnspan=2, pady=10)  # 使用columnspan横跨3列

    app_state.column_listbox.bind('<<ListboxSelect>>', toggle_selection)

    return app_state.file_entry, app_state.file_button, app_state.column_listbox


def add_progress_bar_and_process_button(frame):
    # 进度条
    app_state.progress_label = tk.Label(frame, text="处理进度:", font=("Arial", 12), bg="#f0f0f0")
    app_state.progress_label.grid(row=8, column=0, padx=5, pady=5, sticky="w")

    app_state.progress_bar = ttk.Progressbar(frame, length=300, mode='determinate')
    app_state.progress_bar.grid(row=8, column=1, columnspan=2, pady=10)  # 使用columnspan横跨3列

    # 处理按钮
    app_state.process_button = tk.Button(frame, text="处理文件", command=process_file, font=("Arial", 12),
                                         relief="solid",
                                         width=20)
    app_state.process_button.grid(row=9, column=0, columnspan=4, pady=20)  # 横跨4列

    # 状态标签
    app_state.status_label = tk.Label(frame, text="状态信息", font=("Arial", 12), bg="#f0f0f0")
    app_state.status_label.grid(row=10, column=0, columnspan=4, pady=5)  # 横跨4列

    return app_state.progress_bar, app_state.process_button, app_state.status_label


# 页面显示函数，减少重复代码
def show_page(frame, model_name, page_title):
    # 显示欢迎标签
    label = tk.Label(frame, text=page_title, font=("Arial", 20, "bold"), bg="#f0f0f0")
    label.grid(row=0, column=0, columnspan=4, pady=20)
    # 添加模型切换和状态标签
    app_state.model_status_label = add_model_toggle_and_status(frame)
    # 添加音频模型切换和状态标签
    app_state.audio_model_status_label = add_audio_toggle_and_status(frame)
    # 添加文件选择和列选择功能
    app_state.file_entry, app_state.file_button, app_state.column_listbox = add_file_select_and_column_select(frame)
    # 添加进度条和处理按钮
    app_state.progress_bar, app_state.process_button, app_state.status_label = add_progress_bar_and_process_button(
        frame)
    return app_state.model_status_label, app_state.audio_model_status_label, app_state.file_entry, app_state.file_button, app_state.column_listbox, app_state.progress_bar, app_state.process_button, app_state.status_label


# 抖音页面内容
def show_douyin():
    app_state.current_interface = "Douyin"
    load_webui_server_url()
    frame_douyin.grid_forget()
    frame_tiktok.grid_forget()
    frame_douyin.grid(row=0, column=0, sticky="nsew")
    # 调用通用页面显示函数
    app_state.model_status_label, app_state.audio_model_status_label, app_state.file_entry, app_state.file_button, app_state.column_listbox, app_state.progress_bar, app_state.process_button, app_state.status_label = show_page(
        frame_douyin, "Douyin", "抖音业务页面！")

    # 可以在这里添加特定于抖音的额外功能


# TikTok页面内容
def show_tiktok():
    app_state.current_interface = "TikTok"
    load_webui_server_url()
    frame_douyin.grid_forget()
    frame_tiktok.grid_forget()
    frame_tiktok.grid(row=0, column=0, sticky="nsew")
    # 调用通用页面显示函数
    app_state.model_status_label, app_state.audio_model_status_label, app_state.file_entry, app_state.file_button, app_state.column_listbox, app_state.progress_bar, app_state.process_button, app_state.status_label = show_page(
        frame_tiktok, "TikTok", "TikTok业务页面！")

    # 可以在这里添加特定于TikTok的额外功能


# 切换页面的函数
def toggle_page(page):
    if page == "douyin":
        show_douyin()
    elif page == "tiktok":
        show_tiktok()


# 在窗口关闭时释放资源
window.protocol("WM_DELETE_WINDOW", lambda: (close_local_model(), window.destroy()))

# 运行主循环
if __name__ == "__main__":
    window.mainloop()
