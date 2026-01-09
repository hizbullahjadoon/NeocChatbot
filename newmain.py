from allclassesgood import Chroma
from uuid import uuid4
import os
from voicetotext import transcribe
import io
import base64
from LLM import get_result

def newfunc(user_text, action, mode, chat_history, files=None, path=None):
    text = ""
    chroma = Chroma(mode= mode)
    if action == "insert":
        print("Files in insert: ", files)
        chroma.files = files
        chroma.insert_docs()
    elif action == "search":
        print("User Text: ",user_text)
        context, ref = chroma.search_documents(user_text)
        text = chroma.call_llm(context, user_text, chat_history, ref)
        with open("policy brief.txt", "w", encoding="utf-8") as file:
            file.write(text)
            return text
    elif action == "audio":
        
        filename = f"audio_{uuid4()}.wav"
        filenamecopy = filename
        filepath = os.path.join("uploads", filename)
        os.makedirs("uploads", exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(user_text)
        user_message = transcribe(filepath)
        
        return user_message
    elif action == "image":
<<<<<<< HEAD
        summary = get_result().llama_summarize(text = user_text)
=======
        summary = get_result().stable_text_summary(text = user_text)
>>>>>>> b30afc49309a8d088f1f253449f12af7b5102fe2
        print("Summary: ", summary)
        image = get_result().call_stable_diffusion(summary)
        buf = io.BytesIO()
        image.save(buf, format='PNG')
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read()).decode('utf-8')
        
        return image_base64
    
    else:
        return text
