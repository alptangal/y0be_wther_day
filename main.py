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
print(str(driver))

