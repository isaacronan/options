export CUR_DIR=`pwd`
docker run -e ETRADE_KEY=$ETRADE_KEY -e ETRADE_SECRET=$ETRADE_SECRET -v $CUR_DIR:/usr/src/app --rm -it --publish 8088:8088 options-image:latest jupyter notebook --allow-root --ip 0.0.0.0 --port 8088 --notebook-dir notebooks
