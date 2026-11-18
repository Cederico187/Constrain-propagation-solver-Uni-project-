shell := /bin/bash

run:
	cd src && python3 csp_builder.py

visual:
	cd src && python3 visualizer.py