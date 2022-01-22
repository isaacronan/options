export CUR_DIR=`pwd`
docker container run -e PYTHONPATH=/options/src -e ETRADE_KEY=$ETRADE_KEY -e ETRADE_SECRET=$ETRADE_SECRET -v $CUR_DIR:/options --rm -it options-image:latest
