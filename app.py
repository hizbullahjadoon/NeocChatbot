from flask import Flask, render_template, request, jsonify, session
import time
import base64
import os
import secrets
from newmain import newfunc  

app = Flask(__name__)
app.secret_key = 'your-very-secret-key'  # Needed for Flask sessions

# File upload configuration
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def clean_history(conversation_id):
    conversations = session.get('conversations', {})
    if conversation_id not in conversations:
        return []
    return [
        {k: v for k, v in entry.items() if k != 'image'}
        for entry in conversations[conversation_id]['history'][-3:]
    ]

def conversations(conv_id, user_message, mode, type, generate_image=False):
    if 'conversations' not in session:
        session['conversations'] = {}

    conversations = session['conversations']

    if conv_id not in conversations:
        title = user_message[:30] if type == "normal" else "Audio_" + user_message[:25]
        conversations[conv_id] = {
            'title': title,
            'history': [],
            'last_updated': time.time(),
            'mode': mode
        }

    message_entry = {
        'user': user_message,
        'timestamp': time.time()
    }

    conversations[conv_id]['history'].append(message_entry)
    cleaned_history = clean_history(conv_id)

    bot_response = newfunc(user_message, "search", mode=mode, chat_history=cleaned_history)
    conversations[conv_id]['history'][-1]['bot'] = bot_response
    conversations[conv_id]['last_updated'] = time.time()

    image_base64 = None
    if generate_image:
        image_base64 = newfunc(user_text=user_message, action="image", mode=mode, chat_history=cleaned_history)
        if image_base64:
            conversations[conv_id]['history'][-1]['image'] = image_base64

    if len(conversations[conv_id]['history']) == 1:
        conversations[conv_id]['title'] = user_message[:30]

    session['conversations'] = conversations
    return conv_id, image_base64, bot_response


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data.get('message')
    conversation_id = data.get('conversation_id')
    mode = data.get('mode', 'general')
    generate_image = data.get('generate_image', False)

    if not user_message:
        return jsonify({'error': 'Empty message'}), 400

    conv_id, image_base64, bot_response = conversations(
        conv_id=conversation_id,
        user_message=user_message,
        mode=mode,
        type="normal",
        generate_image=generate_image
    )

    return jsonify({
        'response': bot_response,
        'conversation_id': conv_id,
        'mode': mode,
        'image': image_base64
    })


@app.route("/chat-audio", methods=["POST"])
def chat_audio():
    data = request.get_json()
    audio_base64 = data.get("audio")
    conversation_id = data.get("conversation_id")
    mode = data.get("mode", "general")
    generate_image = data.get('generate_image', False)

    if not audio_base64:
        return jsonify({"message": "No audio provided"}), 400

    audio_data = base64.b64decode(audio_base64)
    data_uri = f"data:audio/wav;base64,{audio_base64}"
    cleaned_history = clean_history(conversation_id)

    user_message = newfunc(audio_data, "audio", mode=mode, chat_history=cleaned_history, path=audio_base64)

    conv_id, image_base64, bot_response = conversations(
        conv_id=conversation_id,
        user_message=user_message,
        mode=mode,
        type="normal",
        generate_image=generate_image
    )

    return jsonify({
        "reply": bot_response,
        "conversation_id": conv_id,
        "audio_base64": data_uri,
        "user_message": user_message,
        'image': image_base64
    })


@app.route('/api/new_chat', methods=['POST'])
def new_chat():
    data = request.get_json()
    mode = data.get('mode', 'general')

    if 'conversations' not in session:
        session['conversations'] = {}

    conversation_id = str(int(time.time() * 1000))
    session['conversations'][conversation_id] = {
        'title': 'New Chat',
        'history': [],
        'last_updated': time.time(),
        'mode': mode
    }

    return jsonify({
        'status': 'success',
        'conversation_id': conversation_id,
        'mode': mode
    })


@app.route('/upload', methods=['POST'])
def upload_file():
    files = request.files.getlist('files')
    names = [file.filename for file in files]

    try:
        newfunc('message', "insert", mode=request.form.get('mode'), chat_history=[], files=files)
        return jsonify({
            'status': 'success',
            'message': f'File(s) {names} processed successfully',
            'filename': names
        })

    except Exception as e:
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500


@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    return jsonify({'conversations': session.get('conversations', {})})


@app.route('/api/current_conversation', methods=['GET'])
def get_current_conversation():
    conversations = session.get('conversations', {})
    if not conversations:
        return jsonify({'error': 'No conversations'}), 404

    latest_id = max(conversations.keys(), key=lambda k: conversations[k]['last_updated'])
    return jsonify({
        'conversation_id': latest_id,
        'conversation': conversations[latest_id]
    })


@app.route('/api/delete_chat', methods=['POST'])
def delete_chat():
    conversation_id = request.get_json().get('conversation_id')
    if not conversation_id:
        return jsonify({'error': 'Missing conversation ID'}), 400

    conversations = session.get('conversations', {})
    if conversation_id in conversations:
        del conversations[conversation_id]
        session['conversations'] = conversations
        return jsonify({'status': 'success', 'message': 'Chat deleted'})

    return jsonify({'error': 'Conversation not found'}), 404


if __name__ == '__main__':
    ''''
    from pyngrok import ngrok, conf
    import subprocess

    # Kill existing ngrok process (optional for Windows)
    try:
        subprocess.call('taskkill /f /im ngrok.exe', shell=True)
    except Exception as e:
        print("Could not kill ngrok:", e)
    conf.get_default().auth_token = "30gB5vf0VhlQqksHptqvqbpcJCh_78GUSU1i1PyTvaZj9JUWy"
    # Start ngrok tunnel
    public_url = ngrok.connect(5001)
    print(" * ngrok tunnel:", public_url)
    '''
    #app.run(host="0.0.0.0", port=5001, debug=True)

    app.run(port=5001, debug=True)
