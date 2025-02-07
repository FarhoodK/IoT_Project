import os
import cherrypy
import cherrypy._json
from cherrypy_cors import install as install_cors
from logger import Logger

class SmartenderAPI:
    def __init__(self, smartender_instance):
        self.smartender = smartender_instance
        self.current_order = None
        

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def cocktails(self):
        # Return list of available cocktails
        return [
            {
                'name': cocktail.name, 
                'ingredients': cocktail.ingredients, 
                'steps': cocktail.steps
            } for cocktail in self.smartender.available_cocktails
        ]

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def selected_cocktails(self):
        # Return list of selected cocktails
        return [
            {
                'name': cocktail.name, 
                'ingredients': cocktail.ingredients
            } for cocktail in self.smartender.selected_cocktails
        ]

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def select_cocktail(self):
        self.logger.info("Selecting cocktail for preparation")
        # Select a cocktail for preparation
        data = cherrypy.request.json
        cocktail_name = data.get('cocktail_name')
        
        if not cocktail_name:
            cherrypy.response.status = 400
            self.logger.error("Cocktail name is required")
            return {"error": "Cocktail name is required"}
        
        try:
            self.smartender.add_cocktail(cocktail_name)
            self.smartender.setup_pumps()
            return {"status": f"Cocktail {cocktail_name} selected successfully"}
        except Exception as e:
            self.logger.error(f"Error selecting cocktail: {e}")
            cherrypy.response.status = 500
            return {"error": str(e)}
    
    @cherrypy.expose
    @cherrypy.tools.json_out()
    def configure(self):
        # Trigger Smartender configuration for cocktail and pump setup
        try:
            # Call the configure method to allow user to select cocktails and set up pumps
            self.smartender.configure()
            return {"status": "Smartender configured successfully"}
        except Exception as e:
            cherrypy.response.status = 500
            return {"error": str(e)}
        
    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def configure_cocktails(self):
        # Configure Smartender pumps based on selected cocktails
        try:
            data = cherrypy.request.json
            selected_cocktails = data.get('cocktails', [])
        
            if not selected_cocktails:
                cherrypy.response.status = 400
                return {"error": "No cocktails selected"}

            # Pass the selected cocktails to the Smartender instance
            self.smartender.configure(selected_cocktails=selected_cocktails)

            return {"status": "Smartender pumps configured successfully with selected cocktails"}
        except Exception as e:
            cherrypy.response.status = 500
            return {"error": str(e)}

    @classmethod
    def run_server(cls, smartender_instance, host='0.0.0.0', port=8080):
        # Run the Smartender API server
        # Create instance and mount app
        api_instance = cls(smartender_instance)  # Pass the Smartender instance here
        
        # Install and enable CORS
        install_cors()
        cherrypy.config.update({
            'server.socket_host': host,
            'server.socket_port': port,
            'cors.expose.on': True,
        })
        
        # Mount the application
        cherrypy.tree.mount(api_instance, '/', {
            '/': {
                'tools.sessions.on': True,
                'tools.staticdir.root': os.path.abspath(os.getcwd()),
                'cors.expose.on': True,
            }
        })
        
        # Start the server
        cherrypy.engine.start()
        cherrypy.engine.block()