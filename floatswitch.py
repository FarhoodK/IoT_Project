class FloatSwitch:
    """Simulates a float switch sensor to monitor the remaining quantity."""
    
    def __init__(self):
        self.quantity = 100
        self.left_quantity = 100.0
        self.maintenance = "Not required"
        
    def read_quantity(self, ml):
        """
        Update the remaining quantity and return the updated value.
        Trigger maintenance warning if necessary.
        """
        erogated_qty = ((ml / 10) / self.quantity) * 100
        self.left_quantity -= erogated_qty
        self.maintenance = "Required" if self.left_quantity <= 10 else "Not required"
        return round(self.left_quantity, 2)
    