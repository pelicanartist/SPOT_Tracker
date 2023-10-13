#!/usr/bin/python

#####
# Script to retrieve location information from SPOT satelite tracker website and store offline
# Logs nearest available weather report from OpenWeather if possible.
#
# History:
# 1.1 added Darksky support
# 1.2 7/25/20 - Deprecated Darksky and replaced with OpenWeather API
#
#####

import sys, string, re, time, datetime, fileinput, urllib, getopt, json
import xml.etree.ElementTree as ET

start_time = datetime.datetime.now()

# Update these values with your information.
feed_id = "Your_Spot_Feed_ID"
Weather_api_key = 'Your_openweather_API_Key'

SPOT_URL = 'https://api.findmespot.com/spot-main-web/consumer/rest-api/2.0/public/feed/FEED_ID/message.xml'
#Weather_URL = 'https://api.darksky.net/forecast/WEATHER_API_KEY/LAT,LON'
Weather_URL = 'https://api.openweathermap.org/data/2.5/onecall?lat=LAT\&lon=LON\&appid=WEATHER_API_KEY'
Weather_URL = Weather_URL.replace('WEATHER_API_KEY', Weather_api_key)

testfile = "message.xml"
weatherfile = "test_weather.json"

# Create a new log file for each run
#f = open('spot_parsing.log','w')
# Append to the existing log for each run
f = open('spot_parsing.log','a')

diagnostic = 0
old_messages = []
new_lines = []

def localtime():
	return time.strftime("%H:%M:%S", time.localtime(time.time()))

def timestamp():
	print>>f, "+++ Timestamp: " +localtime() +" "+time.strftime("%B %d, %Y", time.localtime(time.time())) +" (" +str(	datetime.datetime.now() - start_time ) +")"

def unixtime_to_human(unixtime):
	return str(datetime.datetime.fromtimestamp(int(unixtime)).strftime('%Y-%m-%d %H:%M:%S'))
	
def clean_up():
	try:
		print>>f, "+++ Log entry ends " +localtime() +" "+time.strftime("%B %d, %Y", time.localtime(time.time())) +" (" +str(	datetime.datetime.now() - start_time ) +")\n"
		f.close()
	except:
		print "Error closing log file", sys.exc_info()[0]
	sys.exit()

def load_old_data():
	if (diagnostic > 0):
		print>>f, "Section: load_old_data"
	# Read in the previous location data to identify duplicate readings from API calls later.
	count = 0
	message_ids = []
	try: 
		count = 0
		with open('spot_data.csv') as o:
			for line in o:
				count = count + 1
				line_id = line.split(",")
				message_ids.append(line_id[0])
		print>>f, "    Loaded " +str(count) +" lines of old data."
		timestamp()
		return message_ids
	except: 
		print>>f, "*** Starting new data file, exception looking for old file: ", sys.exc_info()[0]
		try:
			o = open('spot_data.csv','w')
			print>>o, "message_id,messenger_id,messenger_name,message_localtime,message_localtime_text,message_type,message_lat,message_lon,message_model,message_custom,message_gmt,message_bat,message_hidden,message_alt,weather_reading_time,weather_summary,temperature,humidity,windspeed,windbearing"
			o.close()
		except:
			print>>f, "*** Problem creating data file: ", sys.exc_info()[0]
		return "0"
	
def isNewMessage(message_id):
	global old_messages
	count = 0
	for line in old_messages:
		if (line == message_id):
			count = count + 1
			if (diagnostic > 2):
				print>>f, "    " +line +" = " +message_id
		else:
			if (diagnostic > 2):
				print>>f, "    " +line +" =/= " +message_id
				
	if (diagnostic > 1):
		if (count > 0):
			print>>f, "    Rejecting message " +str(message_id) +" as a duplicate."
		else:
			print>>f, "    Message ID " +str(message_id) +" is a new message!"
	if (count == 0):
		return 1
	else: 
		return 0
			
def parse_weather(weather_data):
	if (diagnostic > 0):
			print>>f, "Section: parse_weather"
	try:
		raw_data = json.loads(weather_data)
		readingtime = raw_data['current']['dt']
		summary = raw_data['current']['weather.description']
		#neareststormdist = raw_data['current']['nearestStormDistance']
		#neareststormbearing = raw_data['current']['nearestStormBearing']
		temperature = raw_data['current']['temp']
		feels_like = raw_data['current']['feels_like']
		dewpoint = raw_data['current']['dew_point']
		humidity = raw_data['current']['humidity']
		pressure = raw_data['current']['pressure']
		windspeed = raw_data['current']['wind_speed']
		windgust = raw_data['current']['wind_gust']
		windbearing = raw_data['current']['wind_deg']
		cloudcover = raw_data['current']['clouds']
		uvindex = raw_data['current']['uvi']
		visibility = raw_data['current']['visibility']
		
		if (diagnostic > 3):
			print>>f, "    Observation time:", unixtime_to_human(readingtime)
			print>>f, "    Conditions:", summary
			print>>f, "    Temperature:", temperature, "F"
			print>>f, "    Humidity:", (humidity*100), "%"
			print>>f, "    Wind Speed:", windspeed, "MPH"
			print>>f, "    Direction:", windbearing
		
		local_weather = unixtime_to_human(readingtime), str(summary), str(temperature), str(humidity), str(windspeed), str(windbearing)
		
	except: 
		local_weather = str(unixtime_to_human(0)) +",no weather data available,,,,"
		print>>f, "*** parse_weather - Problem parsing weather data: ", sys.exc_info()[0]
	if (diagnostic > 0):
		print>>f, "    parse_weather returning:" +str(local_weather)
	return local_weather
	
