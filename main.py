from selenium import webdriver
from selenium.webdriver.common.by import By
import time
from PIL import Image
from gtts import gTTS
import subprocess
import os,random
import speech_recognition as sr
from pydub import AudioSegment
import re
import emoji

def remove_special_characters(string):
    # Định nghĩa pattern để giữ lại chữ cái, số và khoảng trắng
    pattern = r'[^a-zA-Z0-9\s]'
    
    # Thay thế các ký tự đặc biệt bằng chuỗi rỗng
    cleaned_string = re.sub(pattern, '', string)
    
    # Loại bỏ khoảng trắng thừa và trả về kết quả
    return ' '.join(cleaned_string.split())
def remove_emojis(text):
    # Chuyển đổi emoji thành mô tả Unicode
    text = emoji.demojize(text)
    
    # Xóa các mô tả Unicode của emoji
    text = re.sub(r':[a-zA-Z_]+:', '', text)
    
    return text


def scroll_to_element_center(driver, element):
    viewport_height = driver.execute_script("return window.innerHeight;")
    element_location = element.location['y']
    scroll_position = element_location - (viewport_height / 2)
    driver.execute_script(f"window.scrollTo(0, {scroll_position});")
    time.sleep(1)

def capture_full_screenshot(driver):
    return driver.get_screenshot_as_png()

def capture_post_screenshot(driver):
    post_content = driver.find_element(By.XPATH, '//shreddit-post')
    scroll_to_element_center(driver, post_content)
    full_screenshot = capture_full_screenshot(driver)
    temp_full_path = 'temp_full.png'
    with open(temp_full_path, 'wb') as f:
        f.write(full_screenshot)
    image = Image.open(temp_full_path)
    location = post_content.location
    size = post_content.size
    left = int(location['x'])
    top = int(location['y']) + 50
    right = left + int(size['width'])
    bottom = top + int(size['height'])
    cropped_image = image.crop((left, top, right, bottom))
    os.remove(temp_full_path)
    return cropped_image

def generate_voice(text, save_path):
    stop=False
    while not stop:
        try:
            tts = gTTS(text, lang='en')
            tts.save(save_path)
            stop=True
        except:
            pass
def ensure_even_dimensions(image_path):
    with Image.open(image_path) as img:
        width, height = img.size
        if height % 2 != 0:
            height += 1
        if width % 2 != 0:
            width += 1
        img = img.resize((width, height), Image.LANCZOS)
        img.save(image_path)

def generate_subtitles(audio_path, text):
    print(f"Generating subtitles for audio: {audio_path}")
    r = sr.Recognizer()
    audio = AudioSegment.from_mp3(audio_path)
    audio.export("temp.wav", format="wav")
    
    with sr.AudioFile("temp.wav") as source:
        audio_listened = r.record(source)
    
    try:
        print("Performing speech recognition...")
        recognized_text = r.recognize_google(audio_listened, language='en-US')
        words = recognized_text.split()
        
        duration = len(audio) / 1000.0
        time_per_word = duration / len(words)
        
        subtitles = []
        current_time = 0
        for word in words:
            start_time = current_time
            end_time = current_time + time_per_word
            subtitles.append({
                'word': word,
                'start': start_time,
                'end': end_time
            })
            current_time = end_time
        
        print(f"Generated {len(subtitles)} subtitle entries")
        os.remove("temp.wav")
        return subtitles
    except Exception as e:
        print(f"Error in speech recognition: {str(e)}")
        if os.path.exists("temp.wav"):
            os.remove("temp.wav")
        return []

def create_subtitle_file(subtitles, output_path):
    print(f"Creating subtitle file: {output_path}")
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            for sub in subtitles:
                f.write(f"{sub['start']:.3f},{sub['end']:.3f},{sub['word']}\n")
        print(f"Subtitle file created successfully: {output_path}")
    except Exception as e:
        print(f"Error creating subtitle file: {str(e)}")
def escape_text_for_ffmpeg(text):
    return text.replace("'", "'\\''").replace('"', '\\"').replace(':', '\\:').replace('\\', '\\\\')
def create_wrapped_title(title, max_line_length=100):
    words = title.split(' ')
    lines = []
    current_line = []
    current_length = 0
    
    for word in words:
        if current_length + len(word) + 1 <= max_line_length:
            current_line.append(word)
            current_length += len(word) + 1
        else:
            lines.append(' '.join(current_line))
            current_line = [word]
            current_length = len(word) + 1
    
    if current_line:
        lines.append(' '.join(current_line))
    return title
    return '\\n'.join(lines)

def create_ffmpeg_subtitle_filter(subtitles):
    subtitle_filters = []
    for i, sub in enumerate(subtitles):
        start_time = sub['start']
        end_time = sub['end']
        word = escape_text_for_ffmpeg(sub['word'])
        if word:  # Chỉ thêm filter nếu từ không trống
            fontsize = random.randint(64, 160)  # Random font size between 64 and 160
            subtitle_filters.append(
                f"drawtext=fontfile=/path/to/font.ttf:fontsize={fontsize}:fontcolor=yellow:box=1:boxcolor=black@0.5:boxborderw=5:x=(w-tw)/2:y=h-th-200:text='{word}':enable='between(t,{start_time},{end_time})'"
            )
    return ','.join(subtitle_filters) if subtitle_filters else 'null'

