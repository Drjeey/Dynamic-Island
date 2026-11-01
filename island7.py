"""Starts Lumi Island. The app itself lives in the lumi/ package and the interface in ui/."""
from lumi.window import IslandController

if __name__ == '__main__':
    IslandController().start()
