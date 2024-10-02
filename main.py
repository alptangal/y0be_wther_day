import os,sys
import time
import subprocess
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
from gtts import gTTS
import server,requests

# Initialize Firefox WebDriver
def init_webdriver():
    options = Options()
    options.add_argument('-headless')  # Run in headless mode
    options.binary_location = '/usr/bin/geckodriver'
    #service = Service(FirefoxDriverManager(chrome_type=FirefoxType.CHROMIUM).install())  # Path to your geckodriver
    driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options)
    return driver

# Function to capture Reddit posts and create audio files
def capture_reddit_posts(driver):
    driver.get('https://www.reddit.com/r/all/new')
    time.sleep(5)  # Wait for the page to load

    posts = driver.find_elements("css selector", "article.w-full.m-0")[:2]  # Limit to 2 posts
    images = []
    audios = []

    for index, post in enumerate(posts):
        title_link = post.find_element("css selector", "a.absolute.inset-0")
        title_text = title_link.text

        # Create a screenshot for each post
        screenshot_path = f'reddit_post_{index}.png'
        post.screenshot(screenshot_path)
        images.append(screenshot_path)

        # Convert title to speech
        audio_path = f'reddit_post_audio_{index}.mp3'
        tts = gTTS(text=title_text, lang='en')
        tts.save(audio_path)
        audios.append(audio_path)

    return images, audios

# Function to stream to YouTube using FFmpeg
def start_stream_to_youtube(image_files, audio_files, stream_key):
    ffmpeg_command = [
        'ffmpeg',
        '-stream_loop', '-1',  # Loop the images
        '-i', audio_files[0],  # Use the first audio file
        '-i', image_files[0],  # Use the first image file
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-vf', 'fps=1',  # Set frame rate to 1 fps
        '-pix_fmt', 'yuv420p',
        '-f', 'flv',  # Output format
        f'rtmp://a.rtmp.youtube.com/live2/{stream_key}'  # RTMP URL
    ]

    print("Starting the stream to YouTube...")
    subprocess.Popen(ffmpeg_command)

# Main function
def main():
    driver = init_webdriver()
    stream_key = 'pmfq-5pc5-u1e8-5s1p-caqf'  # Replace with your YouTube stream key

    try:
        while True:
            images, audios = capture_reddit_posts(driver)
            start_stream_to_youtube(images, audios, stream_key)

            time.sleep(60)  # Wait before capturing new posts

    except KeyboardInterrupt:
        print("Streaming stopped.")
    finally:
        driver.quit()  # Close the WebDriver
try:
    req=requests.get('http://localhost:8888')
    print(req.status_code)
    print('Client closed')
    sys.exit()
except Exception as e:
    print(e)
    server.b()
    main()
