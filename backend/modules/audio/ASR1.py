from openai import OpenAI

client = OpenAI(
    base_url="http://114.212.96.222:8009/v1",
    api_key="1"
)
audio_file= open("D:/User/Document/NJU Works/My Project/fast-vid-processor/2.mp3", "rb")

transcription = client.audio.transcriptions.create(
    model="large-v3", 
    file=audio_file
)

print(transcription.text)