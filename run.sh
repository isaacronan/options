docker container run -e PYTHONPATH=/options/src -e ETRADE_KEY=$ETRADE_KEY -e ETRADE_SECRET=$ETRADE_SECRET -v `pwd`:/options --rm -it options-image:latest
