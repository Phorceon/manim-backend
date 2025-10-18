from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import subprocess
import os
import tempfile
import uuid
from pathlib import Path

app = Flask(__name__)
CORS(app)

VIDEOS_DIR = Path("generated_videos")
VIDEOS_DIR.mkdir(exist_ok=True)

@app.route('/generate-video', methods=['POST'])
def generate_video():
    try:
        data = request.json
        manim_code = data.get('code')
        
        if not manim_code:
            return jsonify({'error': 'No code provided'}), 400
        
        video_id = str(uuid.uuid4())
        temp_dir = tempfile.mkdtemp()
        
        script_path = os.path.join(temp_dir, 'scene.py')
        with open(script_path, 'w') as f:
            f.write(manim_code)
        
        result = subprocess.run(
            ['manim', '-ql', '-o', f'{video_id}.mp4', script_path],
            cwd=temp_dir,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            return jsonify({
                'error': 'Manim rendering failed',
                'details': result.stderr
            }), 400
        
        video_path = None
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith('.mp4'):
                    video_path = os.path.join(root, file)
                    break
        
        if not video_path:
            return jsonify({'error': 'Video file not found after rendering'}), 400
        
        final_path = VIDEOS_DIR / f'{video_id}.mp4'
        os.makedirs(VIDEOS_DIR, exist_ok=True)
        os.rename(video_path, final_path)
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'video_url': f'/watch-video/{video_id}'
        })
    
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Rendering took too long (timeout)'}), 408
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/watch-video/<video_id>', methods=['GET'])
def watch_video(video_id):
    try:
        video_path = VIDEOS_DIR / f'{video_id}.mp4'
        if not video_path.exists():
            return jsonify({'error': 'Video not found'}), 404
        return send_file(video_path, mimetype='video/mp4')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
