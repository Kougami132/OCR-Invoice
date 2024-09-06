class BoundingBox:
    def __init__(self, coordinates, label_info):
        self.coordinates = coordinates
        self.text, self.confidence = label_info
        self.left = self.coordinates[0][0]
        self.top = self.coordinates[0][1]
        self.right = self.coordinates[2][0]
        self.bottom = self.coordinates[2][1]