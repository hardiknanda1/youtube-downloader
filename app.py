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
    }
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
    
    if format_type == 'audio':
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'outtmpl': os.path.join(DOWNLOADS_DIR, f'{file_id}.%(ext)s'),
            'quiet': True,
        }
    else:
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': os.path.join(DOWNLOADS_DIR, f'{file_id}.%(ext)s'),
            'quiet': True,
        }

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
