import cherrypy
from smartender import Smartender

class SmartenderAPI:
    """CherryPy RESTful API for Smartender."""

    def __init__(self, filename):
        self.smartender = Smartender(filename)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def index(self):
        """Return a welcome message."""
        return {"message": "Welcome to the Smartender API!"}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def show_cocktails(self):
        """Return available cocktails."""
        return {"available_cocktails": self.smartender.show_cocktails()}

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def configure(self):
        """Configure the Smartender with selected cocktails."""
        input_data = cherrypy.request.json
        cocktail_name = input_data.get("cocktail_name")
        if not cocktail_name:
            return {"status": "error", "message": "No cocktail name provided."}
        self.smartender.configure(cocktail_name)
        return {"status": "success", "message": f"{cocktail_name} configured successfully!"}

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def make(self):
        """Make a selected cocktail."""
        input_data = cherrypy.request.json
        cocktail_name = input_data.get("cocktail_name")
        if not cocktail_name:
            return {"status": "error", "message": "No cocktail name provided."}
        self.smartender.make_cocktail(cocktail_name)
        return {"status": "success", "message": f"{cocktail_name} is being prepared!"}

if __name__ == '__main__':
    cherrypy.config.update({'server.socket_port': 8080})
    cherrypy.quickstart(SmartenderAPI('cocktails.json'))