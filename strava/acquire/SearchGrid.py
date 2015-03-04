#lat/lon grid class
import math, os, json, urllib, urllib2, StringIO, simplekml
earthRad = 40075000/2*math.pi #radius of earth in meters

########################### Google Maps Address Search ################################
def get_address_coordinates(address):
    #print address
    #define Google Maps API URL parameters
    urlparams = {
        'address': address,
        'sensor': 'false',
    }
    url = 'http://maps.google.com/maps/api/geocode/json?' + urllib.urlencode(urlparams)
    #print url
    response = urllib2.urlopen(url)
    responsebody = response.read()

    body = StringIO.StringIO(responsebody)
    #print body
    result = json.load(body) #load the JSON data into a dictionary

    if 'status' not in result or result['status'] != 'OK':
        return None
    else:
        return {
            'sw.lat': result['results'][0]['geometry']['bounds']['southwest']['lat'],
            'sw.lng': result['results'][0]['geometry']['bounds']['southwest']['lng'],
            'ne.lat': result['results'][0]['geometry']['bounds']['northeast']['lat'],
            'ne.lng': result['results'][0]['geometry']['bounds']['northeast']['lng']
        }

############################ Lat/Lon formulas ########################################
def dist_lat_lon(latCoord1, lonCoord1, latCoord2, lonCoord2):
    # Distance between two points, (lat1,lon1) and (lat2,lon2)
    distance = 0 #reset the distance calculation
    latRad1 = math.radians(latCoord1) #convert the first latitude to radians
    lonRad1 = math.radians(lonCoord1) #convert the first longitude to radians
    latRad2 = math.radians(latCoord2) #convert the second latitude to radians
    lonRad2 = math.radians(lonCoord2) #convert the second longitude to radians
    distance = earthRad * math.atan2(math.sqrt((math.cos(latRad2)*math.sin(lonRad1 - lonRad2))**2+(math.cos(latRad1)*math.sin(latRad2)-math.sin(latRad1)*math.cos(latRad2)*math.cos(lonRad1-lonRad2))**2),(math.sin(latRad2)*math .sin(latRad1)+math.cos(latRad1)*math.cos(latRad2)*math.cos(lonRad1-lonRad2)))
    return distance

def lat_lon_from_point_and_bearing(lat,lon,angle,dist):
    #returns a lat/lon pair that is dist NM from given lat/lon at the given angle bearing
    lat2  = math.degrees(math.asin(math.sin(math.radians(lat))*math.cos(dist/earthRad) + math.cos(math.radians(lat))*math.sin(dist/earthRad)*math.cos(math.radians(angle))))
    lon2 = lon + math.degrees(math.atan2(math.sin(math.radians(angle))*math.sin(dist/earthRad)*math.cos(math.radians(lat)),math.cos(dist/earthRad) - math.sin(math.radians(lat))*math.sin(math.radians(lat2))))
    return lat2, lon2

def bearing_from_two_lat_lons(lat1,lon1,lat2,lon2):
    x = math.sin(math.radians(lon2)-math.radians(lon1))*math.cos(math.radians(lat2))
    y = math.cos(math.radians(lat1))*math.sin(math.radians(lat2)) - math.sin(math.radians(lat1))*math.cos(math.radians(lat2))*math.cos(math.radians(lon2)-math.radians(lon1))
    return (math.degrees(math.atan2(x,y))+360)%360

def find_midpoint_between_lat_lons(lat1,lon1,lat2,lon2):
    return lat_lon_from_point_and_bearing(lat1,lon1,bearing_from_two_lat_lons(lat1,lon1,lat2,lon2),dist_lat_lon(lat1,lon1,lat2,lon2)/2)
########################################################################################


