# Plane_Tracker_TwitterBot

# Overview

This project is a Twitter Bot which automatically checks if a specified aircraft is transmitting flight data (i.e., it checks if the aircraft is currently in-flight). If the aircraft is transmitting flight data, the bot will tweet the current location, altitude and airspeed of the aircraft. Also included in the tweet is a map image with a marker showing the plane's current location. The map image is retrieved from the Google Static Maps API. The source code for the bot is written entirely in Python and hosted as an AWS Lambda function which is invoked every 30 minutes.

### This project utilises the following APIs / Services / Libraries:
  1. [AWS Lambda](https://aws.amazon.com/lambda/) -> AWS Service which executes the Bot script every 30 minutes
  2. [OpenSky Network API](https://opensky-network.org/apidoc/) -> Flight Tracking API which provides data from aircraft transponders
  3. [Google Maps API](https://developers.google.com/maps/documentation/maps-static/overview) -> Maps API which takes GPS co-ordinates of the aircraft and returns a static map image
  4. [Twitter API](https://developer.twitter.com/en/docs/twitter-api) -> API which allows the bot to tweet programatically
  5. [GeoPy](https://geopy.readthedocs.io/en/stable/) -> Python Library which can convert GPS co-ordinates into a human readable address
  6. [Tweepy](https://www.tweepy.org/) -> Python Library which simplifies use of the Twitter API

# How It Works

## Step One: Determine if aircraft is currently in-flight
First, the bot sends a request to OpenSky Network API to determine if the specified aircraft is currently transmitting flight data. If the aircraft is not transmitting flight data, we know that it is not in-flight, and therefore the program is terminated.
```
# Enter Hex-Code to identify the aircraft we want to track (ANY LETTERS MUST BE LOWERCASE)
transponder_hex_code = '395d66&icao24=395d67&icao24=395d68&icao24=395d69' # Currently Set to the 4 planes in the BelugaXL Fleet

# Send a GET request to OpenSky API to check if this aircraft is currently in-flight
url = f"https://opensky-network.org/api/states/all?&icao24={transponder_hex_code}"
response = requests.get(url).json()

# If the Aircraft is not currently being tracked (ie: not in-flight), terminate this script
if response['states'] == None:
    print("AIRCRAFT IS NOT CURRENTLY TRACKED")
    return None
```
If OpenSky Network does return flight data, the program will parse the response and extract the relevant data-points (altitude/speed/GPS co-ordinates). The GPS co-ordinates are then passed to the Geopy `reverse()` method which returns a human-readable address. Using all of the aforementioned data, the text content of our tweet is composed.
```
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
```

## Step Two: Retrieve map of aircraft's location from Google Static Maps API
Next, the bot makes a request to Google Static Maps API. The request URL is dynamically constructed using the GPS co-ordinates retrieved from OpenSky Network. Google Maps Static API responds with a map image of the aircraft's location. This image is stored in the /tmp directory of the AWS Lambda virtual server.

```
        # Call Google Static Maps API for map of plane's location
        key = os.environ.get("Google_Maps_API_Key")
        url = f"https://maps.googleapis.com/maps/api/staticmap?center={latitude},{longitude}&zoom=6&size=500x300&region=ie&markers=color:red%7C{latitude},{longitude}&key={key}"
        maps_response = requests.get(url)

        # Save map image so we can attach it to our tweet
        file = open("/tmp/map.png", "wb")
        file.write(maps_response.content)
        file.close()
```

## Step Three: Compose and publish Tweet
Finally, the program connects to the Twitter bot account, completes authentication and publishes the tweet, including the map image which was saved previously. Information about the Lambda invocation and the various API responses are printed to AWS Cloudwatch logs.

```
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
```

