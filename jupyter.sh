docker container run --name options-jupyter --network options-network -e PYTHONPATH=/options/src -e ETRADE_KEY=$ETRADE_KEY -e ETRADE_SECRET=$ETRADE_SECRET -v `pwd`:/options --rm -it --publish 8088:8088 options-image:latest \
  jupyter notebook --allow-root --ip 0.0.0.0 --port 8088 --notebook-dir notebooks
