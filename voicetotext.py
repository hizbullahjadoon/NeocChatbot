import whisper

def transcribe(path):
    model = whisper.load_model("base")
    result = model.transcribe(path)

    return result["text"]

#result = transcribe("c:/Users/4303Sattar/Documents/Chatbot 4 CHANGING/uploads/audio_1.wav")
#print(result)
