docker container run --name options-server --network options-network -e PYTHONPATH=/options/src -v `pwd`:/options --rm -it --publish 8000:8000 --publish 8765:8765 options-image:latest \
  python server.py
