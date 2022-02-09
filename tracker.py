import tweepy
import os
import requests
import time

from geopy.geocoders import Nominatim

def lambda_handler(event, context):

                ############## STEP ONE: OPENSKY API CALL - DETERMINE IF FLIGHT CAN BE TRACKED #############

    # Enter Hex-Code to identify the aircraft we want to track (ANY LETTERS MUST BE LOWERCASE)
    transponder_hex_code = '395d66&icao24=395d67&icao24=395d68&icao24=395d69' # Currently Set to the 4 planes in the BelugaXL Fleet

    # Send a GET request to OpenSky API to check if this aircraft is currently in-flight
    url = f"https://opensky-network.org/api/states/all?&icao24={transponder_hex_code}"
    response = requests.get(url).json()

    # If the Aircraft is not currently being tracked (ie: not in-flight), terminate this script
    if response['states'] == None:
        print("AIRCRAFT IS NOT CURRENTLY TRACKED")
        return None

    # If the Aircraft is in-flight, retrieve its GPS co-ordinates and other info
    else:
        plane_info = response['states'][0]
        plane_callsign = plane_info[1]
        plane_nationality = plane_info[2]
        altitude = plane_info[13]
        velocity = plane_info[9]
        longitude = plane_info[5]
        latitude = plane_info[6]

    # Use GeoPy to find the human-readable address of the GPS co-ordinates
        geolocator = Nominatim(user_agent="test")
        location = geolocator.reverse(f"{latitude}, {longitude}")
        # If an address cannot be found, GeoPy will return none. In this case we will just use the Lat/Long co-ordinates instead
        if location == None:
            location = f"Latitude: {latitude}, Longitude: {longitude}"

    # Compose the string of text we want to use in our Tweet
        text = f"BelugaXL {plane_callsign}is on the move!\n\nCurrent position: {location}.\n\nCruising at {altitude:,}m with an airspeed of {velocity}m/s\n #Beluga @Airbus" 
        
                ############# STEP TWO: GOOGLE STATIC MAPS API CALL TO GET MAP IMAGE OF PLANES LOCATION ###########

        # Call Google Static Maps API for map of plane's location
        key = os.environ.get("Google_Maps_API_Key")
        url = f"https://maps.googleapis.com/maps/api/staticmap?center={latitude},{longitude}&zoom=6&size=500x300&region=ie&markers=color:red%7C{latitude},{longitude}&key={key}"
        maps_response = requests.get(url)

        # Save map image so we can attach it to our tweet
        file = open("/tmp/map.png", "wb")
        file.write(maps_response.content)
        file.close()
        
                ############# STEP THREE: TWITTER API CALL TO PUBLISH TWEET #############

        # Retrieving Twitter authentication tokens from environment variables
        consumer_key = os.environ.get("Twitter_API_Key")
        consumer_secret = os.environ.get("Twitter_API_Key_Secret")
        access_token = os.environ.get("Twitter_Access_Token")
        access_token_secret = os.environ.get("Twitter_Secret_Access_Token")
        
        # Creating authentication object 
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)
        
        # Creating API object
        api = tweepy.API(auth)

        # Publishing our Tweet To @BelugaXLTracker Twitter Account
        new_tweet = text
        twitter_response = api.update_status_with_media(status=new_tweet, filename="/tmp/map.png", lat=latitude, long=longitude)
        
        # Print to logs
        print(f"Twitter API Response: {twitter_response}")
        print(f"Tweet Content: {new_tweet}")
        print(f"Event = {event}")
        print(f"Context = {context}")
        
        # Return statement to terminate Lambda function
        return None
