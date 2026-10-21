#!/bin/bash
set -e
# The single remaining blocker to training is data placement:
# run this on any unrestricted machine into data/, then python scripts/prepare_data.py
echo "Download competition data from https://www.drivendata.org/competitions/306/competition-doe-gems/data/ (requires login) to data/"
echo "Mirrors available via Dropbox (see README) if egress allows:"
echo " - existing_faults.tif https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&st=rnino7ya&dl=1"
echo " - example_submission.tif https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&st=8junzdyw&dl=1"
echo " - gems-geodawn-numerical-features.tif https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?rlkey=je8d8fepqfbst9lnwsq9rkplu&st=zj1lag1r&dl=1"
echo "After placing training_features.tif labels.tif sample_submission.tif 1m_DEM_links.csv into data/, run: python scripts/prepare_data.py"
