import os
import uuid
import glob
from flask import Flask, request, jsonify, send_file, render_template

app = Flask(__name__)
# Use absolute path to the directory where app.py is located
import tempfile
DOWNLOADS_DIR = tempfile.gettempdir()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/info', methods=['POST'])
def get_info():
    import yt_dlp
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
    }
    
    # Add cookies if the file exists to avoid "Sign in to confirm you're not a bot" error
    cookies_path = os.path.join(os.path.dirname(__file__), 'cookies.txt')
    if os.path.exists(cookies_path):
        import shutil
        tmp_cookies = os.path.join(DOWNLOADS_DIR, 'cookies.txt')
        try:
            shutil.copyfile(cookies_path, tmp_cookies)
            ydl_opts['cookiefile'] = tmp_cookies
        except Exception as e:
            print(f"Error copying cookies: {e}")
            ydl_opts['cookiefile'] = cookies_path
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({
                'title': info.get('title'),
                'thumbnail': info.get('thumbnail'),
                'duration': info.get('duration'),
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/download', methods=['POST'])
def download():
    import yt_dlp
    data = request.json
    url = data.get('url')
    format_type = data.get('type')

    if not url or format_type not in ['audio', 'video']:
        return jsonify({'error': 'Invalid request'}), 400

    file_id = str(uuid.uuid4())
    
    import imageio_ffmpeg
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

    if format_type == 'audio':
        ydl_opts = {
            'format': 'bestaudio',
            'outtmpl': os.path.join(DOWNLOADS_DIR, f'{file_id}.%(ext)s'),
            'quiet': True,
            'ffmpeg_location': ffmpeg_path,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            }
        }
    else:
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': os.path.join(DOWNLOADS_DIR, f'{file_id}.%(ext)s'),
            'quiet': True,
            'ffmpeg_location': ffmpeg_path,
            'merge_output_format': 'mp4',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            }
        }

    # Add cookies if the file exists to avoid "Sign in to confirm you're not a bot" error
    cookies_path = os.path.join(os.path.dirname(__file__), 'cookies.txt')
    if os.path.exists(cookies_path):
        import shutil
        tmp_cookies = os.path.join(DOWNLOADS_DIR, 'cookies.txt')
        try:
            shutil.copyfile(cookies_path, tmp_cookies)
            ydl_opts['cookiefile'] = tmp_cookies
        except Exception as e:
            print(f"Error copying cookies: {e}")
            ydl_opts['cookiefile'] = cookies_path

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'download')
            
            # Find the downloaded file
            search_pattern = os.path.join(DOWNLOADS_DIR, f"{file_id}.*")
            files = glob.glob(search_pattern)
            
            if not files:
                return jsonify({'error': 'Download failed to save file'}), 500
                
            file_path = files[0]
            ext = os.path.splitext(file_path)[1]
            
            clean_title = "".join(x for x in title if x.isalnum() or x in " -_")
            download_name = f"{clean_title}{ext}"

        # We return the file. Since send_file may block deletion, we'll leave it in the folder 
        # and periodically clean up or let the user do it.
        return send_file(
            file_path,
            as_attachment=True,
            download_name=download_name
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