class SearchGrid():
    #defines the address search grid
    def __init__(self,zipCode=00000,resolution=5000):
        self.zipCode = zipCode
        self.resolution = resolution #resolution of the grid squares (in meters)
        self.googleBB = get_address_coordinates(zipCode) #Google Maps API returned bounding coordinates of zip code
        #characteristics of the grid
        self.diagonal_dist = dist_lat_lon(self.googleBB['sw.lat'],self.googleBB['sw.lng'],self.googleBB['ne.lat'],self.googleBB['ne.lng']) #distance of diagonal between bounding coordinates
        self.diagonal_bearing = bearing_from_two_lat_lons(self.googleBB['sw.lat'],self.googleBB['sw.lng'],self.googleBB['ne.lat'],self.googleBB['ne.lng']) #bearing between bounding coordinates
        self.side_length = math.sqrt((self.diagonal_dist**2)/2) #width of bounding box (KM)
        #other bounding points of the box
        nw_lat,nw_lng = lat_lon_from_point_and_bearing(self.googleBB['sw.lat'],self.googleBB['sw.lng'],self.diagonal_bearing - 45,self.side_length)
        se_lat,se_lng = lat_lon_from_point_and_bearing(self.googleBB['sw.lat'],self.googleBB['sw.lng'],self.diagonal_bearing + 45,self.side_length)

        #dictionary defining the points of the entire bounding box
        self.bounding_box = {
            'sw.lat': self.googleBB['sw.lat'],
            'sw.lng': self.googleBB['sw.lng'],
            'se.lat': se_lat,
            'se.lng': se_lng,
            'nw.lat': nw_lat,
            'nw.lng': nw_lng,
            'ne.lat': self.googleBB['ne.lat'],
            'ne.lng': self.googleBB['ne.lng']
            }

    def bounding_box_kml(self):
        #Creates a Google Earth KML of the address bounding-box
        kml = simplekml.Kml()
        coords = [
                (self.bounding_box['se.lng'],self.bounding_box['se.lat']),
                (self.bounding_box['sw.lng'],self.bounding_box['sw.lat']),
                (self.bounding_box['nw.lng'],self.bounding_box['nw.lat']),
                (self.bounding_box['ne.lng'],self.bounding_box['ne.lat']),
                (self.bounding_box['se.lng'],self.bounding_box['se.lat'])
                ]
        kml.newlinestring(name='bouding_box', description='bounding box',
                                coords=coords)
        kml.save(os.getcwd() + "\\bb_" + str(self.zipCode) + ".kml")

    def grid_walk(self):
        #generator function for grid points
        #need to make more robust for crossing hemispheres
        steps = int(self.side_length/self.resolution) + 1 #number of grid squares per side (+ 1 provides a little overlap for completeness)

        lat,lng = self.bounding_box['sw.lat'],self.bounding_box['sw.lng'] #start the walk at the southwest corner
        lat1,lng1 = lat,lng #sw point of grid square
        for i in range(steps):
            for j in range(steps):
                lat2,lng2 = lat_lon_from_point_and_bearing(lat1,lng1,self.diagonal_bearing, math.sqrt(2 * self.resolution**2)) #ne point of grid square
                center_lat,center_lng = lat_lon_from_point_and_bearing(lat1,lng1,self.diagonal_bearing, math.sqrt(2 * self.resolution**2)/2) #center point of grid square
                grid_square = {
                    'sw.lat': lat1,
                    'sw.lng': lng1,
                    'ne.lat': lat2,
                    'ne.lng': lng2,
                    'center.lat': center_lat,
                    'center.lng': center_lng
                    }
                yield grid_square
                lat1,lng1 = lat_lon_from_point_and_bearing(lat1,lng1,self.diagonal_bearing + 45, self.resolution) #move <resolution> meters to the east
            lat,lng = lat_lon_from_point_and_bearing(lat,lng,self.diagonal_bearing - 45, self.resolution) #move starting point og grid walk <resolution> meters north
            lat1,lng1 = lat,lng #reset lat1, lng1

    def print_grid(self):
        #prints the grid walk
        walk = self.grid_walk()
        try:
            while True:
                print walk.next()
        except StopIteration:
            pass

    def grid_kml(self):
        #creates a Google Earth KML file of the grid points
        walk = self.grid_walk()
        kml = simplekml.Kml()
        index = 0
        try:
            while True:
                index+=1
                points = walk.next()

                coords = [(points['sw.lng'],points['sw.lat'])]
                pnt = kml.newpoint(name='', coords=coords)
                pnt.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png'

                coords = [(points['center.lng'],points['center.lat'])]
                pnt = kml.newpoint(name='', coords=coords)
                pnt.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png'

                coords = [(points['ne.lng'],points['ne.lat'])]
                pnt = kml.newpoint(name='', coords=coords)
                pnt.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png'
        except StopIteration:
            pass
        kml.save(os.getcwd() + "\\grid_" + str(self.zipCode) + "_" + str(self.resolution) + "_meters.kml")


grid = SearchGrid(95051,5000)
grid.bounding_box_kml()
grid.grid_kml()




