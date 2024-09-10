"""
app.py

Contents:
1. Configuration
2. Create a helper function
3. Define the main call handler
4. Write the transcription route

This code is a Flask-based application that handles incoming calls using Twilio's Voice API, with functionality for 
forwarding calls during work hours and taking voicemail outside of work hours. The app can also handle multiple languages 
for voicemail prompts and transcribe voicemails. The app supports multiple languages by using a country-specific greeting dictionary.
"""

from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)

"""
1. Configuration
Write a dictionary that stores different language responses for after-hours calls. The default greeting is in English, but if the call originates 
from Germany ("DE"), the app uses a German greeting.

"""
GREETINGS = {
    "_default": {
        "text": "Hi there! You are calling after my work hours. Please leave a message after the beep.",
        "language": "en-US",
        "voice": "Polly.Joey",
    },
    "DE": {
        "text": "Hallo! Sie rufen außerhalb meiner Arbeitszeiten an. Bitte hinterlassen Sie mir eine Nachricht nach dem Ton.",
        "language": "de-DE",
        "voice": "Polly.Hans",
    },
}

# Default values for environment variables
DEFAULT_UTC_OFFSET = 0
DEFAULT_WORK_WEEK_START = 1  # Monday
DEFAULT_WORK_WEEK_END = 5  # Friday
DEFAULT_WORK_HOUR_START = 8  # 8:00 AM
DEFAULT_WORK_HOUR_END = 18  # 6:59 PM

"""
2. Create a helper function
This function ensures that any incoming string data can be safely converted to an integer. If it fails, it returns the provided default value.
"""
def parse_integer(value, default):
    try:
        return int(value)
    except (ValueError, TypeError):
        return default
    
"""
3. Define the main call handler
This is the main function that handles the incoming phone call logic.
If it's within working hours, the call is forwarded to the specified phone number using response.dial().
If the call is outside working hours, the system plays a recorded message using response.say() and prompts the caller to leave a voicemail using 
response.record(). The voicemail is limited to 120 seconds, and transcription is enabled with a callback to the /transcription endpoint.

"""
@app.route("/handle_call", methods=["POST"])
def handle_call():
    # Parse environment variables and get the work hours and timezone
    phone_number_to_forward_to = "+19143601212"  # Replace with your Twilio phone number
    timezone_offset = parse_integer(request.form.get("TIMEZONE_OFFSET"), DEFAULT_UTC_OFFSET)
    work_week = {
        "start": parse_integer(request.form.get("WORK_WEEK_START"), DEFAULT_WORK_WEEK_START),
        "end": parse_integer(request.form.get("WORK_WEEK_END"), DEFAULT_WORK_WEEK_END),
    }
    work_hour = {
        "start": parse_integer(request.form.get("WORK_HOUR_START"), DEFAULT_WORK_HOUR_START),
        "end": parse_integer(request.form.get("WORK_HOUR_END"), DEFAULT_WORK_HOUR_END),
    }

    # Calculate the current day and time according to the timezone
    utc_time = datetime.utcnow()
    local_time = utc_time + timedelta(hours=timezone_offset)
    current_hour = local_time.hour
    current_day = local_time.isoweekday()  # Monday is 1, Sunday is 7

    # Check if there is a translated greeting for the caller's country
    from_country = request.form.get("FromCountry", "_default")
    translated_greeting = GREETINGS.get(from_country, GREETINGS["_default"])

    # Determine if it's a working day and working hour
    is_working_day = work_week["start"] <= current_day <= work_week["end"]
    is_working_hour = work_hour["start"] <= current_hour <= work_hour["end"]

    response = VoiceResponse()

    if is_working_day and is_working_hour:
        response.dial(phone_number_to_forward_to)
    else:
        response.say(
            translated_greeting["text"],
            voice=translated_greeting["voice"],
            language=translated_greeting["language"],
        )
        response.record(
            max_length=120,  # Maximum recording length in seconds
            transcribe=True,  # Enable transcription
            transcribe_callback="/transcription"
        )

    return Response(str(response), mimetype="application/xml")

"""
4. Write the transcription route
When a voicemail is recorded, Twilio sends the transcription to this endpoint. The transcription text is printed out, 
and the route responds with an empty 204 status (no content), indicating that the transcription was received successfully.
"""
@app.route("/transcription", methods=["POST"])
def transcription():
    # Handle the transcription of the voicemail
    transcription_text = request.form.get("TranscriptionText")
    print(f"Voicemail Transcription: {transcription_text}")
    return '', 204  # Respond with no content

if __name__ == "__main__":
    app.run(debug=True)
