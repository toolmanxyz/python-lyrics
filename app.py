import gradio as gr
import numpy as np
import re
import requests
from PIL import Image, ImageDraw, ImageFont
from pydub import AudioSegment
from moviepy.editor import *
from moviepy.video.fx.all import *


def main(lyric_file, music_file, background_video):
    # 使用 gradio 讓使用者上傳相關的檔案，並在 `.name` 讀取路徑
    lyric_file_path = lyric_file.name
    music_file_path = music_file.name
    if background_video:
        background_video = background_video.name
    else:
        background_video = None

    # 下載字型，我用的是正體中文的字型，別的語言的字會沒有辦法顯示
    response = requests.get("https://github.com/justfont/open-huninn-font/releases/download/v2.0/jf-openhuninn-2.0.ttf")
    with open("jf-openhuninn-2.0.ttf", "wb") as file:
        file.write(response.content)

    # 載入音樂檔
    audio = AudioSegment.from_file(music_file_path)

    # 讀取歌詞
    with open(lyric_file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    lyrics = []
    pattern = re.compile(r'\[(\d+):(\d+\.\d+)\](.*)')  # [12:34]歌詞內容

    for line in lines:
        match = pattern.match(line)
        if match:
            minutes = int(match.group(1))
            seconds = float(match.group(2))
            lyric = match.group(3).strip()

            # 轉換時間為毫秒
            start_time = (minutes * 60 + seconds) * 1000

            lyrics.append((start_time, lyric))

    # 找到最長的一句歌詞的歌詞長度
    longest_lyric = len(max(lyrics, key=lambda x: len(x[1]))[1])

    # 創建一個空的影片片段列表
    clips = []

    # 為了讓最後一行歌詞也能顯示，可以把音樂的總長度加到 lyrics 裡面
    # 注意：音樂的長度需以毫秒為單位
    audio_length = len(audio) # pydub 的 AudioSegment 會返回音樂的長度（毫秒）
    lyrics.append((audio_length, ""))

    font_path = 'jf-openhuninn-2.0.ttf'
    font = ImageFont.truetype(font_path)

    # 建立影片片段
    for i in range(len(lyrics) - 1):
        start_time, lyric = lyrics[i]
        next_start_time = lyrics[i + 1][0]

        # 計算此行歌詞應該持續的時間
        duration = (next_start_time - start_time) / 1000.0 # 轉換為秒

        # 設定字型和字型大小
        font_size = 188
        # 根據該行歌詞的字數，動態調整字體大小
        font_size = int(font_size - (font_size - (font_size - 100)) * (len(lyric) / longest_lyric))

        # 設定文字顏色和背景顏色
        text_color = (255, 255, 255)  # 白色
        bg_color = (0, 0, 0)  # 黑色

        # 創建一個空白圖像 (1080p)
        image = Image.new('RGB', (1920, 1080), bg_color)

        # 載入字型
        font = ImageFont.truetype(font_path, font_size)

        # 在圖像上繪製文字
        draw = ImageDraw.Draw(image)
        left, top, right, bottom = draw.textbbox((0, 0), str(lyric), font=font)
        text_width, text_height = right - left, bottom - top
        text_position = ((image.width - text_width) // 2, (image.height - text_height) // 2)
        draw.text(text_position, lyric, font=font, fill=text_color)

        # 將圖像轉換為 NumPy 陣列
        image_array = np.array(image)

        # 將 NumPy 陣列轉換為 ImageClip
        image_clip = ImageClip(image_array, duration=duration)

        # 設定顯示的時間
        image_clip = image_clip.set_start(start_time / 1000.0).set_duration(duration)

        clips.append(image_clip)

    # 合併所有影片片段
    video = concatenate_videoclips(clips)

    # 插入背景影片、動畫
    if background_video:
        video = mask_color(video, color=[0, 0, 0])  # ,thr=10,s=0

        # 背景影片
        background_video = VideoFileClip(background_video)
        background_video_repeated = background_video.loop(duration = video.duration)

        video = CompositeVideoClip([background_video_repeated, video])

    # 設定背景音樂
    video = video.set_audio(AudioFileClip(music_file_path))

    # 輸出影片，要設定 `codec`, `audio_codec` 才會同時有畫面和聲音
    # 參考: https://steam.oxxostudio.tw/category/python/example/video-audio.html
    video.write_videofile("output.mp4", codec="libx264", audio_codec="aac", fps=25)
    
    return gr.PlayableVideo("output.mp4")


iface = gr.Interface(fn=main, inputs=["file", "file", "file"], outputs="video", title="歌詞影片製作")
iface.launch()