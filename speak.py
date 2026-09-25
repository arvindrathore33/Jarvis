import pyttsx3

engine = pyttsx3.init()
engine.setProperty('rate', 165)
engine.setProperty('volume', 0.9)

def speak(text):
    engine.say(text)
    engine.runAndWait()
