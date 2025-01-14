"Update the logic of the main.py file here in order to make it run with the RESTful Smartender class in the smartender_REST.py file"
import cherrypy
from smartender_REST import SmartenderREST

if __name__ == "__main__":
    cherrypy.config.update({
        'server.socket_host': '0.0.0.0',
        'server.socket_port': 8080,
        'log.screen': True
    })

    cherrypy.quickstart(SmartenderREST(), "/api", {"/": {"tools.json_out.on": True}})
