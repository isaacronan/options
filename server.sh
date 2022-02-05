docker container run --name options-server --network options-network -e PYTHONPATH=/options/src -e ETRADE_KEY=$ETRADE_KEY -e ETRADE_SECRET=$ETRADE_SECRET -v `pwd`:/options --rm -it --publish 8000:8000 --publish 8765:8765 options-image:latest \
  /bin/bash -c 'python websocket_server.py > /dev/null 2>&1 & python -m http.server -d web > /dev/null 2>&1'
