"""Create a RESTful version of the Smartender class here using cherrypy"""
import cherrypy
import json
from smartender import Smartender

class SmartenderREST:
    def __init__(self):
        self.smartender = Smartender('cocktails.json')

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def cocktails(self):
        """Get a list of available cocktails."""
        return [{"name": cocktail.name} for cocktail in self.smartender.available_cocktails]

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @cherrypy.tools.json_in()
    def configure(self):
        """Configure the Smartender with selected cocktails."""
        data = cherrypy.request.json
        cocktail_names = data.get("cocktails", [])
        for name in cocktail_names:
            self.smartender.add_cocktail(name)
        self.smartender.setup_pumps()
        return {"status": "Smartender configured", "selected_cocktails": cocktail_names}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def pumps(self):
        """Get the status of all active pumps."""
        return [
            {
                "id": pump.id,
                "ingredient": pump.ingredient,
                "remaining_quantity": pump.float_switch.left_quantity,
                "maintenance_needed": pump.float_switch.maintenance,
                "configured_for": pump.cocktails
            }
            for pump in self.smartender.active_pumps
        ]

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @cherrypy.tools.json_in()
    def make_cocktail(self):
        """Prepare a cocktail."""
        data = cherrypy.request.json
        cocktail_name = data.get("name")
        if not cocktail_name:
            raise cherrypy.HTTPError(400, "Cocktail name is required.")

        self.smartender.make_cocktail(cocktail_name)
        return {"status": f"Cocktail '{cocktail_name}' prepared."}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @cherrypy.tools.json_in()
    def refill_pump(self):
        """Refill a specific pump."""
        data = cherrypy.request.json
        pump_id = data.get("pump_id")
        if pump_id is None:
            raise cherrypy.HTTPError(400, "Pump ID is required.")

        for pump in self.smartender.active_pumps:
            if pump.id == pump_id:
                pump.refill()
                return {"status": f"Pump {pump_id} refilled."}

        raise cherrypy.HTTPError(404, f"Pump with ID {pump_id} not found.")

if __name__ == "__main__":
    cherrypy.quickstart(SmartenderREST(), "/", {"/": {"tools.json_out.on": True}})