def get_weather(lat, lon):
	if (diagnostic > 0):
		print>>f, "Section: get_weather"
		print>>f, "    Determining weather for ", str(lat), ",", str(lon)
	url = Weather_URL.replace('LAT', lat)
	url = url.replace('LON', lon)
	
	if (diagnostic == 2):
		print>>f, "    Opening static file ", weatherfile
		#print>>f, "    URL request would be ", url
		s = open(weatherfile,'r')
		weather_data = s.read()
		s.close()
		local_weather = parse_weather(weather_data)
		
	else:
		if (diagnostic > 0):
			print>>f, "    Retrieving URL: " +url
		weather_data = urllib.urlopen (url).read()	
		local_weather = parse_weather(weather_data)
		
	if (diagnostic > 0):
			print>>f, "    get_weather: returning", local_weather
			timestamp()
	return local_weather
	
def get_feed():
	if (diagnostic > 0):
			print>>f, "Section: get_feed"
	url = SPOT_URL.replace('FEED_ID', feed_id)
	
	if (diagnostic == 2):
		print>>f, "    Opening static file ", testfile
		#print>>f, "    Request URL would be ", url
		s = open(testfile,'r')
		spot_data = s.read()
		s.close()
		return spot_data
		
	else:
		if (diagnostic > 0):
			print>>f, "    Retrieving URL: " +url
		spot_data = urllib.urlopen (url).read()
		if (diagnostic > 0):
			print>>f, "    Recieved ", len(spot_data), " characters."
			timestamp()
		return spot_data

def parse_feed(feed):
	if (diagnostic > 0):
		print>>f, "Section: parse_feed"
	global new_lines
	tree = ET.fromstring(feed)
	newcount = 0
	dupecount = 0
	totalcount = 0
	for message in tree.iter('message'):
		totalcount = totalcount + 1
		if (diagnostic > 0):
			print>>f, "    Processing message #", str(totalcount)
		message_id = message.find('id').text
		messenger_id = message.find('messengerId').text
		messenger_name = message.find('messengerName').text
		message_localtime =  message.find('unixTime').text
		message_type =  message.find('messageType').text
		message_lat =  message.find('latitude').text
		message_lon =  message.find('longitude').text
		message_model = message.find('modelId').text
		message_custom = message.find('showCustomMsg').text
		message_gmt = message.find('dateTime').text
		message_bat = message.find('batteryState').text
		message_hidden = message.find('hidden').text
		message_alt = message.find('altitude').text
		
		if (isNewMessage(message_id) == 1):
			newcount = newcount + 1
			message_localtime_text = unixtime_to_human(message_localtime)
			local_weather = get_weather(message_lat, message_lon)
			logline = str(message_id) +"," +messenger_id +"," +messenger_name +"," +message_localtime +"," +message_localtime_text +"," +message_type +"," +message_lat +"," +message_lon +"," +message_model +"," +message_custom +"," +message_gmt +"," +message_bat +"," +message_hidden +"," +message_alt +"," +local_weather[0] +"," +local_weather[1] +"," +local_weather[2] +"," +local_weather[3] +"," +local_weather[4] +"," +local_weather[5]
			new_lines.append(logline)
			if (diagnostic > 0):
				print>>f, "    " +str(logline)
		else:
			dupecount = dupecount + 1
			if (diagnostic > 0):
				print>>f, "    Skipping duplicate message ", message_id
	
	
	print>>f, "    Parsed ", str(totalcount), " total messages:", newcount, "new, and ", dupecount, " previously recorded."
	if (diagnostic > 0):	
		timestamp()

def store_new():
	global new_lines
	try:
		o = open('spot_data.csv', 'a')
		for line in new_lines:
			print>>o, line
		o.close()
	except:
		print>>f, "*** Error writing data file:", sys.exc_info()[0]
		
def usage():
	usage = """
	-h --help			Print this message
	-l --loglevel={0-5}		Enable debug logging, default is """ +str(diagnostic) +"""
	-f --feed			Feed ID String
	
	Loglevel details: 		0 = Summary messages, no log file.
					1 = Summary messages, standard log file: spot_parsing.log.
					2 = Verbose logging
					3 = Debug logging
					
	"""
	print usage
	sys.exit()		

def primary():
	global old_messages
	print>>f, "+++ Log entry starts " +localtime() +" "+time.strftime("%B %d, %Y", time.localtime(time.time())) +" (" +str(	datetime.datetime.now() - start_time ) +")"
	print>>f, "Diagnostic Log Level = ", str(diagnostic)
	
	old_messages = load_old_data()
	feed_data = get_feed()
	parse_feed(feed_data)
	store_new()
	
	clean_up()
	
	
	
def main(argv):
	try:
		opts, args = getopt.getopt(sys.argv[1:], "hl:f:", ["help", "loglevel=", "feed="])
	except getopt.GetoptError, err:
		# print help information and exit:
		print str(err) # unrecognized option message
		usage()
		sys.exit(2)
	for o, a in opts:
		if o in ("-h", "--help"):
			usage()
		elif o in ("-l", "--loglevel"):
			global diagnostic
			diagnostic = a
			diagnostic = int(diagnostic)
		elif o in ("-f", "--feed"):
			global feed_id
			feed_id = a
		else:
			assert False, "unhandled option"
	primary()

if __name__ == "__main__":
	main(sys.argv[1:])

