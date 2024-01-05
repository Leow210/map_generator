from flask import Flask, render_template, send_file
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use the 'Agg' backend, which is suited for non-interactive environments
import matplotlib.pyplot as plt
from noise import pnoise2 #perlin noise
import io
import os

basedir = os.path.abspath(os.path.dirname(__file__))


#absolute path to templates
app = Flask(__name__, template_folder=os.path.join(basedir, '../templates'))

@app.route('/')
def index(): 
    return render_template('index.html')


@app.route('/generate_map')
def generate_map():
    #setup dimensions of map to create
    width = 600
    height = 400

    #create an empty array that will store the map data
    map_data = np.zeros((height, width))

    sea_level = 0.15 #create the sea level threshold
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



    #generate the map
    plt.figure(figsize=(10,6))
    plt.imshow(map_data, cmap = 'terrain')
    plt.colorbar()

    #save image to bytes buffer:
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return send_file(buf, mimetype='image/png')



if __name__ == '__main__':
    app.run(port=8000, debug=True)