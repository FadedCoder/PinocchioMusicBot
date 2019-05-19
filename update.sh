#!/bin/bash
git pull
source venv/bin/activate
pip install -U youtube-dl
sudo systemctl restart pinocchio
