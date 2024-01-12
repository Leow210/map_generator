from flask import Flask, render_template, send_file, request, jsonify
from flask_caching import Cache
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use the 'Agg' backend, which is suited for non-interactive environments
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from noise import pnoise2 #perlin noise
import io
import os
import random

basedir = os.path.abspath(os.path.dirname(__file__))


#absolute path to templates
app = Flask(__name__, template_folder=os.path.join(basedir, '../templates'))
cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache'}) #configure the cache

@app.route('/')
def index(): 
    return render_template('index.html')


@app.route('/generate_map')
def generate_map():
    #setup dimensions of map to create
    width = 600
    height = 400
    
    def generate_noise_map(width, height, scale, octaves, persistence, lacunarity):
         #create an empty array that will store the map data
        map_data = np.zeros((height, width))

        for y in range(height):
            for x in range(width):
                map_data[y][x] = pnoise2(x/scale, y/scale, octaves=octaves, persistence=persistence, lacunarity=lacunarity)
        return map_data

    #create an empty array that will store the map data
    map_data = np.zeros((height, width))

    sea_level = float(request.args.get('seaLevel', '0.15')) #create the sea level threshold from user input, deafault is 0.15
    coastline= 0.05 #controls the ruggedness/smoothness of the coast

    #fill in the map with perlin noise
    for y in range(height):
        for x  in range(width):

            elevation = pnoise2(x/100, y/100, octaves=10 , persistence=0.50, lacunarity=2.0) #primary elevation noise
            coast_noise =  pnoise2(x/50, y/50, octaves=1) * coastline  #secondary noise for coastlines
            map_data[y][x] = pnoise2(x/100, y/100)

            coast_threshold = sea_level - coastline

            #Adjust the elevation near sea level with additional coast noise - only if coast noise is higher than elevation
            if coast_threshold < elevation < sea_level + coast_noise:
                elevation += coast_noise

            if elevation < sea_level:
                map_data[y][x] = 0 #ocean

            else:
                map_data[y][x] = elevation #land

    #Generate noise maps for temperature and moisture to create biomes
    temperature_map = generate_noise_map(width, height, 100, 6, 0.5, 2.0)
    moisture_map = generate_noise_map(width, height, 150, 6, 0.5, 2.0)

    #create definitions for the different biomes based on temperature and moisture
    def get_biome(temperature, moisture):
        if temperature < -0.05:
            return 'Tundra'
        elif moisture < -0.1:
            return 'Desert'
        elif moisture < 0.1:
            return 'Grassland'
        else:
            return 'Forest'

    #assign biomes
    biome_map = np.zeros((height, width), dtype=object)
    for y in range(height):
        for x in range(width):
            if map_data[y][x] <= sea_level:
                biome_map[y][x] = 'Ocean'
            else:
                temp = temperature_map[y][x]
                moist = moisture_map[y][x]
                biome_map[y][x] = get_biome(temp, moist)

    #define the biome colors
    biome_colors = {
        'Ocean': 'blue',
        'Tundra': 'white',
        'Desert': 'yellow',
        'Grassland': 'lightgreen',
        'Forest': 'green',
    }

    color_map = np.zeros((height, width, 3))
    for y in range(height):
        for x in range(width):
            biome = biome_map[y][x]
            color_map[y][x] = matplotlib.colors.to_rgb(biome_colors[biome])
    
    #cache the maps for later retrieval from outside functions
    cache.set("temperature_map", temperature_map)
    cache.set("biome_map", biome_map)
    cache.set("moisture_map", moisture_map)
    cache.set("map_data", map_data)





    #generate the map
    plt.figure(figsize=(10,6))
    plt.imshow(color_map)
    plt.axis('off')
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)


    #save image to bytes buffer:
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return send_file(buf, mimetype='image/png')

@app.route('/get_location_data')
def get_location_data():
    x = int(request.args.get('x', '0')) #gets the x coordinate from user hover.
    y = int(request.args.get('y', '0'))

    temperature_map = cache.get("temperature_map")
    biome_map = cache.get("biome_map")
    moisture_map = cache.get("moisture_map")
    map_data = cache.get("map_data")




    temp = temperature_map[y][x]
    moist = moisture_map[y][x]
    elevation = map_data[y][x]
    biome = biome_map[y][x]

    data = {
        'temp': temp,
        'moist': moist,
        'elevation': elevation,
        'biome': biome
    }

    return jsonify(data)

if __name__ == '__main__':
    app.run(port=8000, debug=True)