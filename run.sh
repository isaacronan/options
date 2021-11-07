. ./env.sh
export CUR_DIR=`pwd`
docker container run -e ETRADE_KEY=$ETRADE_KEY -e ETRADE_SECRET=$ETRADE_SECRET -v $CUR_DIR:/usr/src/app --rm -it options-image:latest
