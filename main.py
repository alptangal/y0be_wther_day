from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.service import Service as ChromiumService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from PIL import Image
from gtts import gTTS
import subprocess
import os
import random
import speech_recognition as sr
from pydub import AudioSegment
import re
import emoji

def remove_special_characters(string):
    pattern = r'[^a-zA-Z0-9\s]'
    cleaned_string = re.sub(pattern, '', string)
    return ' '.join(cleaned_string.split())

def remove_emojis(text):
    text = emoji.demojize(text)
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
    try:
        post_content = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//shreddit-post'))
        )
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
    except Exception as e:
        print(f"Error capturing screenshot: {str(e)}")
        return None

def generate_voice(text, save_path):
    stop = False
    while not stop:
        try:
            tts = gTTS(text, lang='en')
            tts.save(save_path)
            stop = True
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
    return '\\n'.join(lines)

def create_ffmpeg_subtitle_filter(subtitles):
    subtitle_filters = []
    for i, sub in enumerate(subtitles):
        start_time = sub['start']
        end_time = sub['end']
        word = escape_text_for_ffmpeg(sub['word'])
        if word:
            fontsize = random.randint(64, 160)
            subtitle_filters.append(
                f"drawtext=fontfile=/path/to/font.ttf:fontsize={fontsize}:fontcolor=yellow:box=1:boxcolor=black@0.5:boxborderw=5:x=(w-tw)/2:y=h-th-200:text='{word}':enable='between(t,{start_time},{end_time})'"
            )
    return ','.join(subtitle_filters) if subtitle_filters else 'null'

def check_file_exists(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return False
    return True

options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--disable-features=NetworkService")
options.add_argument("--disable-features=VizDisplayCompositor")
options.add_argument('--ignore-certificate-errors')
options.add_argument("--window-size=1920,1080")
options.add_argument("--start-maximized")
options.add_argument("--disable-extensions")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.71 Safari/537.36")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.get("https://www.reddit.com")
WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'article.w-full.m-0')))
posts = driver.find_elements(By.CSS_SELECTOR, 'article.w-full.m-0')[:3]

post_data = []
video_clips = []
for post in posts:
    title_element = post.find_element(By.CSS_SELECTOR, 'a.absolute.inset-0')
    title = title_element.text
    url = title_element.get_attribute('href')
    post_data.append({'title': title, 'url': url})

for i, post in enumerate(post_data, start=1):
    driver.get(post['url'])
    time.sleep(5)  # Increased wait time

    post_image = capture_post_screenshot(driver)
    if post_image is None:
        print(f"Failed to capture screenshot for post {i}. Skipping...")
        continue

    post_screenshot_path = os.path.abspath(f"post_{i}.png")
    post_image.save(post_screenshot_path)

    background_image_path = os.path.abspath(f"post_{i}_fullview.png")
    fullview_screenshot = capture_full_screenshot(driver)
    with open(background_image_path, 'wb') as f:
        f.write(fullview_screenshot)

    ensure_even_dimensions(background_image_path)
    ensure_even_dimensions(post_screenshot_path)

    audio_path = os.path.abspath(f"post_{i}_audio.mp3")
    generate_voice(post['title'], audio_path)

    subtitles = generate_subtitles(audio_path, post['title'])
    subtitle_path = os.path.abspath(f"subtitles_{i}.txt")
    create_subtitle_file(subtitles, subtitle_path)

    video_output_path = os.path.abspath(f"post_{i}_final.mp4")

    subtitle_filter = create_ffmpeg_subtitle_filter(subtitles)
    escaped_title = escape_text_for_ffmpeg(post['title'])

    if all(check_file_exists(f) for f in [background_image_path, post_screenshot_path, audio_path]):
        wrapped_title = create_wrapped_title(escaped_title)
        wrapped_title = remove_emojis(wrapped_title)
        wrapped_title = remove_special_characters(wrapped_title)
        filter_complex = (
            "[0:v]scale=1920:-1,boxblur=6:2[bg];"
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
            print(f"FFmpeg command: {' '.join(ffmpeg_command)}")
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
concat_file = os.path.abspath("concat.txt")
if video_clips:
    concat_file = os.path.abspath("concat.txt")
    with open(concat_file, 'w') as f:
        for clip in video_clips:
            if os.path.exists(clip):
                f.write(f"file '{clip}'\n")
    
    with open(concat_file, 'r') as f:
        print("Contents of concat.txt:")
        print(f.read())
    
    if os.path.getsize(concat_file) > 0:
        final_video_path = os.path.abspath("final_video.mp4")
        ffmpeg_concat_command = [
            "ffmpeg",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            final_video_path
        ]
        try:
            subprocess.run(ffmpeg_concat_command, check=True)
            print(f"Final video created: {final_video_path}")
        except subprocess.CalledProcessError as e:
            print(f"Error concatenating videos: {e}")
    else:
        print("No valid video clips to concat.")
else:
    print("No video clips were created.")

# Clean up temporary files
for file in [concat_file] + video_clips:
    if os.path.exists(file):
        os.remove(file)

print("Video creation process completed.")