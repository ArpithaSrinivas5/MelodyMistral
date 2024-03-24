

import json
import os
from dotenv import load_dotenv
load_dotenv()
from IPython.display import display, Markdown

from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
import os
import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import streamlit as st

import requests

def get_current_weather(city, api_key=os.getenv("OPENWEATHER_API_KEY"), unit="metric"):
    """Get the current weather for a given city using OpenWeather API."""
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": api_key,
        "units": unit
    }
    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        data = response.json()
        #print(data)
        weather = {
            "location": data["name"],
            "temperature": int(data["main"]["temp"]),
            "rain": data["weather"][0]["main"],
            "unit": "Celsius" if unit == "metric" else "Fahrenheit"
        }
        return json.dumps(weather)
    else:
        return {"location": city, "temperature": "unknown", "unit": unit, "rain": "unknown"}

api_key = os.getenv("OPENWEATHER_API_KEY")

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
from IPython.display import Image, display, Audio

def search_song(song_name):
    # Set up your Spotify credentials
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

    # Authenticate with Spotify
    client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

    # Search for the song
    results = sp.search(q=song_name, limit=1, type='track')
    tracks = results['tracks']['items']

    # Display the first result
    if tracks:
        track = tracks[0]
        return json.dumps({
            "song": track['name'],
            "artist": ', '.join(artist['name'] for artist in track['artists']),
            "album": track['album']['name'],
            "album_cover_url": track['album']['images'][0]['url'],
            "preview_url": track['preview_url']
        })

    else:
        return "No song found"
    


available_tools = [
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "Get the current weather in a given location, use farhenheit",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The city to get the weather for",
                    },
                    "unit": {
                        "type": "string",
                        "description": "The unit to use for the temperature, metric is default",
                        "enum": ["metric", "imperial"],
                    }
                },
                "required": ["city", "unit"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_song",
            "description": "Search for a song on Spotify and display its details including the artist, album, album cover, and a preview link if available",
            "parameters": {
                "type": "object",
                "properties": {
                    "song_name": {
                        "type": "string",
                        "description": "The name of the song to search for",
                    }
                },
                "required": ["song_name"],
            }
        }
    }
]

names_to_functions = {
    'get_current_weather': get_current_weather,
    'search_song': search_song
}

client = MistralClient(api_key=api_key)


def get_weather(city):
    messages = [
        ChatMessage(role="user", content=f"What's the current weather in {city}?")
    ]

    model = "mistral-large-latest"
    api_key = os.getenv("MISTRAL_API_KEY")

    client = MistralClient(api_key=api_key)
    response = client.chat(model=model, messages=messages, tools=available_tools, tool_choice="auto")

    tool_call = response.choices[0].message.tool_calls[0]
    function_name = tool_call.function.name
    function_params = json.loads(tool_call.function.arguments)

    function_result = names_to_functions[function_name](**function_params)
    return json.loads(function_result)

def suggest_songs(weather_info):
    messages = [
        ChatMessage(role="system", content="A Song Suggestions Assistant based on local weather and language"),
        ChatMessage(role="user", content=f"""The current weather is {weather_info['temperature']} degrees {weather_info['unit']} with {weather_info['rain']} in {weather_info['location']}.
        Suggest 5 songs based on this weather and the local language.
        Return a json object with keys as song, artist, album, album_cover_url, preview_url and reason.
        Use the key 'song_suggestions' and provide the value as a list of json objects with keys song, artist, album, album_cover_url, preview_url and reason.""")
    ]

    model = "mistral-large-latest"
    api_key = os.getenv("MISTRAL_API_KEY")

    client = MistralClient(api_key=api_key)
    response = client.chat(model=model, messages=messages, tools=available_tools, tool_choice="auto")

    while response.choices[0].message.tool_calls:
        tool_call = response.choices[0].message.tool_calls[0]
        function_name = tool_call.function.name
        function_params = json.loads(tool_call.function.arguments)

        function_result = names_to_functions[function_name](**function_params)

        messages.append(ChatMessage(role="tool", name=function_name, content=function_result))
        response = client.chat(model=model, messages=messages, tools=available_tools, tool_choice="auto")

    return response


model = "mistral-large-latest"
api_key = os.getenv("MISTRAL_API_KEY")
client = MistralClient(api_key=api_key)



@st.cache_data
def generate_weather_music(city):
    messages = [
        {
            "role": "system",
            "content": "A Song Suggestions Assistant based on local weather in metric and local language"
        },
        {
            "role": "user",
            "content": f"""I am in {city}, suggest 5 songs based on their current weather and their local language
            and display their album details such as album cover, artist, and preview link.
            return a json object with keys as song, artist, album, album_cover_url, and preview_url and reason

            key as song_suggestions and value as a list of json objects with keys as song, artist, album, album_cover_url, preview_url, and reason
            """
        }
    ]
    tools = available_tools
    response = client.chat(
        model=model,
        messages=messages,
        tools=tools,
        tool_choice="any",

    )
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    if tool_calls:
        function_name = tool_calls[0].function.name
        function_args = json.loads(tool_calls[0].function.arguments)
        function_response = names_to_functions[function_name](**function_args)

        messages.append(response_message)
        messages.append(
            {
                "tool_call_id": tool_calls[0].id,
                "role": "tool",
                "name": function_name,
                "content": function_response,
            }
        )

        second_response = client.chat(
            model=model,
            messages=messages,
            tools=available_tools,
            tool_choice="any",
        )

        response_message = second_response.choices[0].message
        tool_calls = response_message.tool_calls

        if tool_calls:
            messages.append(response_message)
            for tool in tool_calls:
                function_name = tool.function.name
                function_args = json.loads(tool.function.arguments)
                function_response = names_to_functions[function_name](**function_args)

                messages.append(
                    {
                        "tool_call_id": tool.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
                    }
                )

            third_response = client.chat(
                model= model,
                messages=messages,
                response_format={"type":"json_object"}
            )

            return third_response


def main():
    st.title("MelodyMistral - Your AI DJ")
    city = st.text_input("Enter a city name")

    if st.button("Get Song Suggestions"):
        if city:
            result = generate_weather_music(city)
            song_suggestions_json = json.loads(result.choices[0].message.content)

            for song in song_suggestions_json["song_suggestions"]:
                st.markdown(f"### {song['song']}")
                st.markdown(f"**Artist:** {song['artist']}")
                st.markdown(f"**Album:** {song['album']}")
                st.image(song['album_cover_url'], width=200)
                st.markdown(f"[Preview the song]({song['preview_url']})")
                st.markdown(f"**Reason:** {song['reason']}")
                st.markdown("----")
        else:
            st.warning("Please enter a city name.")

if __name__ == "__main__":
    main()