def check_file_exists(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return False
    return True
driver = webdriver.Firefox()
driver.get("https://www.reddit.com")

posts = driver.find_elements(By.CSS_SELECTOR, 'article.w-full.m-0')[:3]

post_data = []
video_clips = []
for post in posts:
    title_element = post.find_element(By.CSS_SELECTOR, 'a.absolute.inset-0')
    title = title_element.text
    url = title_element.get_attribute('href')
    post_data.append({'title': title, 'url': url})
def remove_credential_picker(driver):
    try:
        credential_picker = driver.find_element(By.ID, "credential_picker_container")
        driver.execute_script("arguments[0].remove();", credential_picker)
        print("Đã xoá div credential_picker_container.")
    except Exception as e:
        print("Div credential_picker_container không tồn tại hoặc không thể xoá: ", str(e))

for i, post in enumerate(post_data, start=1):
    driver.get(post['url'])
    time.sleep(3)

    # Gọi hàm để xoá div nếu tồn tại
    remove_credential_picker(driver)

    post_image = capture_post_screenshot(driver)
    post_screenshot_path = f"post_{i}.png"
    post_image.save(post_screenshot_path)

    background_image_path = f"post_{i}_fullview.png"
    fullview_screenshot = capture_full_screenshot(driver)
    with open(background_image_path, 'wb') as f:
        f.write(fullview_screenshot)

    ensure_even_dimensions(background_image_path)
    ensure_even_dimensions(post_screenshot_path)

    audio_path = f"post_{i}_audio.mp3"
    generate_voice(post['title'], audio_path)

    subtitles = generate_subtitles(audio_path, post['title'])
    subtitle_path = f"subtitles_{i}.txt"
    create_subtitle_file(subtitles, subtitle_path)

    video_output_path = f"post_{i}_final.mp4"

    subtitles = generate_subtitles(audio_path, post['title'])
    subtitle_filter = create_ffmpeg_subtitle_filter(subtitles)
    escaped_title = escape_text_for_ffmpeg(post['title'])

    if all(check_file_exists(f) for f in [background_image_path, post_screenshot_path, audio_path]):
        escaped_title = escape_text_for_ffmpeg(post['title'])
        wrapped_title = create_wrapped_title(escaped_title)
        wrapped_title=remove_emojis(wrapped_title)
        wrapped_title=remove_special_characters(wrapped_title)
        filter_complex = (
            "[0:v]scale=3840:-1,boxblur=6:2[bg];"
            "[1:v]scale=iw*3:ih*3[post];"
            "[bg][post]overlay=(W-w)/2:(H-h)/2[v1];"
            f"[v1]drawtext=fontfile=/path/to/font.ttf:fontsize=100:fontcolor=white:box=1:boxcolor=black@0.5:boxborderw=5:"
            f"x='w-mod(t*w/5,w+tw)':y=60:text='{wrapped_title}':shadowcolor=black:shadowx=2:shadowy=2[v2];"
        )
        
        if subtitle_filter != 'null':
            filter_complex += f"[v2]{subtitle_filter}[vout]"
        else:
            filter_complex += "[v2]null[vout]"

        ffmpeg_command = [
            "ffmpeg",
            "-y",
            "-loop", "1", "-i", background_image_path,
            "-i", post_screenshot_path,
            "-i", audio_path,
            "-filter_complex", filter_complex,
            "-map", "[vout]",
            "-map", "2:a",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-shortest",
            "-c:a", "aac", "-b:a", "192k",
            video_output_path
        ]

        try:
            print(f"Running FFmpeg command for post {i}")
            print(f"FFmpeg command: {' '.join(ffmpeg_command)}")  # Print the full command for debugging
            result = subprocess.run(ffmpeg_command, check=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
            print(f"FFmpeg stdout: {result.stdout}")
            print(f"FFmpeg stderr: {result.stderr}")
            if check_file_exists(video_output_path):
                video_clips.append(video_output_path)
            else:
                print(f"Error: Failed to create video file: {video_output_path}")
        except subprocess.CalledProcessError as e:
            print(f"Error running FFmpeg command for post {i}: {e}")
            print(f"FFmpeg error output: {e.stderr}")
    else:
        print(f"Skipping video creation for post {i} due to missing files.")
driver.quit()

video_clips = [f"post_{i}_final.mp4" for i in range(1, len(post_data) + 1)]
concat_file = "concat.txt"
with open(concat_file, 'w') as f:
    for clip in video_clips:
        f.write(f"file '{os.path.abspath(clip)}'\n")

final_video_path = "final_video.mp4"
ffmpeg_concat_command = [
    "ffmpeg",
    "-y",
    "-f", "concat", "-safe", "0", "-i", concat_file, "-c", "copy", final_video_path
]
subprocess.run(ffmpeg_concat_command)

os.remove(concat_file)
for clip in video_clips:
    os.remove(clip)

print("Video creation process completed.")